"""agent-launch CLI."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import typer

from agent_launch.config import LaunchConfigError, Platform, load_launch_config
from agent_launch.context import ContextError, gather_context
from agent_launch.draft import DraftResult, draft_one

app = typer.Typer(
    name="agent-launch",
    help="Draft platform-native release announcements from CHANGELOG + README.",
    add_completion=False,
    no_args_is_help=True,
)


def _load_config_or_exit(cwd: Path) -> tuple:
    path = cwd / "launch.yaml"
    try:
        cfg = load_launch_config(path)
    except FileNotFoundError as err:
        typer.echo(f"launch.yaml not found at {path}", err=True)
        raise typer.Exit(1) from err
    except LaunchConfigError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from err
    return cfg, path


def _filename_for(platform: Platform, out_dir: Path) -> Path:
    if platform.kind == "reddit":
        return out_dir / f"reddit-{platform.subreddit}.md"  # type: ignore[attr-defined]
    return out_dir / f"{platform.kind}.md"


def _render_draft_file(result: DraftResult) -> str:
    fm: dict[str, object] = {
        "platform": result.platform,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "length_chars": result.length,
        "length_cap": result.length_cap,
        "capped": result.capped,
    }
    if result.title is not None:
        fm["title"] = result.title
    if result.tweet_count is not None:
        fm["tweet_count"] = result.tweet_count
    lines = []
    for k, v in fm.items():
        if isinstance(v, str):
            lines.append(f"{k}: {json.dumps(v)}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    fm_yaml = "\n".join(lines)
    return f"---\n{fm_yaml}\n---\n\n{result.body}\n"


@app.command()
def context(
    version: str = typer.Argument(..., help="Version that has a CHANGELOG section."),
) -> None:
    """Print the gathered repo context as JSON (debug launch.yaml)."""
    cwd = Path.cwd()
    cfg, _ = _load_config_or_exit(cwd)
    manifest_path = (cwd / cfg.context.manifest).resolve() if cfg.context.manifest else None
    try:
        ctx = gather_context(cwd, version, manifest_path=manifest_path)
    except ContextError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from err
    typer.echo(json.dumps(ctx.to_dict(), indent=2))


@app.command()
def draft(
    version: str = typer.Argument(..., help="Version with a CHANGELOG section."),
    platforms: str | None = typer.Option(
        None,
        "--platforms",
        help="Comma-separated platform kinds to render (default: all configured).",
    ),
    out: str | None = typer.Option(None, "--out", help="Output dir (default: launches/v<version>)."),
) -> None:
    """Draft platform-native release announcements."""
    cwd = Path.cwd()
    cfg, _ = _load_config_or_exit(cwd)

    out_arg = out if out is not None else f"launches/v{version}"
    out_abs = (cwd / out_arg).resolve()
    # S5: --out must resolve under cwd, no .. traversal, no absolute outside cwd.
    try:
        out_abs.relative_to(cwd)
    except ValueError as err:
        typer.echo(f"--out must resolve to a path inside {cwd}", err=True)
        raise typer.Exit(1) from err

    manifest_path = (cwd / cfg.context.manifest).resolve() if cfg.context.manifest else None
    try:
        ctx = gather_context(cwd, version, manifest_path=manifest_path)
    except ContextError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(2) from err

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        typer.echo("ANTHROPIC_API_KEY not set", err=True)
        raise typer.Exit(3)

    # Lazy import: anthropic is heavy and the SDK shape only matters for real calls.
    from anthropic import AsyncAnthropic  # type: ignore[import-not-found]

    client = AsyncAnthropic(api_key=api_key)

    # Adapter so our draft_one's small Protocol fits the SDK's kwargs API.
    class _Adapter:
        class messages:  # noqa: N801
            @staticmethod
            async def create(params: dict) -> object:
                return await client.messages.create(**params)

    filter_kinds = (
        {s.strip() for s in platforms.split(",")} if platforms else None
    )
    targets = [
        p for p in cfg.platforms if filter_kinds is None or p.kind in filter_kinds
    ]
    if not targets:
        typer.echo("no platforms match the --platforms filter", err=True)
        raise typer.Exit(1)

    out_abs.mkdir(parents=True, exist_ok=True)
    summary: list[tuple[str, Path, bool]] = []

    async def run() -> None:
        for platform in targets:
            result = await draft_one(
                platform=platform,
                project=cfg.project,
                context=ctx,
                repo=cfg.context.repo,
                anthropic=_Adapter(),  # type: ignore[arg-type]
            )
            file_path = _filename_for(platform, out_abs)
            file_path.write_text(_render_draft_file(result), encoding="utf-8")
            summary.append((platform.kind, file_path, result.capped))

    asyncio.run(run())
    typer.echo(f"Drafted {len(summary)} posts for v{version} in {out_abs}")
    for kind, file_path, capped in summary:
        suffix = "" if capped else "  (over length cap)"
        typer.echo(f"  - {kind}: {file_path}{suffix}")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
