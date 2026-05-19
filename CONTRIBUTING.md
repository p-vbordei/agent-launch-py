# Contributing

Thanks for your interest. This repo is a port of [`@p-vbordei/agent-launch`](https://github.com/p-vbordei/agent-launch); behaviour changes must land in the TS reference first so all ports can stay in sync.

## Setup

```bash
git clone https://github.com/p-vbordei/agent-launch-py
cd agent-launch-py
uv sync --extra dev
```

## Run the tests

```bash
uv run pytest -v
```

48 tests should pass in under 3 seconds. No network or API key needed.

## Lint

```bash
uv run ruff check .
uv run ruff format --check .
```

## Before opening a PR

- New behaviour must come with a test. Use the scripted-Anthropic-client pattern in `tests/test_draft.py` — no live API calls.
- Run `uv run pytest -v` and `uv run ruff check .` locally. CI runs both on Python 3.10–3.13.
- Keep the diff scoped to the change. Don't reformat unrelated files.
- If your change affects the public API, update `CHANGELOG.md` under `## [Unreleased]`.

## Scope of changes

- **Prompts** (`prompts/*.md`) are vendored verbatim from the TS reference. Prompt changes must land there first; this repo updates by re-copying.
- **Behaviour deltas vs. the TS reference** are not accepted unless they fix a clear bug or close a gap in the spec. Open an issue first.
- Pure-Python ergonomics (better error messages, type hints, docstrings, test cleanup) are welcome.

## License

By contributing, you agree your contributions are licensed under Apache-2.0 (see [LICENSE](./LICENSE)).
