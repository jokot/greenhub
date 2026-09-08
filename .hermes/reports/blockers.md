# Spec Blockers — GitHub Daily Activity Keeper

Task: t_90944116 (implement specs sequentially)
Date: 2026-09-08

## Spec 06 — Create `streak-log`, push both repos, set the PAT secret — BLOCKED (fatal for remote portion)

**What's done (local, verifiable):**
- `/Users/jokot/dev/streak-log` created: git repo on `main`, `README.md` + empty
  `activity.log`, seed commit `a53c8ca` authored `jokot|25982672+jokot@users.noreply.github.com`.

**What's blocked (remote):**
- Creating public `jokot/streak-log` and private `jokot/streak-keeper` on GitHub,
  and setting the `STREAK_PAT` Actions secret.

**Why it cannot proceed autonomously:**
1. **Credential minting is human-only.** The fine-grained PAT (Contents read+write
   on `jokot/streak-log` + `read:user`) must be created by a human in the GitHub UI:
   Settings → Developer settings → Fine-grained tokens. No automation can mint it
   (the spec itself states this: "The PAT must be created in the GitHub UI by hand").
2. **Wrong active gh account.** `gh auth status` shows the active account is
   `jokot-podifi`; the target repos live under `jokot` (id 25982672, currently the
   inactive keyring account). Repo creation/secret-setting would need to run against
   `jokot`.

**Unblock action (human):**
- Switch gh to the `jokot` account (`gh auth switch --user jokot`) or otherwise
  authenticate as account id 25982672.
- Mint the fine-grained PAT and make it available, then either:
  - run the Spec 06 step 1–2 commands by hand, or
  - provide the token and let a respawned worker run them.

## Spec 07 — End-to-end verification — BLOCKED (depends on Spec 06)

- Workflow triggers, idempotency second-run, and the 7-day graph gate all require
  the live repos + `STREAK_PAT` from Spec 06.
- **Verifiable now:** the local-mode commit path is already proven by the offline
  pytest suite (tests/test_commit.py + tests/test_main.py run real append-commit-push
  against temp repos + bare remotes). The `--local` real dry-run also succeeded with a
  live GraphQL call (see below).
- Block until Spec 06 unblocks; then the 7-day observation remains time-gated.

## Verified status of resolved specs (commits on main in /Users/jokot/dev/greenhub)

| Spec | Commit | Verification |
|------|--------|--------------|
| 01 scaffold | `59a9dd1` | local_midnight + constants asserted |
| 02 GraphQL check | `629538b` | 3/3 pytest offline |
| 03 append-commit-push | `164e924` | 3/3 pytest offline |
| 04 CLI/idempotency | `c73514b` | 9/9 pytest; real `--local --dry-run` → exit 0 |
| 05 Actions workflow | `b2a9c7e` | YAML parses; triggers/steps asserted |

### Deviation from spec test fixtures (documented, required)
The spec's test fixtures used `git init -q -b main <bare>.git` **without `--bare`**.
On Apple Git 2.50.1 that produces a non-bare repo, so pushing to it is refused
("refusing to update checked out branch... non-bare repository"), failing 2 of 3
tests in test_commit.py and 3/3 in test_main.py. Fixed by adding `--bare` to both
fixtures. This is a real correctness fix, not a dodge — push genuinely needs a bare
remote and the spec's as-written fixture was broken on macOS.