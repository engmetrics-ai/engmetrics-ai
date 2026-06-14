# Governance

EngMetrics AI is an open source project maintained by Dennis Rojas Pereira and community contributors. This document describes how decisions are made and how contributors can participate.

## Roles

### Maintainer

The maintainer is responsible for:

- Reviewing and merging pull requests.
- Triaging issues and setting priorities.
- Cutting releases and maintaining the changelog.
- Defining the project roadmap.

Current maintainer: **Dennis Rojas Pereira** ([@dennisrp](https://github.com/dennisrp))

### Contributors

Anyone who opens a pull request, files an issue, or improves the documentation. All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

### Reviewers (future)

As the project grows, trusted contributors may be invited as reviewers with write access to approve PRs.

## Decision-making

Decisions follow a lightweight consensus model:

1. **Small changes** (bug fixes, doc improvements, test additions) — merged by the maintainer once CI passes and the checklist is satisfied.
2. **Medium changes** (new metrics, new integrations, API shape changes) — discussed in the relevant issue before a PR is opened. The maintainer has final say.
3. **Large changes** (architecture shifts, new intelligence lenses, plugin system) — require an RFC (Request for Comment) issue labelled `rfc`. Open for at least one week before implementation begins.

## RFC process

1. Open a GitHub issue with the `rfc` label.
2. Describe: the problem, the proposed solution, alternatives considered, and open questions.
3. Community discussion for a minimum of 7 days.
4. Maintainer accepts, rejects, or requests changes. Accepted RFCs move to an implementation issue.

## Releases

- Releases follow [Semantic Versioning](https://semver.org/).
- Release notes are maintained in [CHANGELOG.md](CHANGELOG.md).
- Tags and GitHub Releases are created from `main`.

## Roadmap

The project roadmap is in [ROADMAP.md](ROADMAP.md). Community input is welcome via issues labelled `roadmap`.

## Code of Conduct

All participants must follow the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Violations can be reported to **dennisrojaspereira@gmail.com**.

## Questions?

Open a [GitHub Discussion](https://github.com/engmetrics-ai/engmetrics-ai/discussions) for anything that is not a bug or feature request.
