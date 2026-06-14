"""Deployment data source backed by a JSON file.

Mirrors the interface expected by AnalysisService: a ``get_deployments()``
method returning a list of :class:`~ai_engineering_metrics.domain.models.Deployment`.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering_metrics.domain.models import Deployment
from ai_engineering_metrics.integrations.base import IntegrationError


class JsonDeploymentClient:
    """Loads deployment events from a JSON file on disk."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def get_deployments(self, period_days: int = 30) -> list[Deployment]:
        if not self._path.exists():
            raise IntegrationError(f"Deployments file not found: {self._path}")
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IntegrationError(f"Invalid JSON in deployments file: {exc}") from exc
        return [Deployment.model_validate(item) for item in raw]
