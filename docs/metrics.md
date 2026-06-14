# Metrics Reference

EngMetrics AI computes metrics across five intelligence lenses: DORA, AI impact, code quality, flow & rework, and risk. This document defines each metric, explains why it matters, how it is calculated, and its limitations.

> **Note on heuristics.** Several metrics are heuristic proxies derived from diff statistics and commit patterns because the underlying ground-truth data (e.g. actual test coverage, real static-analysis scores) is not always available. They are useful directional signals — treat them as a starting point for conversation, not as ground truth.

---

## DORA Metrics

The four DORA metrics are the industry standard for measuring software delivery performance. See the [DORA research](https://dora.dev) for Elite/High/Medium/Low band definitions.

### Lead Time

**What it measures:** The time from the first commit on a feature to when it is deployed to production — end-to-end cycle time.

**Why it matters:** Shorter lead times mean faster feedback loops, less work in progress, and a more responsive team. Long lead times often indicate batch sizes that are too large or hand-off delays.

**How it is calculated:**
`Lead Time = merge time of last PR − creation time of first commit linked to the epic`

When story-level data is available, it is computed per story and averaged.

**Limitations:** Relies on PR merge events as a proxy for deployment. If PRs are merged but not deployed (e.g., behind a feature flag), Lead Time will be understated.

**Example:** Epic opened 2026-01-10. Last PR merged 2026-01-24. Lead Time = 14 days.

---

### Deployment Frequency

**What it measures:** How often the team deploys to production.

**Why it matters:** Higher deployment frequency correlates with lower risk per deployment, faster feedback, and higher team confidence. Elite teams deploy multiple times per day.

**How it is calculated:**
`Deployment Frequency = number of merged PRs / number of working days in the epic window`

Each merged PR to the main branch is treated as a deployment event.

**Limitations:** Not all merged PRs are deployments (squash merges, hotfixes, docs-only changes). Without a CI/CD webhook, the tool cannot distinguish deployment types.

**Example:** 8 PRs merged over 10 working days → 0.8 deploys/day (High band).

---

### Change Failure Rate

**What it measures:** The percentage of deployments that result in a degraded service or require a hotfix / rollback.

**Why it matters:** High CFR indicates quality or testing problems. Elite teams keep CFR below 5%.

**How it is calculated:**
`CFR = PRs with "hotfix", "revert", or "fix" in their title or branch / total PRs merged`

**Limitations:** Title/branch heuristic can miss unlabelled hotfixes or flag routine fixes incorrectly. Connecting to an incident management system (PagerDuty, OpsGenie) would give a more accurate signal.

**Example:** 2 out of 20 PRs are reverts → CFR = 10% (Medium band).

---

### MTTR (Mean Time to Recovery)

**What it measures:** The average time to restore service after a production incident or failed deployment.

**Why it matters:** Fast recovery limits the blast radius of failures and reflects system resilience and team response maturity.

**How it is calculated:**
`MTTR = average time from a revert/hotfix PR being opened to it being merged`

**Limitations:** Without an incident timeline from a monitoring system, the tool uses hotfix PR duration as a proxy, which underestimates the full recovery time (detection + response + deploy).

**Example:** Two hotfix PRs took 1h and 3h to merge → MTTR = 2h (High band).

---

## Pull Request Metrics

### PR Cycle Time

**What it measures:** The elapsed time from PR creation to merge.

**Why it matters:** Long PR cycle times signal review bottlenecks, large PRs, or unclear ownership. Reducing cycle time shortens the feedback loop for authors.

**How it is calculated:**
`PR Cycle Time = PR merged_at − PR created_at`

Averaged across all PRs in the epic.

**Limitations:** Does not distinguish wait time (waiting for a reviewer) from active review time. A PR can be open for days with zero review activity.

**Example:** 8 PRs with an average of 18 hours from open to merge.

---

### Review Time

**What it measures:** The time from the first review request (or first review comment) to the final approval.

**Why it matters:** Long review times block authors and delay deployments. They can signal reviewers are overloaded or that PRs are too large to review quickly.

**How it is calculated:**
`Review Time = first_approval_at − first_review_event_at`

Uses GitHub review events fetched via the `gh` CLI.

**Limitations:** The `gh` CLI does not always expose the exact moment a review was requested. If the first review event is an approval with no preceding comment, Review Time may be 0.

**Example:** First review comment 2h after PR opened; approval 4h later → Review Time = 4h.

---

### Throughput

**What it measures:** The number of stories or PRs delivered per time unit (sprint, week).

**Why it matters:** Throughput is an aggregate health signal. A sustained drop in throughput while story points stay the same suggests hidden rework or scope growth.

**How it is calculated:**
`Throughput = number of stories resolved / number of sprint weeks in the epic`

Story points are tracked separately as Velocity.

**Limitations:** Throughput conflates small quick-wins with large complex stories. Always pair it with story point data.

**Example:** 5 stories resolved over 2 weeks → Throughput = 2.5 stories/week.

---

## AI Adoption Metrics

### AI Adoption Rate

**What it measures:** The proportion of stories in the epic where AI tools were used.

**Why it matters:** Teams adopting AI tools unevenly may not be realising their full productivity potential. High adoption with flat velocity may point to low-quality AI usage; high adoption with rising velocity is a positive signal.

**How it is calculated:**
`AI Adoption Rate = stories with AI token data / total stories` × 100%

Requires the `JIRA_AI_TOKENS_FIELD` custom field to be populated.

**Limitations:** Adoption is measured by whether a story has token data — it does not capture *how* AI was used (writing code vs. writing comments vs. test generation).

**Example:** 4 out of 5 stories have AI tokens recorded → 80% adoption rate.

---

### AI Assisted PR Ratio

**What it measures:** The share of PRs that were produced with AI assistance (based on token data on the linked story).

**Why it matters:** Complements the AI Adoption Rate by looking at the code output level rather than story level.

**How it is calculated:**
`AI Assisted PR Ratio = PRs linked to stories with AI token data / total PRs` × 100%

**Limitations:** Indirect inference — if the story has tokens but the PR was written manually, the ratio will be overstated.

**Example:** 6 out of 8 PRs link to AI-assisted stories → 75% AI Assisted PR Ratio.

---

## Quality Metrics

### Review Rework Rate

**What it measures:** The proportion of PRs that required one or more rounds of post-review rework (re-commits after a review comment or "changes requested" event).

**Why it matters:** High rework rates can indicate unclear requirements, quality issues in the initial implementation, or overly strict reviews. Chronic rework is a leading indicator of delivery slow-down.

**How it is calculated:**
`Review Rework Rate = PRs with commits_after_review > 0 / total PRs` × 100%

`commits_after_review` is the number of commits pushed after the first review comment was posted.

**Limitations:** Not all post-review commits are rework — some are merge commits, rebases, or minor nits. The heuristic will overcount rework for teams that rebase frequently.

**Example:** 3 out of 8 PRs had commits after a review comment → Rework Rate = 37.5%.

---

## Bands and benchmarks

Where DORA bands apply, EngMetrics AI labels each metric according to the [DORA 2023 report](https://dora.dev/research/2023/dora-report/) thresholds:

| Band | Lead Time | Deployment Freq | CFR | MTTR |
|---|---|---|---|---|
| **Elite** | < 1 hour | Multiple/day | < 5% | < 1 hour |
| **High** | 1 day – 1 week | 1/day – 1/week | 5–10% | < 1 day |
| **Medium** | 1 week – 1 month | 1/week – 1/month | 10–15% | 1 day – 1 week |
| **Low** | > 1 month | < 1/month | > 15% | > 1 week |

Non-DORA metrics do not have industry-standard bands yet. Treat them as relative signals within your team's own history.
