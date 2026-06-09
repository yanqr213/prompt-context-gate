import unittest

from prompt_context_gate.checks import run_checks, should_fail
from prompt_context_gate.models import ContextBundle, ContextFile, RuleSet


def bundle(files, raw="raw"):
    return ContextBundle("memory", raw, [ContextFile(path, content) for path, content in files])


class CheckTests(unittest.TestCase):
    def test_budget_total_bytes(self):
        findings = run_checks(bundle([("README.md", "abc")], raw="abcdef"), RuleSet(max_total_bytes=3, require_tests=False, require_ci=False))
        self.assertIn("max_total_bytes", [finding.rule for finding in findings])

    def test_budget_estimated_tokens(self):
        findings = run_checks(bundle([("README.md", "abc")], raw="a" * 100), RuleSet(max_estimated_tokens=5, require_tests=False, require_ci=False))
        self.assertIn("max_estimated_tokens", [finding.rule for finding in findings])

    def test_required_path_missing(self):
        findings = run_checks(bundle([("README.md", "# R")]), RuleSet(required_paths=["src/**"], require_tests=False, require_ci=False))
        self.assertEqual(findings[0].rule, "required_paths")

    def test_forbidden_path_detected(self):
        findings = run_checks(bundle([(".env", "SECRET=x")]), RuleSet(forbidden_paths=[".env"], require_readme=False, require_tests=False, require_ci=False))
        self.assertIn("forbidden_paths", [finding.rule for finding in findings])

    def test_sensitive_pattern_detected_without_secret_value(self):
        findings = run_checks(
            bundle([("src/app.py", "API_KEY='abc123abc123abc123abc123'")]),
            RuleSet(sensitive_patterns=[r"API_KEY='[A-Za-z0-9]+'"], require_readme=False, require_tests=False, require_ci=False),
        )
        self.assertEqual(findings[0].rule, "sensitive_patterns")
        self.assertNotIn("abc123", findings[0].message)

    def test_invalid_sensitive_pattern_is_reported_as_finding(self):
        findings = run_checks(
            bundle([("src/app.py", "print('ok')")]),
            RuleSet(sensitive_patterns=["(?i)[unterminated"], require_readme=False, require_tests=False, require_ci=False),
        )

        self.assertEqual(findings[0].rule, "invalid_sensitive_pattern")
        self.assertEqual(findings[0].severity, "error")
        self.assertIn("unterminated", findings[0].detail)

    def test_invalid_sensitive_pattern_does_not_skip_valid_patterns(self):
        findings = run_checks(
            bundle([("src/app.py", "API_KEY='abc123abc123abc123abc123'")]),
            RuleSet(
                sensitive_patterns=["(?i)[unterminated", r"API_KEY='[A-Za-z0-9]+'"],
                require_readme=False,
                require_tests=False,
                require_ci=False,
            ),
        )

        self.assertIn("invalid_sensitive_pattern", [finding.rule for finding in findings])
        self.assertIn("sensitive_patterns", [finding.rule for finding in findings])

    def test_todo_detected(self):
        findings = run_checks(bundle([("src/app.py", "# TODO finish")]), RuleSet(require_readme=False, require_tests=False, require_ci=False))
        self.assertIn("todo_patterns", [finding.rule for finding in findings])

    def test_todo_can_be_allowed(self):
        findings = run_checks(bundle([("src/app.py", "# TODO finish")]), RuleSet(allow_todos=True, require_readme=False, require_tests=False, require_ci=False))
        self.assertNotIn("todo_patterns", [finding.rule for finding in findings])

    def test_max_file_bytes(self):
        findings = run_checks(bundle([("src/big.py", "abcdef")]), RuleSet(max_file_bytes=3, require_readme=False, require_tests=False, require_ci=False))
        self.assertIn("max_file_bytes", [finding.rule for finding in findings])

    def test_coverage_readme_tests_ci(self):
        findings = run_checks(bundle([("src/app.py", "x = 1")]), RuleSet())
        rules = [finding.rule for finding in findings]
        self.assertIn("coverage_readme", rules)
        self.assertIn("coverage_tests", rules)
        self.assertIn("coverage_ci", rules)

    def test_coverage_passes_with_expected_files(self):
        findings = run_checks(
            bundle([
                ("README.md", "# R"),
                ("tests/test_app.py", "def test_ok(): pass"),
                (".github/workflows/ci.yml", "name: CI"),
            ]),
            RuleSet(),
        )
        self.assertEqual(findings, [])

    def test_should_fail_only_configured_severity(self):
        findings = run_checks(bundle([("src/app.py", "# TODO")]), RuleSet(require_readme=False, require_tests=False, require_ci=False))
        self.assertFalse(should_fail(findings, RuleSet(fail_on=["error"], require_readme=False, require_tests=False, require_ci=False)))
        self.assertTrue(should_fail(findings, RuleSet(fail_on=["warning"], require_readme=False, require_tests=False, require_ci=False)))


if __name__ == "__main__":
    unittest.main()
