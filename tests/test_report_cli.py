import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from prompt_context_gate.cli import main
from prompt_context_gate.models import Finding, Inspection
from prompt_context_gate.report import render_findings, render_inspection


class ReportAndCliTests(unittest.TestCase):
    def test_render_findings_json(self):
        output = render_findings([Finding("error", "rule", "message", "path.py", 3)], "json")
        data = json.loads(output)
        self.assertEqual(data["findings"][0]["line"], 3)

    def test_render_findings_csv(self):
        output = render_findings([Finding("warning", "todo", "message")], "csv")
        self.assertIn("severity,rule,path,line,message,detail", output)
        self.assertIn("warning,todo", output)

    def test_render_findings_sarif(self):
        output = render_findings([Finding("error", "sensitive_patterns", "Sensitive pattern matched.", "src/app.py", 7)], "sarif")
        payload = json.loads(output)

        self.assertEqual(payload["version"], "2.1.0")
        self.assertEqual(payload["runs"][0]["tool"]["driver"]["name"], "prompt-context-gate")
        self.assertEqual(payload["runs"][0]["results"][0]["ruleId"], "sensitive_patterns")
        self.assertEqual(payload["runs"][0]["results"][0]["level"], "error")
        self.assertEqual(
            payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "src/app.py",
        )

    def test_render_findings_markdown_no_findings(self):
        output = render_findings([], "markdown")
        self.assertIn("No findings.", output)

    def test_render_inspection_json(self):
        inspection = Inspection("bundle.md", 10, 10, 3, 1, [{"path": "README.md", "bytes": 3, "lines": 1, "source": "json"}])
        output = render_inspection(inspection, "json")
        self.assertEqual(json.loads(output)["file_count"], 1)

    def test_cli_init_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["init-rules", "-o", str(path)])
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertIn("max_total_bytes", data)

    def test_cli_inspect_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            bundle.write_text(json.dumps({"files": [{"path": "README.md", "content": "# R"}]}), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["inspect", str(bundle), "-f", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["file_count"], 1)

    def test_cli_inspect_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            report = Path(tmp) / "reports" / "inspection.json"
            bundle.write_text(json.dumps({"files": [{"path": "README.md", "content": "# R"}]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["inspect", str(bundle), "-f", "json", "-o", str(report)])
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["file_count"], 1)

    def test_cli_build_json_then_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "README.md").write_text("# R", encoding="utf-8")
            (root / "tests" / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")
            (root / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            manifest = root / "manifest.txt"
            manifest.write_text("README.md\ntests/test_app.py\n.github/workflows/ci.yml\n", encoding="utf-8")
            bundle = root / "context.json"
            with contextlib.redirect_stdout(io.StringIO()):
                build_code = main(["build", "--root", str(root), "--manifest", str(manifest), "-o", str(bundle)])
                check_code = main(["check", str(bundle), "-f", "json"])

        self.assertEqual(build_code, 0)
        self.assertEqual(check_code, 0)

    def test_cli_build_markdown_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# R", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["build", "--root", str(root), "README.md", "-f", "markdown"])

        self.assertEqual(code, 0)
        self.assertIn("path=README.md", stdout.getvalue())

    def test_cli_check_success_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            rules = Path(tmp) / "rules.json"
            bundle.write_text(
                json.dumps(
                    {
                        "files": [
                            {"path": "README.md", "content": "# R"},
                            {"path": "tests/test_app.py", "content": "def test_ok(): pass"},
                            {"path": ".github/workflows/ci.yml", "content": "name: CI"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rules.write_text(json.dumps({"required_paths": ["README.md"], "fail_on": ["error"]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["check", str(bundle), "-r", str(rules), "-f", "json"])
        self.assertEqual(code, 0)

    def test_cli_check_failure_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            rules = Path(tmp) / "rules.json"
            bundle.write_text(json.dumps({"files": [{"path": ".env", "content": "SECRET=abc123abc123abc123"}]}), encoding="utf-8")
            rules.write_text(json.dumps({"forbidden_paths": [".env"], "require_readme": False, "require_tests": False, "require_ci": False}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["check", str(bundle), "-r", str(rules), "-f", "json"])
        self.assertEqual(code, 2)

    def test_cli_check_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            report = Path(tmp) / "report.md"
            bundle.write_text(json.dumps({"files": [{"path": "README.md", "content": "# R"}]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["check", str(bundle), "-f", "markdown", "-o", str(report)])
            text = report.read_text(encoding="utf-8")
        self.assertEqual(code, 2)
        self.assertIn("Prompt Context Gate Report", text)

    def test_cli_check_writes_sarif_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            rules = Path(tmp) / "rules.json"
            report = Path(tmp) / "reports" / "context.sarif"
            bundle.write_text(json.dumps({"files": [{"path": ".env", "content": "SECRET=abc123abc123abc123"}]}), encoding="utf-8")
            rules.write_text(json.dumps({"forbidden_paths": [".env"], "require_readme": False, "require_tests": False, "require_ci": False}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["check", str(bundle), "-r", str(rules), "-f", "sarif", "-o", str(report)])
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(code, 2)
        self.assertEqual(payload["version"], "2.1.0")
        forbidden_result = next(item for item in payload["runs"][0]["results"] if item["ruleId"] == "forbidden_paths")
        self.assertEqual(
            forbidden_result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            ".env",
        )


if __name__ == "__main__":
    unittest.main()
