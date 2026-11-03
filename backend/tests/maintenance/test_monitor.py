"""Monitoring detects missed, failed, and stuck maintenance work."""

from datetime import datetime, timedelta, timezone

from src.maintenance.monitor import unhealthy_jobs


def test_missing_and_failed_jobs_are_unhealthy():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    assert unhealthy_jobs(
        {"missing": 60, "failed": 60}, [{"job": "failed", "state": "failed"}], now=now
    ) == ["missing", "failed"]


def test_recent_success_is_healthy_and_old_success_is_not():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=2)).isoformat()
    old = (now - timedelta(minutes=20)).isoformat()
    rows = [
        {"job": "recent", "state": "idle", "last_succeeded_at": recent},
        {"job": "old", "state": "idle", "last_succeeded_at": old},
    ]
    assert unhealthy_jobs({"recent": 300, "old": 300}, rows, now=now) == ["old"]


def test_running_first_pass_has_grace_but_stuck_pass_does_not():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    rows = [
        {"job": "fresh", "state": "running", "started_at": now.isoformat()},
        {
            "job": "stuck",
            "state": "running",
            "started_at": (now - timedelta(hours=1)).isoformat(),
        },
    ]
    assert unhealthy_jobs({"fresh": 300, "stuck": 300}, rows, now=now) == ["stuck"]


def test_later_failure_is_unhealthy_until_next_success():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    rows = [
        {
            "job": "retry",
            "state": "idle",
            "last_succeeded_at": (now - timedelta(minutes=2)).isoformat(),
            "last_failed_at": (now - timedelta(minutes=1)).isoformat(),
        }
    ]
    assert unhealthy_jobs({"retry": 300}, rows, now=now) == ["retry"]


def test_stale_organization_phone_guard_is_reported_without_organization_id():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    rows = [
        {
            "job": "phone-guard",
            "state": "running",
            "started_at": (now - timedelta(hours=1)).isoformat(),
        }
    ]
    assert unhealthy_jobs({}, rows, now=now) == ["phone-guard"]
