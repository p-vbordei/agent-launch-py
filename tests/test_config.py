from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent_launch.config import LaunchConfigError, load_launch_config

VALID = """version: 1
project:
  name: agent-id
  oneliner: "Machine-first identity for AI agents"
  audience: "AI infra builders"
  hooks:
    - "Self-custody DID + Capability VC"
    - "Three functions, five deps, zero blockchain"
platforms:
  - kind: hn
    pattern: show-hn
  - kind: reddit
    subreddit: programming
  - kind: reddit
    subreddit: typescript
  - kind: x
    handle: vbordei
  - kind: mastodon
    instance: hachyderm.io
    handle: vbordei
  - kind: linkedin
context:
  repo: p-vbordei/agent-id
"""


def _write(yaml_str: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix="al-cfg-"))
    p = d / "launch.yaml"
    p.write_text(yaml_str, encoding="utf-8")
    return p


def test_parses_a_valid_config() -> None:
    cfg = load_launch_config(_write(VALID))
    assert cfg.version == 1
    assert cfg.project.name == "agent-id"
    assert len(cfg.project.hooks) == 2
    assert len(cfg.platforms) == 6
    assert cfg.context.repo == "p-vbordei/agent-id"


def test_allows_multiple_reddit_platforms() -> None:
    cfg = load_launch_config(_write(VALID))
    reddits = [p for p in cfg.platforms if p.kind == "reddit"]
    assert len(reddits) == 2


def test_rejects_invalid_platform_kind() -> None:
    bad = VALID.replace("  - kind: hn\n    pattern: show-hn\n", "  - kind: alien\n")
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_rejects_invalid_hn_pattern() -> None:
    bad = VALID.replace("pattern: show-hn", "pattern: spam")
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_rejects_invalid_subreddit() -> None:
    bad = VALID.replace("subreddit: programming", "subreddit: r/has-slash")
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_rejects_extra_top_level_key() -> None:
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(VALID + "extra: y\n"))


def test_rejects_empty_hooks() -> None:
    bad = VALID.replace(
        '  hooks:\n    - "Self-custody DID + Capability VC"\n    - "Three functions, five deps, zero blockchain"\n',
        "  hooks: []\n",
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_rejects_more_than_5_hooks() -> None:
    six = "  hooks:\n" + "".join(f'    - "{c}"\n' for c in "abcdef")
    bad = VALID.replace(
        '  hooks:\n    - "Self-custody DID + Capability VC"\n    - "Three functions, five deps, zero blockchain"\n',
        six,
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_rejects_malformed_repo() -> None:
    bad = VALID.replace("repo: p-vbordei/agent-id", "repo: norepo")
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_manifest_optional() -> None:
    cfg = load_launch_config(_write(VALID))
    assert cfg.context.manifest is None
    cfg2 = load_launch_config(_write(VALID + "  manifest: ./release-manifest.json\n"))
    assert cfg2.context.manifest == "./release-manifest.json"
