"""Command line interface for prompt-context-gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .bundle import build_bundle, inspect_bundle, parse_bundle
from .checks import run_checks, should_fail
from .report import render_findings, render_inspection
from .rules import load_rules, write_default_rules


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-rules":
            write_default_rules(args.output)
            print(f"Wrote default rules to {args.output}")
            return 0
        if args.command == "inspect":
            bundle = parse_bundle(args.bundle)
            rendered = render_inspection(inspect_bundle(bundle), args.output_format)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
            else:
                print(rendered)
            return 0
        if args.command == "build":
            rendered = build_bundle(
                args.root,
                args.paths,
                manifest=args.manifest,
                output_format=args.output_format,
                max_file_bytes=args.max_file_bytes,
            )
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(rendered, encoding="utf-8")
            else:
                print(rendered, end="")
            return 0
        if args.command == "check":
            bundle = parse_bundle(args.bundle)
            rules = load_rules(args.rules)
            findings = run_checks(bundle, rules)
            rendered = render_findings(findings, args.output_format)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
            else:
                print(rendered)
            return 2 if should_fail(findings, rules) else 0
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"prompt-context-gate: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-context-gate",
        description="Local policy gate for AI coding context bundles.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-rules", help="Write a starter JSON rules file.")
    init_parser.add_argument("-o", "--output", default="context-rules.json", help="Rules file path to create.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect bundle size and included files.")
    inspect_parser.add_argument("bundle", help="Markdown or JSON context bundle.")
    inspect_parser.add_argument("-f", "--output-format", choices=["markdown", "json", "csv"], default="markdown")
    inspect_parser.add_argument("-o", "--output", help="Write inspection report to a file instead of stdout.")

    build_context_parser = subparsers.add_parser("build", help="Build a JSON or Markdown context bundle from repository files.")
    build_context_parser.add_argument("paths", nargs="*", help="File paths under --root to include.")
    build_context_parser.add_argument("--root", default=".", help="Repository root for resolving file paths.")
    build_context_parser.add_argument("--manifest", help="Optional newline-delimited file list. # comments and blank lines are ignored.")
    build_context_parser.add_argument("-f", "--output-format", choices=["json", "markdown"], default="json")
    build_context_parser.add_argument("-o", "--output", help="Write bundle to this path instead of stdout.")
    build_context_parser.add_argument("--max-file-bytes", type=int, help="Refuse to include any single file above this byte limit.")

    check_parser = subparsers.add_parser("check", help="Run policy checks against a context bundle.")
    check_parser.add_argument("bundle", help="Markdown or JSON context bundle.")
    check_parser.add_argument("-r", "--rules", help="JSON or simple YAML rules file. Defaults to built-in rules.")
    check_parser.add_argument("-f", "--output-format", choices=["markdown", "json", "csv", "sarif"], default="markdown")
    check_parser.add_argument("-o", "--output", help="Write report to a file instead of stdout.")

    return parser


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
