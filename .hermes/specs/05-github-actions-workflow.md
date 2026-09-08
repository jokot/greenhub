# Spec 05 — GitHub Actions workflow (two-repo checkout)

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plants/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 5.

**Goal:** Add `.github/workflows/daily-keep.yml` to `~/dev/streak-keeper`: a twice-daily schedule (plus manual dispatch) that checks out **both** repos, sets the exact git identity inside the `streak-log` worktree, and runs `keeper.py` against it.

**Approach:** A single `keep` job. The first `actions/checkout@v4` fetches `streak-keeper` itself (this workflow's repo); the second checks out `jokot/streak-log` into the path `streak-log` using the `STREAK_PAT` secret (the default `GITHUB_TOKEN` could not push to another repo). Git identity is configured with `working-directory: streak-log` because `append_commit_push` (Spec 03) sets user config too, but the explicit step keeps the worktree's identity correct even for any manual git operations.

**Depends on:** Spec 04 (working CLI with exit codes the workflow relies on: non-zero exit fails the run).

**Files:**
- Create: `~/dev/streak-keeper/.github/workflows/daily-keep.yml`

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

GitHub Actions cron fires in **UTC** and drifts 5–60 minutes, so one tick per day is fragile: two ticks are scheduled (23:30 UTC ≈ 06:30 JKT morning, and 09:30 UTC ≈ 16:30 JKT afternoon). A Jakarta day stays covered if **either** tick runs; the idempotency guard from Spec 04 makes the second tick a harmless skip. Commits only turn the graph green because `streak-log` is public, `main` is its default branch, and the author email is the account-attributed noreply address. Push failure inside `keeper.py` exits non-zero, which marks the Actions run failed — desired behavior (FR4).

## Steps

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/daily-keep.yml` (note FR7: **both** repos are checked out, and git identity is set inside the `streak-log` worktree):

```yaml
name: daily-keep
on:
  schedule:
    - cron: "30 23 * * *"   # 06:30 JKT
    - cron: "30 9 * * *"    # 16:30 JKT
  workflow_dispatch: {}
jobs:
  keep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4            # streak-keeper itself
      - uses: actions/checkout@v4            # the commit target
        with:
          repository: jokot/streak-log
          token: ${{ secrets.STREAK_PAT }}
          path: streak-log
      - run: |
          git config user.name  "jokot"
          git config user.email "25982672+jokot@users.noreply.github.com"
        working-directory: streak-log
      - run: python keeper.py --repo streak-log
        env:
          GH_TOKEN: ${{ secrets.STREAK_PAT }}
```

- [ ] **Step 2: Lint-check the YAML locally**

Run: `python -c "import yaml, sys; yaml.safe_load(open('.github/workflows/daily-keep.yml')); print('yaml ok')"` (install `pyyaml` ad hoc if missing: `pip install -q pyyaml`; it is a dev-only check, not a runtime dependency).

Expected: `yaml ok`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "ci: twice-daily keep workflow with two-repo checkout"
```

## Acceptance criteria

- [ ] `.github/workflows/daily-keep.yml` exists in `streak-keeper`, parses as valid YAML, and is committed on `main`.
- [ ] Triggers: exactly the two `schedule` crons `"30 23 * * *"` and `"30 9 * * *"` plus `workflow_dispatch` (manual runs for Spec 07's verification).
- [ ] Two `actions/checkout@v4` steps: the first without parameters (streak-keeper itself), the second with `repository: jokot/streak-log`, `token: ${{ secrets.STREAK_PAT }}`, `path: streak-log`.
- [ ] Git identity step sets exactly `jokot` / `25982672+jokot@users.noreply.github.com` with `working-directory: streak-log`.
- [ ] Final step runs `python keeper.py --repo streak-log` with `GH_TOKEN: ${{ secrets.STREAK_PAT }}` — no `--local` in CI, no `--dry-run`, no `--now`.
- [ ] Runtime dependencies of the workflow on repo secrets are limited to `STREAK_PAT`.
