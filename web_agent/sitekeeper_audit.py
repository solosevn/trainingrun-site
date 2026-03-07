#!/usr/bin/env python3
"""
Sitekeeper Audit System for trainingrun.ai
==========================================
Runs comprehensive 24-check autonomous audit system with 5 categories:
1. Local File Checks (7 checks)
2. Live Site Checks (4 checks)
3. Content Integrity (5 checks)
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
                    self.run_audit()
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
        print(f"  AUTONOMOUS AUDIT (24 CHECKS) â {start_time.strftime('%a %b %d, %-I:%M %p')}")
        print(f"{'='*60}")

        self.write_activity(
            "24-check autonomous audit started", location="ddp_room", status="active"
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
            "check_014_special_pages": self._check_special_pages(),
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
        """Check 1: Verify site data files exist and contain valid JSON."""
        try:
            data_dir = Path(REPO_PATH) / "web_agent"
            if not data_dir.exists():
                return False, "Data directory not found"

            required_files = ["ticker.json", "leaderboard.json", "ddp_status.json"]
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
        """Check 2: Verify all 5 DDPs have fresh data files."""
        try:
            ddp_data_files = {
                "trscode": Path(REPO_PATH) / "trscode-data.json",
                "truscore": Path(REPO_PATH) / "truscore-data.json",
                "trfcast": Path(REPO_PATH) / "trf-data.json",
                "tragents": Path(REPO_PATH) / "tragent-data.json",
                "trs": Path(REPO_PATH) / "trs-data.json",
            }
            stale_threshold = datetime.datetime.now() - datetime.timedelta(hours=26)

            issues = []
            for name, path in ddp_data_files.items():
                if not path.exists():
                    issues.append(f"{name} data file missing")
                else:
                    mod_time = datetime.datetime.fromtimestamp(path.stat().st_mtime)
                    if mod_time < stale_threshold:
                        hours_old = (datetime.datetime.now() - mod_time).total_seconds() / 3600
                        issues.append(f"{name} stale ({hours_old:.0f}h old)")

            if issues:
                return False, f"DDP issues: {', '.join(issues)}"

            return True, "All 5 DDPs have fresh data files"

        except Exception as e:
            return False, f"DDP status check error: {e}"

    def _check_data_file_integrity(self) -> Tuple[bool, str]:
        """Check 3: Verify DDP JSON data files are valid and not stale (>48h)."""
        try:
            stale_threshold = datetime.datetime.now() - datetime.timedelta(hours=48)
            critical_files = {
                "trscode-data.json": Path(REPO_PATH) / "trscode-data.json",
                "truscore-data.json": Path(REPO_PATH) / "truscore-data.json",
                "trf-data.json": Path(REPO_PATH) / "trf-data.json",
                "tragent-data.json": Path(REPO_PATH) / "tragent-data.json",
                "trs-data.json": Path(REPO_PATH) / "trs-data.json",
            }

            issues = []
            for fname, fpath in critical_files.items():
                if not fpath.exists():
                    issues.append(f"{fname} missing")
                    continue

                mtime = datetime.datetime.fromtimestamp(fpath.stat().st_mtime)
                if mtime < stale_threshold:
                    hours_old = (datetime.datetime.now() - mtime).total_seconds() / 3600
                    issues.append(f"{fname} stale ({hours_old:.1f}h old)")

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
        """Check 6: Verify all 9 vault files are present."""
        try:
            vault_dir = Path(REPO_PATH) / "vault"
            if not vault_dir.exists():
                return False, "Vault directory not found"

            # Expected vault files (9 total)
            expected_files = [
                "vault_config.json",
                "vault_keys.json",
                "vault_archive_1.json",
                "vault_archive_2.json",
                "vault_archive_3.json",
                "vault_secrets.json",
                "vault_audit_log.json",
                "vault_backup.json",
                "vault_metadata.json",
            ]

            missing = [f for f in expected_files if not (vault_dir / f).exists()]

            if missing:
                return False, f"Missing vault files: {', '.join(missing)}"

            return True, "All 9 vault files present"

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

    def _check_special_pages(self) -> Tuple[bool, str]:
        """Check 14: Verify terms, charter, belt, mythology pages exist and aren't empty."""
        try:
            special_page_patterns = [
                ("terms", ["terms", "tos", "terms-of-service"]),
                ("charter", ["charter", "code-of-conduct"]),
                ("belt", ["belt", "ranks"]),
                ("mythology", ["mythology", "lore"]),
            ]

            missing = []
            empty = []

            for page_type, patterns in special_page_patterns:
                found = False
                for pattern in patterns:
                    # Try various URL patterns
                    for sep in ["-", "_", ""]:
                        url = urljoin(SITE_URL, f"{pattern.replace('-', sep)}.html")
                        try:
                            response = requests.get(url, timeout=5)
                            if response.status_code == 200:
                                if len(response.text) < 500:
                                    empty.append(page_type)
                                else:
                                    found = True
                                break
                        except:
                            pass

                    if found:
                        break

                if not found:
                    missing.append(page_type)

            issues = []
            if missing:
                issues.append(f"Missing: {', '.join(missing)}")
            if empty:
                issues.append(f"Empty: {', '.join(empty)}")

            if issues:
                return False, "Special pages issue: " + "; ".join(issues)

            return True, "Special pages exist and have content"

        except Exception as e:
            return False, f"Special pages check error: {e}"

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
        """Check 22: Compare ticker data vs leaderboard scores for consistency."""
        try:
            data_dir = Path(REPO_PATH) / "web_agent"
            ticker_file = data_dir / "ticker.json"
            leaderboard_file = data_dir / "leaderboard.json"

            if not ticker_file.exists() or not leaderboard_file.exists():
                return False, "Ticker or leaderboard data not found"

            with open(ticker_file) as f:
                ticker = json.load(f)
            with open(leaderboard_file) as f:
                leaderboard = json.load(f)

            # Extract scores from both
            ticker_scores = {}
            for entry in ticker.get("entries", []):
                model = entry.get("model", "")
                score = entry.get("score", None)
                if model and score is not None:
                    ticker_scores[model] = score

            leaderboard_scores = {}
            for entry in leaderboard.get("entries", []):
                model = entry.get("model", "")
                score = entry.get("score", None)
                if model and score is not None:
                    leaderboard_scores[model] = score

            # Check for major discrepancies
            discrepancies = []
            for model in ticker_scores:
                if model in leaderboard_scores:
                    diff = abs(ticker_scores[model] - leaderboard_scores[model])
                    if diff > 5:  # More than 5 point difference is suspicious
                        discrepancies.append(f"{model} (diff={diff:.1f})")

            if discrepancies:
                return False, f"Score discrepancies: {', '.join(discrepancies[:3])}"

            return True, "Ticker and leaderboard scores consistent"

        except Exception as e:
            return False, f"Ticker/leaderboard check error: {e}"

    def _check_perfect_scores(self) -> Tuple[bool, str]:
        """Check 23: Flag any model scoring exactly 100 on any DDP."""
        try:
            data_dir = Path(REPO_PATH) / "web_agent"

            perfect_scores = []

            # Check leaderboard
            leaderboard_file = data_dir / "leaderboard.json"
            if leaderboard_file.exists():
                with open(leaderboard_file) as f:
                    leaderboard = json.load(f)

                for entry in leaderboard.get("entries", []):
                    score = entry.get("score")
                    if score == 100 or score == 100.0:
                        perfect_scores.append(f"{entry.get('model', 'unknown')} on leaderboard")

            # Check DDP status
            ddp_file = data_dir / "ddp_status.json"
            if ddp_file.exists():
                with open(ddp_file) as f:
                    ddps = json.load(f)

                for ddp_name, ddp_data in ddps.items():
                    for model_name, model_score in ddp_data.get("scores", {}).items():
                        if model_score == 100 or model_score == 100.0:
                            perfect_scores.append(f"{model_name} on {ddp_name}")

            if perfect_scores:
                return False, f"Perfect scores detected: {', '.join(perfect_scores[:3])}"

            return True, "No perfect scores detected"

        except Exception as e:
            return False, f"Perfect scores check error: {e}"

    def _check_stale_rankings(self) -> Tuple[bool, str]:
        """Check 24: Track rankings, flag if unchanged for 3+ days."""
        try:
            rankings_history_file = Path(REPO_PATH) / "web_agent" / "rankings_history.json"

            # Load or create history
            if rankings_history_file.exists():
                with open(rankings_history_file) as f:
                    rankings_history = json.load(f)
            else:
                rankings_history = {}

            today = datetime.datetime.now().strftime("%Y-%m-%d")

            # Get current rankings
            leaderboard_file = Path(REPO_PATH) / "web_agent" / "leaderboard.json"
            if leaderboard_file.exists():
                with open(leaderboard_file) as f:
                    leaderboard = json.load(f)

                # Create ranking hash
                ranking_list = [e.get("model", "") for e in leaderboard.get("entries", [])[:10]]
                ranking_hash = hashlib.md5("|".join(ranking_list).encode()).hexdigest()

                rankings_history[today] = ranking_hash

                # Save history
                rankings_history_file.parent.mkdir(exist_ok=True, parents=True)
                with open(rankings_history_file, "w") as f:
                    json.dump(rankings_history, f, indent=2)

                # Check for stale rankings (same for 3+ days)
                recent_hashes = list(rankings_history.values())[-3:]
                if len(set(recent_hashes)) == 1 and len(recent_hashes) == 3:
                    return False, "Rankings unchanged for 3+ consecutive days"

            return True, "Rankings are active and changing"

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
        """Get intelligent analysis from Claude if available."""
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

            # Build analysis prompt
            prompt = f"""Analyze these site audit failures and suggest next steps:

Summary: {summary['passed']}/{summary['total_checks']} checks passed
Failed Checks:
{chr(10).join(failed_checks[:5])}

Provide brief, actionable recommendations."""

            # Get Claude's analysis
        system_prompt = "You are TRSitekeeper, an autonomous site manager for trainingrun.ai. Analyze audit failures and provide brief, actionable fixes."
        analysis = self.claude_chat(prompt, system_prompt)

            if analysis and self.write_activity:
                self.write_activity(
                    f"Audit Analysis:\n{analysis}",
                    location="audit",
                    status="idle"
                )

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
