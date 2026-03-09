# CEO-LEARNING-005: .env Files Security Audit — Investigation Methodology

**Date:** March 9, 2026
**Issue:** Fix #7 — .env files reported exposed at `daily_news_agent/.env` AND `agents/daily-news/.env`
**Severity:** CRITICAL (if real) — API keys, tokens, and credentials publicly visible on GitHub Pages repo
**Directive:** Verify not git-tracked, update gitignore for both old and new paths, clean from history if tracked, rotate creds if needed
**Status:** NO ISSUE FOUND — .env files were never committed. Gitignore coverage is correct. No credentials exposed.

---

## 1. Why This Investigation Matters

A `.env` file in a public GitHub repo is one of the worst security failures possible. The trainingrun-site repo is public (GitHub Pages), so any `.env` file committed to it — even briefly, even if later deleted — is permanently accessible in git history. Anyone can extract API keys, bot tokens, and access credentials.

The reported paths were:
- `daily_news_agent/.env` (old pre-V10 path)
- `agents/daily-news/.env` (new post-V10 path)

The directive was clear: verify, fix gitignore, clean history if needed, rotate credentials if exposed.

---

## 2. Investigation Methodology — Step by Step

### Check 1: Direct file access on current `main` branch
**What:** Navigate directly to both file paths on GitHub.
**How:** `https://github.com/solosevn/trainingrun-site/blob/main/daily_news_agent/.env` and `https://github.com/solosevn/trainingrun-site/blob/main/agents/daily-news/.env`
**Result:** Both return "File not found" (404). Neither file exists on the current `main` branch.

### Check 2: Verify the directories exist
**What:** Check if the parent directories are present.
**How:** Navigate to the directory tree on GitHub.
**Result:**
- `daily_news_agent/` — Does NOT exist on `main`. This is the old pre-V10 path. The entire directory was removed during the V10 restructure.
- `agents/daily-news/` — EXISTS on `main`. Contains 14 files (article_writer.py, config.py, main.py, etc.) and 2 subdirectories (staging/, vault/). No `.env` file in the listing.

### Check 3: GitHub code search for .env files
**What:** Search the entire repo for any file with `.env` in the path.
**How:** GitHub search: `repo:solosevn/trainingrun-site path:**/.env`
**Result:** 0 files found.

### Check 4: Examine the .gitignore
**What:** Verify `.env` is properly excluded.
**How:** Read `/.gitignore` on `main`.
**Result:** Line 14 has `.env` — this is a bare pattern (no path prefix) which means git ignores any file named `.env` in any directory. Both `daily_news_agent/.env` and `agents/daily-news/.env` are covered. Also has `venv/` and `.venv/` on lines 15-16 for virtual environments.

### Check 5: How does the code use .env?
**What:** Check if the application expects a `.env` file and how it loads secrets.
**How:** Read `agents/daily-news/config.py` (89 lines, 5.89 KB).
**Result:**
- Line 4: "Loads secrets from .env, defines all constants."
- Line 12: `load_dotenv(Path(__file__).parent / ".env")` — expects `.env` in the agent directory
- All secrets use `os.getenv()` with empty string defaults:
  - `TRNEWZ_BOT_TOKEN` — Telegram bot token
  - `DAVID_CHAT_ID` — Telegram chat ID
  - `XAI_API_KEY` — xAI/Grok API key
  - `GITHUB_TOKEN` — GitHub personal access token
  - `TR_REPO_PATH` — local repo path
- No hardcoded credentials anywhere in the file. All secrets come from environment variables.

### Check 6: Git history — was .env EVER committed?
**What:** Search the last 30 commits for any commit that added, modified, or deleted a `.env` file (not `.env.example`).
**How:** GitHub API — fetched each commit's file list and filtered for `.env` in filename, excluding `.env.example`.
**Result:** Zero commits in the last 30 ever touched a `.env` file. The `.env` file was never committed to this repo.

### Check 7: What about .env.example?
**What:** Check if the template file exists and whether it contains real credentials.
**How:** Found commit `87088cc` (March 5, 2026) which created `daily_news_agent/.env.example`.
**Result:** The `.env.example` file contains only placeholder values:
- `TRNEWZ_BOT_TOKEN=your_daily_news_bot_token_here`
- `DAVID_CHAT_ID=your_telegram_user_id_here`
- `XAI_API_KEY=your_xai_api_key_here`
- `GITHUB_TOKEN=your_github_pat_here`
- `TR_REPO_PATH=/Users/davidsolomon/trainingrun-site`
- Line 5 explicitly states: "NEVER commit .env to GitHub (it's in .gitignore)"
- This file was at the old path `daily_news_agent/.env.example` and was removed during V10 restructure. It was NOT recreated at `agents/daily-news/.env.example`.

### Check 8: Hardcoded secrets search across entire codebase
**What:** Search for common API key patterns that might indicate hardcoded credentials.
**How:** GitHub code search for `sk-`, `xai-`, `ghp_`, `gho_` patterns in the repo.
**Result:** Zero results. No hardcoded API keys or tokens anywhere in the codebase.

### Check 9: All agent directories audit
**What:** Check every agent directory for `.env` files.
**How:** GitHub API listing of each directory under `agents/`.
**Result:**
- `agents/ceo/` — Only contains `vault/`. No `.env`.
- `agents/content-scout/` — 7 files. No `.env`.
- `agents/daily-news/` — 14 files + 2 dirs. No `.env`.
- `agents/ddp/` — No `.env`.
- `agents/trsitekeeper/` — No `.env`.

---

## 3. Findings Summary

| Check | Result | Status |
|-------|--------|--------|
| .env on current main (old path) | 404 — directory doesn't exist | CLEAN |
| .env on current main (new path) | 404 — not in directory | CLEAN |
| GitHub code search | 0 files found | CLEAN |
| .gitignore coverage | `.env` on line 14, covers all paths | PROTECTED |
| config.py secrets | All via `os.getenv()`, no hardcoding | CLEAN |
| Git history (30 commits) | Zero .env file changes | CLEAN |
| .env.example contents | Placeholder values only | SAFE |
| Hardcoded secrets search | 0 results for key patterns | CLEAN |
| All agent directories | No .env in any agent dir | CLEAN |

**Conclusion:** The `.env` files exist only on the local machine (David's Mac) where they're needed for the agents to run. The `.gitignore` properly prevents them from being committed. They were never in the git history. No credential rotation is needed.

---

## 4. Minor Gap Found

The `.env.example` template file was at `daily_news_agent/.env.example` and got removed during the V10 restructure. It was NOT migrated to `agents/daily-news/.env.example`. This means a new developer or agent setting up the daily-news agent wouldn't have a template showing what environment variables are needed.

**Not a security issue** — but a usability gap. The required env vars can be inferred from `config.py`, but having an explicit `.env.example` is better practice.

---

## 5. How to Investigate .env Exposure — Reusable Playbook

For any future agent investigating potential credential exposure, follow these steps in this order:

### Priority 1: Immediate threat assessment
1. **Direct file access** — Navigate to the exact reported paths on GitHub. If 404, the file isn't on current branch.
2. **GitHub code search** — `repo:owner/name path:**/.env` to find any .env files anywhere in the repo.
3. **If found: DO NOT PROCEED with other work.** Credential rotation is the #1 priority.

### Priority 2: History check
4. **Git history scan** — Check commits for any .env file additions/deletions. Even if a file was deleted, it exists forever in git history.
5. **If found in history:** The credentials are compromised. Even if the file was deleted, anyone can access it via `git log` or GitHub's commit history. Rotation is mandatory.

### Priority 3: Code audit
6. **Check how secrets are loaded** — Read config files. Look for `load_dotenv`, `os.getenv`, or hardcoded strings.
7. **Search for key patterns** — `sk-`, `ghp_`, `gho_`, `xai-`, `AKIA` (AWS), `bearer`, etc.

### Priority 4: Prevention verification
8. **Verify .gitignore** — Confirm `.env` is listed. A bare `.env` entry covers all directories. Path-specific entries like `agents/daily-news/.env` only cover that one location.
9. **Check all agent directories** — Enumerate every directory that could contain a `.env` file.

### If credentials ARE exposed:
1. **Rotate immediately** — Every key in the exposed `.env` must be regenerated
2. **Use `git filter-branch` or BFG Repo-Cleaner** to remove the file from history
3. **Force push** the cleaned history
4. **Verify** the file is gone from all commits
5. **Document** which keys were rotated and when

---

## 6. Gitignore Best Practices for This Repo

The current `.gitignore` has `.env` on line 14 which is correct. For defense-in-depth, consider also adding:
```
# Secrets - belt and suspenders
.env
.env.*
!.env.example
agents/**/.env
agents/**/.env.*
```
The `!.env.example` pattern explicitly allows `.env.example` files to be committed (they're templates with placeholder values). The additional path-specific patterns provide redundancy.

---

## 7. Related Documents

- **CEO-LEARNING-002:** DDP pipeline path breakage — different V10 restructure issue
- **CEO-LEARNING-003:** status.json rebase overwrite — git operations issue
- **CEO-LEARNING-004:** news.html duplication — file handling issue
- **Common thread with this issue:** The V10 restructure moved `daily_news_agent/` to `agents/daily-news/`. The `.env` file correctly stayed local (gitignored), but the `.env.example` template wasn't migrated to the new path.
