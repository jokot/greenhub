# Spec 03 — Log-append, commit-and-push routine

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 3.

**Goal:** Implement the two persistence functions in `~/dev/streak-keeper/keeper.py`: `already_logged_today()` (idempotency read) and `append_commit_push()` (append the dated log line, commit with the exact author identity, push to `origin main`). Strict TDD against a real temp git repo with a bare remote, so everything runs offline.

**Approach:** A private `_git()` helper runs git and raises `RuntimeError` on any non-zero exit — that is the fail-loudly path (FR4). `already_logged_today` reads only the last non-blank line of `activity.log` and checks it starts with today's date; a missing file counts as "not logged". `append_commit_push` sets repo-local user config (the noreply identity) before every commit, so the author is correct regardless of the machine's global git config.

**Depends on:** Spec 01 (scaffolded repo, `already_logged_today`/`append_commit_push` stubs, author constants).

**Files:**
- Modify: `~/dev/streak-keeper/keeper.py` (replace both stubs)
- Create: `~/dev/streak-keeper/tests/test_commit.py`

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

The keeper appends one line per quiet JKT day to `activity.log` in the `streak-log` working copy: `<YYYY-MM-DD> auto: kept streak alive`, commits it as `chore: daily activity <YYYY-MM-DD>`, and pushes `origin main`. The commit message format and the author identity are load-bearing: the noreply email is what attributes the automated commit to account `jokot` (id 25982672) and turns the contribution graph green. Because the contribution-graph API can lag real events by minutes, the last-line date check is the guard against double commits when both daily ticks run on the same JKT day.

## Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/test_commit.py`:

```python
# tests/test_commit.py
import subprocess

import pytest

from keeper import already_logged_today, append_commit_push, AUTHOR_NAME, AUTHOR_EMAIL


def _git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """Real git repo with a bare origin so push succeeds offline."""
    work, bare = tmp_path / "log", tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "-b", "main", str(bare)])
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)])
    _git("config", "user.name", AUTHOR_NAME, cwd=work)
    _git("config", "user.email", AUTHOR_EMAIL, cwd=work)
    (work / "activity.log").write_text("2026-09-01 auto: kept streak alive\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "seed", cwd=work)
    _git("remote", "add", "origin", str(bare), cwd=work)
    _git("push", "-q", "origin", "main", cwd=work)
    return work


def test_appends_and_commits(repo):
    append_commit_push(str(repo), "2026-09-07")
    log = (repo / "activity.log").read_text()
    assert log.endswith("2026-09-07 auto: kept streak alive\n")
    name = subprocess.run(["git", "log", "-1", "--format=%an|%ae"],
                          cwd=repo, check=True, capture_output=True, text=True).stdout
    assert name.strip() == f"{AUTHOR_NAME}|{AUTHOR_EMAIL}"


def test_already_logged_true(repo):
    assert already_logged_today(str(repo), "2026-09-01") is True
    assert already_logged_today(str(repo), "2026-09-07") is False


def test_push_failure_raises(tmp_path):
    work = tmp_path / "orphan"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)])
    _git("config", "user.name", AUTHOR_NAME, cwd=work)
    _git("config", "user.email", AUTHOR_EMAIL, cwd=work)
    (work / "activity.log").write_text("")
    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "seed", cwd=work)
    with pytest.raises(RuntimeError):
        append_commit_push(str(work), "2026-09-07")
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `~/dev/streak-keeper`): `python -m pytest tests/test_commit.py -v`

Expected: FAIL — `NotImplementedError` from both stubs.

- [ ] **Step 3: Implement**

Replace both stubs in `keeper.py` with:

```python
def _git(*argv: str, cwd: str) -> str:
    r = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(argv)} failed: {r.stderr.strip()}")
    return r.stdout


def already_logged_today(repo: str, today: str) -> bool:
    try:
        with open(f"{repo}/{LOG_FILE}") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except FileNotFoundError:
        return False
    return bool(lines) and lines[-1].startswith(today)


def append_commit_push(repo: str, today: str) -> None:
    _git("config", "user.name", AUTHOR_NAME, cwd=repo)
    _git("config", "user.email", AUTHOR_EMAIL, cwd=repo)
    with open(f"{repo}/{LOG_FILE}", "a") as f:
        f.write(f"{today} auto: kept streak alive\n")
    _git("add", LOG_FILE, cwd=repo)
    _git("commit", "-m", f"chore: daily activity {today}", cwd=repo)
    _git("push", "origin", "main", cwd=repo)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_commit.py -v`

Expected: **3 passed**.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: append-commit-push routine with author identity"
```

## Acceptance criteria

- [ ] `python -m pytest tests/test_commit.py -v` → **3 passed**, fully offline (git only, no network — pushes hit a local bare remote).
- [ ] After `append_commit_push`, `git log -1 --format=%an|%ae` in the repo equals `jokot|25982672+jokot@users.noreply.github.com` — the repo-local identity is set on every run, independent of global git config.
- [ ] The appended line format is exactly `<YYYY-MM-DD> auto: kept streak alive` and the commit message is exactly `chore: daily activity <YYYY-MM-DD>`.
- [ ] `already_logged_today` returns True only when the last non-blank line of `activity.log` starts with `today`; a missing file returns False.
- [ ] Any git failure (e.g. push without a remote) raises `RuntimeError` — no silent success, no `--allow-empty` fallback.
- [ ] Commit `feat: append-commit-push routine with author identity` exists on `main`.
