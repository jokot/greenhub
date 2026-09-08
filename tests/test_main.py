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
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
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