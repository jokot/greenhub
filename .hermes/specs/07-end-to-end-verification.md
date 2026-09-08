# Spec 07 — End-to-end verification

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 7.

**Goal:** Prove the whole system works: one manual workflow run ends green and (on a quiet day) lands a commit on `jokot/streak-log`'s `main`; an immediate second run stays green **without** adding a commit (FR3 idempotency); local mode works from Jokot's laptop. Then hand off to the 7-day graph observation.

**Approach:** Trigger via `workflow_dispatch`, inspect the run and the commit log through `gh`, then exercise the CLI locally against the `~/dev/streak-log` working copy created in Spec 06. Everything here is verification — no new code.

**Depends on:** Spec 06 (both repos on GitHub, `STREAK_PAT` secret set).

**Files:** None created. Verification only.

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

What "green" means: a commit on the **default branch** (`main`) of a **public** repo (`jokot/streak-log`), authored with the **account-attributed noreply email**. The graph API can lag real events by minutes (R1), which is exactly why the negative test below must show `success` **with no new commit**: the second run must hit the log-tail idempotency skip, not the activity check. If today was genuinely active on GitHub, the positive run's `skip: already active` outcome is equally valid evidence the activity check works — in that case validate the commit path via the local-mode step with an artificial quiet window or on a future quiet day.

## Steps

- [ ] **Step 1: Positive test — trigger the workflow manually**

```bash
gh workflow run daily-keep -R jokot/streak-keeper
sleep 90 && gh run list -R jokot/streak-keeper --limit 1
```

Expected: latest run `success`. If the JKT day was quiet, the commit landed:

```bash
gh api repos/jokot/streak-log/commits --jq '.[0].commit.message'
# → "chore: daily activity <today>"
gh api repos/jokot/streak-log/commits --jq '.[0].commit.author.email'
# → 25982672+jokot@users.noreply.github.com
```

If instead the log shows `skip: already active on <today>` in the run's output, that is a valid success — record it and rely on Step 3 for the commit path.

- [ ] **Step 2: Negative test (FR3) — trigger again immediately**

```bash
gh workflow run daily-keep -R jokot/streak-keeper
sleep 90 && gh run list -R jokot/streak-keeper --limit 1
gh api repos/jokot/streak-log/commits --jq 'length'
```

Expected: run `success` again, and the commit count **unchanged** from Step 1 (the second run hit `skip: log already has <date> (graph cache lag)` or `skip: already active`).

- [ ] **Step 3: Local mode check — on this laptop**

Uses the `~/dev/streak-log` working copy created in Spec 06 (do **not** `git clone` into that path again — it already exists):

```bash
cd ~/dev/streak-log && git pull -q
GH_TOKEN=$(gh auth token) python ~/dev/streak-keeper/keeper.py --repo . --local
```

Expected: `skip:` (today already active, locally or via log tail) — or a real `kept streak alive: committed for <today>` with the commit pushed to `origin main`:

```bash
git log -1 --format='%an|%ae|%s'   # jokot|25982672+jokot@users.noreply.github.com|chore: daily activity <today>
```

- [ ] **Step 4: Acceptance gate — 7 consecutive green days**

After a week of scheduled runs: `github.com/jokot` shows 7 consecutive green days on the contribution graph. Check remotely:

```bash
gh api graphql -f query='{ viewer { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }' --jq '.data.viewer.contributionsCollection.contributionCalendar'
```

Expected: every day of the trailing week has `contributionCount > 0` (kept days show exactly the one auto commit; active days come from real activity). If a day is gray, pull the failed run's log (`gh run view <id> --log-failed -R jokot/streak-keeper`) before diagnosing.

## Acceptance criteria

- [ ] A manual `daily-keep` run completes with conclusion `success`.
- [ ] On a quiet JKT day, the run produces exactly one new commit on `jokot/streak-log@main` with message `chore: daily activity <today>` and author email `25982672+jokot@users.noreply.github.com`; on an active day, the run succeeds with a `skip: already active` message instead (both count; record which happened).
- [ ] An immediate second run also concludes `success` **and** the commit count on `jokot/streak-log` is unchanged — idempotency (FR3) proven end-to-end.
- [ ] Local mode: `keeper.py --repo . --local` exits 0 from `~/dev/streak-log` with either a `skip:` message or a pushed, correctly-attributed commit.
- [ ] The scheduled crons appear under the workflow's triggers in the Actions UI (`gh workflow list -R jokot/streak-keeper` shows `daily-keep` active).
- [ ] Final acceptance: after one week of scheduled operation, 7 consecutive green days on `github.com/jokot`. This last item is a time-gated observation — mark the spec implemented once Steps 1–3 pass and the schedule is armed; the 7-day check closes the project.
