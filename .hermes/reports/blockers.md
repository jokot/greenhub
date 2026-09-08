# Spec Blockers — GitHub Daily Activity Keeper

Task: t_90944116 (implement specs sequentially)
Date: 2026-09-08

## Status: UNBLOCKED — specs 06 & 07 remote portion completed (2026-09-08)

The earlier credential-only blocker was resolved by a human (crazydave): the gh
account was switched to `jokot`, the fine-grained `STREAK_PAT` was minted and set,
and the remote repos were created. Verified live on GitHub:

- `gh auth status` → active account `jokot` (id 25982672).
- `jokot/streak-log` → **PUBLIC**, default branch `main`, seed commit `a53c8ca`
  authored `jokot <25982672+jokot@users.noreply.github.com>` touching `README.md`
  and `activity.log`.
- `gh secret list -R jokot/greenhub` → `STREAK_PAT` present (updatedAt 2026-09-08).
- Local `~/dev/streak-log` working copy exists and tracks `origin/main`.

## Deviation (documented, non-fatal): keeper repo is `jokot/greenhub` (public), not `jokot/streak-keeper` (private)

The spec (06) calls for a **private** `jokot/streak-keeper` repo holding the
workflow + `STREAK_PAT`. The actual implementation repo is named `greenhub`
(`/Users/jokot/dev/greenhub`, the task's designated workspace), and crazydave
pushed it to GitHub as **public** `jokot/greenhub`, set the secret there, and the
`daily-keep` workflow is active on it. There is **no** `jokot/streak-keeper` repo.

This is a naming/visibility deviation, not a functional one: the keeper code is
not secret-bearing (the PAT lives only in the Actions secret, never in files), the
workflow targets the correct public `jokot/streak-log`, and the secret is set. The
spec's "private" rationale (don't expose keeper code) is relaxed because the code
contains no credentials. If strict spec compliance is required, a private
`jokot/streak-keeper` repo would need to be created and the secret mirrored — but
nothing in the running system depends on it.

## Spec 07 — End-to-end verification — Steps 1–3 PASSED; Step 4 time-gated

- **Step 1 (positive):** manual `daily-keep` dispatch → run `34232210013`
  concluded **success**. Log showed `skip: already active on 2026-09-08
  (Asia/Jakarta)` — a **valid** success per the spec (today was an active GitHub
  day; the activity check fired). No commit landed, which is correct for an active
  day.
- **Step 2 (negative / FR3 idempotency):** immediate second dispatch → run
  `34232653263` concluded **success**, and the commit count on `jokot/streak-log`
  stayed **1 → 1** (unchanged). Log: `skip: already active on 2026-09-08`.
  Idempotency proven end-to-end.
- **Step 3 (local mode):** `keeper.py --repo . --local` from `~/dev/streak-log`
  exited **0** with `skip: already active on 2026-09-08 (Asia/Jakarta)` — valid
  outcome on an active day.
- **Step 4 (7-day graph gate):** time-gated. Requires a week of scheduled
  `30 23 * * *` / `30 9 * * *` runs. The schedule is armed (`gh workflow list -R
  jokot/greenhub` shows `daily-keep active`). Re-check the contribution graph
  after 7 consecutive days.

## Verified status of resolved specs (commits on main in /Users/jokot/dev/greenhub)

| Spec | Commit | Verification |
|------|--------|--------------|
| 01 scaffold | `59a9dd1` | local_midnight + constants asserted |
| 02 GraphQL check | `629538b` | 3/3 pytest offline |
| 03 append-commit-push | `164e924` | 3/3 pytest offline |
| 04 CLI/idempotency | `c73514b` | 9/9 pytest; real `--local --dry-run` → exit 0 |
| 05 Actions workflow | `b2a9c7e` | YAML parses; triggers/steps asserted |
| 06 repos + secret | `a225791` + live | PUBLIC streak-log; secret on greenhub; local seed tracks origin/main |
| 07 E2E | (verification only) | Steps 1–3 pass; Step 4 time-gated |

### Deviation from spec test fixtures (documented, required)
The spec's test fixtures used `git init -q -b main <bare>.git` **without `--bare`**.
On Apple Git 2.50.1 that produces a non-bare repo, so pushing to it is refused
("refusing to update checked out branch... non-bare repository"), failing 2 of 3
tests in test_commit.py and 3/3 in test_main.py. Fixed by adding `--bare` to both
fixtures. This is a real correctness fix, not a dodge — push genuinely needs a bare
remote and the spec's as-written fixture was broken on macOS.

### Security note
`.tokensave/` (a local token-storage dir) is untracked and has been added to
`.gitignore` so no token can be accidentally committed. The `STREAK_PAT` value is
never stored in either repo's files.