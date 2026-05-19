"""Gather repo context: CHANGELOG section, README, recent commits, optional manifest."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContextError(Exception):
    """Raised when required repo context (CHANGELOG, README, version) is missing."""


README_MAX = 2000


@dataclass(frozen=True)
class GatheredContext:
    version: str
    changelog: str
    readme: str
    commits: list[str]
    manifest: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "changelog": self.changelog,
            "readme": self.readme,
            "commits": list(self.commits),
        }
        if self.manifest is not None:
            d["manifest"] = self.manifest
        return d


def gather_context(
    cwd: str | Path,
    version: str,
    *,
    manifest_path: str | Path | None = None,
) -> GatheredContext:
    """Gather CHANGELOG section, README, recent commits, optional manifest from a repo."""
    cwd_p = Path(cwd)

    changelog_path = cwd_p / "CHANGELOG.md"
    if not changelog_path.exists():
        raise ContextError(f"CHANGELOG.md not found at {changelog_path}")
    changelog = _extract_changelog_section(changelog_path.read_text(encoding="utf-8"), version)

    readme_path = cwd_p / "README.md"
    if not readme_path.exists():
        raise ContextError(f"README.md not found at {readme_path}")
    readme = readme_path.read_text(encoding="utf-8")[:README_MAX]

    commits = _read_recent_commits(cwd_p, 50)

    manifest: dict[str, Any] | None = None
    if manifest_path is not None:
        mp = Path(manifest_path)
        if not mp.exists():
            raise ContextError(f"manifest file not found: {mp}")
        try:
            manifest = json.loads(mp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise ContextError(f"failed to parse manifest at {mp}: {err}") from err

    return GatheredContext(
        version=version,
        changelog=changelog,
        readme=readme,
        commits=commits,
        manifest=manifest,
    )


def _extract_changelog_section(content: str, version: str) -> str:
    escaped = re.escape(version)
    pattern = rf"^## \[{escaped}\][^\n]*\n([\s\S]*?)(?=^## \[|\Z)"
    m = re.search(pattern, content, flags=re.MULTILINE)
    if not m:
        raise ContextError(f"version {version} not found in CHANGELOG.md")
    return m.group(1).strip()


def _read_recent_commits(cwd: Path, limit: int) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "log", "--pretty=format:%h %s", f"-{limit}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []
    if r.returncode != 0:
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]
