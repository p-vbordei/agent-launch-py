from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from agent_launch.context import ContextError, gather_context


def _git(args: list[str], cwd: Path) -> None:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")


def _setup_repo() -> Path:
    d = Path(tempfile.mkdtemp(prefix="al-ctx-"))
    _git(["init", "-b", "main"], d)
    _git(["config", "user.email", "t@example.com"], d)
    _git(["config", "user.name", "T"], d)
    (d / "README.md").write_text("# agent-id\n\nMachine-first identity for AI agents.\n")
    (d / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.2.0] - 2026-04-27\n\n### Added\n- batch verification\n\n"
        "## [0.1.0] - 2026-04-20\n\n### Added\n- initial release\n"
    )
    _git(["add", "."], d)
    _git(["commit", "-m", "feat: batch verification"], d)
    (d / "README.md").write_text("# agent-id\n\nMachine-first identity. Updated.\n")
    _git(["add", "."], d)
    _git(["commit", "-m", "docs: update README"], d)
    return d


def test_extracts_changelog_and_commits() -> None:
    d = _setup_repo()
    ctx = gather_context(d, "0.2.0")
    assert "batch verification" in ctx.changelog
    assert "## [0.1.0]" not in ctx.changelog
    assert "Machine-first identity" in ctx.readme
    assert len(ctx.commits) >= 2
    assert any("batch verification" in c for c in ctx.commits)


def test_throws_on_missing_version() -> None:
    d = _setup_repo()
    with pytest.raises(ContextError):
        gather_context(d, "9.9.9")


def test_throws_on_missing_readme() -> None:
    d = _setup_repo()
    (d / "README.md").unlink()
    with pytest.raises(ContextError, match=r"README"):
        gather_context(d, "0.2.0")


def test_truncates_readme_to_2000_chars() -> None:
    d = _setup_repo()
    (d / "README.md").write_text("a" * 5000)
    ctx = gather_context(d, "0.2.0")
    assert len(ctx.readme) <= 2000


def test_reads_optional_manifest() -> None:
    d = _setup_repo()
    manifest_path = d / "release-manifest.json"
    manifest_path.write_text(
        json.dumps({"schema": "agent-publish/release-manifest/v1", "version": "0.2.0"})
    )
    ctx = gather_context(d, "0.2.0", manifest_path=manifest_path)
    assert ctx.manifest is not None
    assert ctx.manifest["version"] == "0.2.0"
