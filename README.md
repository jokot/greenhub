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