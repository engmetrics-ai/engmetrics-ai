"""Tests for setup_wizard (unit) and CLI configure/analyze wizard integration (e2e)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from typer.testing import CliRunner

from ai_engineering_metrics.cli import app
from ai_engineering_metrics.setup_wizard import _map_yaml_to_env, get_config_path, load_user_config

runner = CliRunner()

# Simulates a user filling in the wizard with all-default custom fields.
# The trailing "\n" is required so the last prompt (Story Points) receives an
# empty line rather than EOF, which Click would interpret as Abort.
_WIZARD_INPUT = (
    "\n".join(
        [
            "https://company.atlassian.net",
            "dev@company.com",
            "mytoken",
            "",  # JIRA Epic Link Field  → default
            "",  # JIRA AI Tokens Field  → default
            "",  # Estimate Without AI   → default
            "",  # Estimate With AI      → default
            "",  # Story Points Field    → default
        ]
    )
    + "\n"
)


# ── config path ───────────────────────────────────────────────────────────────


def test_config_path_has_correct_filename():
    assert get_config_path().name == "config.yaml"


def test_config_path_contains_package_name():
    assert "ai-engineering-metrics" in str(get_config_path())


def test_config_path_windows_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    monkeypatch.setattr(sys, "platform", "win32")
    import ai_engineering_metrics.setup_wizard as sw

    path = sw.get_config_dir()
    assert str(path).startswith(r"C:\Users\test\AppData\Roaming")


@pytest.mark.skipif(sys.platform == "win32", reason="XDG_CONFIG_HOME is a POSIX concept")
def test_config_path_linux_uses_xdg(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    import ai_engineering_metrics.setup_wizard as sw

    path = sw.get_config_dir()
    assert str(path).startswith("/custom/config")


# ── load_user_config ──────────────────────────────────────────────────────────


def test_load_user_config_noop_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ai_engineering_metrics.setup_wizard.get_config_path",
        lambda: tmp_path / "nonexistent.yaml",
    )
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    load_user_config()
    assert "JIRA_BASE_URL" not in os.environ


def test_load_user_config_sets_env_from_yaml(tmp_path, monkeypatch):
    cfg = {
        "jira": {
            "baseUrl": "https://test.atlassian.net",
            "email": "a@b.com",
            "apiToken": "tok",
        }
    }
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

    load_user_config()

    assert os.environ["JIRA_BASE_URL"] == "https://test.atlassian.net"
    assert os.environ["JIRA_EMAIL"] == "a@b.com"
    assert os.environ["JIRA_API_TOKEN"] == "tok"


def test_load_user_config_does_not_override_existing_env(tmp_path, monkeypatch):
    cfg = {
        "jira": {"baseUrl": "https://from-yaml.atlassian.net", "email": "y@b.com", "apiToken": "y"}
    }
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setenv("JIRA_BASE_URL", "https://from-env.atlassian.net")

    load_user_config()

    assert os.environ["JIRA_BASE_URL"] == "https://from-env.atlassian.net"


def test_load_user_config_tolerates_corrupt_yaml(tmp_path, monkeypatch):
    f = tmp_path / "config.yaml"
    f.write_text(":: invalid: yaml: [", encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    load_user_config()  # must not raise
    assert "JIRA_BASE_URL" not in os.environ


# ── _map_yaml_to_env ──────────────────────────────────────────────────────────


def test_map_yaml_to_env_full_config(monkeypatch):
    for key in (
        "JIRA_BASE_URL",
        "JIRA_EPIC_LINK_FIELD",
        "GITHUB_SEARCH_ALL_REPOS",
        "AI_TOKEN_PRICE_INPUT_PER_1M",
        "STORY_POINT_HOURS",
    ):
        monkeypatch.delenv(key, raising=False)

    _map_yaml_to_env(
        {
            "jira": {
                "baseUrl": "https://co.atlassian.net",
                "email": "e@co.com",
                "apiToken": "t",
                "epicLinkField": "customfield_10014",
                "aiTokensField": "customfield_10100",
                "estimateWithoutAiField": "customfield_10101",
                "estimateWithAiField": "customfield_10102",
                "storyPointsField": "customfield_10016",
            },
            "github": {"searchAllRepos": False},
            "pricing": {"inputPer1M": 5.0, "outputPer1M": 20.0, "defaultPer1M": 10.0},
            "estimation": {"storyPointHours": 2.0, "aiSavingsPercent": 50},
        }
    )

    assert os.environ["JIRA_BASE_URL"] == "https://co.atlassian.net"
    assert os.environ["JIRA_EPIC_LINK_FIELD"] == "customfield_10014"
    assert os.environ["GITHUB_SEARCH_ALL_REPOS"] == "false"
    assert os.environ["AI_TOKEN_PRICE_INPUT_PER_1M"] == "5.0"
    assert os.environ["STORY_POINT_HOURS"] == "2.0"


def test_map_yaml_to_env_skips_none_values(monkeypatch):
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    _map_yaml_to_env({"jira": {"baseUrl": None}})
    assert "JIRA_BASE_URL" not in os.environ


def test_map_yaml_to_env_does_not_override_existing(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://existing.atlassian.net")
    _map_yaml_to_env({"jira": {"baseUrl": "https://new.atlassian.net"}})
    assert os.environ["JIRA_BASE_URL"] == "https://existing.atlassian.net"


# ── Settings.from_env integration ────────────────────────────────────────────


def test_settings_from_env_picks_up_user_yaml(tmp_path, monkeypatch):
    cfg = {
        "jira": {
            "baseUrl": "https://myco.atlassian.net",
            "email": "eng@myco.com",
            "apiToken": "secret",
        },
        "pricing": {"inputPer1M": 4.5},
    }
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_TOKEN_PRICE_INPUT_PER_1M", raising=False)

    from ai_engineering_metrics.config import Settings

    settings = Settings.from_env(load_dotenv_file=False)

    assert settings.jira.base_url == "https://myco.atlassian.net"
    assert settings.jira.email == "eng@myco.com"
    assert settings.jira.is_configured
    assert settings.pricing.input_per_1m == 4.5


def test_settings_from_env_env_var_wins_over_yaml(tmp_path, monkeypatch):
    cfg = {
        "jira": {"baseUrl": "https://from-yaml.atlassian.net", "email": "y@y.com", "apiToken": "y"}
    }
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setenv("JIRA_BASE_URL", "https://from-env.atlassian.net")

    from ai_engineering_metrics.config import Settings

    settings = Settings.from_env(load_dotenv_file=False)

    assert settings.jira.base_url == "https://from-env.atlassian.net"


# ── CLI: configure command ────────────────────────────────────────────────────


def test_cli_configure_writes_valid_yaml(tmp_path, monkeypatch):
    f = tmp_path / "config.yaml"
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: True)

    result = runner.invoke(app, ["configure"], input=_WIZARD_INPUT)

    assert result.exit_code == 0, result.output
    assert f.exists()
    saved = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert saved["jira"]["baseUrl"] == "https://company.atlassian.net"
    assert saved["jira"]["email"] == "dev@company.com"
    assert saved["jira"]["apiToken"] == "mytoken"
    assert saved["jira"]["epicLinkField"] == "customfield_10014"
    assert saved["github"]["searchAllRepos"] is True
    assert saved["pricing"]["inputPer1M"] == 3.0
    assert saved["estimation"]["storyPointHours"] == 1.0


def test_cli_configure_strips_trailing_slash_from_url(tmp_path, monkeypatch):
    f = tmp_path / "config.yaml"
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: True)
    inp = _WIZARD_INPUT.replace("https://company.atlassian.net", "https://company.atlassian.net/")

    runner.invoke(app, ["configure"], input=inp)

    saved = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert not saved["jira"]["baseUrl"].endswith("/")


def test_cli_configure_overwrites_existing_config(tmp_path, monkeypatch):
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump({"jira": {"baseUrl": "https://old.atlassian.net"}}), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: True)

    result = runner.invoke(app, ["configure"], input=_WIZARD_INPUT)

    assert result.exit_code == 0
    saved = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert saved["jira"]["baseUrl"] == "https://company.atlassian.net"


def test_cli_configure_creates_parent_dirs(tmp_path, monkeypatch):
    f = tmp_path / "nested" / "deep" / "config.yaml"
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: True)

    result = runner.invoke(app, ["configure"], input=_WIZARD_INPUT)

    assert result.exit_code == 0
    assert f.exists()


# ── CLI: analyze — wizard integration ────────────────────────────────────────


def test_cli_analyze_mock_never_triggers_wizard(monkeypatch):
    """--mock must skip the wizard entirely, even if Jira is unconfigured."""
    called = []
    monkeypatch.setattr("ai_engineering_metrics.cli.run_wizard", lambda: called.append(1))

    result = runner.invoke(app, ["analyze", "--mock", "--stdout"])

    assert result.exit_code == 0
    assert not called, "wizard must not run in --mock mode"


def test_cli_analyze_unconfigured_non_tty_exits_1(monkeypatch):
    """Without config and no TTY, analyze must exit 1 with a clear error message."""
    # Use setenv("", "") rather than delenv so that load_dotenv() cannot re-populate
    # these keys from the project .env file (dotenv skips keys already in os.environ).
    monkeypatch.setenv("JIRA_BASE_URL", "")
    monkeypatch.setenv("JIRA_EMAIL", "")
    monkeypatch.setenv("JIRA_API_TOKEN", "")
    monkeypatch.setattr(
        "ai_engineering_metrics.setup_wizard.get_config_path",
        lambda: Path("/nonexistent/never/config.yaml"),
    )
    # Force non-TTY regardless of the test runner environment.
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: False)

    result = runner.invoke(app, ["analyze", "--epic", "PROJ-1"])

    assert result.exit_code != 0, f"expected non-zero exit, got 0; output={result.output!r}"
    assert "configure" in result.output.lower() or "JIRA_BASE_URL" in result.output


def test_cli_analyze_triggers_wizard_then_proceeds(tmp_path, monkeypatch):
    """When Jira is unconfigured, wizard runs and analyze continues with the saved creds."""
    f = tmp_path / "config.yaml"
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard._is_interactive", lambda: True)
    # Use setenv("", "") so load_dotenv() cannot re-populate these from the project .env.
    monkeypatch.setenv("JIRA_BASE_URL", "")
    monkeypatch.setenv("JIRA_EMAIL", "")
    monkeypatch.setenv("JIRA_API_TOKEN", "")

    # After the wizard writes config.yaml, Settings.from_env() will find Jira configured.
    # Patch AnalysisService so no real network call is made.
    from ai_engineering_metrics.config import Settings
    from ai_engineering_metrics.service import AnalysisService

    real_report = AnalysisService.for_settings(Settings(), mock=True).analyze("PROJ-1")
    mock_cls = MagicMock()
    mock_svc = MagicMock()
    mock_svc.analyze.return_value = real_report
    mock_cls.for_settings.return_value = mock_svc
    monkeypatch.setattr("ai_engineering_metrics.cli.AnalysisService", mock_cls)

    result = runner.invoke(app, ["analyze", "--epic", "PROJ-1", "--stdout"], input=_WIZARD_INPUT)

    assert result.exit_code == 0, result.output
    assert f.exists(), "wizard must write config.yaml"
    saved = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert saved["jira"]["baseUrl"] == "https://company.atlassian.net"
    assert saved["jira"]["email"] == "dev@company.com"


def test_cli_analyze_configured_skips_wizard(tmp_path, monkeypatch):
    """When Jira IS configured via YAML, the wizard must NOT run again."""
    cfg = {"jira": {"baseUrl": "https://co.atlassian.net", "email": "e@co.com", "apiToken": "tok"}}
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.setattr("ai_engineering_metrics.setup_wizard.get_config_path", lambda: f)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

    called = []
    monkeypatch.setattr("ai_engineering_metrics.cli.run_wizard", lambda: called.append(1))

    # Patch service to avoid network.
    from ai_engineering_metrics.config import Settings
    from ai_engineering_metrics.service import AnalysisService

    real_report = AnalysisService.for_settings(Settings(), mock=True).analyze("PROJ-1")
    mock_cls = MagicMock()
    mock_cls.for_settings.return_value.analyze.return_value = real_report
    monkeypatch.setattr("ai_engineering_metrics.cli.AnalysisService", mock_cls)

    runner.invoke(app, ["analyze", "--epic", "PROJ-1", "--stdout"])

    assert not called, "wizard must not run when Jira is already configured"
