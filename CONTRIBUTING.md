# Contributing to kubeseal-webgui

Thanks for your interest in improving kubeseal-webgui. This document covers
how to file issues, submit pull requests, and structure your commits so
releases stay automatic.

For local development setup (API and UI), see
[docs/development.md](docs/development.md).

## How to contribute

1. Fork the repository on GitHub.
2. Create a feature branch from `master`.
3. Make your changes following the guidelines below.
4. Open a pull request against `master`. Describe what you changed and why.

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Please
include:

- Versions of kubeseal-webgui, the Sealed Secrets controller, and Kubernetes.
- Steps to reproduce.
- What you expected to happen vs. what actually happened.

**Security vulnerabilities should not be filed as public issues.** Follow
the process in [SECURITY.md](SECURITY.md) instead.

## Proposing changes

For anything non-trivial — new endpoints, new chart values, UI flow changes —
open a draft pull request or discussion first so we can agree on the
direction before you write a lot of code.

## Commit messages

This repository uses [Conventional Commits](https://www.conventionalcommits.org/)
because [semantic-release](https://semantic-release.gitbook.io/) drives
versioning, the changelog, and GitHub Releases from commit messages. The
exact configuration lives in [`.releaserc`](.releaserc).

Use one of these types as the prefix of your commit subject:

| Type | When to use | Release impact |
|---|---|---|
| `feat` | A new feature, new endpoint, new chart value. | minor |
| `fix` | A bug fix. | patch |
| `perf` | A performance improvement. | patch |
| `revert` | Reverting a previous commit. | patch |
| `docs` | Documentation only. | none |
| `style` | Formatting changes that do not affect behavior. | none |
| `chore` | Maintenance work that does not fit the other categories. | patch |
| `refactor` | Code change that neither fixes a bug nor adds a feature. | none |
| `test` | Adding or fixing tests. | none |
| `build` | Build-system or dependency changes. | none |
| `ci` | CI configuration changes. | none |
| `deps` | Dependency bumps. | patch |

A commit with `BREAKING CHANGE:` in the body triggers a major release.

Examples:

```text
feat: add bulk-encrypt endpoint to the API
fix(ui): handle empty namespace list gracefully
docs: explain auto-fetch certificate RBAC
chore(deps): bump fastapi to 0.137
```

## Pull request checklist

Before requesting review, make sure:

- [ ] Tests pass locally (`poetry run pytest` for the API,
      `npm run lint` for the UI).
- [ ] Linters are clean (`ruff`, `black`, `isort`, `mypy` for the API;
      `eslint` and `prettier` for the UI).
- [ ] If you changed behavior, you updated the relevant page in `docs/`.
- [ ] If you changed Helm values, you updated
      [`docs/configuration.md`](docs/configuration.md) and
      [`chart/kubeseal-webgui/values.yaml`](chart/kubeseal-webgui/values.yaml)
      together.
- [ ] Your commit messages follow Conventional Commits.

## Code of conduct

Be respectful and constructive. Harassment, personal attacks, and
discrimination of any kind are not tolerated in issues, pull requests, or
any other project space. Maintainers reserve the right to remove comments
and block users that do not follow this rule.
