# TR Web Manager — Setup Guide

## One-Time Setup (15 minutes)

### 1. Install Ollama model with tool support
```bash
ollama pull llama3.1:8b
```
This is the recommended model. It supports tool/function calling natively.
~4.7GB download. After that, it runs locally forever at zero cost.

### 2. Install Python dependency
```bash
pip3 install requests
```
That's the only external package needed.

### 3. Set your environment variables
Add these to your `~/.zshrc` (or `~/.bash_profile`):
```bash
export TELEGRAM_TOKEN="your_telegram_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
export TR_REPO_PATH="$HOME/trainingrun-site"
export TR_AGENT_MODEL="llama3.1:8b"
```
Then reload: `source ~/.zshrc`

Your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID are already configured from the DDP work.
Check your existing `.env` file in the repo or ask Claude if you can't find them.

### 4. Make sure Ollama is running
```bash
ollama serve
```
Ollama must be running in the background for the agent to work.
You can leave this terminal open, or set up a launchd service to auto-start it.

---

## Starting the Agent

```bash
cd ~/trainingrun-site/web_agent
python3 agent.py
```

You'll see startup messages in the terminal, and a green "TR Manager online" message in Telegram.

---

## Stopping the Agent

Press `Ctrl+C` in the terminal running agent.py.
It will send a shutdown message to Telegram.

---

## Usage Examples (Telegram messages)

**Checking status:**
- `status` → Shows all 5 DDPs with last run, status, top score
- `check the log` → Shows recent DDP run log
- `what files are in the repo?` → Lists all files

**Making changes:**
- `update the nav color to cyan on index.html` → Agent reads file, proposes edit, waits for YES
- `push the changes I just approved` → Stages and pushes after approval
- `run the TRSbench DDP` → Triggers manual run after approval

**Memory:**
- `remember that I want the footer background to always be #0a0f1a` → Saves to brain.md permanently

---

## How the Approval Gate Works

For any write operation (editing files, pushing to GitHub, running DDPs):

1. Agent sends: "🔐 APPROVAL NEEDED — Edit file: index.html [description]. Reply YES or NO."
2. You reply: `YES`
3. Agent executes and reports back.

Reply `NO` to cancel. The agent will ask for clarification if needed.

---

## Updating the Brain File

`web_agent/brain.md` is the agent's persistent memory. You can:
- Tell the agent: `"remember that [preference]"` — it writes to brain.md automatically
- Edit brain.md directly anytime to add/update knowledge
- The agent reads it fresh at the start of every response

---

## Changing the Model

If llama3.1:8b is too slow or you want to try another model:
```bash
# Faster, less capable:
ollama pull llama3.2:3b
export TR_AGENT_MODEL="llama3.2:3b"

# Slower, more capable (needs more RAM):
ollama pull llama3.1:70b
export TR_AGENT_MODEL="llama3.1:70b"

# Great for coding/tool use:
ollama pull qwen2.5-coder:7b
export TR_AGENT_MODEL="qwen2.5-coder:7b"
```

---

## Troubleshooting

**"Cannot connect to Ollama"**
→ Run `ollama serve` in a separate terminal first.

**Agent not responding to Telegram**
→ Check TELEGRAM_TOKEN and TELEGRAM_CHAT_ID are set correctly.
→ Make sure agent.py is still running (check terminal).

**Model gives bad tool calls**
→ Try a different model. llama3.1:8b is most reliable for tool use.
→ `qwen2.5:7b-instruct` is a good backup.

**"Repo not found"**
→ Set `export TR_REPO_PATH="/full/path/to/trainingrun-site"` in your shell config.
