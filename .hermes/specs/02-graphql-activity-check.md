# Spec 02 — Timezone-aware GraphQL activity check

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 2.

**Goal:** Implement `has_activity_today()` in `~/dev/streak-keeper/keeper.py`: query the GitHub GraphQL API for the account's contribution total since Asia/Jakarta midnight and return whether it is positive. Strict TDD: tests first, watch them fail, implement, watch them pass.

**Approach:** The window starts at `local_midnight(now, tzid)` (exists from Spec 01) and ends at `now`; both are sent as GraphQL `DateTime!` variables. HTTP goes through stdlib `urllib.request`; tests mock `urlopen`, so no network or token is needed.

**Depends on:** Spec 01 (scaffolded repo on `main`, `local_midnight()` implemented, `has_activity_today` stub in place).

**Files:**
- Modify: `~/dev/streak-keeper/keeper.py` (replace the `has_activity_today` stub; extend the datetime import)
- Create: `~/dev/streak-keeper/tests/__init__.py` (empty — makes `tests/` a package so `import keeper` resolves from the repo root)
- Create: `~/dev/streak-keeper/tests/test_activity.py`

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

GitHub's contribution graph marks a day green when commits land on the **default branch of a public repo** authored with an **email attributed to the account** (issues, PRs, and reviews also count; automated commits are allowed). This project deliberately asks the same source the graph uses — `viewer { contributionsCollection }` — instead of a local `git log`, which would miss activity elsewhere and count unpushed commits. `totalContributions > 0` for the JKT day window ⇒ the day is already active and the keeper must do nothing.

## Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/__init__.py` as an empty file, then `tests/test_activity.py`:

```python
# tests/test_activity.py
import json
import urllib.request
from datetime import datetime, timezone
from unittest.mock import patch

from keeper import local_midnight, has_activity_today


def test_local_midnight_jakarta():
    from zoneinfo import ZoneInfo
    now = datetime(2026, 9, 7, 18, 30, tzinfo=timezone.utc)  # 01:30 JKT next day
    assert local_midnight(now, "Asia/Jakarta") == datetime(
        2026, 9, 8, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta")
    )


class _FakeResp:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode()
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _payload(total: int) -> dict:
    return {"data": {"viewer": {"contributionsCollection":
            {"contributionCalendar": {"totalContributions": total}}}}}


def test_has_activity_true_when_total_positive():
    captured = {}
    def fake_urlopen(req, timeout=30):
        captured["body"] = json.loads(req.data.decode())
        return _FakeResp(_payload(3))
    with patch.object(urllib.request, "urlopen", fake_urlopen):
        now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
        assert has_activity_today("t0k3n", "Asia/Jakarta", now=now) is True
    assert captured["body"]["query"].count("contributionsCollection") == 1


def test_has_activity_false_when_zero():
    with patch.object(urllib.request, "urlopen", lambda *a, **k: _FakeResp(_payload(0))):
        now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
        assert has_activity_today("t0k3n", "Asia/Jakarta", now=now) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `~/dev/streak-keeper`):

```bash
python -m pip install -q -r requirements-dev.txt
python -m pytest tests/test_activity.py -v
```

Expected: FAIL/ERROR — `NotImplementedError` raised inside `has_activity_today`.

- [ ] **Step 3: Implement**

In `keeper.py`, extend the datetime import to `from datetime import datetime, timezone`, then replace the `has_activity_today` stub with:

```python
def has_activity_today(token: str, tzid: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    since = local_midnight(now, tzid)
    query = """
    query($from: DateTime!, $to: DateTime!) {
      viewer {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
        }
      }
    }"""
    body = json.dumps({"query": query,
                       "variables": {"from": since.isoformat(),
                                     "to": now.isoformat()}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    total = data["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return total > 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_activity.py -v`

Expected: **3 passed** — `test_local_midnight_jakarta`, `test_has_activity_true_when_total_positive`, `test_has_activity_false_when_zero`. (The source plan said "2 passed"; the file has 3 tests — see the index README, Deviation 1.)

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: timezone-aware GraphQL activity check"
```

## Acceptance criteria

- [ ] `python -m pytest tests/test_activity.py -v` → **3 passed**, fully offline (`urlopen` is mocked; no token or network required).
- [ ] The GraphQL request body's `query` contains the string `contributionsCollection` exactly once, and `variables.from` is the ISO datetime (with `+07:00` offset) of Asia/Jakarta midnight of `now`'s JKT day.
- [ ] `has_activity_today` returns `True` iff `totalContributions > 0`.
- [ ] `tests/__init__.py` exists (empty) so `import keeper` works from the repo root.
- [ ] Runtime imports remain stdlib-only (`urllib.request`, `json`, `datetime`, `zoneinfo`).
- [ ] Commit `feat: timezone-aware GraphQL activity check` exists on `main`.
