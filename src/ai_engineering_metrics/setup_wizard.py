"""Interactive first-run setup wizard.

Creates the user-scoped config file so no per-project .env is required:
  Linux/macOS: ~/.config/ai-engineering-metrics/config.yaml
  Windows:     %APPDATA%/ai-engineering-metrics/config.yaml
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import typer


def get_config_dir() -> Path:
    """Return the platform-appropriate user config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ai-engineering-metrics"


def get_config_path() -> Path:
    return get_config_dir() / "config.yaml"


def config_exists() -> bool:
    return get_config_path().exists()


def load_user_config() -> None:
    """Load user-scoped YAML config into os.environ, skipping keys already set.

    Called early in Settings.from_env() so env vars and .env always take priority.
    """
    path = get_config_path()
    if not path.exists():
        return
    try:
        import yaml

        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except Exception:
        return

    _map_yaml_to_env(data)


def _map_yaml_to_env(data: dict[str, Any]) -> None:
    """Populate env vars from a YAML config dict without overriding existing values."""

    def _set(key: str, value: Any) -> None:
        if key not in os.environ and value is not None:
            os.environ[key] = str(value)

    jira: dict = data.get("jira") or {}
    _set("JIRA_BASE_URL", jira.get("baseUrl"))
    _set("JIRA_EMAIL", jira.get("email"))
    _set("JIRA_API_TOKEN", jira.get("apiToken"))
    _set("JIRA_EPIC_LINK_FIELD", jira.get("epicLinkField"))
    _set("JIRA_AI_TOKENS_FIELD", jira.get("aiTokensField"))
    _set("JIRA_ESTIMATE_WITHOUT_AI_FIELD", jira.get("estimateWithoutAiField"))
    _set("JIRA_ESTIMATE_WITH_AI_FIELD", jira.get("estimateWithAiField"))
    _set("JIRA_STORY_POINTS_FIELD", jira.get("storyPointsField"))

    github: dict = data.get("github") or {}
    if "searchAllRepos" in github:
        _set("GITHUB_SEARCH_ALL_REPOS", str(github["searchAllRepos"]).lower())

    pricing: dict = data.get("pricing") or {}
    _set("AI_TOKEN_PRICE_INPUT_PER_1M", pricing.get("inputPer1M"))
    _set("AI_TOKEN_PRICE_OUTPUT_PER_1M", pricing.get("outputPer1M"))
    _set("DEFAULT_TOKEN_PRICE_PER_1M", pricing.get("defaultPer1M"))

    estimation: dict = data.get("estimation") or {}
    _set("STORY_POINT_HOURS", estimation.get("storyPointHours"))
    _set("AI_SAVINGS_PERCENT", estimation.get("aiSavingsPercent"))


def _is_interactive() -> bool:
    """Return True when stdin is a real terminal (not CI/pipe). Extracted for testability."""
    return sys.stdin.isatty()


def run_wizard() -> None:
    """Prompt for credentials interactively and write config.yaml.

    Safe to call on re-configure — overwrites the existing file.
    Exits with an error message if stdin is not a TTY (CI/pipe environment).
    """
    if not _is_interactive():
        typer.secho(
            "Error: JIRA credentials are not configured and no interactive terminal is available.\n"
            "  Run 'ai-engineering-metrics configure' in a terminal to set them up,\n"
            "  or set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN as environment variables.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    config_path = get_config_path()
    if config_path.exists():
        typer.secho(f"Updating configuration at {config_path}\n", bold=True)
    else:
        typer.secho("\nNo configuration found.\n", bold=True)
        typer.echo("Let's configure ai-engineering-metrics.\n")

    base_url = typer.prompt("JIRA Base URL (e.g. https://company.atlassian.net)").rstrip("/")
    email = typer.prompt("JIRA Email")
    api_token = typer.prompt("JIRA API Token", hide_input=True)

    typer.echo("\nCustom field IDs (press Enter to keep defaults):\n")
    epic_link = typer.prompt("JIRA Epic Link Field", default="customfield_10014")
    ai_tokens = typer.prompt("JIRA AI Tokens Field", default="customfield_10100")
    est_without = typer.prompt("JIRA Estimate Without AI Field", default="customfield_10101")
    est_with = typer.prompt("JIRA Estimate With AI Field", default="customfield_10102")
    story_pts = typer.prompt("JIRA Story Points Field", default="customfield_10016")

    config: dict[str, Any] = {
        "jira": {
            "baseUrl": base_url,
            "email": email,
            "apiToken": api_token,
            "epicLinkField": epic_link,
            "aiTokensField": ai_tokens,
            "estimateWithoutAiField": est_without,
            "estimateWithAiField": est_with,
            "storyPointsField": story_pts,
        },
        "github": {"searchAllRepos": True},
        "pricing": {"inputPer1M": 3.0, "outputPer1M": 15.0, "defaultPer1M": 6.0},
        "estimation": {"storyPointHours": 1.0, "aiSavingsPercent": 40},
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)

    import yaml

    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    typer.secho(f"\nConfiguration saved to:\n  {config_path}\n", fg=typer.colors.GREEN, bold=True)
    _map_yaml_to_env(config)
