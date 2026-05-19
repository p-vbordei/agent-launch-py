"""launch.yaml loader + strict pydantic schema."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class LaunchConfigError(Exception):
    """Raised when launch.yaml is missing or fails schema validation."""


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SUBREDDIT_RE = re.compile(r"^[a-zA-Z0-9_]{2,21}$")
_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HnPlatform(_Strict):
    kind: Literal["hn"]
    pattern: Literal["show-hn", "ask-hn", "regular"]


class RedditPlatform(_Strict):
    kind: Literal["reddit"]
    subreddit: str = Field(..., pattern=_SUBREDDIT_RE.pattern)


class XPlatform(_Strict):
    kind: Literal["x"]
    handle: str = Field(..., min_length=1)


class MastodonPlatform(_Strict):
    kind: Literal["mastodon"]
    instance: str = Field(..., min_length=1)
    handle: str = Field(..., min_length=1)


class LinkedinPlatform(_Strict):
    kind: Literal["linkedin"]


Platform = Annotated[
    HnPlatform | RedditPlatform | XPlatform | MastodonPlatform | LinkedinPlatform,
    Field(discriminator="kind"),
]


class Project(_Strict):
    name: str = Field(..., pattern=_NAME_RE.pattern)
    oneliner: str = Field(..., min_length=1, max_length=120)
    audience: str = Field(..., min_length=1, max_length=200)
    hooks: list[str] = Field(..., min_length=1, max_length=5)


class Context(_Strict):
    repo: str = Field(..., pattern=_REPO_RE.pattern)
    manifest: str | None = None


class LaunchConfig(_Strict):
    version: Literal[1]
    project: Project
    platforms: list[Platform] = Field(..., min_length=1)
    context: Context


def load_launch_config(path: str | Path) -> LaunchConfig:
    """Load and strictly validate a launch.yaml file."""
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (yaml.YAMLError, OSError) as err:
        raise LaunchConfigError(f"failed to read or parse {p}: {err}") from err

    try:
        return LaunchConfig.model_validate(raw)
    except ValidationError as err:
        issues = "; ".join(
            f"{'.'.join(str(x) for x in e['loc']) or '<root>'}: {e['msg']}" for e in err.errors()
        )
        raise LaunchConfigError(f"invalid launch.yaml: {issues}") from err
