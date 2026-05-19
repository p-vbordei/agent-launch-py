"""Offline quickstart: draft a Show HN post with a scripted Anthropic client.

Run: `python examples/quickstart.py` from the repo root.
No network, no API key. The Anthropic client is a fake that returns a
hardcoded JSON string — same shape the real SDK returns.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agent_launch import (
    GatheredContext,
    HnPlatform,
    Project,
    draft_one,
)


class ScriptedAnthropic:
    """Fake Anthropic client: returns a canned `messages.create` response."""

    def __init__(self, text: str) -> None:
        outer = self

        class _Messages:
            async def create(self, params: dict[str, Any]) -> dict[str, Any]:
                outer.last_params = params
                return {"content": [{"type": "text", "text": text}]}

        self.messages = _Messages()
        self.last_params: dict[str, Any] | None = None


async def main() -> None:
    scripted_reply = json.dumps({
        "title": "Show HN: agent-launch — draft platform-native release posts",
        "body": (
            "agent-launch turns your CHANGELOG + README into platform-tuned "
            "release announcements for HN, Reddit, X, Mastodon, and LinkedIn. "
            "v0.1 drafts only — you post. "
            "https://github.com/p-vbordei/agent-launch-py"
        ),
    })

    result = await draft_one(
        platform=HnPlatform(kind="hn", pattern="show-hn"),
        project=Project(
            name="agent-launch",
            oneliner="Draft platform-native release announcements from CHANGELOG + README",
            audience="OSS maintainers shipping releases",
            hooks=["5 platforms", "Strict YAML", "Anti-slop prompts"],
        ),
        context=GatheredContext(
            version="0.1.0",
            changelog="### Added\n- Initial Python port.",
            readme="# agent-launch\n\nDraft release posts.",
            commits=["abc123 feat: initial port"],
        ),
        repo="p-vbordei/agent-launch-py",
        anthropic=ScriptedAnthropic(scripted_reply),
    )

    print(f"platform : {result.platform}")
    print(f"title    : {result.title}")
    print(f"length   : {result.length} / cap {result.length_cap}")
    print(f"capped   : {result.capped}")
    print(f"retries  : {result.retries}")
    print("---")
    print(result.body)


if __name__ == "__main__":
    asyncio.run(main())
