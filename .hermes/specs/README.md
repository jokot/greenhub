# GitHub Daily Activity Keeper — Implementation Specs

Decomposed from the source plan `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md` (evidence gathered 2026-09-07). Each spec in this directory is **self-contained**: an engineer can implement it without re-reading the source plan. The plan is referenced only for provenance.

## What this builds

A small Python CLI (`streak-keeper`) that keeps Jokot's GitHub contribution graph green every day: on any Asia/Jakarta day with no GitHub activity, it appends a dated line to `activity.log` in the public repo `jokot/streak-log`, commits, and pushes to `main`. It runs twice daily from GitHub Actions and can also be run locally (`--local`).

Why that keeps the graph green: GitHub counts a day as a contribution when commits land on the **default branch** of a **public** repo authored with an **email attributed to the account** (issues, PRs, and reviews also count; automated commits are allowed). The author-email trap is solved by the global noreply identity below. The "already active today?" check reads `viewer.contributionsCollection` — the **same source the graph itself uses** — instead of a local `git log`, which would miss activity elsewhere and count unpushed commits.

## Global constraints (apply to every spec; repeated verbatim in each spec)

- Python 3.11+; stdlib only at runtime (`urllib.request`, `urllib.error`, `json`, `subprocess`, `argparse`, `zoneinfo`). `pytest` is a dev-only dependency (`requirements-dev.txt`).
- Commit author identity, everywhere, exactly: name `jokot`, email `25982672+jokot@users.noreply.github.com` (account `jokot`, id `25982672` — the noreply address always attributes to the account regardless of verified-email list state).
- "Today" always means the **Asia/Jakarta (UTC+7)** calendar day — for the GraphQL window and for log-line dates.
- `jokot/streak-log` is **public**; commits go only to `main` (the default branch). `jokot/streak-keeper` is private.
- One commit per quiet day; never `--allow-empty`; no backfill in v1.
- Push/network failure ⇒ non-zero exit. The tool must never exit 0 without having verified activity or committed.
- GraphQL auth via the `GH_TOKEN` env var; `--local` mode may fall back to `gh auth token`.
- PAT scope (`STREAK_PAT`): fine-grained, Contents: read+write on `jokot/streak-log`, plus `read:user` for the GraphQL query.

## Implementation order

Implement strictly in order; each spec's acceptance criteria gate the next.

| # | Spec file | Deliverable | Depends on |
|---|-----------|-------------|------------|
| 01 | `01-scaffold-streak-keeper.md` | Repo `~/dev/streak-keeper` on `main`: `keeper.py` skeleton (constants, `local_midnight()`, stubs), README, `.gitignore`, `requirements-dev.txt`; initial commit | — |
| 02 | `02-graphql-activity-check.md` | `has_activity_today()` implemented TDD; `tests/test_activity.py` green (3 tests, offline) | 01 |
| 03 | `03-append-commit-push.md` | `already_logged_today()` + `append_commit_push()` implemented TDD against a real temp repo + bare remote (3 tests) | 01 |
| 04 | `04-cli-main-idempotency.md` | `main()` wired: exit codes, `--dry-run`, `--local`, `--now`, token resolution, idempotency guard; full suite green (9 tests) | 02, 03 |
| 05 | `05-github-actions-workflow.md` | `.github/workflows/daily-keep.yml`: two-repo checkout, git identity set inside the `streak-log` worktree, two cron ticks + manual dispatch | 04 |
| 06 | `06-create-streak-log-and-secrets.md` | Public `jokot/streak-log` created and seeded; private `jokot/streak-keeper` pushed (workflow included); `STREAK_PAT` secret set | 05 |
| 07 | `07-end-to-end-verification.md` | Workflow run green; idempotency proven by an immediate second run; local-mode check; 7-day graph acceptance gate | 06 |

## Final file structure (after all specs)

- `~/dev/streak-keeper/keeper.py` — the entire CLI: timezone math, GraphQL check, git routine, `main()`
- `~/dev/streak-keeper/tests/test_activity.py` — GraphQL payload/window + response parsing
- `~/dev/streak-keeper/tests/test_commit.py` — commit routine against a real temp repo + bare remote
- `~/dev/streak-keeper/tests/test_main.py` — CLI exit codes, idempotency (double-run skip), dry-run
- `~/dev/streak-keeper/.github/workflows/daily-keep.yml` — two-repo checkout workflow
- `~/dev/streak-log/activity.log` — one line per kept day (repo created in Spec 06)

## Deviations from the source plan (deliberate, documented)

1. **Test-count expectations corrected.** `tests/test_activity.py` contains 3 tests (the plan said "2 passed"); the full suite is 9 tests (the plan said "6 passed").
2. **Spec 04's `_init()` fixture creates a seed commit and a bare `origin` remote.** The plan's fixture ran bare `git init` with no remote, so `append_commit_push`'s push failed and `main()` returned 1 — the plan's own test asserted 0 and could not pass.
3. **Spec 07 reuses the local `~/dev/streak-log` working copy created in Spec 06** instead of `git clone`-ing into `~/dev/streak-log`, which would collide with the directory Spec 06 already created there.
4. `tests/test_idempotency.py` mentioned in the plan's file-structure section does not exist as a separate file; the idempotency tests live in `tests/test_main.py` (as the plan's own Task 4 specifies).

## Known risks carried into the specs

- **R1 — Graph API cache lag:** `contributionsCollection` can lag real events by minutes; the log-tail idempotency check (Spec 04, FR3) prevents double commits between the two daily ticks.
- **R2 — Cron drift:** Actions cron fires in UTC and drifts 5–60 minutes; two ticks per day (23:30 UTC = 06:30 JKT and 09:30 UTC = 16:30 JKT) make a single missed tick harmless — a JKT day is covered if either tick runs.
- **R3 — Token scope:** see Global constraints (`STREAK_PAT`).
- **R4 — Optics:** automation is allowed by GitHub; a perfectly uniform graph is human-detectable. Accepted by the plan (assumption A4).

## Non-goals (v1)

Backfilling history (deferred to Phase 2: a `--backfill N` loop over past dates using `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`); variable commit counts/hours; private-repo graph coloring; any log content beyond the one dated line.
