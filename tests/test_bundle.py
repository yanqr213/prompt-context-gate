import json
import tempfile
import unittest
from pathlib import Path

from prompt_context_gate.bundle import inspect_bundle, parse_bundle


class BundleParsingTests(unittest.TestCase):
    def test_parse_markdown_fenced_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.md"
            path.write_text("```python src/app.py\nprint('ok')\n```\n\n```md README.md\n# Readme\n```", encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual([file.path for file in bundle.files], ["src/app.py", "README.md"])
        self.assertIn("print", bundle.files[0].content)

    def test_parse_markdown_ignores_plain_fences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.md"
            path.write_text("```\nplain note\n```\n```python src/app.py\nx = 1\n```", encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual([file.path for file in bundle.files], ["src/app.py"])

    def test_parse_markdown_path_equals_fence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.md"
            path.write_text("```python path=tests/test_app.py\nassert True\n```", encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual(bundle.files[0].path, "tests/test_app.py")

    def test_parse_markdown_heading_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.md"
            path.write_text("## file: README.md\n# Hi\n## path: src/app.py\nx = 1\n", encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual([file.path for file in bundle.files], ["README.md", "src/app.py"])

    def test_parse_markdown_raw_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.md"
            path.write_text("# Plain notes", encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual(bundle.files[0].path, "notes.md")
        self.assertEqual(bundle.files[0].source, "raw-markdown")

    def test_parse_json_files_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps({"files": [{"path": "README.md", "content": "# R"}]}), encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual(bundle.files[0].path, "README.md")
        self.assertEqual(bundle.files[0].content, "# R")

    def test_parse_json_files_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps({"files": {"src/app.py": {"value": 1}}}), encoding="utf-8")
            bundle = parse_bundle(path)
        self.assertEqual(bundle.files[0].path, "src/app.py")
        self.assertIn('"value"', bundle.files[0].content)

    def test_inspect_bundle_sorts_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps({"files": {"z.py": "z", "a.py": "a"}}), encoding="utf-8")
            inspection = inspect_bundle(parse_bundle(path))
        self.assertEqual([file["path"] for file in inspection.files], ["a.py", "z.py"])
        self.assertEqual(inspection.file_count, 2)

    def test_unsupported_bundle_format_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.xml"
            path.write_text("<x />", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_bundle(path)


if __name__ == "__main__":
    unittest.main()
