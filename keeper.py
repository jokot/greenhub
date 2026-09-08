"""streak-keeper: keep the GitHub contribution graph green."""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

AUTHOR_NAME = "jokot"
AUTHOR_EMAIL = "25982672+jokot@users.noreply.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
DEFAULT_TZ = "Asia/Jakarta"
LOG_FILE = "activity.log"


def local_midnight(now: datetime, tzid: str) -> datetime:
    """Local midnight of `now`'s day, in `tzid`, as an aware datetime."""
    tz = ZoneInfo(tzid)
    local = now.astimezone(tz)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _resolve_token(local: bool) -> str:
    import os
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    if local:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    raise RuntimeError("no GitHub token: set GH_TOKEN or run with --local while gh is logged in")


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


if __name__ == "__main__":
    sys.exit(main())