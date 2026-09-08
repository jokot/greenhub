# Spec 06 — Create `streak-log`, push both repos, set the PAT secret

> Implementation spec for the GitHub Daily Activity Keeper. Self-contained — everything needed is in this file. Source plan (provenance only): `~/dev/plans/.hermes/plans/2026-09-07_201115-github-daily-activity-keeper.md`, Task 6.

**Goal:** Create the public `jokot/streak-log` repo (seeded with a README and an empty `activity.log`), push the private `jokot/streak-keeper` repo (workflow included), and store the fine-grained PAT as the `STREAK_PAT` Actions secret.

**Approach:** Two `gh repo create` invocations — one per repo — from the already-initialized local directories. The PAT must be created in the GitHub UI by hand (automation cannot mint credentials); everything else is CLI. This is the first spec that talks to GitHub for real, and the first whose acceptance criteria cannot be fully verified offline.

**Depends on:** Spec 05 (the workflow file must exist before `streak-keeper` is pushed, so Actions picks it up on the first push).

**Files:**
- Create locally: `~/dev/streak-log/README.md`, `~/dev/streak-log/activity.log` (then pushed as the new repo's seed commit)
- Remote: `jokot/streak-log` (public), `jokot/streak-keeper` (private), Actions secret `STREAK_PAT` on `jokot/streak-keeper`

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

The commit target must be a **public** repo with `main` as its **default branch**, or commits will never color the contribution graph. The noreply email (`25982672+jokot@users.noreply.github.com`) attributes automated commits to account `jokot` regardless of verified-email list state — that is why the seed commit already uses it. `STREAK_PAT` needs: Contents **read+write** on `jokot/streak-log` (checkout + push) and `read:user` (the GraphQL `viewer` query). Least privilege: a fine-grained PAT restricted to the single repository. The local `~/dev/streak-log` directory created here is reused by Spec 07's local-mode check — do not clone into the same path again.

## Steps

- [ ] **Step 1: Create the public repo and seed it** (from `~/dev`)

```bash
cd ~/dev
mkdir streak-log && cd streak-log && git init -b main
git config user.name  "jokot"
git config user.email "25982672+jokot@users.noreply.github.com"
printf "# streak-log\nA tiny public activity log kept by streak-keeper.\n" > README.md
touch activity.log
git add -A && git commit -m "chore: seed streak-log"
gh repo create jokot/streak-log --public --source . --push
```

- [ ] **Step 2: Push `streak-keeper` (with the workflow) and set the secret**

```bash
cd ~/dev/streak-keeper
gh repo create jokot/streak-keeper --private --source . --push
gh secret set STREAK_PAT   # paste a fine-grained PAT: Contents:read+write on jokot/streak-log, read:user
```

For the PAT: GitHub → Settings → Developer settings → Fine-grained tokens → generate with **Repository access: only `jokot/streak-log`**, **Permissions: Contents = Read and write**, plus **Account permissions: read:user** (or the equivalent fine-grained user-read permission that satisfies GraphQL `viewer` queries). Paste it when `gh secret set` prompts.

- [ ] **Step 3: Verify remotes and visibility**

```bash
gh repo view jokot/streak-log   --json visibility,defaultBranchRef -q '.visibility + " " + .defaultBranchRef.name'
gh repo view jokot/streak-keeper --json visibility,defaultBranchRef -q '.visibility + " " + .defaultBranchRef.name'
gh secret list -R jokot/streak-keeper
```

Expected: `PUBLIC main` then `PRIVATE main`; `STREAK_PAT` listed with a recent `updatedAt`.

## Acceptance criteria

- [ ] `gh repo view jokot/streak-log` shows visibility `PUBLIC` and default branch `main`; it contains a seed commit authored as `jokot <25982672+jokot@users.noreply.github.com>` touching `README.md` and `activity.log`.
- [ ] `gh repo view jokot/streak-keeper` shows visibility `PRIVATE`, default branch `main`, and contains the full history from Specs 01–05 including `.github/workflows/daily-keep.yml`.
- [ ] `gh secret list -R jokot/streak-keeper` includes `STREAK_PAT`.
- [ ] The local `~/dev/streak-log` working copy exists and tracks `origin/main` (it is reused, not re-created, by Spec 07).
- [ ] The PAT used for `STREAK_PAT` is fine-grained and scoped to: Contents read+write on `jokot/streak-log` + `read:user`; it is **not** stored anywhere in either repo's files.
