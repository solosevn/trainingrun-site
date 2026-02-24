#!/usr/bin/env python3
"""
TR Web Manager Agent
====================
A local AI agent that manages trainingrun.ai via Telegram + Ollama.

- Communicates with David via Telegram
- Uses local Ollama model (llama3.1:8b recommended)
- Has persistent memory via brain.md
- Full write access with Telegram approval gates
- Manages DDPs, files, and GitHub for the site

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
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG — edit these or set as env vars
# ─────────────────────────────────────────────

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OLLAMA_MODEL     = os.getenv("TR_AGENT_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REPO_PATH        = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
BRAIN_FILE       = os.path.join(os.path.dirname(__file__), "brain.md")
MEMORY_FILE      = os.path.join(os.path.dirname(__file__), "memory_log.jsonl")

# ─────────────────────────────────────────────
# TELEGRAM HELPERS
# ─────────────────────────────────────────────

def tg_send(text: str):
    """Send a message to David via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
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
            "name": "write_file",
            "description": "Write or edit a file in the repo. REQUIRES DAVID'S APPROVAL before executing. Always explain what you're changing and why.",
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
            "name": "git_push",
            "description": "Stage specific files, commit with a message, and push to GitHub. REQUIRES DAVID'S APPROVAL.",
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
                        "description": "Which DDP to run: 'all', 'trsbench', 'trscode', 'truscore', 'trfcast', or 'tragents'"
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
                last_date = agent.get("last_run_date", "never")
                top_score = agent.get("top_score")
                score_str = f"{top_score:.1f}" if top_score else "—"
                icon = "✅" if status == "success" else ("❌" if status == "failed" else "⚫")
                lines.append(f"{icon} {emoji} {key}: {status} | last: {last_date} | top: {score_str}")
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
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
                for fname in filenames:
                    if not fname.startswith('.'):
                        rel = os.path.relpath(os.path.join(root, fname), REPO_PATH)
                        files.append(rel)
            return f"📁 Files in {'repo root' if not subdir else subdir}:\n" + "\n".join(sorted(files))
        except Exception as e:
            return f"Error listing files: {e}"

    elif name == "write_file":
        # This is a WRITE operation — caller must handle approval gate
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

    elif name == "git_push":
        files = args.get("files", [])
        message = args.get("message", "Update from TR Manager")
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
                return f"❌ git commit failed: {result.stderr}"

            # Push
            result = subprocess.run(
                ["git", "push"],
                cwd=REPO_PATH, capture_output=True, text=True
            )
            if result.returncode != 0:
                return f"❌ git push failed: {result.stderr}"

            return f"✅ Pushed to GitHub. Files: {', '.join(files)}\nCommit: {message}"
        except Exception as e:
            return f"Error during git push: {e}"

    elif name == "run_ddp":
        target = args.get("target", "all")
        cmd = ["python3", "daily_runner.py"]
        if target != "all":
            cmd += ["--score", target]
        try:
            result = subprocess.run(
                cmd, cwd=REPO_PATH, capture_output=True, text=True, timeout=600
            )
            output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            if result.returncode != 0:
                return f"❌ DDP run failed:\n{result.stderr[-1000:]}"
            return f"✅ DDP run complete ({target}):\n{output}"
        except subprocess.TimeoutExpired:
            return "⏱ DDP run timed out after 10 minutes."
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

    return f"Unknown tool: {name}"


# ─────────────────────────────────────────────
# WRITE-PROTECTED TOOLS (require approval)
# ─────────────────────────────────────────────

PROTECTED_TOOLS = {"write_file", "git_push", "run_ddp"}


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
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Ollama. Is it running? Try: ollama serve"}
    except Exception as e:
        return {"error": str(e)}


def build_system_prompt() -> str:
    brain = load_brain()
    return f"""You are TR Manager — the AI web manager for trainingrun.ai. You run locally on David's MacBook Pro M4 via Ollama.

Your personality: Direct, reliable, no-BS. You know this site inside out. You take your job seriously.
Your role: Manage the site, monitor DDPs, handle GitHub, support David's requests.
Your rule: Never do anything destructive without David's explicit YES in Telegram.

Here is your complete memory and knowledge base — read it before every response:

{brain}

---

RESPONSE RULES:
1. Keep responses short — David reads on his phone.
2. Use emojis sparingly for status (✅ ❌ ⚠️).
3. When you want to use a tool that requires approval (write_file, git_push, run_ddp), call the tool — the system will handle asking David for approval before executing.
4. If you don't know something about the site, say so and offer to read the relevant file.
5. Never make up file contents or status — always use tools to check real data.
"""


# ─────────────────────────────────────────────
# APPROVAL GATE STATE
# ─────────────────────────────────────────────

pending_approval = None  # {"tool": str, "args": dict, "description": str}


def request_approval(tool_name: str, args: dict) -> str:
    """Format an approval request message for Telegram."""
    global pending_approval

    descriptions = {
        "write_file": f"Edit file: <b>{args.get('path')}</b>\n{args.get('description', '')}",
        "git_push": f"Push to GitHub:\nFiles: {', '.join(args.get('files', []))}\nCommit: {args.get('message', '')}",
        "run_ddp": f"Run DDP: <b>{args.get('target', 'all')}</b>"
    }

    desc = descriptions.get(tool_name, f"Execute: {tool_name}")
    pending_approval = {"tool": tool_name, "args": args}

    return f"🔐 <b>APPROVAL NEEDED</b>\n\n{desc}\n\nReply <b>YES</b> to approve or <b>NO</b> to cancel."


def is_approval(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "yeah", "yep", "go", "do it", "approved", "approve")


def is_rejection(text: str) -> bool:
    return text.strip().lower() in ("no", "n", "nope", "cancel", "stop", "abort")


# ─────────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────────

def run():
    global pending_approval

    print("=" * 50)
    print("  TR Web Manager — Starting Up")
    print(f"  Model: {OLLAMA_MODEL}")
    print(f"  Repo:  {REPO_PATH}")
    print(f"  Brain: {BRAIN_FILE}")
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

    # Announce startup
    tg_send("🟢 <b>TR Manager online.</b>\nReady for your instructions. Type <code>status</code> to check the DDPs.")
    print("✅ Startup message sent to Telegram. Polling for messages...")

    conversation_history = []
    offset = 0

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
                        result = execute_tool(tool, args)
                        print(f"[Tool: {tool}] {result[:200]}")
                        tg_send(result[:3000])
                        continue

                    elif is_rejection(text):
                        pending_approval = None
                        tg_send("❌ Cancelled. What else can I help with?")
                        continue

                    else:
                        # Unclear — re-ask
                        tg_send("⚠️ Still waiting on approval. Reply <b>YES</b> or <b>NO</b>.")
                        continue

                # ── NORMAL MESSAGE HANDLING ──
                # Add user message to conversation
                conversation_history.append({"role": "user", "content": text})

                # Build full message list with system prompt
                messages = [
                    {"role": "system", "content": build_system_prompt()}
                ] + conversation_history[-10:]  # Keep last 10 turns in context

                # Call Ollama
                tg_send("⏳ Thinking...")
                response = ollama_chat(messages)

                if "error" in response:
                    error_msg = f"⚠️ Agent error: {response['error']}"
                    tg_send(error_msg)
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
                            approval_msg = request_approval(tool_name, tool_args)
                            tg_send(approval_msg)
                            break  # Wait for approval before doing anything else
                        else:
                            # Safe tool — execute immediately and send result directly
                            result = execute_tool(tool_name, tool_args)
                            print(f"[Tool result] {result[:200]}")

                            # Send tool result straight to Telegram — no second LLM call needed
                            tg_send(result[:3000])

                            # Keep conversation history updated
                            conversation_history.append({"role": "assistant", "content": f"[Called {tool_name}] {result[:500]}"})


                elif assistant_content:
                    # Plain text response
                    tg_send(assistant_content[:3000])
                    conversation_history.append({"role": "assistant", "content": assistant_content})

                # Trim conversation history to prevent token bloat
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]

        except KeyboardInterrupt:
            print("\n\n[Shutting down TR Manager]")
            tg_send("🔴 TR Manager going offline.")
            break
        except Exception as e:
            print(f"[Main loop error] {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
