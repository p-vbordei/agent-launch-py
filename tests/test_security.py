"""Security tests S2 (no tools), S4 (no fetch), S5 (sandboxed --out)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from agent_launch.config import LinkedinPlatform, MastodonPlatform, Project
from agent_launch.context import GatheredContext
from agent_launch.draft import draft_one


def _project() -> Project:
    return Project(name="x", oneliner="y", audience="a", hooks=["h"])


def _ctx() -> GatheredContext:
    return GatheredContext(version="0.2.0", changelog="c", readme="r", commits=["c"])


@pytest.mark.asyncio
async def test_s2_no_tools_field_in_params() -> None:
    """S2: SDK params for draft_one must NEVER include `tools` (no shell access)."""
    captured: dict[str, Any] = {}

    class _M:
        async def create(self, params: dict[str, Any]) -> dict[str, Any]:
            captured.update(params)
            return {"content": [{"type": "text", "text": "short text"}]}

    class _Client:
        messages = _M()

    await draft_one(
        platform=MastodonPlatform(kind="mastodon", instance="h", handle="v"),
        project=_project(),
        context=_ctx(),
        repo="o/r",
        anthropic=_Client(),
    )
    assert "tools" not in captured
    assert captured["model"] == "claude-opus-4-7"
    assert isinstance(captured["system"], str)


@pytest.mark.asyncio
async def test_s4_no_socket_calls() -> None:
    """S4: draft_one runs purely in-process; no network sockets opened."""
    import socket

    real_socket = socket.socket
    called = {"called": False}

    def fake_socket(*a: Any, **kw: Any):  # type: ignore[no-untyped-def]
        called["called"] = True
        raise RuntimeError("S4 violation: draft attempted to open socket")

    socket.socket = fake_socket  # type: ignore[assignment]
    try:

        class _M:
            async def create(self, params: dict[str, Any]) -> dict[str, Any]:
                return {"content": [{"type": "text", "text": "short text"}]}

        class _Client:
            messages = _M()

        await draft_one(
            platform=LinkedinPlatform(kind="linkedin"),
            project=_project(),
            context=_ctx(),
            repo="o/r",
            anthropic=_Client(),
        )
        assert called["called"] is False
    finally:
        socket.socket = real_socket  # type: ignore[assignment]


def _git(args: list[str], cwd: Path) -> None:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")


def _setup_fixture() -> Path:
    d = Path(tempfile.mkdtemp(prefix="s5-"))
    _git(["init", "-b", "main"], d)
    _git(["config", "user.email", "t@example.com"], d)
    _git(["config", "user.name", "T"], d)
    (d / "README.md").write_text("# x\n")
    (d / "CHANGELOG.md").write_text("## [0.2.0]\n\n### Added\n- thing\n")
    (d / "launch.yaml").write_text(
        'version: 1\nproject:\n  name: x\n  oneliner: y\n  audience: a\n  hooks: ["a"]\n'
        "platforms:\n  - kind: linkedin\ncontext:\n  repo: o/r\n"
    )
    _git(["add", "."], d)
    _git(["commit", "-m", "i"], d)
    return d


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    r = subprocess.run(
        [sys.executable, "-m", "agent_launch", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return r.returncode, r.stdout, r.stderr


def test_s5_rejects_absolute_out_outside_cwd() -> None:
    d = _setup_fixture()
    code, _stdout, stderr = _run_cli(["draft", "0.2.0", "--out", "/tmp/escape"], d)
    assert code == 1
    assert "inside" in stderr


def test_s5_rejects_dotdot_traversal() -> None:
    d = _setup_fixture()
    code, _stdout, stderr = _run_cli(["draft", "0.2.0", "--out", "../escape"], d)
    assert code == 1
    assert "inside" in stderr
