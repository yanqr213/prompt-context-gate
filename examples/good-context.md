# Context Bundle

```md README.md
# Example Service

This service exposes a small API and includes test and CI coverage.
```

```python src/app.py
def add(left: int, right: int) -> int:
    return left + right
```

```python tests/test_app.py
from src.app import add


def test_add():
    assert add(1, 2) == 3
```

```yaml .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python -m unittest discover -s tests
```
