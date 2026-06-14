"""Command-line interface (Typer).

The CLI is a thin shell over :class:`AnalysisService`: it parses options, builds
configuration, runs the analysis and writes a tidy per-epic report bundle. All
real work lives in the service/domain layers so the same logic can back a web
API later.
"""

from __future__ import annotations

import logging
import sys
import webbrowser
from enum import StrEnum
from pathlib import Path

import typer

from ai_engineering_metrics import __version__
from ai_engineering_metrics.config import GitHubConfig, Settings
from ai_engineering_metrics.integrations.base import IntegrationError, NotFoundError
from ai_engineering_metrics.output import (
    DASHBOARD_FILE,
    METRICS_FILE,
    PRS_FILE,
    STORIES_FILE,
    write_bundle,
)
from ai_engineering_metrics.reports.html_report import write_html
from ai_engineering_metrics.service import AnalysisService
from ai_engineering_metrics.setup_wizard import run_wizard
from ai_engineering_metrics.storage.json_storage import report_to_json, save_report

# Make output robust on consoles with a non-UTF-8 default encoding (e.g. the
# Windows cp1252 console) so JSON/text never crashes on a stray character.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

MOCK_EPIC = "DEMO-1"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    help=(
        "[bold]AI Engineering Metrics[/bold] - measure the impact of AI on "
        "engineering delivery.\n\n"
        "Turn a JIRA epic (+ its GitHub PRs and AI token usage) into a local "
        "dashboard, JSON and CSVs.\n\n"
        "[bold]Try it in 30 seconds (no setup):[/bold]\n"
        "  ai-engineering-metrics analyze --mock"
    ),
    epilog="Docs: https://engmetrics.ai",
)


class ArtifactFormat(StrEnum):
    all = "all"
    html = "html"
    json = "json"
    csv = "csv"


def _formats(fmt: ArtifactFormat) -> tuple[str, ...]:
    return ("html", "json", "csv") if fmt is ArtifactFormat.all else (fmt.value,)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ai-engineering-metrics {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """AI Engineering Metrics CLI."""


def _validate_epic(epic: str) -> None:
    # JIRA keys look like PROJ-123. Be lenient but catch obvious mistakes early.
    if "-" not in epic or not any(c.isdigit() for c in epic):
        typer.secho(
            f"'{epic}' doesn't look like a JIRA epic key (expected e.g. PROJ-123).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)


def _print_summary(report, written: dict[str, Path], *, mock: bool) -> Path | None:
    epic = report.epic
    p = report.productivity
    a = report.ai_usage
    green, dim = typer.colors.GREEN, typer.colors.BRIGHT_BLACK

    typer.secho(f"\nAnalysis complete: {epic.key}", fg=green, bold=True)
    if mock:
        typer.secho("  (demo mode - synthetic data, no JIRA/GitHub calls)", fg=dim)
    typer.echo(
        f"  {epic.summary}  |  {len(report.stories)} stories  |  "
        f"{len(report.all_pull_requests)} PRs"
    )
    typer.echo(
        f"  Hours saved: {p.hours_saved:g}h ({p.savings_percent:g}%)   "
        f"AI tokens: {a.total_tokens:,} (~${a.estimated_cost:,.2f})   "
        f"Risk: {report.risk.score:g}/100 ({report.risk.level})"
    )

    if written:
        typer.secho("\n  Report bundle:", bold=True)
        for name in (DASHBOARD_FILE, METRICS_FILE, STORIES_FILE, PRS_FILE):
            path = written.get(name)
            if path:
                hint = "   (open this in a browser)" if name == DASHBOARD_FILE else ""
                typer.echo(f"    - {path}{hint}")
    return written.get(DASHBOARD_FILE)


@app.command()
def analyze(
    epic: str | None = typer.Option(
        None,
        "--epic",
        "-e",
        help="JIRA epic key (e.g. PROJ-123). Optional with --mock (defaults to DEMO-1).",
    ),
    output: Path = typer.Option(
        Path("reports"),
        "--output",
        "-o",
        help="Output directory; a folder named after the epic is created inside it. "
        "(A path ending in .html/.json writes that single file instead.)",
    ),
    fmt: ArtifactFormat = typer.Option(
        ArtifactFormat.all,
        "--format",
        "-f",
        help="Which artifacts to write: all, html, json or csv.",
    ),
    mock: bool = typer.Option(
        False, "--mock", help="Use realistic demo data — no JIRA/GitHub or credentials needed."
    ),
    repo: str | None = typer.Option(
        None,
        "--repo",
        "-r",
        help="GitHub 'owner/name' for PR discovery. Overrides .env and auto-detection.",
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="Open the generated dashboard in your browser when done."
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Print metrics JSON to stdout (for piping) instead of writing files.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """Analyze a JIRA epic and write a dashboard + metrics bundle.

    [bold]Examples[/bold]

      [green]ai-engineering-metrics analyze --mock[/green]              run the demo
      [green]ai-engineering-metrics analyze -e PROJ-123[/green]         a real epic
      [green]ai-engineering-metrics analyze -e PROJ-123 --open[/green]  and open it

    Produces (by default) [cyan]reports/<EPIC>/[/cyan] with dashboard.html,
    metrics.json, stories.csv and pull_requests.csv.
    """
    _configure_logging(verbose)

    # In demo mode an epic key is optional and defaults to DEMO-1.
    if epic is None:
        if mock:
            epic = MOCK_EPIC
        else:
            typer.secho("Missing --epic.", fg=typer.colors.RED, err=True)
            typer.secho(
                "  Provide an epic:  ai-engineering-metrics analyze --epic PROJ-123\n"
                "  Or try the demo:  ai-engineering-metrics analyze --mock",
                err=True,
            )
            raise typer.Exit(code=2)
    _validate_epic(epic)

    settings = Settings.from_env()
    if not mock and not settings.jira.is_configured:
        run_wizard()
        settings = Settings.from_env(load_dotenv_file=False)
    if repo:
        if "/" not in repo:
            typer.secho("--repo must be in 'owner/name' format.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2)
        owner, name = repo.split("/", 1)
        settings.github = GitHubConfig(org=owner, repositories=[name], search_all_repos=False)

    service: AnalysisService | None = None
    try:
        service = AnalysisService.for_settings(settings, mock=mock)
        report = service.analyze(epic)
    except NotFoundError as exc:
        typer.secho(f"Error - not found: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except IntegrationError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        typer.secho(
            "  Tip: run 'ai-engineering-metrics configure' to set up credentials, "
            "or use --mock for a demo.",
            err=True,
        )
        raise typer.Exit(code=1) from exc
    finally:
        if service is not None:
            service.close()

    # Piping mode: emit JSON to stdout and stop.
    if stdout:
        typer.echo(report_to_json(report))
        return

    # Backward compatibility: an explicit .html/.json path writes that one file.
    suffix = output.suffix.lower()
    if suffix == ".html":
        path = write_html(report, output)
        typer.secho(f"Dashboard written to {path}", fg=typer.colors.GREEN)
        if open_browser:
            webbrowser.open(path.resolve().as_uri())
        return
    if suffix == ".json":
        path = save_report(report, output)
        typer.secho(f"JSON written to {path}", fg=typer.colors.GREEN)
        return

    # Default: a tidy per-epic bundle directory.
    written = write_bundle(report, output, formats=_formats(fmt))
    dashboard = _print_summary(report, written, mock=mock)
    if open_browser and dashboard is not None:
        webbrowser.open(dashboard.resolve().as_uri())


@app.command()
def configure() -> None:
    """Set up or update JIRA credentials with an interactive wizard.

    [bold]Examples[/bold]

      [green]ai-engineering-metrics configure[/green]   first-time setup or update credentials

    Saves to [cyan]~/.config/ai-engineering-metrics/config.yaml[/cyan] (Linux/macOS)
    or [cyan]%APPDATA%/ai-engineering-metrics/config.yaml[/cyan] (Windows).
    Configuration is shared across all repositories and projects.
    """
    run_wizard()


if __name__ == "__main__":
    app()
