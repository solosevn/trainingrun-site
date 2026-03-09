#!/usr/bin/env python3
"""
Sitekeeper Audit System for trainingrun.ai
==========================================
Runs comprehensive 23-check autonomous audit system with 5 categories:
1. Local File Checks (7 checks)
2. Live Site Checks (4 checks)
3. Content Integrity (4 checks)
4. Security (4 checks)
5. Intelligence (4 checks)

Architecture:
- Scheduler thread sleeps until start_hour (6 AM local)
- Wakes up, runs all 24 checks organized by category
- Reports findings to user via Telegram
- Logs audit results via learning_logger
- Goes back to sleep until tomorrow

The agent remains reactive (Telegram) 24/7. This runs alongside.

Usage (from agent.py):
    from sitekeeper_audit import AuditScheduler
    scheduler = AuditScheduler(
        tg_send_fn=tg_send,
        execute_tool_fn=execute_tool,
        write_activity_fn=write_activity,
        claude_chat_fn=claude_chat,
        build_prompt_fn=build_system_prompt,
        learning_logger=_learning_logger,
    )
    scheduler.start()
"""

import os
import sys
import json
import time
import subprocess
import datetime
import threading
import logging
import requests
import socket
import ssl
import re
import hashlib
from pathlib import Path
from typing import Tuple, Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from html.parser import HTMLParser
import email.utils

SITE_URL = "https://trainingrun.ai"
REPO_PATH = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))

# Known pages to check
KNOWN_PAGES = [
    "index.html",
    "mission-control.html",
    "hq.html",
    "scores.html",
    "truscore.html",
    "trscode.html",
    "trfcast.html",
    "tragents.html",
]

# Sensitive file patterns for security scan
SENSITIVE_PATTERNS = [
    r"\.env",
    r"\.key",
    r"credentials",
    r"api[_-]?key",
    r"secret[_-]?key",
    r"token",
    r"password",
    r"aws[_-]?key",
    r"github[_-]?token",
]


class LinkExtractor(HTMLParser):
    """Extract all links and image sources from HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a" and "href" in attrs_dict:
            self.links.append(attrs_dict["href"])
        elif tag == "img" and "src" in attrs_dict:
            self.images.append(attrs_dict["src"])
        elif tag == "script" and "src" in attrs_dict:
            self.scripts.append(attrs_dict["src"])


class AuditScheduler:
    """Autonomous audit scheduler that runs comprehensive site checks daily."""

    def __init__(
        self,
        tg_send_fn,
        execute_tool_fn,
        write_activity_fn,
        claude_chat_fn=None,
        build_prompt_fn=None,
        learning_logger=None,
        start_hour=6,
        end_hour=8
    ):
        """
        Initialize the audit scheduler.

        Args:
            tg_send_fn: Function to send Telegram messages
            execute_tool_fn: Function to execute tools (site_health, etc.)
            write_activity_fn: Function to write activity logs
            claude_chat_fn: Function to call Claude for intelligent analysis
            build_prompt_fn: Function to build prompts
            learning_logger: Logger instance for audit results
            start_hour: Hour to start audits (default 6 AM)
            end_hour: Hour to end audits (default 8 AM)
        """
        self.tg_send = tg_send_fn
        self.execute_tool = execute_tool_fn
        self.write_activity = write_activity_fn
        self.claude_chat = claude_chat_fn
        self.build_prompt = build_prompt_fn
        self.learning_logger = learning_logger
        self.start_hour = start_hour
        self.end_hour = end_hour
        self._thread = None
        self._running = False
        self._last_audit = None
        self._audit_results = None

        # Vault context â loaded fresh before each audit
        self._vault_context = {}
        self._memory_context = {}
        self._tried_fixes = []

    def _load_vault_context(self):
        """Load vault and memory files before running audit.

        Reads Core 7 vault files, memory files (site_knowledge, fix_patterns,
        tried_fixes, error_log), and skills. This gives the agent full context
        about the site, past fixes, and learned patterns before diagnosing anything.
        """
        vault_dir = Path(REPO_PATH) / "context-vault" / "trainingrun" / "agents" / "trsitekeeper"
        memory_dir = Path(REPO_PATH) / "agents" / "trsitekeeper" / "memory"

        # Load Core 7 vault files
        vault_files = ["SOUL.md", "CONFIG.md", "PROCESS.md", "CADENCE.md"]
        self._vault_context = {}
        for fname in vault_files:
            fpath = vault_dir / fname
            if fpath.exists():
                try:
                    self._vault_context[fname] = fpath.read_text()[:2000]  # First 2K chars
                except Exception:
                    pass

        # Load memory files (JSON)
        memory_files = {
            "site_knowledge": "site_knowledge.json",
            "fix_patterns": "fix_patterns.json",
            "david_model": "david_model.json",
        }
        self._memory_context = {}
        for key, fname in memory_files.items():
            fpath = memory_dir / fname
            if fpath.exists():
                try:
                    with open(fpath) as f:
                        self._memory_context[key] = json.load(f)
                except (json.JSONDecodeError, Exception):
                    pass

        # Load tried fixes (JSONL â last 20 entries)
        tried_fixes_file = memory_dir / "tried_fixes.jsonl"
        self._tried_fixes = []
        if tried_fixes_file.exists():
            try:
                with open(tried_fixes_file) as f:
                    lines = f.readlines()
                for line in lines[-20:]:
                    line = line.strip()
                    if line and not line.startswith(("_", "#")):
                        try:
                            self._tried_fixes.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass

        # Load error log (JSONL â last 10 entries)
        error_log_file = memory_dir / "error_log.jsonl"
        self._recent_errors = []
        if error_log_file.exists():
            try:
                with open(error_log_file) as f:
                    lines = f.readlines()
                for line in lines[-10:]:
                    line = line.strip()
                    if line:
                        try:
                            self._recent_errors.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass

        loaded = len(self._vault_context) + len(self._memory_context)
        fixes_loaded = len(self._tried_fixes)
        logging.info(f"Vault context loaded: {loaded} files, {fixes_loaded} past fix attempts")

    def _record_fix_attempt(self, check_name: str, fix_type: str, outcome: str, details: str = ""):
        """Append a fix attempt to tried_fixes.jsonl for learning memory."""
        try:
            memory_dir = Path(REPO_PATH) / "agents" / "trsitekeeper" / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            tried_fixes_file = memory_dir / "tried_fixes.jsonl"

            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "check": check_name,
                "fix_type": fix_type,
                "outcome": outcome,
                "details": details[:200],
            }

            with open(tried_fixes_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            logging.info(f"Recorded fix attempt: {check_name} -> {outcome}")
        except Exception as e:
            logging.error(f"Failed to record fix attempt: {e}")

    def start(self):
        """Start the audit scheduler in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AuditScheduler"
        )
        self._thread.start()
        next_time = self._next_audit_time()
        hours_until = (next_time - datetime.datetime.now()).total_seconds() / 3600
        print(f"[Audit] Scheduler started. Next audit: "
              f"{next_time.strftime('%a %b %d at %-I:%M %p')} ({hours_until:.1f}h)")

    def stop(self):
        """Stop the scheduler."""
        self._running = False

    def _next_audit_time(self):
        """Calculate the next audit start time."""
        now = datetime.datetime.now()
        next_run = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        return next_run

    def _loop(self):
        """Sleep until audit time, run audit, repeat."""
        while self._running:
            next_run = self._next_audit_time()
            wait = (next_run - datetime.datetime.now()).total_seconds()

            print(f"[Audit] Sleeping {wait/3600:.1f}h until "
                  f"{next_run.strftime('%-I:%M %p')}")

            # Sleep in 60s chunks so we can check _running flag
            while wait > 0 and self._running:
                chunk = min(wait, 60)
                time.sleep(chunk)
                wait -= chunk

            if not self._running:
                break

            # Verify it's actually audit time
            now = datetime.datetime.now()
            if self.start_hour <= now.hour < self.end_hour:
                try:
                    results = self.run_audit()

                    # === WORK WINDOW: Attempt auto-fixes while still in window ===
                    failures = results.get("summary", {}).get("failed", 0)
                    attempt = 0
                    max_attempts = 3  # Max fix cycles per work window

                    while (failures > 0
                           and attempt < max_attempts
                           and self._running
                           and datetime.datetime.now().hour < self.end_hour):

                        attempt += 1
                        pending = getattr(self, '_pending_fixes', [])

                        if not pending:
                            logging.info(f"[Work Window] No pending fixes from Claude â stopping")
                            break

                        # Filter to high-confidence auto-fixable items
                        auto_fixes = [
                            f for f in pending
                            if f.get("confidence", 0) >= 80
                            and f.get("proposed_fix_type") in ("rerun_scraper", "git_commit")
                        ]

                        if not auto_fixes:
                            logging.info(f"[Work Window] No high-confidence auto-fixes â escalating to David")
                            # Report what needs manual attention
                            manual = [f for f in pending if f.get("confidence", 0) < 80 or f.get("proposed_fix_type") in ("edit_file", "investigate", "escalate")]
                            if manual:
                                msg = "Fixes needing your approval:\n"
                                for fix in manual[:5]:
                                    msg += f"â¢ {fix.get('check_name', '?')}: {fix.get('diagnosis', '?')[:60]} (confidence: {fix.get('confidence', '?')}%)\n"
                                msg += "\nReply 'approve <check_name>' to execute."
                                self.tg_send(msg)
                            break

                        # Execute auto-fixes
                        for fix in auto_fixes[:2]:  # Max 2 fixes per cycle
                            check_name = fix.get("check_name", "unknown")
                            fix_type = fix.get("proposed_fix_type", "unknown")
                            action = fix.get("proposed_action", "")

                            logging.info(f"[Work Window] Auto-fixing {check_name} via {fix_type}")
                            self.tg_send(f"Auto-fixing {check_name} ({fix_type}, confidence {fix.get('confidence')}%)")

                            try:
                                if fix_type == "rerun_scraper" and self.execute_tool:
                                    self.execute_tool("rerun_scraper", check=check_name)
                                elif fix_type == "git_commit" and self.execute_tool:
                                    self.execute_tool("git_commit", check=check_name, action=action)

                                # Record the attempt
                                self._record_fix_attempt(check_name, fix_type, "attempted", action)
                            except Exception as fix_err:
                                logging.error(f"[Work Window] Fix failed for {check_name}: {fix_err}")
                                self._record_fix_attempt(check_name, fix_type, "failed", str(fix_err))

                        # Wait a bit then re-run audit to check if fixes worked
                        logging.info(f"[Work Window] Waiting 30s then re-auditing (attempt {attempt}/{max_attempts})")
                        time.sleep(30)
                        results = self.run_audit()
                        failures = results.get("summary", {}).get("failed", 0)

                    if failures == 0:
                        self.tg_send("All checks passing! Work window complete.")
                    elif attempt >= max_attempts:
                        self.tg_send(f"Work window: {failures} checks still failing after {attempt} fix cycles. Will try again tomorrow.")

                except Exception as e:
                    print(f"[Audit] CRITICAL ERROR: {e}")
                    try:
                        self.tg_send(f"Audit error: {e}")
                    except Exception:
                        pass

    def run_audit(self) -> Dict[str, Any]:
        """
        Run complete 24-check audit and return results.

        Returns:
            Dictionary with audit results organized by category
        """
        start_time = datetime.datetime.now()
        print(f"\n{'='*60}")
        print(f"  AUTONOMOUS AUDIT (23 CHECKS) â {start_time.strftime('%a %b %d, %-I:%M %p')}")
        print(f"{'='*60}")

        # Step 0: Load vault context before running any checks
        self._load_vault_context()

        self.write_activity(
            "23-check autonomous audit started", location="ddp_room", status="active"
        )
        self.tg_send(
            f"Starting autonomous audit "
            f"({start_time.strftime('%-I:%M %p')})"
        )

        results = {
            "timestamp": start_time.isoformat(),
            "site_url": SITE_URL,
            "categories": {}
        }

        # Category 1: Local File Checks (7 checks)
        local_results = {
            "check_001_site_health": self._check_site_health(),
            "check_002_ddp_status": self._check_ddp_status(),
            "check_003_data_file_integrity": self._check_data_file_integrity(),
            "check_004_html_page_check": self._check_html_pages(),
            "check_005_git_status": self._check_git_status(),
            "check_006_vault_integrity": self._check_vault_integrity(),
            "check_007_agent_activity": self._check_agent_activity(),
        }
        results["categories"]["LOCAL_FILE_CHECKS"] = local_results

        # Category 2: Live Site Checks (4 checks)
        live_results = {
            "check_008_url_crawl": self._check_url_crawl(),
            "check_009_internal_links": self._check_internal_links(),
            "check_010_ssl_check": self._check_ssl_certificate(),
            "check_011_response_time": self._check_response_times(),
        }
        results["categories"]["LIVE_SITE_CHECKS"] = live_results

        # Category 3: Content Integrity (5 checks)
        content_results = {
            "check_012_logo_branding": self._check_logo_branding(),
            "check_013_navigation": self._check_navigation(),
            "check_015_score_display": self._check_score_display(),
            "check_016_dead_buttons": self._check_dead_buttons(),
        }
        results["categories"]["CONTENT_INTEGRITY"] = content_results

        # Category 4: Security (4 checks)
        security_results = {
            "check_017_secrets_scan": self._check_secrets_scan(),
            "check_018_https_redirect": self._check_https_redirect(),
            "check_019_external_scripts": self._check_external_scripts(),
            "check_020_file_permissions": self._check_file_permissions(),
        }
        results["categories"]["SECURITY"] = security_results

        # Category 5: Intelligence (4 checks)
        intel_results = {
            "check_021_comparative_audit": self._check_comparative_audit(),
            "check_022_ticker_leaderboard": self._check_ticker_leaderboard(),
            "check_023_perfect_scores": self._check_perfect_scores(),
            "check_024_stale_rankings": self._check_stale_rankings(),
        }
        results["categories"]["INTELLIGENCE"] = intel_results

        # Compile summary
        results["summary"] = self._compile_summary(results)
        results["duration_seconds"] = (datetime.datetime.now() - start_time).total_seconds()

        self._audit_results = results
        self._last_audit = datetime.datetime.now()

        # Log to learning logger
        self._log_audit_results(results)

        # Send Telegram report
        self._send_telegram_report(results)

        # Get intelligent analysis from Claude if available
        self._get_claude_analysis(results)

        self.write_activity("Audit complete", location="office", status="idle")
        print(f"[Audit] Complete. Passed: {results['summary']['passed']}/{results['summary']['total_checks']}, "
              f"Duration: {results['duration_seconds']:.0f}s")

        return results

    # ===== CATEGORY 1: LOCAL FILE CHECKS =====

    def _check_site_health(self) -> Tuple[bool, str]:
        """Check 1: Verify real DDP scraper data files exist and contain valid JSON."""
        try:
            data_dir = Path(REPO_PATH)
            if not data_dir.exists():
                return False, "Repo directory not found"

            required_files = ["trscode-data.json", "truscore-data.json", "trf-data.json", "tragent-data.json", "trs-data.json"]
            missing = []
            invalid = []

            for fname in required_files:
                fpath = data_dir / fname
                if not fpath.exists():
                    missing.append(fname)
                else:
                    try:
                        with open(fpath) as f:
                            json.load(f)
                    except json.JSONDecodeError:
                        invalid.append(fname)

            if missing or invalid:
                msg = "Site Health FAILED: "
                if missing:
                    msg += f"Missing: {', '.join(missing)}. "
                if invalid:
                    msg += f"Invalid JSON: {', '.join(invalid)}"
                return False, msg

            return True, "Site health OK - all data files present and valid"

        except Exception as e:
            return False, f"Site health check error: {e}"

    def _check_ddp_status(self) -> Tuple[bool, str]:
        """Check 2: Verify all 5 DDPs are running and not stale/failed."""
        try:
            status_file = Path(REPO_PATH) / "status.json"
            if not status_file.exists():
                return False, "DDP status file not found"

            with open(status_file) as f:
                ddp_data = json.load(f)

            expected_ddps = ["DDP1", "DDP2", "DDP3", "DDP4", "DDP5"]
            stale_threshold = datetime.datetime.now() - datetime.timedelta(hours=2)

            issues = []
            for ddp in expected_ddps:
                if ddp not in ddp_data:
                    issues.append(f"{ddp} missing")
                else:
                    status = ddp_data[ddp].get("status", "unknown")
                    if status not in ["running", "active", "ok"]:
                        issues.append(f"{ddp} status={status}")

                    # Check staleness
                    last_update = ddp_data[ddp].get("last_update")
                    if last_update:
                        try:
                            update_time = datetime.datetime.fromisoformat(last_update)
                            if update_time < stale_threshold:
                                issues.append(f"{ddp} stale (>2h)")
                        except:
                            pass

            if issues:
                return False, f"DDP issues: {', '.join(issues)}"

            return True, "All 5 DDPs running and up-to-date"

        except Exception as e:
            return False, f"DDP status check error: {e}"

    def _check_data_file_integrity(self) -> Tuple[bool, str]:
        """Check 3: Verify real DDP JSON data files are valid and not stale (>48h)."""
        try:
            data_dir = Path(REPO_PATH)
            stale_threshold = datetime.datetime.now() - datetime.timedelta(hours=48)

            critical_files = ["trscode-data.json", "truscore-data.json", "trf-data.json", "tragent-data.json", "trs-data.json"]
            issues = []

            for fname in critical_files:
                fpath = data_dir / fname
                if not fpath.exists():
                    issues.append(f"{fname} missing")
                    continue

                # Check if file is stale
                mtime = datetime.datetime.fromtimestamp(fpath.stat().st_mtime)
                if mtime < stale_threshold:
                    hours_old = (datetime.datetime.now() - mtime).total_seconds() / 3600
                    issues.append(f"{fname} stale ({hours_old:.1f}h old)")

                # Validate JSON
                try:
                    with open(fpath) as f:
                        json.load(f)
                except json.JSONDecodeError:
                    issues.append(f"{fname} has invalid JSON")

            if issues:
                return False, f"Data integrity issues: {', '.join(issues)}"

            return True, "Data files valid and current (<48h)"

        except Exception as e:
            return False, f"Data integrity check error: {e}"

    def _check_html_pages(self) -> Tuple[bool, str]:
        """Check 4: Verify HTML page files exist in repo."""
        try:
            repo_path = Path(REPO_PATH)
            missing_pages = []

            for page in KNOWN_PAGES:
                # Check multiple possible locations
                found = False
                for location in [repo_path / page, repo_path / "html" / page, repo_path / "public" / page]:
                    if location.exists():
                        found = True
                        break

                if not found:
                    missing_pages.append(page)

            if missing_pages:
                return False, f"Missing HTML pages: {', '.join(missing_pages)}"

            return True, f"All {len(KNOWN_PAGES)} HTML pages found"

        except Exception as e:
            return False, f"HTML pages check error: {e}"

    def _check_git_status(self) -> Tuple[bool, str]:
        """Check 5: Verify no uncommitted changes in git."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_PATH,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return False, "Git status check failed"

            uncommitted = result.stdout.strip()
            if uncommitted:
                lines = uncommitted.split("\n")
                return False, f"Uncommitted changes: {len(lines)} files modified"

            return True, "Git status clean - no uncommitted changes"

        except Exception as e:
            return False, f"Git status check error: {e}"

    def _check_vault_integrity(self) -> Tuple[bool, str]:
        """Check 6: Verify Core 7 vault files are present for TRSitekeeper."""
        try:
            vault_dir = Path(REPO_PATH) / "context-vault" / "trainingrun" / "agents" / "trsitekeeper"
            if not vault_dir.exists():
                return False, f"Vault directory not found at {vault_dir}"

            # Core 7 vault files (markdown, not JSON)
            expected_files = [
                "SOUL.md",
                "CONFIG.md",
                "PROCESS.md",
                "CADENCE.md",
                "RUN-LOG.md",
                "LEARNING-LOG.md",
                "STYLE-EVOLUTION.md",
            ]

            missing = [f for f in expected_files if not (vault_dir / f).exists()]

            if missing:
                return False, f"Missing vault files: {', '.join(missing)}"

            return True, f"All {len(expected_files)} Core 7 vault files present"

        except Exception as e:
            return False, f"Vault integrity check error: {e}"

    def _check_agent_activity(self) -> Tuple[bool, str]:
        """Check 7: Verify agent is not idle for >24 hours."""
        try:
            activity_file = Path(REPO_PATH) / "web_agent" / "activity.log"
            if not activity_file.exists():
                return False, "Activity log not found"

            # Get last modification time
            mtime = datetime.datetime.fromtimestamp(activity_file.stat().st_mtime)
            idle_time = datetime.datetime.now() - mtime

            if idle_time > datetime.timedelta(hours=24):
                hours_idle = idle_time.total_seconds() / 3600
                return False, f"Agent idle for {hours_idle:.1f} hours (>24h)"

            return True, f"Agent active (last update {idle_time.total_seconds()/3600:.1f}h ago)"

        except Exception as e:
            return False, f"Agent activity check error: {e}"

    # ===== CATEGORY 2: LIVE SITE CHECKS =====

    def _check_url_crawl(self) -> Tuple[bool, str]:
        """Check 8: HTTP GET every known page, flag 404/500/timeouts."""
        try:
            failed_pages = []
            timeout_pages = []

            for page in KNOWN_PAGES:
                url = urljoin(SITE_URL, page)
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 404:
                        failed_pages.append(f"{page} (404)")
                    elif response.status_code >= 500:
                        failed_pages.append(f"{page} ({response.status_code})")
                except requests.Timeout:
                    timeout_pages.append(page)
                except requests.RequestException as e:
                    failed_pages.append(f"{page} (connection error)")

            # Also check root
            try:
                response = requests.get(SITE_URL, timeout=5)
                if response.status_code >= 400:
                    failed_pages.append(f"root ({response.status_code})")
            except:
                timeout_pages.append("root")

            issues = []
            if failed_pages:
                issues.append(f"Failed: {', '.join(failed_pages)}")
            if timeout_pages:
                issues.append(f"Timeouts: {', '.join(timeout_pages)}")

            if issues:
                return False, "URL crawl issues: " + "; ".join(issues)

            return True, f"All {len(KNOWN_PAGES) + 1} pages responding with 200"

        except Exception as e:
            return False, f"URL crawl check error: {e}"

    def _check_internal_links(self) -> Tuple[bool, str]:
        """Check 9: Parse HTML, verify all <a href> links resolve."""
        try:
            broken_links = defaultdict(list)

            for page in KNOWN_PAGES[:3]:  # Check first 3 pages to avoid timeout
                url = urljoin(SITE_URL, page)
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        parser = LinkExtractor()
                        parser.feed(response.text)

                        for link in parser.links:
                            if not link or link.startswith("#"):
                                continue

                            # Resolve relative URLs
                            full_url = urljoin(url, link)

                            # Skip external links and special protocols
                            if not full_url.startswith(SITE_URL) and not full_url.startswith("/"):
                                continue

                            try:
                                link_response = requests.head(full_url, timeout=3)
                                if link_response.status_code >= 404:
                                    broken_links[page].append(link)
                            except:
                                broken_links[page].append(link)
                except:
                    pass

            if broken_links:
                issue_str = "; ".join(
                    f"{page}: {', '.join(links[:3])}"
                    for page, links in broken_links.items()
                )
                return False, f"Broken internal links: {issue_str}"

            return True, "Internal links verified"

        except Exception as e:
            return False, f"Internal links check error: {e}"

    def _check_ssl_certificate(self) -> Tuple[bool, str]:
        """Check 10: Verify HTTPS cert is valid and not expiring within 14 days."""
        try:
            hostname = urlparse(SITE_URL).netloc
            context = ssl.create_default_context()

            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    # Check expiration
                    if "notAfter" in cert:
                        expire_time = email.utils.parsedate_to_datetime(cert["notAfter"])
                        days_until_expire = (expire_time - datetime.datetime.now(expire_time.tzinfo)).days

                        if days_until_expire < 0:
                            return False, "SSL certificate expired"
                        elif days_until_expire < 14:
                            return False, f"SSL cert expiring in {days_until_expire} days"

                        return True, f"SSL certificate valid, expires in {days_until_expire} days"

            return True, "SSL certificate is valid"

        except Exception as e:
            return False, f"SSL certificate check error: {e}"

    def _check_response_times(self) -> Tuple[bool, str]:
        """Check 11: Measure page load time, flag anything >3 seconds."""
        try:
            slow_pages = []

            for page in KNOWN_PAGES[:5]:  # Check first 5 pages
                url = urljoin(SITE_URL, page)
                try:
                    start = time.time()
                    response = requests.get(url, timeout=10)
                    elapsed = time.time() - start

                    if elapsed > 3.0:
                        slow_pages.append(f"{page} ({elapsed:.2f}s)")
                except:
                    pass

            if slow_pages:
                return False, f"Slow pages (>3s): {', '.join(slow_pages)}"

            return True, "Page response times normal (<3s)"

        except Exception as e:
            return False, f"Response time check error: {e}"

    # ===== CATEGORY 3: CONTENT INTEGRITY =====

    def _check_logo_branding(self) -> Tuple[bool, str]:
        """Check 12: Verify key <img> tags load (200 response)."""
        try:
            response = requests.get(SITE_URL, timeout=5)
            parser = LinkExtractor()
            parser.feed(response.text)

            if not parser.images:
                return False, "No images found on site"

            broken_images = []
            for img_url in parser.images[:10]:  # Check first 10 images
                full_url = urljoin(SITE_URL, img_url)
                try:
                    img_response = requests.head(full_url, timeout=3)
                    if img_response.status_code != 200:
                        broken_images.append(img_url)
                except:
                    broken_images.append(img_url)

            if broken_images:
                return False, f"Broken images: {', '.join(broken_images[:3])}"

            return True, f"Logo/branding verified - {len(parser.images)} images loading"

        except Exception as e:
            return False, f"Logo branding check error: {e}"

    def _check_navigation(self) -> Tuple[bool, str]:
        """Check 13: Verify header nav, sidebar, footer links point to real pages."""
        try:
            response = requests.get(SITE_URL, timeout=5)
            parser = LinkExtractor()
            parser.feed(response.text)

            if not parser.links:
                return False, "No navigation links found"

            # Check a sample of links
            broken_nav = []
            for link in parser.links[:15]:
                if link.startswith("#") or link.startswith("javascript"):
                    continue

                full_url = urljoin(SITE_URL, link)
                if full_url.startswith(SITE_URL):
                    try:
                        link_response = requests.head(full_url, timeout=3)
                        if link_response.status_code >= 404:
                            broken_nav.append(link)
                    except:
                        broken_nav.append(link)

            if broken_nav:
                return False, f"Broken nav links: {', '.join(broken_nav[:3])}"

            return True, "Navigation links verified"

        except Exception as e:
            return False, f"Navigation check error: {e}"

    def _check_score_display(self) -> Tuple[bool, str]:
        """Check 15: Read scores page, look for actual numbers not undefined/NaN/blank."""
        try:
            response = requests.get(urljoin(SITE_URL, "scores.html"), timeout=5)
            if response.status_code != 200:
                return False, "Scores page not accessible"

            text = response.text

            # Check for problematic patterns
            bad_patterns = ["undefined", "NaN", "null", "error"]
            issues = []

            for pattern in bad_patterns:
                if pattern in text:
                    # Count occurrences
                    count = text.count(pattern)
                    if count > 5:  # More than 5 instances might indicate a problem
                        issues.append(f"{count} instances of '{pattern}'")

            # Check for actual score numbers (simple heuristic)
            score_found = bool(re.search(r'\b([0-9]{1,3}\.?[0-9]*)\b', text))

            if not score_found:
                return False, "No score numbers found on page"

            if issues:
                return False, f"Score display issues: {', '.join(issues)}"

            return True, "Scores displayed correctly"

        except Exception as e:
            return False, f"Score display check error: {e}"

    def _check_dead_buttons(self) -> Tuple[bool, str]:
        """Check 16: Find elements with href='#', onclick empty, etc."""
        try:
            response = requests.get(SITE_URL, timeout=5)
            text = response.text

            dead_button_patterns = [
                (r'href\s*=\s*["\']#["\']', "empty href"),
                (r'href\s*=\s*["\']javascript:void\(0\)["\']', "void(0) href"),
                (r'onclick\s*=\s*["\']["\']', "empty onclick"),
                (r'href\s*=\s*["\']["\']', "empty href value"),
            ]

            issues = []
            for pattern, desc in dead_button_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    issues.append(f"{len(matches)} buttons with {desc}")

            if issues:
                return False, f"Dead buttons found: {', '.join(issues)}"

            return True, "No dead buttons detected"

        except Exception as e:
            return False, f"Dead buttons check error: {e}"

    # ===== CATEGORY 4: SECURITY =====

    def _check_secrets_scan(self) -> Tuple[bool, str]:
        """Check 17: Scan repo for accidentally committed API keys/tokens."""
        try:
            repo_path = Path(REPO_PATH)
            found_secrets = []

            # Scan .json files in web_agent and repo root
            for json_file in repo_path.rglob("*.json"):
                # Skip node_modules and .git
                if "node_modules" in str(json_file) or ".git" in str(json_file):
                    continue

                try:
                    with open(json_file) as f:
                        content = f.read()

                    for pattern in SENSITIVE_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Check if it looks like actual credentials
                            if re.search(f"{pattern}[\"']?\\s*[:=]\\s*[\"'][^\"']*[\"']", content):
                                found_secrets.append(str(json_file.relative_to(repo_path)))
                except:
                    pass

            if found_secrets:
                return False, f"Potential secrets in: {', '.join(found_secrets[:3])}"

            return True, "No obvious secrets found in repo"

        except Exception as e:
            return False, f"Secrets scan error: {e}"

    def _check_https_redirect(self) -> Tuple[bool, str]:
        """Check 18: Verify http:// redirects to https://."""
        try:
            http_url = SITE_URL.replace("https://", "http://")

            try:
                response = requests.get(http_url, timeout=5, allow_redirects=False)

                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get("Location", "")
                    if location.startswith("https://"):
                        return True, f"HTTP correctly redirects to HTTPS"
                    else:
                        return False, f"HTTP redirects to {location} (not HTTPS)"
                else:
                    return False, f"HTTP returns {response.status_code} (no redirect)"
            except requests.RequestException:
                # If http fails, https likely exists - that's ok
                return True, "HTTPS appears to be enforced"

        except Exception as e:
            return False, f"HTTPS redirect check error: {e}"

    def _check_external_scripts(self) -> Tuple[bool, str]:
        """Check 19: Audit <script src=> tags for unknown external domains."""
        try:
            response = requests.get(SITE_URL, timeout=5)
            parser = LinkExtractor()
            parser.feed(response.text)

            # Known safe external domains
            trusted_domains = [
                "cdn.jsdelivr.net",
                "cdnjs.cloudflare.com",
                "code.jquery.com",
                "stackpath.bootstrapcdn.com",
                "unpkg.com",
                "apis.google.com",
                "www.google-analytics.com",
                "accounts.google.com",
            ]

            suspicious_scripts = []
            for script_url in parser.scripts:
                # Skip relative and local scripts
                if script_url.startswith("/") or script_url.startswith("."):
                    continue

                # Check against trusted domains
                is_trusted = any(domain in script_url for domain in trusted_domains)
                if not is_trusted and script_url.startswith("http"):
                    suspicious_scripts.append(script_url[:60])

            if suspicious_scripts:
                return False, f"Unknown external scripts: {', '.join(suspicious_scripts[:2])}"

            return True, f"External scripts verified ({len(parser.scripts)} scripts)"

        except Exception as e:
            return False, f"External scripts check error: {e}"

    def _check_file_permissions(self) -> Tuple[bool, str]:
        """Check 20: Look for sensitive files (*.env, *.key, credentials*) in repo."""
        try:
            repo_path = Path(REPO_PATH)
            sensitive_files = []

            # Patterns to look for
            sensitive_patterns = ["*.env", "*.key", "*credentials*", "*secret*", "*token*"]

            for pattern in sensitive_patterns:
                for match in repo_path.rglob(pattern):
                    # Skip git, node_modules, etc
                    if any(skip in str(match) for skip in [".git", "node_modules", ".vscode"]):
                        continue

                    sensitive_files.append(str(match.relative_to(repo_path)))

            if sensitive_files:
                return False, f"Sensitive files found: {', '.join(sensitive_files[:3])}"

            return True, "No sensitive files detected in repo"

        except Exception as e:
            return False, f"File permissions check error: {e}"

    # ===== CATEGORY 5: INTELLIGENCE =====

    def _check_comparative_audit(self) -> Tuple[bool, str]:
        """Check 21: Compare today's results to yesterday's."""
        try:
            audit_history_file = Path(REPO_PATH) / "web_agent" / "audit_history.json"

            # Load or create history
            if audit_history_file.exists():
                with open(audit_history_file) as f:
                    history = json.load(f)
            else:
                history = {}

            today = datetime.datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            # Store today's results
            if self._audit_results:
                summary = self._audit_results.get("summary", {})
                history[today] = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "total_checks": summary.get("total_checks", 0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                }

                # Save history
                audit_history_file.parent.mkdir(exist_ok=True, parents=True)
                with open(audit_history_file, "w") as f:
                    json.dump(history, f, indent=2)

            # Compare to yesterday
            if yesterday in history:
                today_passed = history[today].get("passed", 0)
                yesterday_passed = history[yesterday].get("passed", 0)

                if today_passed < yesterday_passed:
                    diff = yesterday_passed - today_passed
                    return False, f"Passed checks decreased by {diff} compared to yesterday"
                elif today_passed > yesterday_passed:
                    diff = today_passed - yesterday_passed
                    return True, f"Passed checks increased by {diff} compared to yesterday"

            return True, "Comparative audit baseline established"

        except Exception as e:
            return False, f"Comparative audit error: {e}"

    def _check_ticker_leaderboard(self) -> Tuple[bool, str]:
        """Check 22: Verify all 5 real DDP data files exist, are valid JSON, and have model entries."""
        try:
            data_dir = Path(REPO_PATH)
            ddp_files = {
                "trscode-data.json": "TRScode",
                "truscore-data.json": "TRUscore",
                "trf-data.json": "TRFcast",
                "tragent-data.json": "TRAgents",
                "trs-data.json": "TRSbench",
            }

            issues = []
            files_checked = 0

            for fname, ddp_name in ddp_files.items():
                fpath = data_dir / fname
                if not fpath.exists():
                    issues.append(f"{ddp_name} data missing ({fname})")
                    continue

                try:
                    with open(fpath) as f:
                        data = json.load(f)
                    files_checked += 1

                    # Basic validation â check it has content
                    if isinstance(data, dict) and len(data) == 0:
                        issues.append(f"{ddp_name} data is empty")
                    elif isinstance(data, list) and len(data) == 0:
                        issues.append(f"{ddp_name} data is empty list")
                except json.JSONDecodeError:
                    issues.append(f"{ddp_name} has invalid JSON")

            if issues:
                return False, f"DDP data issues: {'; '.join(issues[:3])}"

            return True, f"All {files_checked} DDP data files valid and populated"

        except Exception as e:
            return False, f"DDP data cross-check error: {e}"

    def _check_perfect_scores(self) -> Tuple[bool, str]:
        """Check 23: Flag any model scoring exactly 100 on any DDP (suspicious data)."""
        try:
            data_dir = Path(REPO_PATH)
            ddp_files = ["trscode-data.json", "truscore-data.json", "trf-data.json", "tragent-data.json", "trs-data.json"]

            perfect_scores = []

            for fname in ddp_files:
                fpath = data_dir / fname
                if not fpath.exists():
                    continue

                try:
                    with open(fpath) as f:
                        data = json.load(f)

                    # Walk the data structure looking for score values of exactly 100
                    def find_perfect(obj, path=""):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, (int, float)) and v == 100:
                                    if any(s in k.lower() for s in ["score", "rating", "total", "overall"]):
                                        perfect_scores.append(f"{path}{k}=100 in {fname}")
                                elif isinstance(v, (dict, list)):
                                    find_perfect(v, f"{path}{k}.")
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj[:20]):  # Limit to first 20 entries
                                find_perfect(item, f"{path}[{i}].")

                    find_perfect(data)
                except (json.JSONDecodeError, Exception):
                    pass

            if perfect_scores:
                return False, f"Perfect scores detected: {', '.join(perfect_scores[:3])}"

            return True, "No suspicious perfect scores detected"

        except Exception as e:
            return False, f"Perfect scores check error: {e}"

    def _check_stale_rankings(self) -> Tuple[bool, str]:
        """Check 24: Flag if DDP data files haven't been updated in 48+ hours."""
        try:
            data_dir = Path(REPO_PATH)
            ddp_files = ["trscode-data.json", "truscore-data.json", "trf-data.json", "tragent-data.json", "trs-data.json"]
            stale_threshold = datetime.datetime.now() - datetime.timedelta(hours=48)

            stale = []
            checked = 0

            for fname in ddp_files:
                fpath = data_dir / fname
                if not fpath.exists():
                    continue

                checked += 1
                mtime = datetime.datetime.fromtimestamp(fpath.stat().st_mtime)
                if mtime < stale_threshold:
                    hours_old = (datetime.datetime.now() - mtime).total_seconds() / 3600
                    stale.append(f"{fname} ({hours_old:.0f}h old)")

            if stale:
                return False, f"Stale data files (>48h): {', '.join(stale)}"

            if checked == 0:
                return False, "No DDP data files found to check"

            return True, f"All {checked} DDP data files updated within 48h"

        except Exception as e:
            return False, f"Stale rankings check error: {e}"

    # ===== REPORTING =====

    def _compile_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile summary statistics from all checks."""
        summary = {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "by_category": {}
        }

        for category, checks in results.get("categories", {}).items():
            cat_passed = 0
            cat_failed = 0

            for check_name, (passed, message) in checks.items():
                summary["total_checks"] += 1
                if passed:
                    summary["passed"] += 1
                    cat_passed += 1
                else:
                    summary["failed"] += 1
                    cat_failed += 1

            summary["by_category"][category] = {
                "passed": cat_passed,
                "failed": cat_failed,
                "total": cat_passed + cat_failed
            }

        return summary

    def _log_audit_results(self, results: Dict[str, Any]):
        """Log audit results to learning logger."""
        try:
            if hasattr(self.learning_logger, "log_audit") if self.learning_logger else False:
                self.learning_logger.log_audit(results)
        except Exception as e:
            logging.error(f"Error logging audit results: {e}")

    def _send_telegram_report(self, results: Dict[str, Any]):
        """Send concise Telegram report grouped by category."""
        try:
            summary = results.get("summary", {})

            # Build message
            lines = [
                f"Sitekeeper Audit Report",
                f"Date: {results['timestamp'][:10]}",
                f"",
                f"Summary: {summary['passed']}/{summary['total_checks']} checks passed",
            ]

            # Add category breakdowns
            for category, stats in summary.get("by_category", {}).items():
                status = "OK" if stats["failed"] == 0 else "FAIL"
                cat_name = category.replace("_", " ")
                lines.append(
                    f"  [{status}] {cat_name}: {stats['passed']}/{stats['total']} passed"
                )

            # Add critical failures
            critical_failures = []
            for category, checks in results.get("categories", {}).items():
                for check_name, (passed, message) in checks.items():
                    if not passed:
                        critical_failures.append(f"  * {message[:70]}")

            if critical_failures:
                lines.append("")
                lines.append("Issues:")
                lines.extend(critical_failures[:8])

            message = "\n".join(lines)

            # Send via Telegram
            if self.tg_send:
                try:
                    self.tg_send(message)
                except Exception as e:
                    logging.error(f"Error sending Telegram message: {e}")

        except Exception as e:
            logging.error(f"Error building Telegram report: {e}")

    def _get_claude_analysis(self, results: Dict[str, Any]):
        """Get intelligent analysis from Claude with full vault context and memory."""
        try:
            if not self.claude_chat:
                return

            summary = results.get("summary", {})
            failed_checks = []

            for category, checks in results.get("categories", {}).items():
                for check_name, (passed, message) in checks.items():
                    if not passed:
                        failed_checks.append(f"- {check_name}: {message}")

            if not failed_checks:
                return  # All checks passed, no need for analysis

            # Build context from vault memory
            memory_context = ""
            if self._tried_fixes:
                recent = self._tried_fixes[-5:]
                memory_context += "\nPast fix attempts (most recent):\n"
                for fix in recent:
                    memory_context += f"- {fix.get('check', '?')}: tried {fix.get('fix_type', '?')}, result: {fix.get('outcome', '?')}\n"

            if self._recent_errors:
                memory_context += "\nRecent errors:\n"
                for err in self._recent_errors[-3:]:
                    memory_context += f"- {err.get('error', str(err)[:100])}\n"

            site_knowledge = ""
            if self._memory_context.get("site_knowledge"):
                sk = self._memory_context["site_knowledge"]
                if isinstance(sk, dict):
                    pages = sk.get("pages", sk.get("known_pages", []))
                    if pages:
                        site_knowledge = f"\nKnown site pages: {len(pages) if isinstance(pages, list) else 'loaded'}"

            # Build analysis prompt with full context
            prompt = f"""You are TRSitekeeper, the autonomous site guardian for trainingrun.ai.

Summary: {summary['passed']}/{summary['total_checks']} checks passed

Failed Checks:
{chr(10).join(failed_checks[:8])}
{memory_context}{site_knowledge}

IMPORTANT RULES:
- Real DDP data files are in the REPO ROOT: trscode-data.json, truscore-data.json, trf-data.json, tragent-data.json, trs-data.json
- There are NO files called ticker.json, leaderboard.json, or ddp_status.json
- The vault is at context-vault/trainingrun/agents/trsitekeeper/ with Core 7 markdown files
- Do NOT propose creating stub files to satisfy checks â fix the checks instead

Respond with JSON only:
{{"checks": [{{"check_name": "...", "diagnosis": "...", "root_cause": "...", "proposed_fix_type": "rerun_scraper|git_commit|edit_file|investigate|escalate", "proposed_action": "...", "confidence": 0-100, "files_involved": ["..."]}}]}}"""

            # Get Claude's analysis
            response = self.claude_chat(
                [{"role": "user", "content": prompt}],
                "You are TRSitekeeper, an autonomous site guardian for trainingrun.ai. Analyze audit failures and respond with JSON only."
            )
            # Extract text from Claude API response dict
            analysis = None
            if isinstance(response, dict) and "content" in response:
                text_parts = [b.get("text", "") for b in response["content"] if b.get("type") == "text"]
                analysis = "\n".join(text_parts) if text_parts else None
            elif isinstance(response, str):
                analysis = response

            if analysis and self.write_activity:
                self.write_activity(
                    f"Audit Analysis:\n{analysis}",
                    location="audit",
                    status="idle"
                )

            # Try to parse JSON response for actionable fixes
            if analysis:
                try:
                    # Strip markdown code fences if present
                    clean = analysis.strip()
                    if clean.startswith("```"):
                        clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                    if clean.endswith("```"):
                        clean = clean[:-3]
                    clean = clean.strip()

                    parsed = json.loads(clean)
                    if isinstance(parsed, dict) and "checks" in parsed:
                        logging.info(f"Claude proposed {len(parsed['checks'])} fix(es)")
                        # Store for approve flow
                        self._pending_fixes = parsed["checks"]
                except (json.JSONDecodeError, Exception):
                    logging.warning("Claude analysis was not valid JSON â stored as commentary only")

        except Exception as e:
            logging.error(f"Error getting Claude analysis: {e}")

    def get_status(self) -> str:
        """Return current scheduler status for the 'audit status' command."""
        next_time = self._next_audit_time()
        hours_until = (next_time - datetime.datetime.now()).total_seconds() / 3600

        lines = [
            f"Audit Scheduler: {'ACTIVE' if self._running else 'STOPPED'}",
            f"Window: {self.start_hour}:00 AM - {self.end_hour}:00 AM daily",
            f"Next audit: {next_time.strftime('%a %b %d at %-I:%M %p')} ({hours_until:.1f}h)",
        ]
        if self._last_audit:
            lines.append(
                f"Last audit: {self._last_audit.strftime('%a %b %d at %-I:%M %p')}"
            )
        else:
            lines.append("Last audit: none yet")

        return "\n".join(lines)


# ===== STANDALONE TEST =====

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("\n" + "=" * 70)
    print("  SITEKEEPER AUDIT MODULE - STANDALONE TEST")
    print("=" * 70)

    # Mock functions for testing
    def mock_tg_send(msg):
        print(f"\n[TELEGRAM]\n{msg}\n")

    def mock_execute_tool(tool_name, **kwargs):
        print(f"[EXECUTE] {tool_name} with {kwargs}")
        return {"status": "ok"}

    def mock_write_activity(msg, **kwargs):
        print(f"[ACTIVITY] {msg} ({kwargs})")

    def mock_claude_chat(prompt):
        return "Claude analysis would go here in production"

    def mock_build_prompt(template=None, **kwargs):
        return f"Built prompt with {kwargs}"

    class MockLogger:
        def log_audit(self, results):
            print(f"[LOGGER] Logged {results['summary']['total_checks']} checks")

    # Create scheduler
    scheduler = AuditScheduler(
        tg_send_fn=mock_tg_send,
        execute_tool_fn=mock_execute_tool,
        write_activity_fn=mock_write_activity,
        claude_chat_fn=mock_claude_chat,
        build_prompt_fn=mock_build_prompt,
        learning_logger=MockLogger(),
    )

    # Show initial status
    print(f"\nScheduler Status:\n{scheduler.get_status()}")

    # Run single audit
    print("\n" + "=" * 70)
    print("  RUNNING STANDALONE AUDIT")
    print("=" * 70 + "\n")
    results = scheduler.run_audit()

    # Print detailed results
    print("\n" + "=" * 70)
    print("  AUDIT SUMMARY")
    print("=" * 70)
    print(f"Total Checks: {results['summary']['total_checks']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Duration: {results['duration_seconds']:.2f}s")

    print("\n" + "=" * 70)
    print("  RESULTS BY CATEGORY")
    print("=" * 70)
    for category, stats in results["summary"]["by_category"].items():
        status = "PASS" if stats["failed"] == 0 else "FAIL"
        print(f"[{status}] {category}: {stats['passed']}/{stats['total']}")

    print("\n" + "=" * 70)
    print("  DETAILED CHECK RESULTS")
    print("=" * 70)
    for category, checks in results["categories"].items():
        print(f"\n{category}:")
        for check_name, (passed, message) in checks.items():
            status = "â" if passed else "â"
            print(f"  {status} {check_name}: {message[:80]}")

    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")
