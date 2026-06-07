import json
import tempfile
import unittest
from pathlib import Path

from prompt_context_gate.rules import load_rules, parse_simple_yaml, write_default_rules


class RuleTests(unittest.TestCase):
    def test_load_default_rules(self):
        rules = load_rules(None)
        self.assertTrue(rules.require_readme)
        self.assertIn("TODO", rules.todo_patterns)

    def test_load_json_rules_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"max_total_bytes": 10, "allow_todos": True}), encoding="utf-8")
            rules = load_rules(path)
        self.assertEqual(rules.max_total_bytes, 10)
        self.assertTrue(rules.allow_todos)
        self.assertTrue(rules.require_tests)

    def test_parse_simple_yaml_lists_and_scalars(self):
        data = parse_simple_yaml(
            """
max_total_bytes: 42
allow_todos: true
required_paths:
  - README.md
  - tests/**
"""
        )
        self.assertEqual(data["max_total_bytes"], 42)
        self.assertTrue(data["allow_todos"])
        self.assertEqual(data["required_paths"], ["README.md", "tests/**"])

    def test_load_yaml_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.yml"
            path.write_text("fail_on:\n  - error\n  - warning\nrequire_ci: false\n", encoding="utf-8")
            rules = load_rules(path)
        self.assertEqual(rules.fail_on, ["error", "warning"])
        self.assertFalse(rules.require_ci)

    def test_write_default_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            write_default_rules(path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("sensitive_patterns", data)
        self.assertIn("forbidden_paths", data)


if __name__ == "__main__":
    unittest.main()
