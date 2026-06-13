"""Tests for the per-epic report bundle output."""

import csv
from pathlib import Path

from ai_engineering_metrics.config import Settings
from ai_engineering_metrics.output import (
    DASHBOARD_FILE,
    METRICS_FILE,
    PRS_FILE,
    STORIES_FILE,
    write_bundle,
)
from ai_engineering_metrics.service import AnalysisService


def _report():
    return AnalysisService.for_settings(Settings(), mock=True).analyze("DEMO-1")


def test_write_bundle_creates_all_artifacts(tmp_path: Path):
    report = _report()
    written = write_bundle(report, tmp_path)

    epic_dir = tmp_path / "DEMO-1"
    assert epic_dir.is_dir()
    for name in (DASHBOARD_FILE, METRICS_FILE, STORIES_FILE, PRS_FILE):
        assert (epic_dir / name).exists()
        assert written[name] == epic_dir / name

    # CSVs are well-formed and populated.
    with (epic_dir / STORIES_FILE).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(report.stories)
    assert "ai_tokens" in rows[0] and "hours_saved" in rows[0]

    with (epic_dir / PRS_FILE).open(encoding="utf-8") as fh:
        pr_rows = list(csv.DictReader(fh))
    assert len(pr_rows) == len(report.all_pull_requests)
    assert "linked_to" in pr_rows[0] and "time_to_merge_hours" in pr_rows[0]


def test_write_bundle_respects_format_selection(tmp_path: Path):
    written = write_bundle(_report(), tmp_path, formats=("html",))
    assert set(written) == {DASHBOARD_FILE}
    assert (tmp_path / "DEMO-1" / DASHBOARD_FILE).exists()
    assert not (tmp_path / "DEMO-1" / METRICS_FILE).exists()
