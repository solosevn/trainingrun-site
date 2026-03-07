#!/usr/bin/env python3
"""
TRSitekeeper Autonomous Audit
==============================
Daily 6-8 AM autonomous site audit.

Architecture:
- Scheduler thread sleeps until AUDIT_START_HOUR (6 AM local)
- Wakes up, runs full audit checklist from PROCESS.md
- Reports findings to David via Telegram
- Logs audit results via LearningLogger
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
import json
import time
import subprocess
import datetime
import threading
from pathlib import Path

REPO_PATH = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(AGENT_DIR, "vault")


class AuditScheduler:
    """Autonomous audit scheduler â runs daily at 6 AM."""

    def __init__(self, tg_send_fn, execute_tool_fn, write_activity_fn,
                 claude_chat_fn=None, build_prompt_fn=None, learning_logger=None,
                 start_hour=6, end_hour=8):
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

    def run_audit(self):
        """Execute the full autonomous audit."""
        start_time = datetime.datetime.now()
        print(f"\n{'='*50}")
        print(f"  AUTONOMOUS AUDIT â {start_time.strftime('%a %b %d, %-I:%M %p')}")
        print(f"{'='*50}")

        self.write_activity(
            "Autonomous audit started", location="ddp_room", status="active"
        )
        self.tg_send(
            f"Autonomous audit started "
            f"({start_time.strftime('%-I:%M %p')})"
        )

        findings = []
        checks_passed = 0
        checks_failed = 0

        # ââ CHECK 1: Site Health ââ
        try:
            health = self.execute_tool("site_health", {})
            if "ALL CLEAR" in health:
                checks_passed += 1
            else:
                checks_failed += 1
                findings.append(f"Site Health Issues:\n{health}")
        except Exception as e:
            findings.append(f"Health check error: {e}")
            checks_failed += 1

        # ââ CHECK 2: DDP Status ââ
        try:
            status = self.execute_tool("check_status", {})
            stale_ddps = []
            failed_ddps = []
            for line in status.split("\n"):
                if "[FAIL]" in line:
                    failed_ddps.append(line.strip())
                # Check if last run date is today
                if "last:" in line:
                    today = datetime.date.today().isoformat()
                    if today not in line and "[OK]" not in line:
                        stale_ddps.append(line.strip())

            if failed_ddps:
                checks_failed += 1
                findings.append("Failed DDPs:\n" + "\n".join(failed_ddps))
            if stale_ddps:
                checks_failed += 1
                findings.append(
                    "Stale DDPs (not run today):\n" + "\n".join(stale_ddps)
                )
            if not failed_ddps and not stale_ddps:
                checks_passed += 1
        except Exception as e:
            findings.append(f"Status check error: {e}")
            checks_failed += 1

        # ââ CHECK 3: Data File Integrity ââ
        data_files = [
            "trs-data.json", "trscode-data.json", "truscore-data.json",
            "trf-data.json", "tragent-data.json", "status.json"
        ]
        data_issues = []
        for df in data_files:
            fp = os.path.join(REPO_PATH, df)
            if not os.path.exists(fp):
                data_issues.append(f"MISSING: {df}")
            else:
                try:
                    with open(fp) as f:
                        json.load(f)
                    # Check file age
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
                    age_hours = (
                        datetime.datetime.now() - mtime
                    ).total_seconds() / 3600
                    if age_hours > 48:
                        data_issues.append(
                            f"STALE: {df} (last modified {age_hours:.0f}h ago)"
                        )
                except json.JSONDecodeError:
                    data_issues.append(f"CORRUPT JSON: {df}")

        if data_issues:
            checks_failed += 1
            findings.append("Data File Issues:\n" + "\n".join(data_issues))
        else:
            checks_passed += 1

        # ââ CHECK 4: HTML Pages Exist ââ
        html_pages = [
            "index.html", "mission-control.html", "hq.html", "scores.html",
            "truscore.html", "trscode.html", "trfcast.html", "tragents.html"
        ]
        missing_pages = []
        for hp in html_pages:
            if not os.path.exists(os.path.join(REPO_PATH, hp)):
                missing_pages.append(hp)

        if missing_pages:
            checks_failed += 1
            findings.append(f"Missing Pages: {', '.join(missing_pages)}")
        else:
            checks_passed += 1

        # ââ CHECK 5: Git Status ââ
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_PATH, capture_output=True, text=True, timeout=10
            )
            uncommitted = result.stdout.strip()
            if uncommitted:
                file_count = len(uncommitted.split("\n"))
                findings.append(f"{file_count} uncommitted file(s) in repo")
                checks_failed += 1
            else:
                checks_passed += 1
        except Exception as e:
            findings.append(f"Git check error: {e}")

        # ââ CHECK 6: Vault Integrity ââ
        expected_vault = [
            "SOUL.md", "CONFIG.md", "PROCESS.md", "CADENCE.md",
            "RUN-LOG.md", "LEARNING-LOG.md", "STYLE-EVOLUTION.md",
            "CAPABILITIES.md", "TASK-LOG.md"
        ]
        missing_vault = [
            f for f in expected_vault
            if not os.path.exists(os.path.join(VAULT_DIR, f))
        ]

        if missing_vault:
            checks_failed += 1
            findings.append(f"Missing vault files: {', '.join(missing_vault)}")
        else:
            checks_passed += 1

        # ââ CHECK 7: Agent Activity File ââ
        activity_file = os.path.join(REPO_PATH, "agent_activity.json")
        try:
            with open(activity_file) as f:
                activity = json.load(f)
            last_updated = activity.get("last_updated", "")
            if last_updated:
                last_dt = datetime.datetime.fromisoformat(last_updated)
                age = (datetime.datetime.now() - last_dt).total_seconds() / 3600
                if age > 24:
                    findings.append(
                        f"Agent activity stale ({age:.0f}h since last update)"
                    )
                    checks_failed += 1
                else:
                    checks_passed += 1
            else:
                checks_passed += 1
        except Exception:
            checks_passed += 1  # Not critical

        # ââ COMPILE REPORT ââ
        duration = (datetime.datetime.now() - start_time).total_seconds()
        total_checks = checks_passed + checks_failed

        report_lines = [
            f"AUDIT REPORT â {start_time.strftime('%a %b %d, %-I:%M %p')}",
            f"Duration: {duration:.0f}s | Passed: {checks_passed}/{total_checks}",
            ""
        ]

        if findings:
            report_lines.append("FINDINGS:")
            report_lines.append("")
            for i, f in enumerate(findings, 1):
                report_lines.append(f"{i}. {f}")
                report_lines.append("")
        else:
            report_lines.append("All checks passed. Site is healthy.")

        report = "\n".join(report_lines)
        self.tg_send(report)

        # ââ INTELLIGENT ANALYSIS (if Claude available and issues found) ââ
        if self.claude_chat and self.build_prompt and findings:
            try:
                self.write_activity(
                    "Analyzing findings...", location="office", status="active"
                )
                analysis_prompt = (
                    f"You just ran an autonomous audit. Here are the findings:\n\n"
                    + "\n".join(f"- {f}" for f in findings) +
                    "\n\nProvide a brief (3-5 line) analysis: what's most urgent, "
                    "what you'd recommend fixing first, and whether any of these "
                    "are related. Be direct. Keep it short â David reads on his phone."
                )

                messages = [{"role": "user", "content": analysis_prompt}]
                system = self.build_prompt(message=analysis_prompt, mode="audit")
                response = self.claude_chat(messages, system)

                if "error" not in response:
                    content = response.get("content", [])
                    text_parts = [
                        b.get("text", "") for b in content
                        if b.get("type") == "text"
                    ]
                    if text_parts:
                        analysis = "\n".join(text_parts)
                        self.tg_send(f"Analysis:\n{analysis}")
            except Exception as e:
                print(f"[Audit] Claude analysis error: {e}")

        # ââ LOG THE AUDIT ââ
        if self.learning_logger:
            try:
                results_dict = {
                    "checks_passed": checks_passed,
                    "checks_failed": checks_failed,
                    "total_checks": total_checks,
                    "duration_seconds": duration,
                }
                lessons = []
                if findings:
                    lessons = [f[:100] for f in findings]

                self.learning_logger.log_audit(
                    results=results_dict,
                    issues_found=checks_failed,
                    lessons=lessons if lessons else None
                )
            except Exception as e:
                print(f"[Audit] Logging error: {e}")

        self._last_audit = datetime.datetime.now()
        self.write_activity("Audit complete", location="office", status="idle")
        print(f"[Audit] Complete. Passed: {checks_passed}/{total_checks}, "
              f"Duration: {duration:.0f}s")

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


# âââââââââââââââââââââââââââââââââââââââââââââ
# STANDALONE TEST
# âââââââââââââââââââââââââââââââââââââââââââââ
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING AUDIT MODULE")
    print("=" * 50)

    def mock_tg_send(text):
        print(f"\n[Telegram] {text}")

    def mock_execute_tool(name, args):
        if name == "site_health":
            return "Health Check: ALL CLEAR (6 checks passed)"
        if name == "check_status":
            return (
                "Mission Control Status\n"
                "[OK] trsbench: success | last: 2026-03-06 | top: 78.2\n"
                "[OK] trscode: success | last: 2026-03-06 | top: 85.1\n"
            )
        return f"Mock result for {name}"

    def mock_write_activity(action, location="office", status="active"):
        print(f"[Activity] {action} ({location}, {status})")

    scheduler = AuditScheduler(
        tg_send_fn=mock_tg_send,
        execute_tool_fn=mock_execute_tool,
        write_activity_fn=mock_write_activity,
    )

    print(f"\nScheduler status:\n{scheduler.get_status()}")
    print("\nRunning audit...")
    scheduler.run_audit()
    print(f"\nScheduler status:\n{scheduler.get_status()}")
