# Spec 01 — Scaffold `streak-keeper`

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 1.

**Goal:** Create the `streak-keeper` repository at `~/dev/streak-keeper` with the full module skeleton: constants, the already-implemented `local_midnight()` helper, and `NotImplementedError` stubs for everything else, plus dev tooling files and an initial commit on `main`. Nothing here touches the GitHub API or any remote.

**Approach:** Plain scaffolding — `git init -b main`, write the files exactly as specified below, commit. Later specs fill the stubs one function at a time via TDD.

**Depends on:** Nothing.

**Files (all under `~/dev/streak-keeper/`):**
- Create: `keeper.py`
- Create: `README.md`
- Create: `.gitignore`
- Create: `requirements-dev.txt`

## Global constraints (apply to every spec)

- Python 3.11+; stdlib only at runtime (`urllib.request`, `urllib.error`, `json`, `subprocess`, `argparse`, `zoneinfo`). `pytest` is a dev-only dependency (`requirements-dev.txt`).
- Commit author identity, everywhere, exactly: name `jokot`, email `25982672+jokot@users.noreply.github.com` (account `jokot`, id `25982672` — the noreply address always attributes to the account regardless of verified-email list state).
- "Today" always means the **Asia/Jakarta (UTC+7)** calendar day — for the GraphQL window and for log-line dates.
- `jokot/streak-log` is **public**; commits go only to `main` (the default branch). `jokot/streak-keeper` is private.
- One commit per quiet day; never `--allow-empty`; no backfill in v1.
- Push/network failure ⇒ non-zero exit. The tool must never exit 0 without having verified activity or committed.
- GraphQL auth via the `GH_TOKEN` env var; `--local` mode may fall back to `gh auth token`.
- PAT scope (`STREAK_PAT`): fine-grained, Contents: read+write on `jokot/streak-log`, plus `read:user` for the GraphQL query.

## Context you need

GitHub's contribution graph marks a day green when commits land on the **default branch of a public repo** authored with an **email attributed to the account** (issues, PRs, and reviews also count; automated commits are allowed). This project asks the same source the graph uses — `viewer.contributionsCollection` — instead of local `git log`, which would miss activity elsewhere and count unpushed commits. One dated line is appended to `activity.log` per quiet day, then committed and pushed to `main`. This spec only lays down the skeleton those behaviors will grow into.

## Steps

- [ ] **Step 1: Create the repo directory and tooling files**

```bash
mkdir -p ~/dev/streak-keeper && cd ~/dev/streak-keeper
git init -b main
printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > .gitignore
printf 'pytest>=8\n' > requirements-dev.txt
```

- [ ] **Step 2: Write `keeper.py`** (skeleton — functions are filled in by Specs 02–04; `local_midnight` is already complete)

```python
"""streak-keeper: keep the GitHub contribution graph green."""
import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

AUTHOR_NAME = "jokot"
AUTHOR_EMAIL = "25982672+jokot@users.noreply.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
DEFAULT_TZ = "Asia/Jakarta"
LOG_FILE = "activity.log"


def local_midnight(now: datetime, tzid: str) -> datetime:
    """Local midnight of `now`'s day, in `tzid`, as an aware datetime."""
    tz = ZoneInfo(tzid)
    local = now.astimezone(tz)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def has_activity_today(token: str, tzid: str, now: datetime | None = None) -> bool:
    raise NotImplementedError


def already_logged_today(repo: str, today: str) -> bool:
    raise NotImplementedError


def append_commit_push(repo: str, today: str) -> None:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, help="path to the streak-log working copy")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--local", action="store_true", help="use ambient git creds + gh auth token")
    p.add_argument("--tz", default=DEFAULT_TZ)
    args = p.parse_args(argv)
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Write `README.md`**

```markdown
# streak-keeper

Keeps the GitHub contribution graph green: once per quiet day (Asia/Jakarta
calendar day), appends a dated line to `activity.log` in `jokot/streak-log`,
commits, and pushes to `main`.

Run (CI or local):

    python keeper.py --repo /path/to/streak-log [--dry-run] [--local] [--tz Asia/Jakarta]

- `--dry-run` prints intended actions and touches nothing.
- `--local` uses ambient git credentials and `gh auth token` for the API check;
  otherwise the `GH_TOKEN` env var must be set.
- Exit codes: 0 = skipped (already active) or committed; non-zero = failure.

Requires Python 3.11+, stdlib only. Dev: `pip install -r requirements-dev.txt && pytest`.
```

- [ ] **Step 4: Initial commit**

```bash
git add -A && git commit -m "chore: scaffold streak-keeper"
```

## Acceptance criteria

- [ ] `~/dev/streak-keeper` is a git repo whose default branch is `main`, with one commit `chore: scaffold streak-keeper`.
- [ ] `keeper.py` defines the constants exactly: `AUTHOR_NAME = "jokot"`, `AUTHOR_EMAIL = "25982672+jokot@users.noreply.github.com"`, `GRAPHQL_URL = "https://api.github.com/graphql"`, `DEFAULT_TZ = "Asia/Jakarta"`, `LOG_FILE = "activity.log"`.
- [ ] `local_midnight` is implemented and correct: `local_midnight(datetime(2026, 9, 7, 18, 30, tzinfo=timezone.utc), "Asia/Jakarta") == datetime(2026, 9, 8, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta"))` (18:30 UTC is already the next JKT day).
- [ ] `has_activity_today`, `already_logged_today`, `append_commit_push`, and `main` raise `NotImplementedError` when called.
- [ ] `.gitignore`, `requirements-dev.txt` (`pytest>=8`), and `README.md` exist and are committed.
- [ ] `cd ~/dev/streak-keeper && python -c "from keeper import AUTHOR_EMAIL, local_midnight; print(AUTHOR_EMAIL)"` prints `25982672+jokot@users.noreply.github.com`.
