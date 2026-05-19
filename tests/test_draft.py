from __future__ import annotations

import json
from typing import Any

import pytest

from agent_launch.config import HnPlatform, MastodonPlatform, Project, XPlatform
from agent_launch.context import GatheredContext
from agent_launch.draft import draft_one

pytestmark = pytest.mark.asyncio


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
        changelog="### Added\n- batch verify",
        readme="# agent-id\n\nDID for agents.",
        commits=["abc123 feat: batch verify"],
    )


class _FakeAnthropic:
    """Records params; returns scripted text per call."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self._i = 0
        self.last_params: dict[str, Any] | None = None

    class messages:  # noqa: N801
        pass

    def __post_init__(self) -> None:  # pragma: no cover - never called, just for shape
        pass


def make_fake(texts: list[str]) -> _FakeAnthropic:
    fa = _FakeAnthropic(texts)

    class _M:
        async def create(self, params: dict[str, Any]) -> dict[str, Any]:
            fa.last_params = params
            i = fa._i
            fa._i += 1
            text = fa._texts[i] if i < len(fa._texts) else fa._texts[-1]
            return {"content": [{"type": "text", "text": text}]}

    fa.messages = _M()  # type: ignore[assignment]
    return fa


async def test_hn_parses_json() -> None:
    platform = HnPlatform(kind="hn", pattern="show-hn")
    fake = make_fake(
        [
            json.dumps(
                {
                    "title": "Show HN: agent-id - DID for agents",
                    "body": "A short body. https://github.com/p-vbordei/agent-id",
                }
            )
        ]
    )
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert r.title == "Show HN: agent-id - DID for agents"
    assert "https://github.com/p-vbordei/agent-id" in r.body
    assert r.capped is True


async def test_x_parses_thread() -> None:
    platform = XPlatform(kind="x", handle="vbordei")
    fake = make_fake(
        [
            "Tweet 1 hook.\n---tweet---\nTweet 2 explains.\n"
            "---tweet---\nhttps://github.com/p-vbordei/agent-id"
        ]
    )
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert "---tweet---" in r.body
    assert r.tweet_count == 3


async def test_mastodon_returns_text() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="hachyderm.io", handle="vbordei")
    fake = make_fake(["Short toot. https://github.com/p-vbordei/agent-id"])
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert "https://github.com/p-vbordei/agent-id" in r.body
    assert r.title is None


async def test_regenerates_when_over_cap() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="hachyderm.io", handle="vbordei")
    long_body = "a" * 700
    short = "short. https://github.com/p-vbordei/agent-id"
    fake = make_fake([long_body, short])
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert r.capped is True
    assert r.body == short
    assert r.retries == 1


async def test_returns_over_length_after_retries() -> None:
    platform = MastodonPlatform(kind="mastodon", instance="hachyderm.io", handle="vbordei")
    long_body = "a" * 700
    fake = make_fake([long_body, long_body, long_body])
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert r.capped is False
    assert r.retries == 2


async def test_hn_enforces_title_cap() -> None:
    platform = HnPlatform(kind="hn", pattern="show-hn")
    long_title = "Show HN: " + "x" * 200
    good = json.dumps(
        {"title": "Show HN: agent-id - DID", "body": "short. https://github.com/p-vbordei/agent-id"}
    )
    fake = make_fake([json.dumps({"title": long_title, "body": "short body"}), good])
    r = await draft_one(
        platform=platform,
        project=_project(),
        context=_ctx(),
        repo="p-vbordei/agent-id",
        anthropic=fake,  # type: ignore[arg-type]
    )
    assert r.capped is True
    assert len(r.title or "") <= 80
