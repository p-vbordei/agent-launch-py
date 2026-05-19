"""Draft one platform-native release announcement via Claude."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from agent_launch.config import Platform, Project
from agent_launch.context import GatheredContext
from agent_launch.platforms import PlatformTemplate, load_platform_template

MAX_RETRIES = 2
MODEL = "claude-opus-4-7"


class _Messages(Protocol):
    async def create(self, params: dict[str, Any]) -> Any: ...


class AnthropicClient(Protocol):
    messages: _Messages


@dataclass(frozen=True)
class DraftResult:
    platform: str
    body: str
    length: int
    length_cap: int
    capped: bool
    retries: int
    title: str | None = None
    tweet_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "platform": self.platform,
            "body": self.body,
            "length": self.length,
            "length_cap": self.length_cap,
            "capped": self.capped,
            "retries": self.retries,
        }
        if self.title is not None:
            d["title"] = self.title
        if self.tweet_count is not None:
            d["tweet_count"] = self.tweet_count
        return d


@dataclass
class _Parsed:
    body: str
    title: str | None = None
    tweet_count: int | None = None


async def draft_one(
    *,
    platform: Platform,
    project: Project,
    context: GatheredContext,
    repo: str,
    anthropic: AnthropicClient,
) -> DraftResult:
    tpl = load_platform_template(platform.kind)
    system_prompt = f"{tpl.system}\n\n## Anti-examples\n{tpl.anti_examples}"
    user_prompt = _render_user_prompt(tpl.user_template, platform, project, context, repo)

    last: _Parsed | None = None
    retries = 0
    for attempt in range(MAX_RETRIES + 1):
        if attempt == 0:
            final_user = user_prompt
        else:
            cap_clause = (
                f"each tweet must be ≤ {tpl.length_cap} chars"
                if tpl.length_cap_field == "per_tweet"
                else f"the body must be ≤ {tpl.length_cap} chars"
            )
            title_clause = (
                f" Title ≤ {tpl.title_cap} chars." if tpl.title_cap is not None else ""
            )
            final_user = (
                f"{user_prompt}\n\nThe previous attempt exceeded the length limit. "
                f"Rewrite shorter; {cap_clause}.{title_clause}"
            )

        resp = await anthropic.messages.create({
            "model": MODEL,
            "max_tokens": 4096,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": final_user}],
        })
        text = _extract_text(resp).strip()
        parsed = _parse_output(tpl.output_format, text)
        last = parsed
        retries = attempt
        if _length_ok(parsed, tpl):
            return DraftResult(
                platform=platform.kind,
                body=parsed.body,
                length=len(parsed.body),
                length_cap=tpl.length_cap,
                capped=True,
                retries=retries,
                title=parsed.title,
                tweet_count=parsed.tweet_count,
            )

    assert last is not None
    return DraftResult(
        platform=platform.kind,
        body=last.body,
        length=len(last.body),
        length_cap=tpl.length_cap,
        capped=False,
        retries=retries,
        title=last.title,
        tweet_count=last.tweet_count,
    )


def _extract_text(resp: Any) -> str:
    # Accept either dict-shaped (test fakes) or attribute-shaped (real SDK) responses.
    if isinstance(resp, dict):
        content = resp.get("content", [])
    else:
        content = getattr(resp, "content", [])
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        else:
            if getattr(block, "type", None) == "text":
                parts.append(str(getattr(block, "text", "") or ""))
    return "".join(parts)


def _parse_output(fmt: str, text: str) -> _Parsed:
    if fmt == "json":
        try:
            obj = json.loads(text)
            return _Parsed(body=str(obj.get("body", "")), title=str(obj.get("title", "")))
        except (json.JSONDecodeError, AttributeError):
            return _Parsed(body=text)
    if fmt == "thread":
        tweets = [s.strip() for s in text.split("---tweet---") if s.strip()]
        return _Parsed(body="\n---tweet---\n".join(tweets), tweet_count=len(tweets))
    return _Parsed(body=text)


def _length_ok(parsed: _Parsed, tpl: PlatformTemplate) -> bool:
    if tpl.title_cap is not None and parsed.title is not None:
        if len(parsed.title) > tpl.title_cap:
            return False
    if tpl.length_cap_field == "per_tweet":
        tweets = [s.strip() for s in parsed.body.split("---tweet---")]
        return all(len(t) <= tpl.length_cap for t in tweets)
    return len(parsed.body) <= tpl.length_cap


def _render_user_prompt(
    template: str,
    platform: Platform,
    project: Project,
    context: GatheredContext,
    repo: str,
) -> str:
    flat: dict[str, str] = {
        "project.name": project.name,
        "project.oneliner": project.oneliner,
        "project.audience": project.audience,
        "project.hooks": "\n".join(f"- {h}" for h in project.hooks),
        "context.changelog": context.changelog,
        "context.readme": context.readme,
        "context.commits": "\n".join(context.commits),
        "context.repo": repo,
        "version": context.version,
    }
    if platform.kind == "reddit":
        flat["platform.subreddit"] = platform.subreddit  # type: ignore[attr-defined]
    out = template
    for k, v in flat.items():
        out = out.replace(f"{{{{{k}}}}}", v)
    return out
