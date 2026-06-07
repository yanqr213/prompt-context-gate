"""Context bundle parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import ContextBundle, ContextFile, Inspection


HEADING_RE = re.compile(r"^#{1,6}\s+(?:file|path)[:\s]+(?P<path>\S[^\n\r]*)$", re.IGNORECASE | re.MULTILINE)


def parse_bundle(path: str | Path) -> ContextBundle:
    """Parse a Markdown or JSON context bundle from disk."""

    bundle_path = Path(path)
    raw_text = bundle_path.read_text(encoding="utf-8")
    suffix = bundle_path.suffix.lower()
    if suffix == ".json":
        return _parse_json_bundle(bundle_path, raw_text)
    if suffix in {".md", ".markdown", ".txt"}:
        return _parse_markdown_bundle(bundle_path, raw_text)
    raise ValueError(f"Unsupported bundle format: {bundle_path.suffix or '(none)'}")


def inspect_bundle(bundle: ContextBundle) -> Inspection:
    files = [
        {
            "path": item.path,
            "bytes": item.size_bytes,
            "lines": item.line_count,
            "source": item.source,
        }
        for item in sorted(bundle.files, key=lambda file: file.path.lower())
    ]
    return Inspection(
        source_path=bundle.source_path,
        total_bytes=bundle.total_bytes,
        total_chars=bundle.total_chars,
        estimated_tokens=bundle.estimated_tokens,
        file_count=len(bundle.files),
        files=files,
    )


def _parse_json_bundle(path: Path, raw_text: str) -> ContextBundle:
    data = json.loads(raw_text)
    files: list[ContextFile] = []

    if isinstance(data, dict):
        raw_files = data.get("files") or data.get("context") or data.get("documents")
        if isinstance(raw_files, dict):
            for file_path, content in raw_files.items():
                files.append(ContextFile(str(file_path), _stringify_content(content), "json"))
        elif isinstance(raw_files, list):
            for index, entry in enumerate(raw_files, start=1):
                parsed = _context_file_from_json_entry(entry, index)
                if parsed is not None:
                    files.append(parsed)
        elif "path" in data and "content" in data:
            files.append(ContextFile(str(data["path"]), _stringify_content(data["content"]), "json"))
        metadata = {key: value for key, value in data.items() if key not in {"files", "context", "documents"}}
    elif isinstance(data, list):
        for index, entry in enumerate(data, start=1):
            parsed = _context_file_from_json_entry(entry, index)
            if parsed is not None:
                files.append(parsed)
        metadata = {}
    else:
        raise ValueError("JSON bundle must be an object or array")

    if not files:
        files = [ContextFile(path.name, raw_text, "raw-json")]
    return ContextBundle(str(path), raw_text, files, metadata)


def _context_file_from_json_entry(entry: Any, index: int) -> ContextFile | None:
    if isinstance(entry, dict):
        file_path = entry.get("path") or entry.get("file") or entry.get("filename") or f"entry-{index}.txt"
        content = entry.get("content", entry.get("text", entry.get("body", "")))
        return ContextFile(str(file_path), _stringify_content(content), "json")
    if isinstance(entry, str):
        return ContextFile(f"entry-{index}.txt", entry, "json")
    return None


def _parse_markdown_bundle(path: Path, raw_text: str) -> ContextBundle:
    files = _files_from_markdown_fences(raw_text)
    if not files:
        files = _files_from_markdown_headings(raw_text)
    if not files:
        files = [ContextFile(path.name, raw_text, "raw-markdown")]
    return ContextBundle(str(path), raw_text, files, {})


def _files_from_markdown_fences(raw_text: str) -> list[ContextFile]:
    files: list[ContextFile] = []
    in_fence = False
    info = ""
    body_lines: list[str] = []
    for line in raw_text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if not in_fence and stripped.startswith("```"):
            in_fence = True
            info = stripped[3:].strip()
            body_lines = []
            continue
        if in_fence and stripped == "```":
            file_path = _path_from_fence_info(info)
            if file_path:
                files.append(ContextFile(file_path, "".join(body_lines).rstrip("\r\n"), "markdown-fence"))
            in_fence = False
            info = ""
            body_lines = []
            continue
        if in_fence:
            body_lines.append(line)
    if in_fence:
        file_path = _path_from_fence_info(info)
        if file_path:
            files.append(ContextFile(file_path, "".join(body_lines).rstrip("\r\n"), "markdown-fence"))
    return files


def _path_from_fence_info(info: str) -> str:
    if not info:
        return ""
    parts = [part.strip() for part in re.split(r"\s+", info) if part.strip()]
    for part in parts:
        lower = part.lower()
        if lower.startswith("path=") or lower.startswith("file="):
            return part.split("=", 1)[1].strip("\"'")
    if len(parts) >= 2 and _looks_like_path(parts[-1]):
        return parts[-1].strip("\"'")
    if len(parts) == 1 and _looks_like_path(parts[0]):
        return parts[0].strip("\"'")
    return ""


def _looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value or "." in Path(value).name


def _files_from_markdown_headings(raw_text: str) -> list[ContextFile]:
    matches = list(HEADING_RE.finditer(raw_text))
    files: list[ContextFile] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        file_path = match.group("path").strip()
        content = raw_text[start:end].strip("\n")
        files.append(ContextFile(file_path, content, "markdown-heading"))
    return files


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, indent=2)
