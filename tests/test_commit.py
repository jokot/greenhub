# tests/test_commit.py
import subprocess

import pytest

from keeper import already_logged_today, append_commit_push, AUTHOR_NAME, AUTHOR_EMAIL


def _git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """Real git repo with a bare origin so push succeeds offline."""
    work, bare = tmp_path / "log", tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)])
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)])
    _git("config", "user.name", AUTHOR_NAME, cwd=work)
    _git("config", "user.email", AUTHOR_EMAIL, cwd=work)
    (work / "activity.log").write_text("2026-09-01 auto: kept streak alive\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "seed", cwd=work)
    _git("remote", "add", "origin", str(bare), cwd=work)
    _git("push", "-q", "origin", "main", cwd=work)
    return work


def test_appends_and_commits(repo):
    append_commit_push(str(repo), "2026-09-07")
    log = (repo / "activity.log").read_text()
    assert log.endswith("2026-09-07 auto: kept streak alive\n")
    name = subprocess.run(["git", "log", "-1", "--format=%an|%ae"],
                          cwd=repo, check=True, capture_output=True, text=True).stdout
    assert name.strip() == f"{AUTHOR_NAME}|{AUTHOR_EMAIL}"


def test_already_logged_true(repo):
    assert already_logged_today(str(repo), "2026-09-01") is True
    assert already_logged_today(str(repo), "2026-09-07") is False


def test_push_failure_raises(tmp_path):
    work = tmp_path / "orphan"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)])
    _git("config", "user.name", AUTHOR_NAME, cwd=work)
    _git("config", "user.email", AUTHOR_EMAIL, cwd=work)
    (work / "activity.log").write_text("")
    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "seed", cwd=work)
    with pytest.raises(RuntimeError):
        append_commit_push(str(work), "2026-09-07")