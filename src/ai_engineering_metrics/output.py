"""Report output: write an :class:`EpicReport` as a tidy per-epic bundle.

A run produces a folder named after the epic, e.g.::

    reports/
    └── DEMO-1/
        ├── dashboard.html
        ├── metrics.json
        ├── stories.csv
        └── pull_requests.csv

This keeps every artifact for a run together and makes the output discoverable.
The CSVs are plain exports (stdlib :mod:`csv`) — no extra dependencies.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ai_engineering_metrics.domain.models import EpicReport, PullRequest, Story
from ai_engineering_metrics.reports.html_report import write_html
from ai_engineering_metrics.storage.json_storage import report_to_json

# Artifact selection keywords accepted by the CLI's --format option.
ALL_FORMATS = ("html", "json", "csv")

DASHBOARD_FILE = "dashboard.html"
METRICS_FILE = "metrics.json"
STORIES_FILE = "stories.csv"
PRS_FILE = "pull_requests.csv"


def _iso(value: object) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else ""


def _story_row(s: Story) -> dict[str, object]:
    return {
        "key": s.key,
        "summary": s.summary,
        "status": s.status,
        "assignee": s.assignee or "",
        "story_points": s.story_points if s.story_points is not None else "",
        "ai_tokens": s.ai_tokens,
        "estimate_without_ai_hours": s.estimate_without_ai_hours,
        "estimate_with_ai_hours": s.estimate_with_ai_hours,
        "hours_saved": s.hours_saved,
        "lead_time_hours": s.lead_time_hours if s.lead_time_hours is not None else "",
        "pull_requests": len(s.pull_requests),
        "labels": ";".join(s.labels),
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
        "resolved_at": _iso(s.resolved_at),
    }


def write_stories_csv(report: EpicReport, path: Path) -> Path:
    fields = list(_story_row(Story(key="", summary="", status="")).keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for story in report.stories:
            writer.writerow(_story_row(story))
    return path


def _pr_row(pr: PullRequest, linked_to: str) -> dict[str, object]:
    return {
        "linked_to": linked_to,
        "number": pr.number,
        "repository": pr.repository,
        "title": pr.title,
        "author": pr.author,
        "status": pr.status,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "commits": pr.commits,
        "review_comments": pr.review_comments,
        "requested_changes": pr.requested_changes,
        "review_cycles": pr.review_cycles,
        "commits_after_review": pr.commits_after_review,
        "reverts_detected": pr.reverts_detected,
        "time_to_merge_hours": pr.time_to_merge_hours if pr.time_to_merge_hours is not None else "",
        "url": pr.url or "",
    }


def write_pull_requests_csv(report: EpicReport, path: Path) -> Path:
    fields = list(
        _pr_row(
            PullRequest(number=0, title="", author="", repository="", branch="", status=""), ""
        ).keys()
    )
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for story in report.stories:
            for pr in story.pull_requests:
                writer.writerow(_pr_row(pr, story.key))
        for pr in report.epic_pull_requests:
            writer.writerow(_pr_row(pr, report.epic.key))
    return path


def write_bundle(
    report: EpicReport,
    base_dir: Path | str,
    *,
    formats: tuple[str, ...] = ALL_FORMATS,
) -> dict[str, Path]:
    """Write the selected artifacts into ``<base_dir>/<EPIC>/`` and return the
    mapping of artifact name -> written path."""
    out_dir = Path(base_dir) / report.epic.key
    out_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    if "html" in formats:
        written[DASHBOARD_FILE] = write_html(report, out_dir / DASHBOARD_FILE)
    if "json" in formats:
        target = out_dir / METRICS_FILE
        target.write_text(report_to_json(report), encoding="utf-8")
        written[METRICS_FILE] = target
    if "csv" in formats:
        written[STORIES_FILE] = write_stories_csv(report, out_dir / STORIES_FILE)
        written[PRS_FILE] = write_pull_requests_csv(report, out_dir / PRS_FILE)
    return written
