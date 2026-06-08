# Changelog

## 0.3.0 - 2026-06-08

- Added `build` to create standard JSON or Markdown context bundles from repository files and manifests.
- Added path traversal protection, duplicate path de-duplication, and optional per-file byte limits during bundle building.
- Added an example manifest and CI smoke coverage for build -> inspect/check workflows.
- Expanded Chinese and English README docs for manifest-driven context bundle generation.

## 0.2.0 - 2026-06-08

- Added SARIF 2.1.0 output for context bundle policy findings.
- Added CLI support for `check -f sarif`.
- Report output now creates parent directories automatically.
- Added SARIF renderer and CLI tests.
- Expanded Chinese and English README docs with GitHub Code Scanning examples.

## 0.1.0 - 2026-06-08

- Initial public project.
- Added standard-library CLI with `init-rules`, `inspect`, and `check`.
- Added Markdown and JSON context bundle parsing.
- Added budget, path, secret-pattern, TODO, file-size, README, tests, and CI coverage checks.
- Added Markdown, JSON, and CSV reports plus CI threshold exit codes.
