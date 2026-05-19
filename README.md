# agent-launch (Python)

[![CI](https://github.com/p-vbordei/agent-launch-py/actions/workflows/ci.yml/badge.svg)](https://github.com/p-vbordei/agent-launch-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-launch.svg)](https://pypi.org/project/agent-launch/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)

> Draft platform-native release announcements (HN, Reddit, X, Mastodon, LinkedIn) from your repo's CHANGELOG + README + recent commits. **v0.1: drafts only — you post.**

Python port of [@p-vbordei/agent-launch](https://github.com/p-vbordei/agent-launch). Behaviour-compatible: same `launch.yaml` schema, same prompt templates, same per-platform length caps, same conformance clauses (C1–C5, S2/S4/S5).

## Install

```bash
pip install agent-launch
# or
uv add agent-launch
```

## Use

```bash
cp launch.yaml.example launch.yaml && $EDITOR launch.yaml
agent-launch context 0.2.0                        # debug: print the gathered context
ANTHROPIC_API_KEY=... agent-launch draft 0.2.0    # → launches/v0.2.0/{hn,reddit-*,x,mastodon,linkedin}.md
agent-launch draft 0.2.0 --platforms hn,x         # only specific platforms
agent-launch draft 0.2.0 --out drafts/            # custom output dir (must be inside cwd)
```

Each draft is platform-native: HN's "Show HN" pattern, Reddit's subreddit etiquette, X's threaded format, Mastodon's longer-form toot, LinkedIn's slightly-more-business voice. Anti-examples (`revolutionary`, `game-changing`, the em-dash AI-cliche pattern, etc.) are baked into every prompt.

## Why drafts only in v0.1

- HN explicitly forbids automated submissions.
- Reddit's API allows posting but rate limits + subreddit moderation make automation fragile.
- The hard part is "well-written platform-native copy informed by the actual repo." That's what v0.1 ships.
- Posting on user approval is v0.2. Reply monitoring is v0.3.

## Programmatic API

```python
import asyncio
from anthropic import AsyncAnthropic

from agent_launch import (
    gather_context, load_launch_config, draft_one,
)

async def main() -> None:
    cfg = load_launch_config("launch.yaml")
    ctx = gather_context(".", "0.2.0")
    client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY

    class Adapter:
        class messages:
            @staticmethod
            async def create(params): return await client.messages.create(**params)

    for platform in cfg.platforms:
        result = await draft_one(
            platform=platform,
            project=cfg.project,
            context=ctx,
            repo=cfg.context.repo,
            anthropic=Adapter(),
        )
        print(platform.kind, result.length, result.capped)

asyncio.run(main())
```

## Conformance

The TypeScript reference defines five conformance clauses (see [SPEC.md](./SPEC.md) §6). All pass here:

- **C1 — Determinism.** Same inputs → same output (with `temperature=0` and a scripted client, byte-identical).
- **C2 — Length caps.** Per-platform caps enforced with up to 2 retries; over-cap drafts are still written but marked `capped: false`.
- **C3 — Repo URL.** Every draft body contains the GitHub URL.
- **C4 — No secrets / declared fields only.** Env-var values are never echoed; `DraftResult` exposes only declared fields.
- **C5 — Strict `launch.yaml`.** Missing/extra/invalid fields fail fast with a clear error.

Plus security clauses **S2** (no `tools` field in the Anthropic call — model has no shell access), **S4** (no sockets opened during drafting), **S5** (`--out` sandboxed under cwd).

## License

[Apache 2.0](./LICENSE)
