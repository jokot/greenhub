# tests/test_activity.py
import json
import urllib.request
from datetime import datetime, timezone
from unittest.mock import patch

from keeper import local_midnight, has_activity_today


def test_local_midnight_jakarta():
    from zoneinfo import ZoneInfo
    now = datetime(2026, 9, 7, 18, 30, tzinfo=timezone.utc)  # 01:30 JKT next day
    assert local_midnight(now, "Asia/Jakarta") == datetime(
        2026, 9, 8, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta")
    )


class _FakeResp:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode()
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _payload(total: int) -> dict:
    return {"data": {"viewer": {"contributionsCollection":
            {"contributionCalendar": {"totalContributions": total}}}}}


def test_has_activity_true_when_total_positive():
    captured = {}
    def fake_urlopen(req, timeout=30):
        captured["body"] = json.loads(req.data.decode())
        return _FakeResp(_payload(3))
    with patch.object(urllib.request, "urlopen", fake_urlopen):
        now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
        assert has_activity_today("t0k3n", "Asia/Jakarta", now=now) is True
    assert captured["body"]["query"].count("contributionsCollection") == 1


def test_has_activity_false_when_zero():
    with patch.object(urllib.request, "urlopen", lambda *a, **k: _FakeResp(_payload(0))):
        now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
        assert has_activity_today("t0k3n", "Asia/Jakarta", now=now) is False