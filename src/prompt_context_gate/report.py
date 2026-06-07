"""Report rendering."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Any

from .models import Finding, Inspection


def render_findings(findings: list[Finding], fmt: str) -> str:
    if fmt == "json":
        return json.dumps({"findings": [asdict(item) for item in findings]}, indent=2)
    if fmt == "csv":
        return _findings_csv(findings)
    if fmt == "markdown":
        return _findings_markdown(findings)
    raise ValueError(f"Unsupported output format: {fmt}")


def render_inspection(inspection: Inspection, fmt: str) -> str:
    data = asdict(inspection)
    if fmt == "json":
        return json.dumps(data, indent=2)
    if fmt == "csv":
        return _inspection_csv(data)
    if fmt == "markdown":
        return _inspection_markdown(data)
    raise ValueError(f"Unsupported output format: {fmt}")


def _findings_markdown(findings: list[Finding]) -> str:
    lines = ["# Prompt Context Gate Report", ""]
    if not findings:
        lines.extend(["No findings.", ""])
        return "\n".join(lines)
    lines.extend(["| Severity | Rule | Path | Line | Message |", "| --- | --- | --- | ---: | --- |"])
    for finding in findings:
        lines.append(
            "| {severity} | {rule} | {path} | {line} | {message} |".format(
                severity=_escape_md(finding.severity),
                rule=_escape_md(finding.rule),
                path=_escape_md(finding.path),
                line=finding.line or "",
                message=_escape_md(finding.message),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _inspection_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Prompt Context Gate Inspection",
        "",
        f"- Source: `{data['source_path']}`",
        f"- Files: {data['file_count']}",
        f"- Bytes: {data['total_bytes']}",
        f"- Estimated tokens: {data['estimated_tokens']}",
        "",
        "| Path | Bytes | Lines | Source |",
        "| --- | ---: | ---: | --- |",
    ]
    for file in data["files"]:
        lines.append(f"| {_escape_md(file['path'])} | {file['bytes']} | {file['lines']} | {_escape_md(file['source'])} |")
    lines.append("")
    return "\n".join(lines)


def _findings_csv(findings: list[Finding]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["severity", "rule", "path", "line", "message", "detail"])
    writer.writeheader()
    for finding in findings:
        writer.writerow(asdict(finding))
    return output.getvalue()


def _inspection_csv(data: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["path", "bytes", "lines", "source"])
    writer.writeheader()
    for file in data["files"]:
        writer.writerow(file)
    return output.getvalue()


def _escape_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
