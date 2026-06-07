"""Rules loading and defaults."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import RuleSet


DEFAULT_RULES: dict[str, Any] = {
    "max_total_bytes": 200000,
    "max_estimated_tokens": 50000,
    "max_file_bytes": 60000,
    "required_paths": ["README.md"],
    "forbidden_paths": [
        ".env",
        ".env.*",
        "**/id_rsa",
        "**/*.pem",
        "**/*.key",
        "**/node_modules/**",
        "**/.git/**",
    ],
    "sensitive_patterns": [
        "(?i)api[_-]?key\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_\\-]{16,}",
        "(?i)secret\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_\\-]{12,}",
        "-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "(?i)ghp_[A-Za-z0-9]{20,}",
    ],
    "todo_patterns": ["TODO", "FIXME"],
    "allow_todos": False,
    "require_readme": True,
    "require_tests": True,
    "require_ci": True,
    "fail_on": ["error"],
}


def load_rules(path: str | Path | None) -> RuleSet:
    if path is None:
        return normalize_rules(DEFAULT_RULES)
    rule_path = Path(path)
    text = rule_path.read_text(encoding="utf-8")
    if rule_path.suffix.lower() in {".yaml", ".yml"}:
        data = parse_simple_yaml(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Rules file must contain an object")
    merged = dict(DEFAULT_RULES)
    merged.update(data)
    return normalize_rules(merged)


def write_default_rules(path: str | Path) -> None:
    output_path = Path(path)
    output_path.write_text(json.dumps(DEFAULT_RULES, indent=2) + "\n", encoding="utf-8")


def normalize_rules(data: dict[str, Any]) -> RuleSet:
    return RuleSet(
        max_total_bytes=_optional_int(data.get("max_total_bytes")),
        max_estimated_tokens=_optional_int(data.get("max_estimated_tokens")),
        max_file_bytes=_optional_int(data.get("max_file_bytes")),
        required_paths=_string_list(data.get("required_paths", [])),
        forbidden_paths=_string_list(data.get("forbidden_paths", [])),
        sensitive_patterns=_string_list(data.get("sensitive_patterns", [])),
        todo_patterns=_string_list(data.get("todo_patterns", ["TODO", "FIXME"])),
        allow_todos=bool(data.get("allow_todos", False)),
        require_readme=bool(data.get("require_readme", True)),
        require_tests=bool(data.get("require_tests", True)),
        require_ci=bool(data.get("require_ci", True)),
        fail_on=_string_list(data.get("fail_on", ["error"])),
    )


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a small YAML subset without external dependencies.

    Supported shapes are enough for this project's rules: scalar keys and
    top-level lists using "- value". JSON remains the recommended format.
    """

    result: dict[str, Any] = {}
    current_key = ""
    for raw_line in text.splitlines():
        line = _strip_yaml_comment(raw_line).rstrip()
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            item = line.strip()
            if item.startswith("- "):
                result.setdefault(current_key, []).append(_yaml_scalar(item[2:].strip()))
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported YAML line: {raw_line}")
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if not value:
            result[current_key] = []
        elif value.startswith("[") or value.startswith("{"):
            result[current_key] = json.loads(value)
        else:
            result[current_key] = _yaml_scalar(value)
    return result


def _strip_yaml_comment(line: str) -> str:
    in_quote = ""
    output = []
    for char in line:
        if char in {"'", '"'}:
            in_quote = "" if in_quote == char else char
        if char == "#" and not in_quote:
            break
        output.append(char)
    return "".join(output)


def _yaml_scalar(value: str) -> Any:
    trimmed = value.strip()
    if trimmed.lower() in {"true", "false"}:
        return trimmed.lower() == "true"
    if trimmed.lower() in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", trimmed):
        return int(trimmed)
    if (trimmed.startswith('"') and trimmed.endswith('"')) or (trimmed.startswith("'") and trimmed.endswith("'")):
        return trimmed[1:-1]
    return trimmed


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]
