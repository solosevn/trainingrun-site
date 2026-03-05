"""
Daily News Agent — Learning Logger
=====================================
Appends entries to RUN-LOG.md and LEARNING-LOG.md after each cycle.
This is the agent's memory — how it gets better over time.
"""

import datetime
from config import VAULT_FILES
from context_loader import load_vault_file
from github_publisher import commit_vault_file


def log_to_run_log(paper_number: int, title: str, source_url: str, category: str,
                   cycle_time_minutes: float, edit_count: int, first_pass: bool,
                   status: str = "Published ✅") -> str:
    """
    Append a new entry to RUN-LOG.md.
    Returns the updated content for commit.
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p CST")
    date_short = datetime.date.today().strftime("%B %d, %Y")

    entry = f"""
---

## Paper {paper_number:03d} | {date_short} | {title}

| Field | Value |
|---|---|
| **Source** | {source_url} |
| **Category** | {category} |
| **Status** | {status} |
| **Process** | Agent — autonomous cycle |
| **Cycle Time** | {cycle_time_minutes:.1f} minutes |
| **Edit Requests** | {edit_count} |
| **First-Pass Approval** | {'Yes ✅' if first_pass else f'No — {edit_count} edit(s) requested'} |
| **Published** | {today} |
"""

    # Load current RUN-LOG.md
    current = load_vault_file("run_log_md")

    # Update summary stats at the bottom
    # Find "Papers published:" line and increment
    updated = current.rstrip() + "\n" + entry

    return updated


def log_to_learning_log(paper_number: int, title: str,
                        selection_time: float, writing_time: float,
                        staging_time: float, approval_time: float,
                        edit_count: int, first_pass: bool,
                        edit_notes: list = None,
                        agent_reflection: str = "") -> str:
    """
    Append a new entry to LEARNING-LOG.md.
    This is the raw data that feeds STYLE-EVOLUTION.md.
    Returns the updated content for commit.
    """
    today = datetime.date.today().strftime("%B %d, %Y")
    total_time = selection_time + writing_time + staging_time + approval_time

    edit_notes_str = ""
    if edit_notes:
        for note in edit_notes:
            edit_notes_str += f"  - {note}\n"
    else:
        edit_notes_str = "  - None — approved on first pass\n"

    entry = f"""
---

## Paper {paper_number:03d} | {today}

### Process Metrics
| Phase | Time |
|---|---|
| Story Selection | {selection_time:.1f} min |
| Article Writing | {writing_time:.1f} min |
| HTML Staging | {staging_time:.1f} min |
| Approval Wait | {approval_time:.1f} min |
| **Total Cycle** | **{total_time:.1f} min** |

### Approval Data
- **First-pass approval:** {'YES ✅' if first_pass else 'NO'}
- **Edit cycles:** {edit_count}
- **David's edit notes:**
{edit_notes_str}
### Audience Metrics (24-48h post-publish)
- Page views: _pending_
- X impressions: _pending_
- X engagements: _pending_
- Click-through rate: _pending_

### Reasoning Checklist
- Applied: YES
- Outcome: Story selected and article written using 5-filter test

### Agent Reflection
{agent_reflection if agent_reflection else '_Reflection will be added after performance data is collected._'}
"""

    # Load current LEARNING-LOG.md
    current = load_vault_file("learning_md")
    updated = current.rstrip() + "\n" + entry

    return updated


def commit_logs(run_log_content: str, learning_log_content: str, paper_number: int) -> dict:
    """
    Commit both log files to GitHub.
    """
    results = {"steps": [], "errors": []}

    # Commit RUN-LOG.md
    try:
        commit_vault_file(
            path=VAULT_FILES["run_log_md"],
            content=run_log_content,
            message=f"RUN-LOG: Paper {paper_number:03d} published",
        )
        results["steps"].append("✅ RUN-LOG.md updated")
    except Exception as e:
        results["errors"].append(f"Failed to update RUN-LOG.md: {e}")

    # Commit LEARNING-LOG.md
    try:
        commit_vault_file(
            path=VAULT_FILES["learning_md"],
            content=learning_log_content,
            message=f"LEARNING-LOG: Paper {paper_number:03d} cycle data",
        )
        results["steps"].append("✅ LEARNING-LOG.md updated")
    except Exception as e:
        results["errors"].append(f"Failed to update LEARNING-LOG.md: {e}")

    return results


if __name__ == "__main__":
    print("[LearningLogger] Module loaded. Use log_to_run_log() and log_to_learning_log().")
