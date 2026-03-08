#!/usr/bin/env python3
"""
TRSitekeeper Learning Logger â The Filesystem Writer
=====================================================
Writes to all memory layers after every significant action.
Implements the consolidation cycle:
  - After every fix â error_log, fix_patterns, site_knowledge, RUN-LOG
  - After every audit â RUN-LOG, LEARNING-LOG
  - Weekly â consolidation pass (pattern promotion, skill synthesis)
  - Monthly â deep consolidation (SOUL.md proposals, selective forgetting)

Usage:
    from sitekeeper_learning_logger import LearningLogger
    logger = LearningLogger()
    logger.log_fix(file="index.html", symptom="...", fix="...", root_cause="...")
    logger.log_audit(results={...})
    logger.log_error(error_type="css", symptom="...", fix="...", ...)
    logger.update_david_model(key="anticipated_needs", update={...})
"""

import os
import json
import datetime
from pathlib import Path
from typing import Optional

# âââââââââââââââââââââââââââââââââââââââââââââ
# PATHS
# âââââââââââââââââââââââââââââââââââââââââââââ

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(AGENT_DIR, "memory")
SKILLS_DIR = os.path.join(AGENT_DIR, "skills")
VAULT_DIR = os.path.join(AGENT_DIR, "vault")

MEMORY_FILES = {
    "error_log": os.path.join(MEMORY_DIR, "error_log.jsonl"),
    "fix_patterns": os.path.join(MEMORY_DIR, "fix_patterns.json"),
    "site_knowledge": os.path.join(MEMORY_DIR, "site_knowledge.json"),
    "david_model": os.path.join(MEMORY_DIR, "david_model.json"),
}

VAULT_LOGS = {
    "RUN_LOG": os.path.join(VAULT_DIR, "RUN-LOG.md"),
    "LEARNING_LOG": os.path.join(VAULT_DIR, "LEARNING-LOG.md"),
    "STYLE_EVOLUTION": os.path.join(VAULT_DIR, "STYLE-EVOLUTION.md"),
}


class LearningLogger:
    """Handles all memory writes for TRSitekeeper."""

    def __init__(self):
        """Initialize â ensure directories exist."""
        os.makedirs(MEMORY_DIR, exist_ok=True)
        os.makedirs(SKILLS_DIR, exist_ok=True)
        os.makedirs(VAULT_DIR, exist_ok=True)

    # âââââââââââââââââââââââââââââââââââââ
    # CORE LOGGING METHODS
    # âââââââââââââââââââââââââââââââââââââ

    def log_error(self, error_type: str, file: str, symptom: str,
                  root_cause: str, fix: str, confidence: str = "medium",
                  line: Optional[int] = None) -> dict:
        """Log an error event to error_log.jsonl.

        This is the foundation of the 'Never Repeat a Mistake' protocol.
        Every error + resolution is recorded so the agent can query history
        before attempting future fixes.

        Args:
            error_type: Category (css_alignment, data_staleness, git_conflict, etc.)
            file: Which file was affected
            symptom: What the user reported / what was observed
            root_cause: What actually caused it
            fix: What was done to fix it
            confidence: How confident in the fix (low/medium/high)
            line: Optional line number

        Returns:
            The error entry dict that was logged.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "error_type": error_type,
            "file": file,
            "symptom": symptom,
            "root_cause": root_cause,
            "fix": fix,
            "confidence": confidence,
            "times_seen": 1,
        }
        if line is not None:
            entry["line"] = line

        # Check if we've seen this exact error_type + file combo before
        existing = self._read_error_log()
        for prev in existing:
            if prev.get("error_type") == error_type and prev.get("file") == file:
                entry["times_seen"] = prev.get("times_seen", 1) + 1
                break

        self._append_jsonl(MEMORY_FILES["error_log"], entry)

        # Auto-promote: if times_seen >= 3, update fix_patterns
        if entry["times_seen"] >= 3:
            self._promote_to_fix_pattern(error_type, entry)

        return entry

    def log_fix(self, file: str, symptom: str, fix: str,
                tool_used: str = "edit_file", details: str = "") -> dict:
        """Log a fix action to RUN-LOG.md.

        Called after every successful file edit/fix.

        Args:
            file: Which file was fixed
            symptom: What was wrong
            fix: What was done
            tool_used: Which tool was used (edit_file, write_file)
            details: Additional details

        Returns:
            The log entry dict.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "fix",
            "file": file,
            "symptom": symptom,
            "fix": fix,
            "tool": tool_used,
            "details": details,
        }

        # Append to RUN-LOG.md
        run_log_entry = (
            f"\n---\n"
            f"### {entry['timestamp'][:10]} â Fix: {file}\n"
            f"- **Symptom:** {symptom}\n"
            f"- **Fix:** {fix}\n"
            f"- **Tool:** {tool_used}\n"
        )
        if details:
            run_log_entry += f"- **Details:** {details}\n"

        self._append_to_vault_log("RUN_LOG", run_log_entry)

        # Update site_knowledge.json if we learned something about the page
        self._update_site_knowledge_from_fix(file, symptom, fix)

        return entry

    def log_audit(self, results: dict, issues_found: int = 0,
                  lessons: list = None) -> dict:
        """Log an audit result to RUN-LOG.md and LEARNING-LOG.md.

        Args:
            results: Audit results dict
            issues_found: Number of issues discovered
            lessons: List of lessons learned

        Returns:
            The audit log entry.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "audit",
            "issues_found": issues_found,
            "results": results,
        }

        # Append to RUN-LOG
        run_log_entry = (
            f"\n---\n"
            f"### {entry['timestamp'][:10]} â Audit\n"
            f"- **Issues found:** {issues_found}\n"
            f"- **Summary:** {json.dumps(results, indent=2)[:500]}\n"
        )
        self._append_to_vault_log("RUN_LOG", run_log_entry)

        # Append lessons to LEARNING-LOG
        if lessons:
            learning_entry = (
                f"\n---\n"
                f"### {entry['timestamp'][:10]} â Audit Lessons\n"
            )
            for lesson in lessons:
                learning_entry += f"- {lesson}\n"
            self._append_to_vault_log("LEARNING_LOG", learning_entry)

        return entry

    def log_interaction(self, message: str, response_summary: str,
                        tools_used: list = None, anticipation_hit: bool = False) -> dict:
        """Log an interaction for david_model evolution.

        Tracks whether the agent's anticipation was correct,
        which feeds back into the Theory-of-Mind accuracy metric.

        Args:
            message: What David said
            response_summary: Brief summary of agent's response
            tools_used: List of tools invoked
            anticipation_hit: Whether the ToM prediction was confirmed

        Returns:
            The interaction log entry.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "message_preview": message[:100],
            "response_summary": response_summary[:100],
            "tools_used": tools_used or [],
            "anticipation_hit": anticipation_hit,
        }

        # If anticipation was correct, strengthen the prediction in david_model
        if anticipation_hit:
            self._strengthen_prediction(message)

        return entry

    # âââââââââââââââââââââââââââââââââââââ
    # DAVID MODEL UPDATES
    # âââââââââââââââââââââââââââââââââââââ

    def update_david_model(self, section: str, key: str, value) -> bool:
        """Update a specific field in david_model.json.

        Args:
            section: Top-level key (e.g., 'decision_patterns', 'anticipated_needs')
            key: Sub-key or list index identifier
            value: New value to set or append

        Returns:
            True if update succeeded.
        """
        dm = self._read_json(MEMORY_FILES["david_model"])
        if not dm:
            return False

        if section in dm:
            if isinstance(dm[section], list):
                # Append to list if not already present
                if value not in dm[section]:
                    dm[section].append(value)
            elif isinstance(dm[section], dict):
                dm[section][key] = value
            else:
                dm[section] = value

        dm["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        dm["version"] = dm.get("version", 0) + 1
        self._write_json(MEMORY_FILES["david_model"], dm)
        return True

    def add_anticipated_need(self, trigger: str, prediction: str,
                             confidence: float = 0.5) -> bool:
        """Add a new anticipated need to david_model.json."""
        dm = self._read_json(MEMORY_FILES["david_model"])
        if not dm:
            return False

        needs = dm.get("anticipated_needs", [])

        # Check if trigger already exists â update confidence if so
        for need in needs:
            if need.get("trigger", "").lower() == trigger.lower():
                # Strengthen existing prediction
                need["confidence"] = min(1.0, need.get("confidence", 0.5) + 0.05)
                dm["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
                self._write_json(MEMORY_FILES["david_model"], dm)
                return True

        # Add new prediction
        needs.append({
            "trigger": trigger,
            "prediction": prediction,
            "confidence": confidence,
        })
        dm["anticipated_needs"] = needs
        dm["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        self._write_json(MEMORY_FILES["david_model"], dm)
        return True

    # âââââââââââââââââââââââââââââââââââââ
    # FIX PATTERN MANAGEMENT
    # âââââââââââââââââââââââââââââââââââââ

    def update_fix_pattern(self, pattern_name: str, success: bool = True) -> bool:
        """Update a fix pattern's success tracking.

        Args:
            pattern_name: Key in fix_patterns.json
            success: Whether this application was successful

        Returns:
            True if update succeeded.
        """
        fp = self._read_json(MEMORY_FILES["fix_patterns"])
        if not fp or "patterns" not in fp:
            return False

        if pattern_name in fp["patterns"]:
            pattern = fp["patterns"][pattern_name]
            applied = pattern.get("times_applied", 0) + 1
            if success:
                # Recalculate success rate
                prev_rate = pattern.get("success_rate", 1.0)
                prev_applied = pattern.get("times_applied", 0)
                if prev_applied > 0:
                    pattern["success_rate"] = (
                        (prev_rate * prev_applied + 1.0) / applied
                    )
                else:
                    pattern["success_rate"] = 1.0
            else:
                prev_rate = pattern.get("success_rate", 1.0)
                prev_applied = pattern.get("times_applied", 0)
                if prev_applied > 0:
                    pattern["success_rate"] = (
                        (prev_rate * prev_applied) / applied
                    )
            pattern["times_applied"] = applied
            fp["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
            self._write_json(MEMORY_FILES["fix_patterns"], fp)

            # Check for skill promotion eligibility
            if applied >= 10 and pattern.get("success_rate", 0) >= 0.90:
                self._check_skill_promotion(pattern_name, pattern)

            return True
        return False

    # âââââââââââââââââââââââââââââââââââââ
    # SITE KNOWLEDGE UPDATES
    # âââââââââââââââââââââââââââââââââââââ

    def update_site_knowledge(self, page: str, field: str, value) -> bool:
        """Update site_knowledge.json for a specific page.

        Args:
            page: Page filename (e.g., 'index.html')
            field: Field to update (e.g., 'known_quirks', 'common_issues')
            value: Value to set or append

        Returns:
            True if update succeeded.
        """
        sk = self._read_json(MEMORY_FILES["site_knowledge"])
        if not sk or "pages" not in sk:
            return False

        if page not in sk["pages"]:
            sk["pages"][page] = {
                "purpose": "",
                "importance": "unknown",
                "known_quirks": [],
                "common_issues": [],
            }

        page_data = sk["pages"][page]
        if field in page_data:
            if isinstance(page_data[field], list):
                if value not in page_data[field]:
                    page_data[field].append(value)
            else:
                page_data[field] = value

        sk["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        self._write_json(MEMORY_FILES["site_knowledge"], sk)
        return True

    # âââââââââââââââââââââââââââââââââââââ
    # CONSOLIDATION (Weekly / Monthly)
    # âââââââââââââââââââââââââââââââââââââ

    def run_weekly_consolidation(self) -> dict:
        """Weekly consolidation pass (Saturday night).

        - Review error_log for recurring patterns
        - Promote 3+ occurrence patterns to STYLE-EVOLUTION
        - Check fix_patterns for skill promotion eligibility
        - Summarize week's activity
        - Update david_model accuracy

        Returns:
            Summary of consolidation actions taken.
        """
        actions = {"patterns_promoted": 0, "skills_created": 0, "errors_reviewed": 0}

        # Review error_log for recurring patterns
        errors = self._read_error_log()
        error_counts = {}
        for err in errors:
            key = err.get("error_type", "unknown")
            error_counts[key] = error_counts.get(key, 0) + 1

        for error_type, count in error_counts.items():
            if count >= 3:
                # Already should be in fix_patterns â verify
                fp = self._read_json(MEMORY_FILES["fix_patterns"])
                if fp and "patterns" in fp and error_type not in fp["patterns"]:
                    # Auto-create pattern from error history
                    relevant_errors = [e for e in errors if e.get("error_type") == error_type]
                    if relevant_errors:
                        latest = relevant_errors[-1]
                        self._promote_to_fix_pattern(error_type, latest)
                        actions["patterns_promoted"] += 1

        actions["errors_reviewed"] = len(errors)

        # Check all fix_patterns for skill promotion
        fp = self._read_json(MEMORY_FILES["fix_patterns"])
        if fp and "patterns" in fp:
            for pname, pdata in fp["patterns"].items():
                if (pdata.get("times_applied", 0) >= 10 and
                        pdata.get("success_rate", 0) >= 0.90):
                    created = self._check_skill_promotion(pname, pdata)
                    if created:
                        actions["skills_created"] += 1

        # Log consolidation to LEARNING-LOG
        learning_entry = (
            f"\n---\n"
            f"### {datetime.datetime.now().strftime('%Y-%m-%d')} â Weekly Consolidation\n"
            f"- Errors reviewed: {actions['errors_reviewed']}\n"
            f"- Patterns promoted: {actions['patterns_promoted']}\n"
            f"- Skills created: {actions['skills_created']}\n"
        )
        self._append_to_vault_log("LEARNING_LOG", learning_entry)

        return actions

    def run_monthly_consolidation(self) -> dict:
        """Monthly deep consolidation.

        - Review STYLE-EVOLUTION hypothesis rules
        - Deep skill review (merge/refine/retire)
        - David Bible reflection (propose SOUL.md updates)
        - Selective forgetting (purge old error_log entries)

        Returns:
            Summary of consolidation actions.
        """
        actions = {"errors_purged": 0, "skills_reviewed": 0, "soul_proposals": []}

        # Selective forgetting: purge error_log entries > 90 days old
        # that have been promoted to fix_patterns
        errors = self._read_error_log()
        cutoff = datetime.datetime.now() - datetime.timedelta(days=90)
        fp = self._read_json(MEMORY_FILES["fix_patterns"])
        promoted_types = set(fp.get("patterns", {}).keys()) if fp else set()

        kept = []
        for err in errors:
            try:
                ts = datetime.datetime.fromisoformat(err.get("timestamp", ""))
                if ts < cutoff and err.get("error_type") in promoted_types:
                    actions["errors_purged"] += 1
                    continue
            except (ValueError, TypeError):
                pass
            kept.append(err)

        if actions["errors_purged"] > 0:
            self._rewrite_error_log(kept)

        # Count skills for review
        if os.path.isdir(SKILLS_DIR):
            actions["skills_reviewed"] = len(
                [f for f in os.listdir(SKILLS_DIR) if f.endswith(".md")]
            )

        return actions

    # âââââââââââââââââââââââââââââââââââââ
    # PRIVATE HELPERS
    # âââââââââââââââââââââââââââââââââââââ

    def _read_json(self, path: str) -> Optional[dict]:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _write_json(self, path: str, data: dict):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _append_jsonl(self, path: str, entry: dict):
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _append_to_vault_log(self, log_key: str, content: str):
        path = VAULT_LOGS.get(log_key)
        if path and os.path.isfile(path):
            with open(path, "a") as f:
                f.write(content)

    def _read_error_log(self) -> list:
        entries = []
        try:
            with open(MEMORY_FILES["error_log"], "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('{"_meta"'):
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return entries

    def _rewrite_error_log(self, entries: list):
        """Rewrite error_log.jsonl with filtered entries."""
        with open(MEMORY_FILES["error_log"], "w") as f:
            f.write('{"_meta": "TRSitekeeper Error Log â rewritten during consolidation"}\n')
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _promote_to_fix_pattern(self, error_type: str, error_entry: dict):
        """Promote a recurring error to fix_patterns.json."""
        fp = self._read_json(MEMORY_FILES["fix_patterns"])
        if not fp:
            fp = {"version": 1, "updated": "", "patterns": {}}

        if error_type not in fp.get("patterns", {}):
            fp["patterns"][error_type] = {
                "description": error_entry.get("symptom", error_type),
                "diagnostic_steps": [
                    f"Check {error_entry.get('file', 'affected file')}",
                    f"Look for: {error_entry.get('root_cause', 'root cause')}",
                ],
                "common_fixes": [error_entry.get("fix", "See error log")],
                "files_usually_involved": [error_entry.get("file", "unknown")],
                "times_applied": error_entry.get("times_seen", 3),
                "success_rate": 1.0 if error_entry.get("confidence") == "high" else 0.8,
            }
            fp["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
            self._write_json(MEMORY_FILES["fix_patterns"], fp)

    def _update_site_knowledge_from_fix(self, file: str, symptom: str, fix: str):
        """After a fix, update site_knowledge.json with what we learned."""
        sk = self._read_json(MEMORY_FILES["site_knowledge"])
        if not sk or "pages" not in sk:
            return

        # Only update if the file is a known page
        if file in sk["pages"]:
            page = sk["pages"][file]
            # Add to common_issues if not already there
            issues = page.get("common_issues", [])
            # Create a brief issue description
            brief = symptom[:60] if len(symptom) > 60 else symptom
            if brief not in issues:
                issues.append(brief)
                page["common_issues"] = issues[-10:]  # Keep last 10
                page["last_modified"] = datetime.datetime.now().strftime("%Y-%m-%d")
                sk["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
                self._write_json(MEMORY_FILES["site_knowledge"], sk)

    def _strengthen_prediction(self, message: str):
        """Strengthen relevant predictions in david_model.json when anticipation was correct."""
        dm = self._read_json(MEMORY_FILES["david_model"])
        if not dm:
            return

        msg_lower = message.lower()
        for need in dm.get("anticipated_needs", []):
            trigger = need.get("trigger", "").lower()
            if any(w in msg_lower for w in trigger.split() if len(w) > 3):
                need["confidence"] = min(1.0, need.get("confidence", 0.5) + 0.05)

        dm["updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        self._write_json(MEMORY_FILES["david_model"], dm)

    def _check_skill_promotion(self, pattern_name: str, pattern_data: dict) -> bool:
        """Check if a fix pattern should be promoted to a skill file.

        A pattern qualifies when: times_applied >= 10 AND success_rate >= 0.90

        Returns:
            True if a new skill file was created.
        """
        skill_path = os.path.join(SKILLS_DIR, f"{pattern_name}.md")
        if os.path.isfile(skill_path):
            return False  # Skill already exists

        # Generate skill file from pattern
        desc = pattern_data.get("description", pattern_name)
        diagnostics = pattern_data.get("diagnostic_steps", [])
        fixes = pattern_data.get("common_fixes", [])
        files = pattern_data.get("files_usually_involved", [])
        applied = pattern_data.get("times_applied", 0)
        rate = pattern_data.get("success_rate", 0)

        content = f"""# Skill: {pattern_name}
*Auto-generated from fix_patterns.json â promoted after {applied} applications at {rate:.0%} success rate*

## When to activate
{desc}. Activate when working on: {', '.join(files)}.

## Reasoning pattern
"""
        for i, step in enumerate(diagnostics, 1):
            content += f"{i}. {step}\n"

        content += "\n## Common fixes\n"
        for fix in fixes:
            content += f"- {fix}\n"

        content += f"""
## What NOT to do
- Don't skip the diagnostic steps â they're ordered by likelihood
- Don't assume the first fix works â verify after every change
- Check related pages/elements for the same issue

## Evolved from
fix_patterns key: {pattern_name}
Promoted to skill: {datetime.datetime.now().strftime('%Y-%m-%d')}
Applications: {applied}, Success rate: {rate:.0%}
"""

        with open(skill_path, "w") as f:
            f.write(content)

        return True


# âââââââââââââââââââââââââââââââââââââââââââââ
# STANDALONE TEST
# âââââââââââââââââââââââââââââââââââââââââââââ

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING LEARNING LOGGER")
    print("=" * 60)

    logger = LearningLogger()

    # Test error logging
    entry = logger.log_error(
        error_type="test_error",
        file="test.html",
        symptom="Test symptom",
        root_cause="Test root cause",
        fix="Test fix applied",
        confidence="high",
    )
    print(f"\nLogged error: {json.dumps(entry, indent=2)}")

    # Test fix logging
    fix_entry = logger.log_fix(
        file="test.html",
        symptom="Test alignment issue",
        fix="Added align-items: center",
        tool_used="edit_file",
    )
    print(f"\nLogged fix: {json.dumps(fix_entry, indent=2)}")

    # Show state of memory files
    for name, path in MEMORY_FILES.items():
        if os.path.isfile(path):
            size = os.path.getsize(path)
            print(f"\n{name}: {size} bytes")
        else:
            print(f"\n{name}: NOT FOUND")

    print(f"\n{'=' * 60}")
    print("TESTS COMPLETE")
    print("=" * 60)
