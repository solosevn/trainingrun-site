#!/usr/bin/env python3
"""
TRSitekeeper v1.1
=================
The AI gatekeeper for trainingrun.ai — powered by Claude Sonnet 4.6.

- Communicates with David via Telegram (text + screenshots)
- Uses Anthropic Claude API for fast, intelligent responses
- Has persistent memory via brain.md
- Full write access with Telegram approval gates
- Manages DDPs, files, GitHub, and site health
- Accepts screenshots: "fix this" + photo = instant diagnosis + fix
- Multi-step tool chains: Claude can read a file, then propose an edit

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
import base64
import threading
import traceback
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL     = "claude-sonnet-4-6"
REPO_PATH        = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
BRAIN_FILE       = os.path.join(os.path.dirname(__file__), "brain.md")
MEMORY_FILE      = os.path.join(os.path.dirname(__file__), "memory_log.jsonl")
ACTIVITY_FILE    = os.path.join(REPO_PATH, "agent_activity.json")
BACKUP_DIR       = os.path.join(REPO_PATH, "backups")
BRIDGE_PORT      = 7432

# Full Python path for DDP runs (macOS Playwright needs this)
PYTHON_PATH      = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

# ─────────────────────────────────────────────
# BRIDGE SERVER
# ─────────────────────────────────────────────

TOOL_ROOM_MAP = {
    "check_status":  "ddp_room",
    "run_ddp":       "ddp_room",
    "read_file":     "office",
    "write_file":    "office",
    "edit_file":     "office",
    "backup_file":   "office",
    "site_health":   "ddp_room",
    "git_push":      "office",
    "list_files":    "office",
    "remember":      "office",
    "read_log":      "ddp_room",
}


def write_activity(action: str, location: str = "office", status: str = "active"):
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
        "agent":        "trsitekeeper",
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
        pass


def start_bridge():
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
    """Send a message to David via Telegram. Auto-splits. Falls back to plain text."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    MAX_LEN = 3900
    chunks = []
    while len(text) > MAX_LEN:
        split_at = text.rfind("\n", 0, MAX_LEN)
        if split_at < MAX_LEN // 2:
            split_at = MAX_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    chunks.append(text)

    for chunk in chunks:
        if not chunk.strip():
            continue
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if not resp.ok:
                print(f"[Telegram] HTML failed ({resp.status_code}), retrying plain...")
                payload.pop("parse_mode")
                resp2 = requests.post(url, json=payload, timeout=10)
                if not resp2.ok:
                    print(f"[Telegram send error] {resp2.status_code}: {resp2.text[:200]}")
        except Exception as e:
            print(f"[Telegram send error] {e}")


def tg_get_updates(offset: int) -> list:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 30, "limit": 10}
    try:
        resp = requests.get(url, params=params, timeout=40)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        print(f"[Telegram poll error] {e}")
        return []


def tg_download_photo(file_id: str) -> bytes:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
        resp = requests.get(url, params={"file_id": file_id}, timeout=10)
        resp.raise_for_status()
        file_path = resp.json().get("result", {}).get("file_path", "")
        if not file_path:
            return b""
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        resp = requests.get(download_url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[Telegram photo download error] {e}")
        return b""


# ─────────────────────────────────────────────
# MEMORY / BRAIN
# ─────────────────────────────────────────────

def load_brain() -> str:
    try:
        with open(BRAIN_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "No brain file found."


def append_memory(key: str, value: str):
    timestamp = datetime.datetime.now().strftime("%b %d, %Y")
    entry = {"timestamp": timestamp, "key": key, "value": value}
    with open(MEMORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
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
# TOOLS — Anthropic API format
# ─────────────────────────────────────────────

CLAUDE_TOOLS = [
    {
        "name": "check_status",
        "description": "Check the live status of all 5 DDPs by reading status.json.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "read_file",
        "description": "Read any file in the trainingrun-site repo. Use this to inspect code before making edits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from repo root"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files in the repo or a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subdir": {"type": "string", "description": "Optional subdirectory. Leave empty for root."}
            }
        }
    },
    {
        "name": "edit_file",
        "description": "Surgically edit a file by finding and replacing specific text. Auto-backs up first. REQUIRES APPROVAL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from repo root"},
                "find": {"type": "string", "description": "Exact text to find"},
                "replace": {"type": "string", "description": "Text to replace it with"},
                "description": {"type": "string", "description": "What this change does"}
            },
            "required": ["path", "find", "replace", "description"]
        }
    },
    {
        "name": "write_file",
        "description": "Write an entire file. Use edit_file for small changes. REQUIRES APPROVAL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from repo root"},
                "content": {"type": "string", "description": "Full file content"},
                "description": {"type": "string", "description": "What this change does"}
            },
            "required": ["path", "content", "description"]
        }
    },
    {
        "name": "backup_file",
        "description": "Create a timestamped backup before editing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to back up"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "site_health",
        "description": "Comprehensive health check: data files, status.json, HTML pages, stale data detection.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "git_push",
        "description": "Stage files, commit, pull --rebase, push to GitHub. Always includes agent_activity.json. REQUIRES APPROVAL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage"},
                "message": {"type": "string", "description": "Commit message"}
            },
            "required": ["files", "message"]
        }
    },
    {
        "name": "run_ddp",
        "description": "Trigger one or all DDPs. REQUIRES APPROVAL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "'all', 'trsbench', 'trscode', 'truscore', 'trfcast', or 'tragents'"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "remember",
        "description": "Save something to persistent memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short label"},
                "value": {"type": "string", "description": "What to remember"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "read_log",
        "description": "Read the DDP run log for errors or recent activity.",
        "input_schema": {"type": "object", "properties": {}}
    }
]


# ─────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────

def execute_tool(name: str, args: dict) -> str:

    if name == "check_status":
        status_path = os.path.join(REPO_PATH, "status.json")
        try:
            with open(status_path) as f:
                data = json.load(f)
            agents = data.get("agents", {})
            lines = ["Mission Control Status\n"]
            for key, agent in agents.items():
                status = agent.get("status", "unknown")
                last_date = agent.get("last_run_date", "never")
                top_score = agent.get("top_score")
                score_str = f"{top_score:.1f}" if top_score else "--"
                icon = "OK" if status == "success" else ("FAIL" if status == "failed" else "OFF")
                lines.append(f"[{icon}] {key}: {status} | last: {last_date} | top: {score_str}")
            return "\n".join(lines)
        except FileNotFoundError:
            return "status.json not found."
        except Exception as e:
            return f"Error reading status.json: {e}"

    elif name == "read_file":
        path = args.get("path", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            with open(full_path, "r") as f:
                content = f.read()
            if len(content) > 8000:
                content = content[:8000] + f"\n\n[... truncated -- {len(content)} total chars]"
            return f"File: {path}\n\n{content}"
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
            return f"Files in {'repo root' if not subdir else subdir}:\n" + "\n".join(sorted(files))
        except Exception as e:
            return f"Error listing files: {e}"

    elif name == "edit_file":
        path = args.get("path", "")
        find_text = args.get("find", "")
        replace_text = args.get("replace", "")
        full_path = os.path.join(REPO_PATH, path)

        backup_result = execute_tool("backup_file", {"path": path})
        print(f"[Edit] {backup_result}")

        try:
            with open(full_path, "r") as f:
                content = f.read()
            if find_text not in content:
                return f"EDIT FAILED: Text not found in {path}. No changes made. Backup saved."
            count = content.count(find_text)
            new_content = content.replace(find_text, replace_text, 1)
            with open(full_path, "w") as f:
                f.write(new_content)
            return f"EDITED: {path} (matched {count}x, replaced 1st). Backup saved."
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error editing {path}: {e}"

    elif name == "write_file":
        path = args.get("path", "")
        content = args.get("content", "")
        full_path = os.path.join(REPO_PATH, path)
        if os.path.exists(full_path):
            backup_result = execute_tool("backup_file", {"path": path})
            print(f"[Write] {backup_result}")
        try:
            os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else REPO_PATH, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            return f"Written: {path} ({len(content)} chars)"
        except Exception as e:
            return f"Error writing {path}: {e}"

    elif name == "backup_file":
        path = args.get("path", "")
        full_path = os.path.join(REPO_PATH, path)
        try:
            if not os.path.exists(full_path):
                return f"No file to backup: {path}"
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = path.replace("/", "_").replace("\\", "_")
            backup_path = os.path.join(BACKUP_DIR, f"{safe_name}.{timestamp}.bak")
            shutil.copy2(full_path, backup_path)
            return f"Backed up: {path} -> backups/{safe_name}.{timestamp}.bak"
        except Exception as e:
            return f"Backup error: {e}"

    elif name == "site_health":
        issues = []
        checks = 0

        data_files = [
            "trs-data.json", "trscode-data.json", "truscore-data.json",
            "trf-data.json", "tragent-data.json", "status.json"
        ]
        for df in data_files:
            checks += 1
            fp = os.path.join(REPO_PATH, df)
            if not os.path.exists(fp):
                issues.append(f"MISSING: {df}")
            else:
                try:
                    with open(fp) as f:
                        json.load(f)
                except json.JSONDecodeError:
                    issues.append(f"INVALID JSON: {df}")

        checks += 1
        status_path = os.path.join(REPO_PATH, "status.json")
        try:
            with open(status_path) as f:
                status_data = json.load(f)
            agents = status_data.get("agents", {})
            today = datetime.date.today().isoformat()
            for name_key, agent in agents.items():
                last_date = agent.get("last_run_date", "")
                if last_date != today:
                    issues.append(f"STALE: {name_key} last ran {last_date}")
                if agent.get("status") == "failed":
                    issues.append(f"FAILED: {name_key}")
        except Exception as e:
            issues.append(f"Cannot read status.json: {e}")

        html_pages = [
            "index.html", "mission-control.html", "hq.html",
            "scores.html", "truscore.html", "trscode.html",
            "trfcast.html", "tragents.html"
        ]
        for hp in html_pages:
            checks += 1
            if not os.path.exists(os.path.join(REPO_PATH, hp)):
                issues.append(f"MISSING PAGE: {hp}")

        if issues:
            return f"Health Check: {len(issues)} issues ({checks} checks)\n\n" + "\n".join(issues)
        else:
            return f"Health Check: ALL CLEAR ({checks} checks passed)"

    elif name == "git_push":
        files = args.get("files", [])
        message = args.get("message", "Update from TRSitekeeper")

        # Always include agent_activity.json (changes with every action)
        if "agent_activity.json" not in files:
            files.append("agent_activity.json")

        try:
            for f in files:
                result = subprocess.run(["git", "add", f], cwd=REPO_PATH, capture_output=True, text=True)
                if result.returncode != 0:
                    return f"git add failed for {f}: {result.stderr}"
            result = subprocess.run(["git", "commit", "-m", message], cwd=REPO_PATH, capture_output=True, text=True)
            if result.returncode != 0:
                return f"git commit failed: {result.stderr}"
            result = subprocess.run(["git", "pull", "--rebase"], cwd=REPO_PATH, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return f"git pull --rebase failed: {result.stderr}"
            result = subprocess.run(["git", "push"], cwd=REPO_PATH, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return f"git push failed: {result.stderr}"
            return f"Pushed to GitHub.\nFiles: {', '.join(files)}\nCommit: {message}"
        except Exception as e:
            return f"Git error: {e}"

    elif name == "run_ddp":
        target = args.get("target", "all")
        cmd = [PYTHON_PATH, "daily_runner.py"]
        if target != "all":
            cmd += ["--score", target]
        try:
            result = subprocess.run(cmd, cwd=REPO_PATH, capture_output=True, text=True, timeout=900)
            output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            if result.returncode != 0:
                return f"DDP run failed:\n{result.stderr[-1000:]}"
            return f"DDP run complete ({target}):\n{output}"
        except subprocess.TimeoutExpired:
            return "DDP run timed out after 15 minutes."
        except Exception as e:
            return f"Error running DDP: {e}"

    elif name == "remember":
        key = args.get("key", "note")
        value = args.get("value", "")
        append_memory(key, value)
        return f"Remembered: {key} -> {value}"

    elif name == "read_log":
        log_path = os.path.join(REPO_PATH, "ddp.log")
        try:
            with open(log_path, "r") as f:
                content = f.read()
            if len(content) > 3000:
                content = "...\n" + content[-3000:]
            return f"DDP Log (recent):\n\n{content}"
        except FileNotFoundError:
            return "ddp.log not found."
        except Exception as e:
            return f"Error reading log: {e}"

    return f"Unknown tool: {name}"


# ─────────────────────────────────────────────
# WRITE-PROTECTED TOOLS
# ─────────────────────────────────────────────

PROTECTED_TOOLS = {"run_ddp"}


# ─────────────────────────────────────────────
# CLAUDE API INTERFACE
# ─────────────────────────────────────────────

def claude_chat(messages: list, system_prompt: str) -> dict:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages,
        "tools": CLAUDE_TOOLS
    }
    MAX_RETRIES = 3
    RETRY_DELAYS = [15, 30, 60]  # seconds between retries

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)

            if resp.status_code == 429:
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAYS[attempt]
                    print(f"[Claude] Rate limited (429). Waiting {wait}s — retry {attempt + 1}/{MAX_RETRIES}...")
                    tg_send(f"⏳ Rate limit hit. Waiting {wait}s then retrying ({attempt + 1}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue
                else:
                    tg_send("❌ Rate limit exceeded after 3 retries. Try again in a minute.")
                    return {"error": "Rate limit exceeded after 3 retries. Try again in a minute."}

            if not resp.ok:
                return {"error": f"API error {resp.status_code}: {resp.text[:300]}"}
            return resp.json()

        except requests.exceptions.Timeout:
            return {"error": "Claude API timed out after 60 seconds."}
        except Exception as e:
            return {"error": str(e)}

    return {"error": "Rate limit exceeded after retries."}


def build_system_prompt() -> str:
    brain = load_brain()
    return f"""You are TRSitekeeper — the AI gatekeeper for trainingrun.ai. You run on David's MacBook Pro M4, powered by Claude Sonnet 4.6.

Your personality: Direct, sharp, reliable. You know this site inside out. You take your job seriously. You are the keeper of this site.

Your role: Guard and manage the site, monitor DDPs, handle GitHub, make surgical code fixes, support David's requests. When David sends a screenshot, analyze the visual issue and propose the exact code fix.

BACKUP-FIRST WORKFLOW: Before ANY file edit, ALWAYS call backup_file first. Then use edit_file for surgical changes (preferred) or write_file for full rewrites.

Here is your complete memory and knowledge base:

{brain}

---

RULES:
1. "status" = call check_status. Never touch files for a status check.
2. Only edit files when David explicitly asks for a change.
3. ALWAYS backup before editing. No exceptions.
4. Prefer edit_file (surgical find/replace) over write_file (full overwrite).
5. Keep responses SHORT — David reads on his phone.
6. Never make up data. Always use tools for real info.
7. Each message is a NEW request. Don't carry over context from old messages.
8. When David sends a screenshot, analyze it carefully. Identify the exact file and code that needs changing. Propose a specific fix.
9. For protected operations (edit, write, push, run DDPs), always explain what you'll do and wait for approval.
10. When pushing to git, always include agent_activity.json in the staged files.
"""


# ─────────────────────────────────────────────
# APPROVAL GATE
# ─────────────────────────────────────────────

pending_approval = None


def request_approval(tool_name: str, args: dict) -> str:
    global pending_approval

    descriptions = {
        "edit_file": (
            f"Edit: {args.get('path')}\n"
            f"Find: {args.get('find', '')[:100]}\n"
            f"Replace: {args.get('replace', '')[:100]}\n"
            f"Why: {args.get('description', '--')}"
        ),
        "write_file": (
            f"Write: {args.get('path')}\n"
            f"Size: {len(args.get('content', ''))} chars\n"
            f"Why: {args.get('description', '--')}"
        ),
        "git_push": f"Push to GitHub:\nFiles: {', '.join(args.get('files', []))}\nCommit: {args.get('message', '')}",
        "run_ddp": f"Run DDP: {args.get('target', 'all')}"
    }

    desc = descriptions.get(tool_name, f"Execute: {tool_name}")
    pending_approval = {"tool": tool_name, "args": args}
    return f"APPROVAL NEEDED\n\n{desc}\n\nReply YES to approve or NO to cancel."


def is_approval(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "yeah", "yep", "go", "do it", "approved", "approve")


def is_rejection(text: str) -> bool:
    return text.strip().lower() in ("no", "n", "nope", "cancel", "stop", "abort")


# ─────────────────────────────────────────────
# KEYWORD INTERCEPT — instant, no API call
# ─────────────────────────────────────────────

def keyword_intercept(text: str):
    t = text.strip().lower()

    if t in ("status", "check status", "ddp status", "how are the ddps",
             "what's the status", "whats the status", "show status", "s"):
        return ("check_status", {})

    if t in ("health", "health check", "site health", "check health"):
        return ("site_health", {})

    if any(k in t for k in ("show log", "check log", "ddp log")):
        return ("read_log", {})

    if t in ("log",):
        return ("read_log", {})

    if any(k in t for k in ("list files", "what files", "show files", "ls")):
        return ("list_files", {})

    if any(k in t for k in ("brain", "show brain", "read brain", "memory")):
        return ("read_file", {"path": "web_agent/brain.md"})

    return None


# ─────────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────────

def handle_claude_response(response, conversation_history):
    """
    Process Claude's response. Handles text, tool calls, and multi-step tool chains.
    Loops until: (a) Claude sends final text, (b) a protected tool needs approval,
    or (c) an error occurs.
    """
    global pending_approval

    MAX_TOOL_LOOPS = 10

    for loop_count in range(MAX_TOOL_LOOPS):

        if "error" in response:
            tg_send(f"Agent error: {response['error']}")
            write_activity("Error", location="office", status="idle")
            print(f"[Claude error] {response['error']}")
            return

        content_blocks = response.get("content", [])

        text_parts = []
        tool_uses = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_uses.append(block)

        # ── NO TOOL CALLS — just text, we're done ──
        if not tool_uses:
            if text_parts:
                tg_send("\n".join(text_parts))
            conversation_history.append({"role": "assistant", "content": content_blocks})
            write_activity("Ready", location="office", status="idle")
            return

        # ── TOOL CALLS — execute and continue ──
        conversation_history.append({"role": "assistant", "content": content_blocks})

        if text_parts:
            combined = "\n".join(text_parts)
            if combined.strip():
                tg_send(combined)

        tool_results = []
        hit_protected = False

        for tu in tool_uses:
            tool_name = tu.get("name", "")
            tool_input = tu.get("input", {})
            tool_use_id = tu.get("id", "")

            print(f"[Tool call] {tool_name}({json.dumps(tool_input)[:100]})")

            if tool_name in PROTECTED_TOOLS:
                location = TOOL_ROOM_MAP.get(tool_name, "office")
                write_activity(f"Awaiting approval: {tool_name}", location=location, status="waiting")
                approval_msg = request_approval(tool_name, tool_input)
                pending_approval["tool_use_id"] = tool_use_id
                pending_approval["content_blocks"] = content_blocks
                tg_send(approval_msg)
                hit_protected = True
                break
            else:
                location = TOOL_ROOM_MAP.get(tool_name, "office")
                write_activity(f"Running: {tool_name}", location=location, status="active")
                result = execute_tool(tool_name, tool_input)
                write_activity(f"Done: {tool_name}", location="office", status="idle")
                print(f"[Tool result] {result[:200]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result[:8000]
                })

        if hit_protected:
            return

        if tool_results:
            conversation_history.append({"role": "user", "content": tool_results})
            print(f"[Loop {loop_count + 1}] Sending {len(tool_results)} tool result(s) back to Claude...")
            write_activity("Thinking...", location="office", status="active")
            response = claude_chat(conversation_history[-20:], build_system_prompt())
        else:
            write_activity("Ready", location="office", status="idle")
            return

    tg_send("Stopped after too many tool steps. Let me know if you need more.")
    write_activity("Ready", location="office", status="idle")


def run():
    global pending_approval

    print("=" * 50)
    print("  TRSitekeeper v1.1")
    print(f"  Model: {CLAUDE_MODEL}")
    print(f"  Repo:  {REPO_PATH}")
    print(f"  Brain: {BRAIN_FILE}")
    print("=" * 50)

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set.")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY must be set.")
        print("  Get your key at https://console.anthropic.com")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    if not os.path.exists(REPO_PATH):
        print(f"ERROR: Repo not found at {REPO_PATH}")
        sys.exit(1)

    start_bridge()
    write_activity("Online and ready", location="office", status="idle")

    tg_send("TRSitekeeper v1.1 online.\nPowered by Claude Sonnet 4.6\nType 'status' to check DDPs.")
    print("Startup message sent. Polling...")

    conversation_history = []

    print("[Startup] Skipping old Telegram messages...")
    old_updates = tg_get_updates(0)
    if old_updates:
        offset = old_updates[-1]["update_id"] + 1
        print(f"[Startup] Skipped {len(old_updates)} old messages. Offset: {offset}")
    else:
        offset = 0

    while True:
        try:
            updates = tg_get_updates(offset)

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "").strip()
                caption = message.get("caption", "").strip()
                chat_id = str(message.get("chat", {}).get("id", ""))

                if chat_id != str(TELEGRAM_CHAT_ID):
                    continue

                # ── HANDLE PHOTOS ──
                photo = message.get("photo")
                image_data = None
                if photo:
                    best_photo = photo[-1]
                    file_id = best_photo.get("file_id", "")
                    print(f"[David] Screenshot" + (f" with caption: {caption}" if caption else ""))
                    image_bytes = tg_download_photo(file_id)
                    if image_bytes:
                        image_data = base64.b64encode(image_bytes).decode("utf-8")
                        print(f"[Photo] Downloaded {len(image_bytes)} bytes")
                    else:
                        tg_send("Couldn't download that image. Try again.")
                        continue
                    if not text:
                        text = caption if caption else "What do you see in this screenshot? Any issues?"

                if not text and not image_data:
                    continue

                print(f"\n[David] {text}")

                # ── APPROVAL GATE ──
                if pending_approval:
                    if is_approval(text):
                        tool = pending_approval["tool"]
                        args = pending_approval["args"]
                        tool_use_id = pending_approval.get("tool_use_id", "")
                        pending_approval = None
                        tg_send(f"Approved. Executing {tool}...")
                        write_activity(f"Executing: {tool}", location=TOOL_ROOM_MAP.get(tool, "office"), status="active")
                        result = execute_tool(tool, args)
                        write_activity(f"Done: {tool}", location="office", status="idle")
                        print(f"[Tool: {tool}] {result[:200]}")
                        tg_send(result)

                        # Feed result back to Claude so it can continue
                        if tool_use_id:
                            conversation_history.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": result[:4000]
                                }]
                            })
                            write_activity("Thinking...", location="office", status="active")
                            response = claude_chat(conversation_history[-20:], build_system_prompt())
                            handle_claude_response(response, conversation_history)
                        continue

                    elif is_rejection(text):
                        pending_approval = None
                        tg_send("Cancelled.")
                        continue

                    else:
                        tg_send("Waiting on approval. Reply YES or NO.")
                        continue

                # ── KEYWORD INTERCEPT ──
                if not image_data:
                    intercept = keyword_intercept(text)
                    if intercept:
                        tool_name, tool_args = intercept
                        print(f"[Intercept] {tool_name}")
                        location = TOOL_ROOM_MAP.get(tool_name, "office")
                        write_activity(f"Running: {tool_name}", location=location, status="active")
                        result = execute_tool(tool_name, tool_args)
                        write_activity(f"Done: {tool_name}", location="office", status="idle")
                        tg_send(result)
                        continue

                # ── BUILD MESSAGE FOR CLAUDE ──
                user_content = []
                if image_data:
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data
                        }
                    })
                user_content.append({"type": "text", "text": text})

                conversation_history.append({"role": "user", "content": user_content})

                write_activity(f"Thinking: {text[:40]}", location="office", status="active")
                response = claude_chat(conversation_history[-20:], build_system_prompt())
                handle_claude_response(response, conversation_history)

                if len(conversation_history) > 30:
                    conversation_history = conversation_history[-30:]

        except KeyboardInterrupt:
            print("\n[Shutting down TRSitekeeper]")
            tg_send("TRSitekeeper going offline.")
            write_activity("Offline", location="office", status="offline")
            break
        except Exception as e:
            print(f"[Main loop error] {e}")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    run()
