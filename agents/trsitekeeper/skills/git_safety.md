# Skill: Git Safety

## When to activate
Any time a git push is needed, a conflict is reported, or deployment to GitHub Pages is involved.

## Reasoning pattern
1. **ALWAYS PULL FIRST:** `git pull --rebase` before ANY push. The DDPs push at 4AM, Content Scout at 5:30AM â there's always a chance of upstream changes.
2. **SPECIFIC FILES ONLY:** Never `git add -A` or `git add .`. Always `git add <specific-file>`. This prevents accidentally committing .env, credentials, or backup files.
3. **ALWAYS INCLUDE ACTIVITY:** When pushing, always include `agent_activity.json` in staged files. The HQ page reads this.
4. **COMMIT MESSAGES:** Lowercase, imperative, explain WHY not just WHAT. Good: `fix: alignment on mobile leaderboard rows`. Bad: `updated index.html`.
5. **CHECK FOR CONFLICTS:** If push fails, check if there's a merge conflict. The DDPs use `-X theirs` for rebase strategy. Sitekeeper should check what conflicted and resolve intelligently.
6. **DEPLOY LAG:** GitHub Pages deploys in ~60 seconds after push. Don't panic if the site doesn't update immediately.

## What NOT to do
- Never force push (`git push --force`). Ever.
- Never commit `.env`, credentials, or `backups/` directory.
- Never commit without a descriptive message.
- Never push without pulling first â this causes merge conflicts that break the DDP cron.

## Conflict resolution
- If conflict is in a data JSON file: the DDP's version is authoritative. Use theirs.
- If conflict is in HTML/CSS: Sitekeeper's version is authoritative. Review manually.
- If conflict is in agent files: stop, report to David, don't auto-resolve.

## Key facts
- Repo: `https://github.com/solosevn/trainingrun-site`
- Branch: `main` (single branch, direct push always)
- Platform: GitHub Pages â repo IS the live site
- Git remote uses PAT embedded in URL (cron can't access macOS Keychain)
- `.gitignore` excludes: `backups/`, `.env`, credentials

## Source
Seeded from brain.md GIT WORKFLOW + COMMON FIX PATTERNS. Version 1.0.
