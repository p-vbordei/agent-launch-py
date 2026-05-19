# Changelog

All notable changes to `agent-launch` (Python) are documented in this file. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-19

### Added

- Initial Python port of [`@p-vbordei/agent-launch`](https://github.com/p-vbordei/agent-launch).
- 5 platform drafters: `hn`, `reddit`, `x`, `mastodon`, `linkedin`. Same prompts as the TS reference (vendored verbatim from `prompts/`).
- CLI: `agent-launch context <version>` and `agent-launch draft <version> [--platforms <list>] [--out <dir>]` (typer-based).
- Library API: `draft_one`, `gather_context`, `load_launch_config`, plus the platform dataclasses (`HnPlatform`, `RedditPlatform`, `XPlatform`, `MastodonPlatform`, `LinkedinPlatform`).
- Byte-identical prompt templates with the TS reference. Prompts are shipped inside the wheel via `hatch` `force-include`.
- Scripted-Anthropic-client test pattern: every `draft_one` test injects a fake client, no network, no API key.
- Strict `launch.yaml` schema (pydantic v2, `extra="forbid"`, frozen).
- Length-cap retry (up to 2 regenerations); over-cap drafts still written with `capped: false` in frontmatter.
- Output sandboxing: `--out` rejects absolute paths outside cwd and `..` traversal.
- Conformance vectors C1–C5 (determinism, length caps, repo URL present, no secrets, strict YAML) all pass.
- Security tests S2 (no `tools` field in the Anthropic call), S4 (no sockets opened during scripted-client run), S5 (output sandbox).
- 48 tests across unit, integration, conformance, security suites.
- GitHub Actions CI on Python 3.10, 3.11, 3.12, 3.13.
