# Spec 04 — CLI wiring, token resolution, idempotency guard, dry-run

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 4.

**Goal:** Implement `main()` in `~/dev/streak-keeper/keeper.py` plus `_resolve_token()`: full CLI wiring with exit codes, an idempotency guard against contribution-graph cache lag, `--dry-run`, `--local` token fallback, and a `--now` test hook. Strict TDD.

**Approach:** `main()` composes the functions from Specs 02–03: check the graph first; if quiet, check the log tail; if both quiet, either print the dry-run plan or append-commit-push. All failures (`RuntimeError` from token resolution or git, `urllib.error.URLError` from the API call) are caught at the `main()` boundary, printed to stderr, and returned as exit code 1 — the fail-loudly contract (FR4).

**Depends on:** Spec 02 (`has_activity_today`) and Spec 03 (`already_logged_today`, `append_commit_push`).

**Files:**
- Modify: `~/dev/streak-keeper/keeper.py` (add `import urllib.error` at the top; add `_resolve_token`; replace the `main` stub)
- Create: `~/dev/streak-keeper/tests/test_main.py`

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

Exit-code contract: **0** when the day was already active (graph says so) **or** the log already covers today **or** a dry run completed **or** a commit was made and pushed; **non-zero (1)** for any failure — missing token, network error, git failure. The two skip paths protect against double commits: the graph check handles genuinely active days, and the log-tail check guards against the graph API lagging real events by minutes when the second daily tick fires (FR3 idempotency). `--now` exists purely so tests can pin time; CI and humans omit it.

## Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main.py`:

```python
# tests/test_main.py
import subprocess
from unittest.mock import patch

import keeper


def _init(tmp):
    """Real repo with a seed commit and a bare origin so push succeeds offline.

    NOTE: append_commit_push() (Spec 03) pushes to origin main; a bare
    git-init without a seed commit would make main() return 1, not 0.
    """
    repo, bare = tmp / "log", tmp / "origin.git"
    subprocess.run(["git", "init", "-q", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    for arg in ("user.name", "user.email"):
        subprocess.run(["git", "config", arg, "x" if "name" in arg else "x@x"],
                       cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("seed\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=repo, check=True, capture_output=True)
    return str(repo)


def test_main_skips_when_active(tmp_path):
    repo = _init(tmp_path)
    with patch.object(keeper, "has_activity_today", return_value=True), \
         patch.object(keeper, "_resolve_token", return_value="t"):
        assert keeper.main(["--repo", repo, "--tz", "Asia/Jakarta",
                            "--now", "2026-09-07T10:00:00+00:00"]) == 0


def test_main_commits_when_quiet_then_skips_second_run(tmp_path):
    repo = _init(tmp_path)
    argv = ["--repo", repo, "--tz", "Asia/Jakarta",
            "--now", "2026-09-07T10:00:00+00:00"]
    with patch.object(keeper, "has_activity_today", return_value=False), \
         patch.object(keeper, "_resolve_token", return_value="t"):
        assert keeper.main(argv) == 0
        assert keeper.main(argv) == 0          # second run: FR3 skip
    lines = open(f"{repo}/activity.log").read().strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("2026-09-07")


def test_main_dry_run_touches_nothing(tmp_path):
    repo = _init(tmp_path)
    with patch.object(keeper, "has_activity_today", return_value=False), \
         patch.object(keeper, "_resolve_token", return_value="t"):
        assert keeper.main(["--repo", repo, "--dry-run",
                            "--now", "2026-09-07T10:00:00+00:00"]) == 0
    assert not (tmp_path / "log" / "activity.log").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `~/dev/streak-keeper`): `python -m pytest tests/test_main.py -v`

Expected: FAIL — `argparse` accepts no `--now`, and `keeper._resolve_token` does not exist.

- [ ] **Step 3: Implement `_resolve_token()` and `main()`**

In `keeper.py`, add `import urllib.error` to the top imports, then:

```python
def _resolve_token(local: bool) -> str:
    import os
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    if local:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    raise RuntimeError("no GitHub token: set GH_TOKEN or run with --local while gh is logged in")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--local", action="store_true")
    p.add_argument("--tz", default=DEFAULT_TZ)
    p.add_argument("--now", help="ISO instant override (tests)")
    args = p.parse_args(argv)
    try:
        token = _resolve_token(args.local)
        now = (datetime.fromisoformat(args.now) if args.now
               else datetime.now(timezone.utc))
        today = now.astimezone(ZoneInfo(args.tz)).date().isoformat()
        if has_activity_today(token, args.tz, now=now):
            print(f"skip: already active on {today} ({args.tz})")
            return 0
        if already_logged_today(args.repo, today):
            print(f"skip: log already has {today} (graph cache lag)")
            return 0
        if args.dry_run:
            print(f"dry-run: would commit 'chore: daily activity {today}' in {args.repo}")
            return 0
        append_commit_push(args.repo, today)
        print(f"kept streak alive: committed for {today}")
        return 0
    except (RuntimeError, urllib.error.URLError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
```

- [ ] **Step 4: Run the full suite + a real dry-run**

```bash
python -m pytest tests/ -v
python keeper.py --dry-run --repo /tmp/any --local   # GH_TOKEN set or gh logged in
```

Expected: **9 passed** (3 activity + 3 commit + 3 main; the source plan said "6 passed" — see the index README, Deviation 1). The dry-run prints `dry-run: would commit 'chore: daily activity <today>' ...` or `skip: ...` and exits 0 without touching `/tmp/any`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: CLI wiring, idempotency guard, dry-run"
```

## Acceptance criteria

- [ ] `python -m pytest tests/ -v` → **9 passed** (3 + 3 + 3 across test_activity, test_commit, test_main).
- [ ] Exit codes: activity on graph ⇒ 0 with a `skip:` message and no commit; quiet day ⇒ 0 with a commit pushed; **second run same day ⇒ 0 with `skip: log already has <date> (graph cache lag)` and exactly one log line**; `--dry-run` ⇒ 0 with nothing written to the repo; missing token ⇒ 1 with `error:` on stderr.
- [ ] Token resolution order: `GH_TOKEN` env var first; then, only with `--local`, `gh auth token` stdout; otherwise `RuntimeError`.
- [ ] `--now` accepts an ISO instant (e.g. `2026-09-07T10:00:00+00:00`) and pins both the GraphQL window and the log date.
- [ ] The `main()` failure handler catches both `RuntimeError` and `urllib.error.URLError` and returns 1 — never a silent success.
- [ ] Commit `feat: CLI wiring, idempotency guard, dry-run` exists on `main`.
