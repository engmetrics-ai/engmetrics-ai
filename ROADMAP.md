# Roadmap

This is the living roadmap for **EngMetrics AI**. It captures what we are working on now, what comes next, and what we are thinking about for the future.

Community feedback is welcome — open an issue with the `roadmap` label to suggest, upvote, or discuss items.

> For the full product vision and detailed rationale, see [`docs/product-vision.md`](docs/product-vision.md).

---

## Now — Foundation

These are the things we are actively working on or that are nearly done.

- [x] GitHub integration via `gh` CLI (PR discovery, enrichment, auto-detection)
- [x] DORA metrics (Deployment Frequency, Lead Time, Change Failure Rate, MTTR)
- [x] Local development setup (mock mode, no credentials required)
- [x] Interactive HTML dashboard with per-PR evaluation popup
- [x] Documentation foundation (README, CONTRIBUTING, architecture, metrics)
- [ ] Publish to PyPI (`pipx install ai-engineering-metrics`)
- [ ] Docker Compose quick-start for zero-config local run
- [ ] Public demo environment with live data

---

## Next — Growth

Items that are planned and design work is underway or imminent.

- [ ] **AI adoption metrics** — AI Assisted PR Ratio, token-per-story-point trends, AI Dependency Risk Score improvements
- [ ] **Pull request analytics** — first-review time, review-to-merge time, reviewer load
- [ ] **Team dashboards** — aggregate view across multiple epics and time ranges
- [ ] **Docker image publishing** — `ghcr.io/engmetrics-ai/engmetrics-ai`
- [ ] **Real static-analysis quality source** — SonarQube / CodeClimate adapter
- [ ] **Pluggable AI cost providers** — per-model token pricing, custom rates
- [ ] **Agent-ready JSON API** — structured output for LLM narrative reports
- [ ] **GitHub Actions integration** — post metrics summary as a workflow step

---

## Future — Vision

Longer-horizon ideas that are not yet scoped. Open an RFC if you want to champion one of these.

- [ ] **Jira integration enhancements** — server/DC support, custom field discovery wizard
- [ ] **GitLab integration** — MR-based metrics mirroring the GitHub integration
- [ ] **Slack integration** — weekly digest, anomaly alerts
- [ ] **Linear integration** — issue tracking alternative to Jira
- [ ] **Executive dashboard** — portfolio rollups across teams and quarters
- [ ] **Plugin architecture** — community-contributed integrations and metrics lenses
- [ ] **SDKs** — Python client for embedding metrics in other tools
- [ ] **Natural language queries** — "Which epics had the highest rework cost this quarter?"
- [ ] **Proactive anomaly detection** — alerts when lead time or CFR crosses a threshold

---

## How to influence the roadmap

1. **Vote on existing issues** with a 👍 reaction.
2. **Open a new issue** with the `roadmap` label describing the use case.
3. **Start an RFC** with the `rfc` label for large architectural changes (see [GOVERNANCE.md](GOVERNANCE.md)).
4. **Contribute** — if something is listed here and you want to build it, open an issue first to align on approach.
