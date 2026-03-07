#!/usr/bin/env python3
"""
TRSitekeeper Context Loader â The Boot Sequence
================================================
Replaces flat brain.md loading with structured, layered vault memory.
Implements the Agentic OS boot sequence:
  1. KERNEL LAYER  â SOUL.md, CONFIG.md, PROCESS.md (identity, always loaded first)
  2. OPERATIONAL   â STYLE-EVOLUTION.md, CAPABILITIES.md, TASK-LOG.md
  3. EPISODES      â RUN-LOG.md (last N entries), LEARNING-LOG.md (last N lessons)
  4. LOCAL MEMORY   â error_log, fix_patterns, site_knowledge, david_model
  5. SKILLS         â context-dependent skill files from skills/ directory
  6. ON DEMAND      â CADENCE.md, full logs (only when needed)

Usage:
    from sitekeeper_context_loader import build_vault_prompt, load_vault_layer
    system_prompt = build_vault_prompt(mode="reactive")
"""

import os
import json
import glob
import datetime
from pathlib import Path
from typing import Optional

# âââââââââââââââââââââââââââââââââââââââââââââ
# PATHS
# âââââââââââââââââââââââââââââââââââââââââââââ

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(AGENT_DIR, "memory")
SKILLS_DIR = os.path.join(AGENT_DIR, "skills")
VAULT_DIR = os.path.join(AGENT_DIR, "vault")  # local vault copy synced from GitHub
BRAIN_FILE = os.path.join(AGENT_DIR, "brain.md")

# Vault file paths (local copies â synced from GitHub by the agent or manually)
VAULT_FILES = {
    # Kernel layer (PID 1 â loaded first, always)
    "SOUL": os.path.join(VAULT_DIR, "SOUL.md"),
    "CONFIG": os.path.join(VAULT_DIR, "CONFIG.md"),
    "PROCESS": os.path.join(VAULT_DIR, "PROCESS.md"),
    # Operational layer
    "STYLE_EVOLUTION": os.path.join(VAULT_DIR, "STYLE-EVOLUTION.md"),
    "CAPABILITIES": os.path.join(VAULT_DIR, "CAPABILITIES.md"),
    "TASK_LOG": os.path.join(VAULT_DIR, "TASK-LOG.md"),
    # Episode layer
    "RUN_LOG": os.path.join(VAULT_DIR, "RUN-LOG.md"),
    "LEARNING_LOG": os.path.join(VAULT_DIR, "LEARNING-LOG.md"),
    # On-demand
    "CADENCE": os.path.join(VAULT_DIR, "CADENCE.md"),
}

# Local memory file paths
MEMORY_FILES = {
    "error_log": os.path.join(MEMORY_DIR, "error_log.jsonl"),
    "fix_patterns": os.path.join(MEMORY_DIR, "fix_patterns.json"),
    "site_knowledge": os.path.join(MEMORY_DIR, "site_knowledge.json"),
    "david_model": os.path.join(MEMORY_DIR, "david_model.json"),
}


# âââââââââââââââââââââââââââââââââââââââââââââ
# FILE READERS
# âââââââââââââââââââââââââââââââââââââââââââââ

def read_file_safe(path: str) -> Optional[str]:
    """Read a file, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def read_json_safe(path: str) -> Optional[dict]:
    """Read a JSON file, return None if missing or invalid."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return None


def read_jsonl_tail(path: str, n: int = 20) -> list:
    """Read the last N lines of a JSONL file, return as list of dicts."""
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if not line or line.startswith('{"_meta"'):
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except FileNotFoundError:
        return []


def read_md_tail(path: str, n_entries: int = 10) -> str:
    """Read the last N entries from a markdown log file.
    Entries are separated by '---' or '## ' headers."""
    content = read_file_safe(path)
    if not content:
        return ""

    # Split by entry separators (--- or ## headers)
    sections = []
    current = []
    for line in content.split("\n"):
        if line.strip() == "---" or (line.startswith("## ") and current):
            if current:
                sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    # Return last N sections
    if len(sections) <= n_entries:
        return content  # Small enough to return whole thing
    return "\n".join(sections[-n_entries:])


# âââââââââââââââââââââââââââââââââââââââââââââ
# SKILL LOADER
# âââââââââââââââââââââââââââââââââââââââââââââ

def get_available_skills() -> dict:
    """Return dict of skill_name â file_path for all .md files in skills/."""
    skills = {}
    if os.path.isdir(SKILLS_DIR):
        for f in glob.glob(os.path.join(SKILLS_DIR, "*.md")):
            name = os.path.splitext(os.path.basename(f))[0]
            skills[name] = f
    return skills


def load_skills_for_context(message: str = "", mode: str = "reactive") -> str:
    """Load relevant skill files based on current context/mode.

    Args:
        message: The user's current message (used for keyword matching)
        mode: Operating mode â 'reactive', 'audit', 'consolidation'

    Returns:
        Formatted string of loaded skills for the system prompt.
    """
    available = get_available_skills()
    if not available:
        return ""

    loaded = []
    msg_lower = message.lower() if message else ""

    # Mode-based loading
    if mode == "audit" and "site_audit" in available:
        loaded.append("site_audit")
    if mode == "consolidation" and "consolidation" in available:
        loaded.append("consolidation")

    # Keyword-based loading
    keyword_map = {
        "css_diagnosis": ["css", "style", "align", "spacing", "layout", "visual", "looks weird",
                          "mobile", "responsive", "flex", "grid", "margin", "padding"],
        "data_staleness": ["stale", "data", "ddp", "scores not updating", "old data", "fresh",
                           "status.json", "trs-data", "trscode-data", "truscore-data"],
        "git_safety": ["push", "git", "commit", "deploy", "github", "conflict", "rebase"],
        "mobile_layout": ["mobile", "phone", "responsive", "viewport", "375", "768"],
        "site_audit": ["audit", "check everything", "health check", "full scan"],
    }

    for skill_name, keywords in keyword_map.items():
        if skill_name in available and skill_name not in loaded:
            if any(kw in msg_lower for kw in keywords):
                loaded.append(skill_name)

    # If nothing matched, load top 3 most general skills
    if not loaded:
        priority_order = ["css_diagnosis", "data_staleness", "git_safety"]
        for s in priority_order:
            if s in available:
                loaded.append(s)
            if len(loaded) >= 3:
                break

    # Cap at 3 skills to manage token budget
    loaded = loaded[:3]

    # Build the skills block
    if not loaded:
        return ""

    parts = ["\n## LOADED SKILLS (Reasoning Patterns)\n"]
    for skill_name in loaded:
        content = read_file_safe(available[skill_name])
        if content:
            parts.append(f"### Skill: {skill_name}\n{content.strip()}\n")

    return "\n".join(parts)


# âââââââââââââââââââââââââââââââââââââââââââââ
# THEORY-OF-MIND PRE-PROCESSOR
# âââââââââââââââââââââââââââââââââââââââââââââ

def build_tom_context(message: str = "") -> str:
    """Build Theory-of-Mind context injection for the system prompt.
    Loads david_model.json and generates anticipation guidance."""
    dm = read_json_safe(MEMORY_FILES["david_model"])
    if not dm:
        return ""

    parts = ["\n## THEORY-OF-MIND â Anticipate David\n"]
    parts.append("Before responding, silently model David's current state:")

    # Inject communication style
    comm = dm.get("communication_style", {})
    if comm:
        parts.append(f"- Communication: {comm.get('tone', 'Direct, no fluff')}")
        parts.append(f"- He prefers: {comm.get('prefers', 'Action over explanation')}")
        parts.append(f"- He dislikes: {comm.get('dislikes', 'Being told everything is fine when it is not')}")
        if comm.get("voice_to_text"):
            parts.append(f"- Voice-to-text: {comm.get('note', 'Interpret intent, not literal words')}")

    # Inject anticipated needs (match against message)
    anticipated = dm.get("anticipated_needs", [])
    msg_lower = message.lower() if message else ""
    relevant_predictions = []
    for need in anticipated:
        trigger = need.get("trigger", "").lower()
        # Simple keyword matching for trigger relevance
        trigger_words = trigger.split()
        if any(w in msg_lower for w in trigger_words if len(w) > 3):
            relevant_predictions.append(need)

    if relevant_predictions:
        parts.append("\nPREDICTED NEEDS (based on this message):")
        for p in relevant_predictions:
            conf = p.get("confidence", 0)
            parts.append(f"  - {p['prediction']} (confidence: {conf:.0%})")

    # Inject emotional triggers awareness
    triggers = dm.get("emotional_triggers", {})
    frustrated_by = triggers.get("frustrated_by", [])
    if frustrated_by:
        parts.append(f"\nAVOID triggering frustration: {'; '.join(frustrated_by[:3])}")

    # Inject inner voice questions
    inner_voice = dm.get("inner_voice_questions", [])
    if inner_voice:
        parts.append(f"\nDavid's inner filter: {'; '.join(inner_voice[:2])}")

    parts.append("\nACT on the explicit request AND the predicted unspoken need. Fix first, explain after.\n")

    return "\n".join(parts)


# âââââââââââââââââââââââââââââââââââââââââââââ
# ERROR HISTORY QUERY
# âââââââââââââââââââââââââââââââââââââââââââââ

def query_error_history(message: str = "") -> str:
    """Check error_log for relevant past errors. Returns context for 'never repeat a mistake.'"""
    errors = read_jsonl_tail(MEMORY_FILES["error_log"], n=50)
    if not errors or not message:
        return ""

    msg_lower = message.lower()
    relevant = []
    for err in errors:
        # Match on error_type, symptom, file
        searchable = f"{err.get('error_type', '')} {err.get('symptom', '')} {err.get('file', '')}".lower()
        if any(word in searchable for word in msg_lower.split() if len(word) > 3):
            relevant.append(err)

    if not relevant:
        return ""

    parts = ["\n## PAST ERRORS (Never Repeat These)\n"]
    for err in relevant[-5:]:  # Last 5 relevant
        parts.append(
            f"- [{err.get('timestamp', '?')}] {err.get('symptom', '?')} â "
            f"Fix: {err.get('fix', '?')} (confidence: {err.get('confidence', '?')})"
        )
    parts.append("")
    return "\n".join(parts)


# âââââââââââââââââââââââââââââââââââââââââââââ
# MAIN BUILDER â THE BOOT SEQUENCE
# âââââââââââââââââââââââââââââââââââââââââââââ

def build_vault_prompt(message: str = "", mode: str = "reactive") -> str:
    """Build the complete system prompt from vault memory layers.

    This is THE BOOT SEQUENCE. Loading order matters â SOUL.md is PID 1.

    Args:
        message: Current user message (for context-dependent loading)
        mode: 'reactive' (default), 'audit', or 'consolidation'

    Returns:
        Complete system prompt string assembled from all memory layers.
    """
    sections = []
    vault_loaded = []
    vault_missing = []

    # ââ LAYER 1: KERNEL (Identity â always loaded FIRST) ââ
    sections.append("=" * 60)
    sections.append("TRSITEKEEPER â VAULT-POWERED SYSTEM PROMPT")
    sections.append(f"Boot time: {datetime.datetime.now().isoformat()}")
    sections.append(f"Mode: {mode}")
    sections.append("=" * 60)

    # SOUL.md is PID 1 â the init process. Loaded before anything else.
    for key, label in [("SOUL", "SOUL â Identity & David's Philosophy"),
                       ("CONFIG", "CONFIG â Technical Configuration"),
                       ("PROCESS", "PROCESS â Operating Procedures")]:
        content = read_file_safe(VAULT_FILES[key])
        if content:
            sections.append(f"\n## {label}\n{content.strip()}")
            vault_loaded.append(key)
        else:
            vault_missing.append(key)

    # ââ LAYER 2: OPERATIONAL (Knowledge â always loaded) ââ
    for key, label in [("STYLE_EVOLUTION", "STYLE EVOLUTION â Design & Content Rules"),
                       ("CAPABILITIES", "CAPABILITIES â What I Can Do"),
                       ("TASK_LOG", "TASK LOG â Active Tasks & Priorities")]:
        content = read_file_safe(VAULT_FILES[key])
        if content:
            sections.append(f"\n## {label}\n{content.strip()}")
            vault_loaded.append(key)
        else:
            vault_missing.append(key)

    # ââ LAYER 3: EPISODES (Latest N â not the full log) ââ
    run_log_tail = read_md_tail(VAULT_FILES["RUN_LOG"], n_entries=10)
    if run_log_tail:
        sections.append(f"\n## RUN LOG (Last 10 Entries)\n{run_log_tail.strip()}")
        vault_loaded.append("RUN_LOG")

    learning_tail = read_md_tail(VAULT_FILES["LEARNING_LOG"], n_entries=5)
    if learning_tail:
        sections.append(f"\n## LEARNING LOG (Last 5 Lessons)\n{learning_tail.strip()}")
        vault_loaded.append("LEARNING_LOG")

    # ââ LAYER 4: LOCAL MEMORY (Hot cache) ââ
    # Fix patterns
    fp = read_json_safe(MEMORY_FILES["fix_patterns"])
    if fp and "patterns" in fp:
        sections.append("\n## FIX PATTERNS (Learned from experience)")
        for pname, pdata in fp["patterns"].items():
            sections.append(
                f"- **{pname}**: {pdata.get('description', '')} "
                f"(applied {pdata.get('times_applied', 0)}x, "
                f"success rate {pdata.get('success_rate', 0):.0%})"
            )

    # Site knowledge (compact summary)
    sk = read_json_safe(MEMORY_FILES["site_knowledge"])
    if sk and "pages" in sk:
        sections.append("\n## SITE KNOWLEDGE MAP")
        for page, info in sk["pages"].items():
            quirks = info.get("known_quirks", [])
            issues = info.get("common_issues", [])
            note = ""
            if quirks:
                note += f" Quirks: {'; '.join(quirks[:2])}."
            if issues:
                note += f" Common issues: {', '.join(issues[:3])}."
            sections.append(f"- **{page}**: {info.get('purpose', '')}{note}")

    # Recent errors
    error_context = query_error_history(message)
    if error_context:
        sections.append(error_context)

    # ââ LAYER 5: SKILLS (Context-dependent) ââ
    skills_context = load_skills_for_context(message, mode)
    if skills_context:
        sections.append(skills_context)

    # ââ LAYER 6: THEORY-OF-MIND ââ
    tom_context = build_tom_context(message)
    if tom_context:
        sections.append(tom_context)

    # ââ BOOT STATUS ââ
    sections.append("\n" + "=" * 60)
    sections.append("BOOT STATUS")
    sections.append(f"Vault files loaded: {', '.join(vault_loaded)}")
    if vault_missing:
        sections.append(f"Vault files MISSING: {', '.join(vault_missing)} â check vault/ directory")
    sections.append(f"Skills loaded: {skills_context.count('### Skill:') if skills_context else 0}")
    sections.append(f"Theory-of-Mind: {'ACTIVE' if tom_context else 'INACTIVE (david_model.json missing)'}")
    sections.append("=" * 60)

    # ââ CORE RULES (always appended last â recency bias helps) ââ
    sections.append("""
RULES (Always Follow):
1. "status" = call check_status. Never touch files for a status check.
2. Only edit files when David explicitly asks for a change.
3. ALWAYS backup before editing. No exceptions.
4. Prefer edit_file (surgical find/replace) over write_file (full overwrite).
5. Keep responses SHORT â David reads on his phone via Telegram.
6. Never make up data. Always use tools for real info.
7. When David sends a screenshot, analyze it carefully. Identify the exact file and code. Propose a specific fix.
8. For protected operations (run_ddp only), explain what you'll do and wait for approval.
9. When pushing to git, always git pull --rebase first. Always include agent_activity.json.
10. Before attempting ANY fix, check your error history â have you seen this before?
11. After EVERY fix, log what you did. The learning logger will record it.
12. Address David's explicit request AND his predicted unspoken need. Fix first, explain after.
""")

    return "\n".join(sections)


def build_fallback_prompt() -> str:
    """Fallback: load brain.md if vault is unavailable."""
    brain = read_file_safe(BRAIN_FILE)
    if not brain:
        brain = "No brain file found."
    return f"""You are TRSitekeeper â the AI gatekeeper for trainingrun.ai.
Your personality: Direct, sharp, reliable. You know this site inside out.

{brain}

RULES:
1. "status" = call check_status.
2. ALWAYS backup before editing.
3. Keep responses SHORT.
4. Never make up data.
"""


# âââââââââââââââââââââââââââââââââââââââââââââ
# PUBLIC API
# âââââââââââââââââââââââââââââââââââââââââââââ

def get_system_prompt(message: str = "", mode: str = "reactive",
                      use_vault: bool = True) -> str:
    """Main entry point. Returns the system prompt.

    Args:
        message: Current user message for context-dependent loading
        mode: 'reactive', 'audit', or 'consolidation'
        use_vault: If True, use vault-based prompt. If False, fall back to brain.md.

    Returns:
        Complete system prompt string.
    """
    if not use_vault:
        return build_fallback_prompt()

    # Check if vault directory exists with at least SOUL.md
    if os.path.isfile(VAULT_FILES["SOUL"]):
        return build_vault_prompt(message, mode)
    else:
        # Vault not set up yet â fall back to brain.md
        print("[context_loader] WARN: Vault not found, falling back to brain.md")
        return build_fallback_prompt()


# âââââââââââââââââââââââââââââââââââââââââââââ
# STANDALONE TEST
# âââââââââââââââââââââââââââââââââââââââââââââ

if __name__ == "__main__":
    """Run this directly to test the boot sequence."""
    print("=" * 60)
    print("TESTING CONTEXT LOADER â BOOT SEQUENCE")
    print("=" * 60)

    # Check what's available
    print(f"\nVault dir: {VAULT_DIR}")
    print(f"  Exists: {os.path.isdir(VAULT_DIR)}")
    for key, path in VAULT_FILES.items():
        exists = os.path.isfile(path)
        print(f"  {key}: {'OK' if exists else 'MISSING'} â {path}")

    print(f"\nMemory dir: {MEMORY_DIR}")
    for key, path in MEMORY_FILES.items():
        exists = os.path.isfile(path)
        print(f"  {key}: {'OK' if exists else 'MISSING'} â {path}")

    print(f"\nSkills dir: {SKILLS_DIR}")
    skills = get_available_skills()
    for name, path in skills.items():
        print(f"  {name}: {path}")
    if not skills:
        print("  (no skills yet)")

    # Build the prompt
    prompt = get_system_prompt(message="fix the alignment on mobile", mode="reactive")
    print(f"\n{'=' * 60}")
    print(f"GENERATED PROMPT ({len(prompt)} chars, ~{len(prompt)//4} tokens)")
    print("=" * 60)
    print(prompt[:3000])
    if len(prompt) > 3000:
        print(f"\n... ({len(prompt) - 3000} more characters)")
