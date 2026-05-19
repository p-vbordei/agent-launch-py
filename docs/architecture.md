# Architecture

## Goal

Port the TypeScript reference [`@p-vbordei/agent-launch`](https://github.com/p-vbordei/agent-launch) to idiomatic Python while keeping the runtime behaviour identical: same `launch.yaml` schema, same prompt templates, same length caps, same conformance clauses (C1–C5, S2/S4/S5).

"Identical" here means byte-identical generated drafts when given the same inputs and a `temperature=0` Anthropic client that returns the same text.

## Module map

| File | TS counterpart | Responsibility |
|---|---|---|
| `agent_launch/config.py` | `src/config.ts` | Strict `launch.yaml` schema (pydantic). |
| `agent_launch/context.py` | `src/context.ts` | Gather CHANGELOG section, README, recent `git log`, optional release manifest. |
| `agent_launch/platforms.py` | `src/platforms.ts` | Read one of the five vendored prompt templates from `prompts/<kind>.md`. |
| `agent_launch/draft.py` | `src/draft.ts` | Render the user template, call Anthropic, parse output, enforce length caps with up to 2 retries. |
| `agent_launch/cli.py` | `src/index.ts` | Typer CLI: `context` and `draft` subcommands. |
| `prompts/*.md` | `prompts/*.md` | Vendored verbatim from the TS reference. Hashed in `prompts/_HASHES.txt` (TS-side). |

## Dependency choices

- **Anthropic client = duck-typed `Protocol`, not a hard SDK dep.** `draft.py` defines a tiny `AnthropicClient` protocol with one async method (`messages.create(params: dict)`). Tests pass a fake; the CLI passes a thin adapter over `AsyncAnthropic`. This keeps unit tests offline (S4) and lets library callers bring their own transport.
- **Markdown parsing: none.** The prompt templates use a fixed `---\nfrontmatter\n---\n## System\n## User\n## Anti-examples` shape. We extract sections with a single regex (`re`) rather than pull in a full Markdown parser — matches the TS reference's manual extraction byte-for-byte.
- **YAML: `pyyaml` (safe_load only).** Same library as the launch.yaml spec; `safe_load` avoids constructor-tag injection.
- **Schema: `pydantic` v2 with `extra="forbid"` and `frozen=True`.** Matches the TS Zod schema's `.strict()` behaviour — extra fields are an error (C5).
- **CLI: `typer`.** Argument-parser of choice for typed Python CLIs; thin wrapper over `click`.

## Testing strategy

- **Scripted Anthropic clients.** Every `draft_one` test injects a `_FakeAnthropic` that returns canned text and records the `params` it received. No live API key; tests run in `<1s`.
- **Conformance vectors.** `tests/test_conformance.py` asserts the C1–C5 invariants directly against `draft_one` and the rendered CLI output. The prompt-template byte-identity is enforced by shipping the TS-reference prompt files verbatim (see `pyproject.toml` `force-include`).
- **Security tests.** `tests/test_security.py` covers S2 (no `tools` field passed to the Anthropic call), S4 (no sockets opened during a scripted-client run), and S5 (`--out` sandboxing rejects absolute paths outside cwd and `..` traversal).

## Non-goals (v0.1)

- Live posting. v0.1 writes markdown files only; the user posts them by hand. v0.2 will add post-on-approval for X/Mastodon/LinkedIn.
- Reply monitoring. v0.3.
- Multi-language translation, OG-image generation, analytics. Out of scope entirely.
