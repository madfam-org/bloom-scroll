"""
The daily ingest CronJob's inline script (infra/k8s/production/ingest-cronjob.yaml).

A new Job pod's first connects to the API are refused for a few seconds while
the NetworkPolicy controller admits the pod's IP. The script must wait for the
API (connect failures only, bounded), then run its calls; and keep its exit
contract: 1 only when nothing worked.

The script is executed exactly as the manifest ships it, with httpx's
transport replaced by a scripted one and the clock faked.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

MANIFEST = (
    Path(__file__).resolve().parents[2] / "infra" / "k8s" / "production" / "ingest-cronjob.yaml"
)


_REAL_CLIENT = httpx.Client


def _script() -> str:
    cronjob = yaml.safe_load(MANIFEST.read_text())
    container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["python", "-c"]
    script = container["args"][0]
    assert isinstance(script, str)
    return script


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


Handler = Callable[[httpx.Request], httpx.Response]


def _run(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> tuple[int, _Clock, list[str]]:
    clock = _Clock()
    seen: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        return handler(request)

    def client_factory(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(recording)
        return _REAL_CLIENT(*args, **kwargs)

    monkeypatch.setenv("INGEST_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "Client", client_factory)
    monkeypatch.setattr("time.sleep", clock.sleep)
    monkeypatch.setattr("time.monotonic", clock.monotonic)

    with pytest.raises(SystemExit) as exited:
        exec(compile(_script(), str(MANIFEST), "exec"), {"__name__": "__main__"})
    code = exited.value.code
    return (code if isinstance(code, int) else 1), clock, seen


def _refused(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 111] Connection refused", request=request)


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok"})


def test_waits_through_refused_connects_then_runs_every_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refusals = {"left": 3}

    def handler(request: httpx.Request) -> httpx.Response:
        if refusals["left"]:
            refusals["left"] -= 1
            return _refused(request)
        return _ok(request)

    code, clock, seen = _run(monkeypatch, handler)

    assert code == 0
    assert clock.sleeps == [1.0, 2.0, 4.0]
    assert seen[:4] == ["GET /health"] * 4
    posts = [s for s in seen if s.startswith("POST")]
    assert len(posts) == 6
    assert all(p.startswith("POST /api/v1/ingest/") for p in posts)


def test_gives_up_after_the_budget_and_exits_1_without_calling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    code, clock, seen = _run(monkeypatch, _refused)

    assert code == 1
    assert clock.sleeps == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0, 8.0]
    assert sum(clock.sleeps) <= 45.0
    assert all(s == "GET /health" for s in seen)


def test_an_http_error_from_health_counts_as_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A degraded /health (503) is an answer: no retry, the calls report for
    # themselves.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(503)
        return _ok(request)

    code, clock, seen = _run(monkeypatch, handler)

    assert code == 0
    assert clock.sleeps == []
    assert seen.count("GET /health") == 1


def test_non_connect_errors_are_not_retried_by_the_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A read timeout means the pod connected: not the admission race. The
    # wait stops at once and the calls run (and report) as before.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            raise httpx.ReadTimeout("read timed out", request=request)
        return _ok(request)

    code, clock, seen = _run(monkeypatch, handler)

    assert code == 0
    assert clock.sleeps == []
    assert seen.count("GET /health") == 1
    assert len([s for s in seen if s.startswith("POST")]) == 6


def test_partial_failure_is_tolerated_total_failure_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def one_bad(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/neocities"):
            return httpx.Response(502)
        return _ok(request)

    assert _run(monkeypatch, one_bad)[0] == 0

    def all_bad(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return _ok(request)
        return httpx.Response(500)

    assert _run(monkeypatch, all_bad)[0] == 1
