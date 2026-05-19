"""Load per-platform prompt templates from `prompts/<kind>.md`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml

PlatformKind = Literal["hn", "reddit", "x", "mastodon", "linkedin"]
_ALL_KINDS: tuple[PlatformKind, ...] = ("hn", "reddit", "x", "mastodon", "linkedin")


@dataclass(frozen=True)
class PlatformTemplate:
    platform: PlatformKind
    length_cap: int
    length_cap_field: Literal["body", "per_tweet"]
    output_format: Literal["json", "thread", "text"]
    title_cap: int | None
    min_tweets: int | None
    max_tweets: int | None
    system: str
    user_template: str
    anti_examples: str


def list_platforms() -> list[PlatformKind]:
    return list(_ALL_KINDS)


def _read_prompt(kind: PlatformKind) -> str:
    """Read prompt file from packaged data; fall back to repo prompts/ dir."""
    # Try packaged resource first.
    try:
        pkg = resources.files("agent_launch._data.prompts")
        candidate = pkg.joinpath(f"{kind}.md")
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    # Fall back to repo-relative prompts/ (useful in dev / tests before install).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate_path = parent / "prompts" / f"{kind}.md"
        if candidate_path.is_file():
            return candidate_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"platform template not found: {kind}")


def load_platform_template(kind: str) -> PlatformTemplate:
    if kind not in _ALL_KINDS:
        raise ValueError(f"unknown platform: {kind}")
    raw = _read_prompt(kind)  # type: ignore[arg-type]
    m = re.match(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$", raw)
    if not m:
        raise ValueError(f"invalid template (missing frontmatter): {kind}")
    fm_yaml = m.group(1)
    body = m.group(2)
    fm = yaml.safe_load(fm_yaml)
    if not isinstance(fm, dict):
        raise ValueError(f"invalid frontmatter: {kind}")

    return PlatformTemplate(
        platform=fm["platform"],
        length_cap=int(fm["length_cap"]),
        length_cap_field=fm["length_cap_field"],
        output_format=fm["output_format"],
        title_cap=int(fm["title_cap"]) if "title_cap" in fm else None,
        min_tweets=int(fm["min_tweets"]) if "min_tweets" in fm else None,
        max_tweets=int(fm["max_tweets"]) if "max_tweets" in fm else None,
        system=_extract_section(body, "System"),
        user_template=_extract_section(body, "User"),
        anti_examples=_extract_section(body, "Anti-examples"),
    )


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n([\s\S]*?)(?=^## |\Z)"
    m = re.search(pattern, body, flags=re.MULTILINE)
    if not m:
        raise ValueError(f'section "{heading}" not found in template')
    return m.group(1).strip()
