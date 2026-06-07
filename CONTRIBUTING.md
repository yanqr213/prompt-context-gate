# Contributing

Thanks for helping improve `prompt-context-gate`.

## Local Setup

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests
```

The project intentionally uses only the Python standard library at runtime. Please avoid adding dependencies unless there is a strong reason and the README explains the tradeoff.

## Pull Request Checklist

- Add or update tests for behavior changes.
- Keep CLI output stable for JSON and CSV consumers.
- Do not commit secrets, real customer context bundles, API keys, or tokens.
- Prefer small rules that explain risk clearly.
- Update `CHANGELOG.md` for user-visible changes.

## Security Reports

Please do not open public issues containing live secrets or private repository content. Open a minimal report with redacted examples and enough detail to reproduce the behavior locally.
