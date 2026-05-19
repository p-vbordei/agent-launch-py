"""Conformance tests C1-C5 from the agent-launch SPEC."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from agent_launch.config import (
    HnPlatform,
    LaunchConfigError,
    LinkedinPlatform,
    MastodonPlatform,
    Project,
    XPlatform,
    load_launch_config,
)
from agent_launch.context import GatheredContext
from agent_launch.draft import draft_one
from agent_launch.platforms import load_platform_template


def _project() -> Project:
    return Project(
        name="agent-id",
        oneliner="Machine-first identity for AI agents",
        audience="AI builders",
        hooks=["Self-custody DID", "Three functions"],
    )


def _ctx() -> GatheredContext:
    return GatheredContext(
        version="0.2.0",
        changelog="### Added\n- thing",
        readme="# x",
        commits=["abc"],
    )


def make_fake(texts: list[str]):
    state = {"i": 0}

    class _M:
        async def create(self, params: dict[str, Any]) -> dict[str, Any]:
            i = state["i"]
            state["i"] = i + 1
            text = texts[i] if i < len(texts) else texts[-1]
            return {"content": [{"type": "text", "text": text}]}

    class _Client:
        messages = _M()

    return _Client()


# --- C1 ---


@pytest.mark.asyncio
async def test_c1_determinism() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    text = "Show HN: agent-id\n\nhttps://github.com/p-vbordei/agent-id"
    a = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([text]),
    )
    b = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([text]),
    )
    assert a.body == b.body
    assert a.length == b.length
    assert a.capped == b.capped


# --- C2 ---


@pytest.mark.asyncio
async def test_c2_within_cap_first_try() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    tpl = load_platform_template("mastodon")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake(["short toot"]),
    )
    assert len(r.body) <= tpl.length_cap
    assert r.capped is True
    assert r.retries == 0


@pytest.mark.asyncio
async def test_c2_over_then_within() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake(["x" * 700, "short"]),
    )
    assert r.capped is True
    assert r.retries == 1


@pytest.mark.asyncio
async def test_c2_over_forever() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake(["x" * 700]),
    )
    assert r.capped is False
    assert r.retries == 2


@pytest.mark.asyncio
async def test_c2_x_per_tweet_cap() -> None:
    platform = XPlatform(kind="x", handle="v")
    ok = "\n---tweet---\n".join(
        ["tweet one", "tweet two has more", "https://github.com/p-vbordei/agent-id"]
    )
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([ok]),
    )
    assert r.capped is True
    assert r.tweet_count == 3


# --- C3 ---

REPO_URL = "https://github.com/p-vbordei/agent-id"


@pytest.mark.asyncio
async def test_c3_mastodon_repo_url() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([f"look {REPO_URL}"]),
    )
    assert REPO_URL in r.body


@pytest.mark.asyncio
async def test_c3_hn_repo_url() -> None:
    import json

    platform = HnPlatform(kind="hn", pattern="show-hn")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([json.dumps({"title": "Show HN", "body": REPO_URL})]),
    )
    assert REPO_URL in r.body


@pytest.mark.asyncio
async def test_c3_x_repo_url() -> None:
    platform = XPlatform(kind="x", handle="v")
    thread = f"hook\n---tweet---\nbody\n---tweet---\n{REPO_URL}"
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake([thread]),
    )
    assert REPO_URL in r.body


# --- C4 ---


@pytest.mark.asyncio
async def test_c4_no_secrets_in_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-FAKE_TEST_TOKEN")
    monkeypatch.setenv("GH_TOKEN", "ghp_FAKE_TEST_TOKEN")
    monkeypatch.setenv("NPM_TOKEN", "npm_FAKE_TEST_TOKEN")
    platform = LinkedinPlatform(kind="linkedin")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake(["a clean post about agent-id"]),
    )
    assert "sk-ant-" not in r.body
    assert "ghp_" not in r.body
    assert "npm_" not in r.body


@pytest.mark.asyncio
async def test_c4_only_declared_fields() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="h", handle="v")
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=make_fake(["short"]),
    )
    allowed = {"platform", "title", "body", "length", "length_cap", "capped", "retries", "tweet_count"}
    for k in r.to_dict():
        assert k in allowed


# --- C5 ---


def _write(yaml_str: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix="c5-"))
    p = d / "launch.yaml"
    p.write_text(yaml_str, encoding="utf-8")
    return p


def test_c5_rejects_missing_version() -> None:
    bad = (
        "project:\n  name: x\n  oneliner: y\n  audience: a\n  hooks: [\"a\"]\n"
        "platforms:\n  - kind: linkedin\ncontext:\n  repo: o/r\n"
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_c5_rejects_unknown_top_level_key() -> None:
    bad = (
        "version: 1\nproject:\n  name: x\n  oneliner: y\n  audience: a\n  hooks: [\"a\"]\n"
        "platforms:\n  - kind: linkedin\ncontext:\n  repo: o/r\nextra: y\n"
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_c5_rejects_unknown_platform_kind() -> None:
    bad = (
        "version: 1\nproject:\n  name: x\n  oneliner: y\n  audience: a\n  hooks: [\"a\"]\n"
        "platforms:\n  - kind: alien\ncontext:\n  repo: o/r\n"
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_c5_rejects_too_many_hooks() -> None:
    bad = (
        "version: 1\nproject:\n  name: x\n  oneliner: y\n  audience: a\n"
        "  hooks: [\"a\",\"b\",\"c\",\"d\",\"e\",\"f\"]\n"
        "platforms:\n  - kind: linkedin\ncontext:\n  repo: o/r\n"
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))


def test_c5_rejects_oneliner_too_long() -> None:
    long = "x" * 150
    bad = (
        f"version: 1\nproject:\n  name: x\n  oneliner: \"{long}\"\n  audience: a\n  hooks: [\"a\"]\n"
        "platforms:\n  - kind: linkedin\ncontext:\n  repo: o/r\n"
    )
    with pytest.raises(LaunchConfigError):
        load_launch_config(_write(bad))
