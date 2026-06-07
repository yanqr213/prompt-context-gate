"""Shared data models for prompt-context-gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContextFile:
    """One file included in a context bundle."""

    path: str
    content: str
    source: str = "bundle"

    @property
    def size_bytes(self) -> int:
        return len(self.content.encode("utf-8"))

    @property
    def line_count(self) -> int:
        if not self.content:
            return 0
        return self.content.count("\n") + (0 if self.content.endswith("\n") else 1)


@dataclass(frozen=True)
class ContextBundle:
    """Parsed context bundle plus raw metadata."""

    source_path: str
    raw_text: str
    files: list[ContextFile]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_bytes(self) -> int:
        return len(self.raw_text.encode("utf-8"))

    @property
    def total_chars(self) -> int:
        return len(self.raw_text)

    @property
    def estimated_tokens(self) -> int:
        # A conservative local estimate. It avoids tokenizer dependencies while
        # keeping CI thresholds deterministic.
        return max(1, (len(self.raw_text) + 3) // 4) if self.raw_text else 0


@dataclass(frozen=True)
class RuleSet:
    """Normalized rules loaded from JSON or simple YAML."""

    max_total_bytes: int | None = None
    max_estimated_tokens: int | None = None
    max_file_bytes: int | None = None
    required_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    sensitive_patterns: list[str] = field(default_factory=list)
    todo_patterns: list[str] = field(default_factory=lambda: ["TODO", "FIXME"])
    allow_todos: bool = False
    require_readme: bool = True
    require_tests: bool = True
    require_ci: bool = True
    fail_on: list[str] = field(default_factory=lambda: ["error"])


@dataclass(frozen=True)
class Finding:
    """One policy finding."""

    severity: str
    rule: str
    message: str
    path: str = ""
    line: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class Inspection:
    """Bundle inspection summary."""

    source_path: str
    total_bytes: int
    total_chars: int
    estimated_tokens: int
    file_count: int
    files: list[dict[str, Any]]
