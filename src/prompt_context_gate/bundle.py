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


def build_bundle(
    root: str | Path,
    paths: list[str],
    *,
    manifest: str | Path | None = None,
    output_format: str = "json",
    max_file_bytes: int | None = None,
) -> str:
    """Build a standard context bundle from repository files or a manifest."""

    root_path = Path(root).resolve()
    selected_paths = _selected_manifest_paths(paths, manifest)
    if not selected_paths:
        raise ValueError("At least one file path or manifest entry is required")
    files: list[ContextFile] = []
    for item in selected_paths:
        resolved = _safe_resolve(root_path, item)
        if not resolved.is_file():
            raise ValueError(f"Context file does not exist: {item}")
        content = resolved.read_text(encoding="utf-8", errors="replace")
        context_file = ContextFile(_relative_posix(root_path, resolved), content, "build")
        if max_file_bytes is not None and context_file.size_bytes > max_file_bytes:
            raise ValueError(f"Context file exceeds max_file_bytes ({context_file.size_bytes} > {max_file_bytes}): {item}")
        files.append(context_file)
    if output_format == "json":
        return _render_json_bundle(root_path, files)
    if output_format == "markdown":
        return _render_markdown_bundle(root_path, files)
    raise ValueError(f"Unsupported build output format: {output_format}")


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


def _selected_manifest_paths(paths: list[str], manifest: str | Path | None) -> list[str]:
    selected = []
    if manifest:
        manifest_path = Path(manifest)
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            selected.append(value)
    selected.extend(paths)
    seen = set()
    ordered: list[str] = []
    for item in selected:
        normalized = item.replace("\\", "/").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _safe_resolve(root: Path, item: str) -> Path:
    candidate = (root / item).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Context file is outside root: {item}") from exc
    return candidate


def _relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _render_json_bundle(root: Path, files: list[ContextFile]) -> str:
    payload = {
        "metadata": {
            "generated_by": "prompt-context-gate",
            "root": str(root),
            "file_count": len(files),
        },
        "files": [
            {
                "path": item.path,
                "content": item.content,
            }
            for item in files
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _render_markdown_bundle(root: Path, files: list[ContextFile]) -> str:
    lines = [
        "# Context Bundle",
        "",
        f"Generated by `prompt-context-gate build` from `{root}`.",
        "",
    ]
    for item in files:
        language = _language_for_path(item.path)
        lines.append(f"```{language} path={item.path}")
        lines.append(item.content.rstrip("\n"))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _language_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".json": "json",
        ".md": "md",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".css": "css",
        ".html": "html",
    }.get(suffix, "text")
