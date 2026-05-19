"""CLI integration tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _git(args: list[str], cwd: Path) -> None:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")


def _setup_fixture() -> Path:
    d = Path(tempfile.mkdtemp(prefix="al-cli-"))
    _git(["init", "-b", "main"], d)
    _git(["config", "user.email", "t@example.com"], d)
    _git(["config", "user.name", "T"], d)
    (d / "README.md").write_text("# agent-id\n\nDID for agents.\n")
    (d / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.2.0] - 2026-04-27\n\n### Added\n- batch verify\n"
    )
    (d / "launch.yaml").write_text(
        'version: 1\n'
        "project:\n"
        "  name: agent-id\n"
        '  oneliner: "DID for agents"\n'
        '  audience: "AI builders"\n'
        "  hooks:\n"
        '    - "Self-custody"\n'
        '    - "Three functions"\n'
        "platforms:\n"
        "  - kind: hn\n"
        "    pattern: show-hn\n"
        "context:\n"
        "  repo: p-vbordei/agent-id\n"
    )
    _git(["add", "."], d)
    _git(["commit", "-m", "initial"], d)
    return d


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {**os.environ}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-m", "agent_launch", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return r.returncode, r.stdout, r.stderr


def test_context_prints_valid_json() -> None:
    d = _setup_fixture()
    code, stdout, _stderr = _run_cli(["context", "0.2.0"], d)
    assert code == 0, _stderr
    ctx = json.loads(stdout)
    assert ctx["version"] == "0.2.0"
    assert "batch verify" in ctx["changelog"]
    assert "DID for agents" in ctx["readme"]
    assert isinstance(ctx["commits"], list)


def test_exits_1_if_launch_yaml_missing() -> None:
    d = Path(tempfile.mkdtemp(prefix="al-cli-"))
    code, _stdout, _stderr = _run_cli(["context", "0.2.0"], d)
    assert code == 1


def test_exits_1_if_version_not_in_changelog() -> None:
    d = _setup_fixture()
    code, _stdout, stderr = _run_cli(["context", "9.9.9"], d)
    assert code == 1
    assert "9.9.9" in stderr
