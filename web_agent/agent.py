#!/usr/bin/env python3
"""
TR Web Manager Agent v2.0
=========================
A local AI agent that manages trainingrun.ai via Telegram + Ollama.

- Communicates with David via Telegram
- Uses local Ollama model (qwen2.5-coder:32b for reliable code edits)
- Has persistent memory via brain.md
- Full write access with Telegram approval gates
- Manages DDPs, files, backups, and GitHub for the site

Setup: See README_AGENT.md
Run:   python3 agent.py
Stop:  Ctrl+C
"""

import os
import sys
import json
import time
import subprocess
import requests
import datetime
import re
import shutil
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# ─────────────────────────────────────────────
# CONFIG — edit these or set as env vars
# ─────────────────────────────────────────────

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OLLAMA_MODEL     = os.getenv("TR_AGENT_MODEL", "qwen2.5-coder:32b")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REPO_PATH        = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
BRAIN_FILE       = os.path.join(os.path.dirname(__file__), "brain.md")
MEMORY_FILE      = os.path.join(os.path.dirname(__file__), "memory_log.jsonl")
ACTIVITY_FILE    = os.path.join(REPO_PATH, "agent_activity.json")
BACKUP_DIR       = os.path.join(REPO_PATH, "backups")
BRIDGE_PORT      = 7432

# Full Python path — required for cron compatibility
PYTHON_PATH      = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

# ─────────────────────────────────────────────
# BRIDGE SERVER — serves agent_activity.json
# to hq.html running locally on David's Mac
# ─────────────────────────────────────────────

# Maps tool names → HQ room location
TOOL_ROOM_MAP = {
    "check_status":  "ddp_room",
    "run_ddp":       "ddp_room",
    "read_file":     "office",
    "write_file":    "office",
    "edit_file":     "office",
    "backup_file":   "office",
    "git_push":      "office",
    "list_files":    "office",
    "remember":      "office",
    "read_log":      "ddp_room",
    "site_health":   "ddp_room",
}

def write_activity(action: str, location: str = "office", status: str = "active"):
    """Write current agent state to agent_activity.json for the HQ bridge."""
    try:
        with open(ACTIVITY_FILE) as f:
            existing = json.load(f)
        last_actions = existing.get("last_actions", [])
    except Exception:
        last_actions = []

    timestamp = datetime.datetime.now().strftime("%-I:%M %p")
    last_actions.insert(0, {"time": timestamp, "text": action})
    last_actions = last_actions[:10]

    activity = {
        "status":       status,
        "agent":        "web_manager",
        "location":     location,
        "action":       action,
        "last_actions": last_actions,
        "last_updated": datetime.datetime.now().isoformat()
    }
    try:
        with open(ACTIVITY_FILE, "w") as f:
            json.dump(activity, f, indent=2)
    except Exception as e:
        print(f"[Bridge] Failed to write activity: {e}")


class BridgeHandler(BaseHTTPRequestHandler):
    """Serves agent_activity.json to hq.html with CORS headers."""
    def do_GET(self):
        try:
            with open(ACTIVITY_FILE) as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        except Exception:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress server logs


def start_bridge():
    """Start the local bridge server in a background thread."""
    try:
        server = HTTPServer(("localhost", BRIDGE_PORT), BridgeHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[Bridge] Running at http://localhost:{BRIDGE_PORT}")
    except Exception as e:
        print(f"[Bridge] Could not start server: {e}")


# ─────────────────────────────────────────────
# TELEGRAM HELPERS
# ─────────────────────────────────────────────

def tg_send(text: str):
    """Send a message to David via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Split long messages (Telegram limit is 4096 chars)
    chunks = [text[i:i+3900] for i in range(0, len(text), 3900)]
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Telegram send error] {e}")


def tg_get_updates(offset: int) -> list:
    """Poll Telegram for new messages."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 30, "limit": 10}
    try:
        resp = requests.get(url, params=params, timeout=40)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        print(f"[Telegram poll error] {e}")
        return []


# ─────────────────────────────────────────────
# MEMORY / BRAIN
# ─────────────────────────────────────────────

def load_brain() -> str:
    """Load the brain.md file — the agent's persistent memory."""
    try:
        with open(BRAIN_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "No brain file found. Operating with default knowledge only."


def append_memory(key: str, value: str):
    """Append a new memory to the memory log and brain.md."""
    timestamp = datetime.datetime.now().strftime("%b %Y")
    entry = {"timestamp": timestamp, "key": key, "value": value}

    # Append to structured log
    with open(MEMORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also append to brain.md memory section
    try:
        with open(BRAIN_FILE, "r") as f:
            content = f.read()
        new_line = f"- [{timestamp}] {key}: {value}\n"
        content = content + new_line
        with open(BRAIN_FILE, "w") as f:
            f.write(content)
        print(f"[Memory] Saved: {key}")
    except Exception as e:
        print(f"[Memory write error] {e}")


# ─────────────────────────────────────────────
# TOOLS — what the agent can do
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_status",
            "description": "Check the live status of all 5 DDPs by reading status.json. Returns each DDP's last run time, status (success/failed/disabled), and top score.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of any file in the trainingrun-site repo. Use this to check code, HTML, configs, or logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from repo root, e.g. 'status.json' or 'agent_trs.py' or 'web_agent/brain.md'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the trainingrun-site repo or a subdirectory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subdir": {
                        "type": "string",
                        "description": "Optional subdirectory to list. Leave empty for repo root."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Make a surgical edit to a file — find specific text and replace it. Much safer than write_file because it only changes what needs changing. REQUIRES DAVID'S APPROVAL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from repo root"},
                    "find": {"type": "string", "description": "Exact text to find in the file (must match exactly)"},
                    "replace": {"type": "string", "description": "Text to replace it with"},
                    "description": {"type": "string", "description": "Plain English description of what this change does"}
                },
                "required": ["path", "find", "replace", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write an entire file in the repo. Use edit_file instead for small changes. Only use write_file for creating new files or complete rewrites. REQUIRES DAVID'S APPROVAL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from repo root"},
                    "content": {"type": "string", "description": "Full new content of the file"},
                    "description": {"type": "string", "description": "Plain English description of what this change does"}
                },
                "required": ["path", "content", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backup_file",
            "description": "Create a timestamped backup of a file before making changes. Backups go to ~/trainingrun-site/backups/. Use this BEFORE any risky edit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from repo root to the file to back up"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Stage specific files, commit with a message, pull --rebase, and push to GitHub. REQUIRES DAVID'S APPROVAL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths (relative to repo root) to stage and commit"
                    },
                    "message": {"type": "string", "description": "Git commit message"}
                },
                "required": ["files", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_ddp",
            "description": "Manually trigger one or all DDPs via daily_runner.py. REQUIRES DAVID'S APPROVAL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Which DDP to run: 'all', 'trs', 'trscode', 'truscore', 'trfcast', or 'tragents'"
                    }
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save something David told me to persistent memory so I never forget it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short label for what was learned"},
                    "value": {"type": "string", "description": "What was learned"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_log",
            "description": "Read the DDP run log to check for errors or recent activity.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "site_health",
            "description": "Run a quick health check — verifies all 5 JSON data files exist, checks status.json for failures, confirms last push time in index.html, and reports any issues.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


# ─────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────

def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return its result as a string."""

    if name == "check_status":
        status_path = os.path.join(REPO_PATH, "status.json")
        try:
            with open(status_path) as f:
                data = json.load(f)
            agents = data.get("agents", {})
            lines = [f"📊 Mission Control — {data.get('last_updated', 'unknown')}\n"]
            for key, agent in agents.items():
                emoji = agent.get("emoji", "•")
                status = agent.get("status", "unknown")
                last_run = agent.get("last_run", "never")
                top_model = agent.get("top_model", "—")
                top_score = agent.get("top_score")
                sources_hit = agent.get("sources_hit", "?")
                sources_total = agent.get("sources_total", "?")
                models_qual = agent.get("models_qualified", "?")
                score_str = f"{top_score:.1f}" if top_score else "—"
                icon = "✅" if status == "success" else ("❌" if status == "failed" else "⚫")
                lines.append(
                    f"{icon} {emoji} <b>{key}</b>\n"
                    f"   Last: {last_run}\n"
                    f"   Sources: {sources_hit}/{sources_total} | Models: {models_qual}\n"
                    f"   #1: {top_model} ({score_str})"
                )
            return "\n".join(lines)
        except FileNotFoundError:
            return "status.json not found in repo."
        except Exception as e:
            return f"Error reading status.json: {e}"

    elif name == "read_file":
        path = args.get("path", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            with open(full_path, "r") as f:
                content = f.read()
            if len(content) > 3000:
                content = content[:3000] + f"\n\n[... truncated — {len(content)} total chars]"
            return f"📄 {path}:\n\n{content}"
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading {path}: {e}"

    elif name == "list_files":
        subdir = args.get("subdir", "")
        target = os.path.join(REPO_PATH, subdir)
        try:
            files = []
            for root, dirs, filenames in os.walk(target):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'backups')]
                for fname in filenames:
                    if not fname.startswith('.'):
                        rel = os.path.relpath(os.path.join(root, fname), REPO_PATH)
                        files.append(rel)
            return f"📁 Files in {'repo root' if not subdir else subdir}:\n" + "\n".join(sorted(files))
        except Exception as e:
            return f"Error listing files: {e}"

    elif name == "edit_file":
        # SURGICAL EDIT — find and replace specific text
        # This is a WRITE operation — caller must handle approval gate
        path = args.get("path", "")
        find_text = args.get("find", "")
        replace_text = args.get("replace", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            with open(full_path, "r") as f:
                content = f.read()
            if find_text not in content:
                return f"❌ Could not find the specified text in {path}. No changes made."
            count = content.count(find_text)
            if count > 1:
                return f"⚠️ Found {count} matches in {path}. Please provide more specific text to match exactly one location."
            new_content = content.replace(find_text, replace_text, 1)
            with open(full_path, "w") as f:
                f.write(new_content)
            return f"✅ Edited {path}: replaced {len(find_text)} chars with {len(replace_text)} chars."
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error editing {path}: {e}"

    elif name == "write_file":
        # Full file write — caller must handle approval gate
        path = args.get("path", "")
        content = args.get("content", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            return f"✅ Written: {path} ({len(content)} chars)"
        except Exception as e:
            return f"Error writing {path}: {e}"

    elif name == "backup_file":
        path = args.get("path", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            if not os.path.exists(full_path):
                return f"❌ File not found: {path}"
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(path)
            name_part, ext = os.path.splitext(filename)
            backup_name = f"{name_part}_{timestamp}{ext}"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            shutil.copy2(full_path, backup_path)
            size = os.path.getsize(backup_path)
            return f"✅ Backed up: {path} → backups/{backup_name} ({size:,} bytes)"
        except Exception as e:
            return f"Error backing up {path}: {e}"

    elif name == "git_push":
        files = args.get("files", [])
        message = args.get("message", "Update from Web Manager")
        try:
            # Stage files
            for f in files:
                result = subprocess.run(
                    ["git", "add", f],
                    cwd=REPO_PATH, capture_output=True, text=True
                )
                if result.returncode != 0:
                    return f"❌ git add failed for {f}: {result.stderr}"

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=REPO_PATH, capture_output=True, text=True
            )
            if result.returncode != 0:
                if "nothing to commit" in result.stdout + result.stderr:
                    return "ℹ️ Nothing to commit — files unchanged."
                return f"❌ git commit failed: {result.stderr}"

            # Pull rebase BEFORE push (CRITICAL — Production Bible rule)
            result = subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=REPO_PATH, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"⚠️ git pull --rebase failed: {result.stderr}\nCommit is saved locally. Try manual push."

            # Push
            result = subprocess.run(
                ["git", "push"],
                cwd=REPO_PATH, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"❌ git push failed: {result.stderr}"

            return f"✅ Pushed to GitHub.\nFiles: {', '.join(files)}\nCommit: {message}"
        except Exception as e:
            return f"Error during git push: {e}"

    elif name == "run_ddp":
        target = args.get("target", "all")
        cmd = [PYTHON_PATH, "daily_runner.py"]
        if target != "all":
            cmd += ["--score", target]
        try:
            result = subprocess.run(
                cmd, cwd=REPO_PATH, capture_output=True, text=True, timeout=900
            )
            output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            if result.returncode != 0:
                return f"❌ DDP run failed:\n{result.stderr[-1000:]}"
            return f"✅ DDP run complete ({target}):\n{output}"
        except subprocess.TimeoutExpired:
            return "⏱ DDP run timed out after 15 minutes."
        except Exception as e:
            return f"Error running DDP: {e}"

    elif name == "remember":
        key = args.get("key", "note")
        value = args.get("value", "")
        append_memory(key, value)
        return f"✅ Remembered: {key} → {value}"

    elif name == "read_log":
        log_path = os.path.join(REPO_PATH, "ddp.log")
        try:
            with open(log_path, "r") as f:
                content = f.read()
            # Last 3000 chars
            if len(content) > 3000:
                content = "...\n" + content[-3000:]
            return f"📋 DDP Log (recent):\n\n{content}"
        except FileNotFoundError:
            return "ddp.log not found. Has the cron run yet?"
        except Exception as e:
            return f"Error reading log: {e}"

    elif name == "site_health":
        issues = []
        checks_passed = 0

        # Check all 5 data JSON files exist
        data_files = {
            "trs-data.json": "TRSbench",
            "trscode-data.json": "TRScode",
            "truscore-data.json": "TRUscore",
            "trf-data.json": "TRFcast",
            "tragent-data.json": "TRAgents",
        }
        for fname, label in data_files.items():
            fpath = os.path.join(REPO_PATH, fname)
            if os.path.exists(fpath):
                checks_passed += 1
            else:
                issues.append(f"❌ Missing: {fname} ({label})")

        # Check status.json for failures
        status_path = os.path.join(REPO_PATH, "status.json")
        try:
            with open(status_path) as f:
                sdata = json.load(f)
            for key, agent in sdata.get("agents", {}).items():
                if agent.get("status") == "failed":
                    issues.append(f"❌ {key} last run FAILED: {agent.get('error', 'unknown')}")
                elif agent.get("status") == "success":
                    checks_passed += 1
                # Check if data is stale (more than 36 hours old)
                last_run = agent.get("last_run", "")
                if last_run:
                    try:
                        lr = datetime.datetime.fromisoformat(last_run)
                        age = datetime.datetime.now() - lr
                        if age.total_seconds() > 36 * 3600:
                            issues.append(f"⚠️ {key} data is stale ({age.days}d {age.seconds//3600}h old)")
                    except Exception:
                        pass
        except Exception as e:
            issues.append(f"❌ Cannot read status.json: {e}")

        # Check index.html push timestamp
        index_path = os.path.join(REPO_PATH, "index.html")
        try:
            with open(index_path, "r") as f:
                idx_content = f.read()
            m = re.search(r"var LAST_PUSH_TIME\s*=\s*'([^']*)'", idx_content)
            if m:
                checks_passed += 1
                push_time = m.group(1)
            else:
                issues.append("⚠️ LAST_PUSH_TIME not found in index.html")
                push_time = "unknown"
        except Exception:
            issues.append("❌ Cannot read index.html")
            push_time = "unknown"

        # Build report
        if issues:
            report = f"🔍 Site Health: {checks_passed} OK, {len(issues)} issues\n\n"
            report += "\n".join(issues)
            report += f"\n\nLast push: {push_time}"
        else:
            report = f"✅ Site Health: All {checks_passed} checks passed!\nLast push: {push_time}"

        return report

    return f"Unknown tool: {name}"


# ─────────────────────────────────────────────
# WRITE-PROTECTED TOOLS (require approval)
# ─────────────────────────────────────────────

PROTECTED_TOOLS = {"write_file", "edit_file", "git_push", "run_ddp"}


# ─────────────────────────────────────────────
# OLLAMA INTERFACE
# ─────────────────────────────────────────────

def ollama_chat(messages: list) -> dict:
    """Send messages to Ollama and get a response with optional tool calls."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Ollama. Is it running? Try: ollama serve"}
    except Exception as e:
        return {"error": str(e)}


def build_system_prompt() -> str:
    brain = load_brain()
    return f"""You are the TR Web Manager — the AI web manager for trainingrun.ai. You run locally on David's MacBook Pro M4 via Ollama (qwen2.5-coder:32b).

Your personality: Direct, reliable, no-BS. You know this site inside out. You take your job seriously. You are David's most trusted employee.

Your role: Manage the site, monitor DDPs, handle GitHub, make code edits, run backups, support David's requests.

Here is your complete memory and knowledge base:

{brain}

---

TOOL SELECTION GUIDE — match David's message to the correct tool:

| David says | You do |
|---|---|
| "status" / "check status" / "how are the DDPs" | call check_status |
| "health" / "site health" / "anything broken" | call site_health |
| "read [file]" / "show me [file]" | call read_file |
| "list files" / "what files" | call list_files |
| "check the log" / "show log" | call read_log |
| "remember [x]" | call remember |
| "back up [file]" / "backup [file]" | call backup_file |
| "change [X] to [Y] in [file]" | call backup_file FIRST, then edit_file (needs YES) |
| "edit [file]" / "change [file]" / "fix [file]" | call backup_file FIRST, then edit_file (needs YES) |
| "create [file]" / "write [file]" | call write_file (needs YES) |
| "push" / "push to github" | call git_push (needs YES) |
| "run [DDP name]" / "run the DDPs" | call run_ddp (needs YES) |

CRITICAL RULES — read every one:
1. "status" ALWAYS means call check_status. Never call write_file for a status request.
2. For ANY file edit, ALWAYS backup the file first using backup_file before making changes.
3. Prefer edit_file over write_file — surgical edits are safer than full file rewrites.
4. ONLY call write_file when creating a NEW file or when the change is so large that edit_file won't work.
5. NEVER call write_file or edit_file unless David EXPLICITLY asks you to change something.
6. Keep responses short — David reads on his phone.
7. Use emojis sparingly (✅ ❌ ⚠️).
8. Never make up data — always use tools to get real information.
9. Each message from David is a NEW independent request. Do not carry over tasks from previous messages.
10. When pushing to git, ALWAYS use git pull --rebase before push.
"""


# ─────────────────────────────────────────────
# APPROVAL GATE STATE
# ─────────────────────────────────────────────

pending_approval = None  # {"tool": str, "args": dict, "description": str}


def request_approval(tool_name: str, args: dict) -> str:
    """Format an approval request message for Telegram."""
    global pending_approval

    if tool_name == "edit_file":
        find_preview = args.get('find', '')[:80]
        replace_preview = args.get('replace', '')[:80]
        desc = (
            f"Edit file: <b>{args.get('path')}</b>\n"
            f"Reason: {args.get('description', '—')}\n"
            f"Find: <code>{find_preview}</code>\n"
            f"Replace: <code>{replace_preview}</code>"
        )
    elif tool_name == "write_file":
        content = args.get('content', '')
        preview = content[:120].replace('<', '&lt;').replace('>', '&gt;') + ('...' if len(content) > 120 else '')
        desc = (
            f"Write file: <b>{args.get('path')}</b>\n"
            f"Size: <b>{len(content)} chars</b>\n"
            f"Reason: {args.get('description', '—')}\n"
            f"Preview: <code>{preview}</code>"
        )
    elif tool_name == "git_push":
        desc = f"Push to GitHub:\nFiles: {', '.join(args.get('files', []))}\nCommit: {args.get('message', '')}"
    elif tool_name == "run_ddp":
        desc = f"Run DDP: <b>{args.get('target', 'all')}</b>"
    else:
        desc = f"Execute: {tool_name}"

    pending_approval = {"tool": tool_name, "args": args}

    return f"🔐 <b>APPROVAL NEEDED</b>\n\n{desc}\n\nReply <b>YES</b> to approve or <b>NO</b> to cancel."


def is_approval(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "yeah", "yep", "go", "do it", "approved", "approve")


def is_rejection(text: str) -> bool:
    return text.strip().lower() in ("no", "n", "nope", "cancel", "stop", "abort")


# ─────────────────────────────────────────────
# KEYWORD INTERCEPT — handle common commands
# directly in Python, never send to Ollama.
# This prevents the model hallucinating wrong tools.
# ─────────────────────────────────────────────

def keyword_intercept(text: str):
    """
    Check if text matches a known command pattern.
    Returns (tool_name, args) if matched, or None if Ollama should handle it.
    """
    t = text.strip().lower()

    # STATUS
    if t in ("status", "check status", "ddp status", "how are the ddps",
             "what's the status", "whats the status", "show status", "s"):
        return ("check_status", {})

    # HEALTH CHECK
    if t in ("health", "site health", "check health", "anything broken",
             "health check", "is the site ok", "site ok"):
        return ("site_health", {})

    # LOG
    if any(k in t for k in ("show log", "check log", "ddp log", "read log")):
        return ("read_log", {})
    if t == "log":
        return ("read_log", {})

    # LIST FILES
    if any(k in t for k in ("list files", "what files", "show files", "ls")):
        return ("list_files", {})

    # READ BRAIN
    if any(k in t for k in ("brain", "show brain", "read brain", "memory", "show memory")):
        return ("read_file", {"path": "web_agent/brain.md"})

    return None  # Let Ollama handle it


# ─────────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────────

def run():
    global pending_approval

    print("=" * 50)
    print("  TR Web Manager v2.0 — Starting Up")
    print(f"  Model: {OLLAMA_MODEL}")
    print(f"  Repo:  {REPO_PATH}")
    print(f"  Brain: {BRAIN_FILE}")
    print(f"  Backups: {BACKUP_DIR}")
    print("=" * 50)

    # Validate config
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set.")
        print("   export TELEGRAM_TOKEN='your_token'")
        print("   export TELEGRAM_CHAT_ID='your_chat_id'")
        sys.exit(1)

    if not os.path.exists(REPO_PATH):
        print(f"❌ ERROR: Repo not found at {REPO_PATH}")
        print(f"   Set TR_REPO_PATH env var if your repo is in a different location.")
        sys.exit(1)

    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Start the HQ bridge server
    start_bridge()

    # Set initial idle state
    write_activity("Online and ready", location="office", status="idle")

    # Announce startup
    tg_send("🟢 <b>Web Manager v2.0 online.</b>\nModel: qwen2.5-coder:32b\nReady for your instructions.\n\n<code>status</code> — check DDPs\n<code>health</code> — site health check\n<code>log</code> — view DDP log")
    print("✅ Startup message sent to Telegram. Polling for messages...")

    conversation_history = []

    # Skip all old Telegram messages on startup — only process NEW ones
    print("[Startup] Skipping old Telegram messages...")
    old_updates = tg_get_updates(0)
    if old_updates:
        offset = old_updates[-1]["update_id"] + 1
        print(f"[Startup] Skipped {len(old_updates)} old messages. Offset: {offset}")
    else:
        offset = 0
    print("[Startup] Ready for new messages.")

    while True:
        try:
            updates = tg_get_updates(offset)

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = str(message.get("chat", {}).get("id", ""))

                # Only respond to David's chat
                if chat_id != str(TELEGRAM_CHAT_ID):
                    continue

                if not text:
                    continue

                print(f"\n[David] {text}")

                # ── APPROVAL GATE HANDLING ──
                if pending_approval:
                    if is_approval(text):
                        tool = pending_approval["tool"]
                        args = pending_approval["args"]
                        pending_approval = None
                        tg_send(f"✅ Approved. Executing {tool}...")
                        location = TOOL_ROOM_MAP.get(tool, "office")
                        write_activity(f"Executing: {tool}", location=location, status="active")
                        result = execute_tool(tool, args)
                        write_activity(f"Done: {tool}", location="office", status="idle")
                        print(f"[Tool: {tool}] {result[:200]}")
                        tg_send(result)
                        continue

                    elif is_rejection(text):
                        pending_approval = None
                        write_activity("Approval cancelled", location="office", status="idle")
                        tg_send("❌ Cancelled. What else can I help with?")
                        continue

                    else:
                        # Unclear — re-ask
                        tg_send("⚠️ Still waiting on approval. Reply <b>YES</b> or <b>NO</b>.")
                        continue

                # ── KEYWORD INTERCEPT — handle common commands without Ollama ──
                intercept = keyword_intercept(text)
                if intercept:
                    tool_name, tool_args = intercept
                    print(f"[Intercept] {tool_name} matched for: '{text}'")
                    location = TOOL_ROOM_MAP.get(tool_name, "office")
                    write_activity(f"Running: {tool_name}", location=location, status="active")
                    result = execute_tool(tool_name, tool_args)
                    write_activity(f"Done: {tool_name}", location="office", status="idle")
                    tg_send(result)
                    continue  # Skip Ollama entirely

                # ── NORMAL MESSAGE HANDLING — send to Ollama ──
                write_activity("Thinking...", location="office", status="active")
                conversation_history.append({"role": "user", "content": text})

                messages = [
                    {"role": "system", "content": build_system_prompt()}
                ] + conversation_history[-10:]

                tg_send("⏳ Thinking...")
                response = ollama_chat(messages)

                if "error" in response:
                    error_msg = f"⚠️ Agent error: {response['error']}"
                    tg_send(error_msg)
                    write_activity("Error", location="office", status="idle")
                    print(f"[Ollama error] {response['error']}")
                    continue

                msg = response.get("message", {})
                tool_calls = msg.get("tool_calls", [])
                assistant_content = msg.get("content", "")

                # ── HANDLE TOOL CALLS ──
                if tool_calls:
                    for call in tool_calls:
                        fn = call.get("function", {})
                        tool_name = fn.get("name", "")
                        tool_args = fn.get("arguments", {})

                        print(f"[Tool call] {tool_name}({json.dumps(tool_args)[:100]})")

                        if tool_name in PROTECTED_TOOLS:
                            # Need approval — send request and pause
                            location = TOOL_ROOM_MAP.get(tool_name, "office")
                            write_activity(f"Waiting for approval: {tool_name}", location=location, status="waiting")
                            approval_msg = request_approval(tool_name, tool_args)
                            tg_send(approval_msg)
                            break  # Wait for approval before doing anything else
                        else:
                            # Safe tool — execute immediately
                            location = TOOL_ROOM_MAP.get(tool_name, "office")
                            write_activity(f"Running: {tool_name}", location=location, status="active")
                            result = execute_tool(tool_name, tool_args)
                            write_activity(f"Done: {tool_name}", location="office", status="idle")
                            print(f"[Tool result] {result[:200]}")

                            tg_send(result)
                            conversation_history.append({"role": "assistant", "content": f"[Called {tool_name}] {result[:500]}"})

                elif assistant_content:
                    # Plain text response
                    write_activity("Responded", location="office", status="idle")
                    tg_send(assistant_content)
                    conversation_history.append({"role": "assistant", "content": assistant_content})

                # Trim conversation history to prevent token bloat
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]

        except KeyboardInterrupt:
            print("\n\n[Shutting down Web Manager]")
            write_activity("Offline", location="office", status="offline")
            tg_send("🔴 Web Manager going offline.")
            break
        except Exception as e:
            print(f"[Main loop error] {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
