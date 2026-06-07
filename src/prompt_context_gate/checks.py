"""Policy checks for parsed bundles."""

from __future__ import annotations

import fnmatch
import re

from .models import ContextBundle, Finding, RuleSet


README_PATTERNS = ["README", "README.*", "docs/README.*"]
TEST_PATTERNS = ["tests/**", "test/**", "**/*test*.*", "**/*spec*.*"]
CI_PATTERNS = [".github/workflows/**", ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile"]


def run_checks(bundle: ContextBundle, rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    paths = [file.path for file in bundle.files]

    findings.extend(_budget_findings(bundle, rules))
    findings.extend(_required_path_findings(paths, rules))
    findings.extend(_forbidden_path_findings(paths, rules))
    findings.extend(_coverage_findings(paths, rules))

    for file in bundle.files:
        if rules.max_file_bytes is not None and file.size_bytes > rules.max_file_bytes:
            findings.append(
                Finding(
                    "error",
                    "max_file_bytes",
                    f"File exceeds max_file_bytes ({file.size_bytes} > {rules.max_file_bytes}).",
                    file.path,
                )
            )
        findings.extend(_sensitive_findings(file.path, file.content, rules))
        if not rules.allow_todos:
            findings.extend(_todo_findings(file.path, file.content, rules))

    return sorted(findings, key=lambda item: (_severity_sort(item.severity), item.path, item.line or 0, item.rule))


def should_fail(findings: list[Finding], rules: RuleSet) -> bool:
    fail_on = {severity.lower() for severity in rules.fail_on}
    return any(finding.severity.lower() in fail_on for finding in findings)


def _budget_findings(bundle: ContextBundle, rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    if rules.max_total_bytes is not None and bundle.total_bytes > rules.max_total_bytes:
        findings.append(
            Finding(
                "error",
                "max_total_bytes",
                f"Bundle exceeds max_total_bytes ({bundle.total_bytes} > {rules.max_total_bytes}).",
            )
        )
    if rules.max_estimated_tokens is not None and bundle.estimated_tokens > rules.max_estimated_tokens:
        findings.append(
            Finding(
                "error",
                "max_estimated_tokens",
                f"Bundle exceeds max_estimated_tokens ({bundle.estimated_tokens} > {rules.max_estimated_tokens}).",
            )
        )
    return findings


def _required_path_findings(paths: list[str], rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in rules.required_paths:
        if not any(_path_match(path, pattern) for path in paths):
            findings.append(Finding("error", "required_paths", f"Required path is missing: {pattern}."))
    return findings


def _forbidden_path_findings(paths: list[str], rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        for pattern in rules.forbidden_paths:
            if _path_match(path, pattern):
                findings.append(Finding("error", "forbidden_paths", f"Forbidden path matched: {pattern}.", path))
    return findings


def _coverage_findings(paths: list[str], rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    if rules.require_readme and not any(_matches_any(path, README_PATTERNS) for path in paths):
        findings.append(Finding("error", "coverage_readme", "Context bundle does not include README coverage."))
    if rules.require_tests and not any(_matches_any(path, TEST_PATTERNS) for path in paths):
        findings.append(Finding("error", "coverage_tests", "Context bundle does not include test coverage files."))
    if rules.require_ci and not any(_matches_any(path, CI_PATTERNS) for path in paths):
        findings.append(Finding("warning", "coverage_ci", "Context bundle does not include CI configuration."))
    return findings


def _sensitive_findings(path: str, content: str, rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in rules.sensitive_patterns:
        compiled = re.compile(pattern)
        for line_number, line in enumerate(content.splitlines(), start=1):
            if compiled.search(line):
                findings.append(Finding("error", "sensitive_patterns", "Sensitive pattern matched.", path, line_number, pattern))
    return findings


def _todo_findings(path: str, content: str, rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    if not rules.todo_patterns:
        return findings
    pattern = re.compile("|".join(re.escape(item) for item in rules.todo_patterns), re.IGNORECASE)
    for line_number, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line):
            findings.append(Finding("warning", "todo_patterns", "TODO/FIXME marker is still present.", path, line_number))
    return findings


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_path_match(path, pattern) for pattern in patterns)


def _path_match(path: str, pattern: str) -> bool:
    normalized_path = path.replace("\\", "/").lstrip("./")
    normalized_pattern = pattern.replace("\\", "/").lstrip("./")
    return fnmatch.fnmatch(normalized_path, normalized_pattern) or fnmatch.fnmatch(normalized_path.lower(), normalized_pattern.lower())


def _severity_sort(severity: str) -> int:
    order = {"error": 0, "warning": 1, "info": 2}
    return order.get(severity.lower(), 9)
