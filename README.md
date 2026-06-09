# prompt-context-gate

`prompt-context-gate` 是一个本地运行的 AI 编程上下文检查工具。它帮助团队在把仓库上下文、系统提示、任务说明交给 Codex、Claude Code、ChatGPT 或其他 AI 编程代理之前，先确认这份 context bundle 是否过大、是否漏掉关键文件、是否带入秘密、是否还有未闭合 TODO/FIXME，以及是否覆盖 README、测试和 CI。

分类：AI / Developer tooling

## 适用场景

- 你准备把一个仓库切片发给 AI 编程代理，但担心 token 预算超限。
- 你希望 CI 在生成或提交 context bundle 时阻止 `.env`、私钥、GitHub token、API key 等敏感内容进入提示词。
- 你需要确保交给 AI 的上下文至少包含 `README.md`、测试文件和 CI 配置，避免模型在缺失项目约束时乱改。
- 你想把团队规则写成 JSON 或简单 YAML，并在本地、pre-commit、CI 或内部脚本中复用。

## 特性

- 纯 Python 标准库运行时，不依赖外部网络。
- 支持 Markdown 和 JSON context bundle。
- 支持从仓库文件和 manifest 生成标准 JSON/Markdown context bundle。
- 支持 JSON 规则文件，也支持一个轻量 YAML 子集。
- 检查总字节预算、估算 token 预算、单文件大小、必需路径、禁止路径、敏感正则、TODO/FIXME、README/测试/CI 覆盖。
- 敏感正则写错时会报告 `invalid_sensitive_pattern`，不会让 `check` 以不透明的输入错误中断。
- 输出 Markdown、JSON、CSV、SARIF。
- SARIF 可上传到 GitHub Code Scanning，把上下文 bundle 的安全/质量问题显示在代码扫描视图里。
- `check` 命令按规则阈值返回退出码，适合 CI gate。

## 安装

从源码仓库安装：

```bash
python -m pip install -e .
```

不安装也可以直接运行：

```bash
PYTHONPATH=src python -m prompt_context_gate.cli --help
```

Windows PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m prompt_context_gate.cli --help
```

## 命令

生成默认规则：

```bash
prompt-context-gate init-rules -o context-rules.json
```

查看 context bundle 概况：

```bash
prompt-context-gate inspect examples/good-context.md -f markdown
prompt-context-gate inspect examples/good-context.md -f json
prompt-context-gate inspect examples/good-context.md -f csv
prompt-context-gate inspect context-bundle.json -f json -o reports/context-inspection.json
```

从仓库文件或 manifest 生成标准 context bundle：

```bash
prompt-context-gate build --root . --manifest examples/manifest.txt -f json -o context-bundle.json
prompt-context-gate build --root . README.md src/prompt_context_gate/cli.py -f markdown -o context-bundle.md
```

执行检查：

```bash
prompt-context-gate check examples/good-context.md -r examples/rules.json -f markdown
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f json
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f csv -o report.csv
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f sarif -o context-gate.sarif
```

退出码：

- `0`：没有命中 `fail_on` 中定义的严重级别。
- `1`：命令或输入错误。
- `2`：检查发现应使 CI 失败的问题。

## Context Bundle 格式

如果你还没有 bundle，推荐用 `build` 从真实仓库文件生成：

```text
# context-manifest.txt
README.md
src/app.py
tests/test_app.py
.github/workflows/ci.yml
```

```bash
prompt-context-gate build --root . --manifest context-manifest.txt -f json -o context-bundle.json
prompt-context-gate check context-bundle.json -r context-rules.json -f markdown
```

manifest 支持空行和 `#` 注释；所有路径都必须位于 `--root` 内，避免意外打包仓库外文件。`--max-file-bytes` 可在打包阶段拒绝过大的单文件。

Markdown 支持带路径的代码块：

````markdown
```python src/app.py
def main():
    return "ok"
```

```md README.md
# Project
```
````

也支持标题形式：

```markdown
## file: src/app.py
def main():
    return "ok"
```

JSON 支持对象或数组，最常见的是：

```json
{
  "files": [
    {
      "path": "README.md",
      "content": "# Project"
    },
    {
      "path": "tests/test_app.py",
      "content": "def test_ok():\n    assert True\n"
    }
  ]
}
```

## 规则格式

推荐使用 JSON：

```json
{
  "max_total_bytes": 200000,
  "max_estimated_tokens": 50000,
  "max_file_bytes": 60000,
  "required_paths": ["README.md", "src/**", "tests/**"],
  "forbidden_paths": [".env", ".env.*", "**/*.pem", "**/*.key", "**/.git/**"],
  "sensitive_patterns": ["(?i)api[_-]?key\\s*[:=]\\s*['\\\"]?[A-Za-z0-9_\\-]{16,}"],
  "todo_patterns": ["TODO", "FIXME"],
  "allow_todos": false,
  "require_readme": true,
  "require_tests": true,
  "require_ci": true,
  "fail_on": ["error"]
}
```

说明：

- `required_paths` 和 `forbidden_paths` 使用 shell-style glob，例如 `src/**`、`**/*.pem`。
- `sensitive_patterns` 是 Python 正则表达式。请使用脱敏样例测试规则。
- 无效的 `sensitive_patterns` 会生成 `invalid_sensitive_pattern` error finding；如果 `fail_on` 包含 `error`，`check` 返回 `2`，方便 CI 直接指出是哪条规则需要修正。
- `max_estimated_tokens` 使用本地近似估算：约 4 个字符计为 1 token。它不是模型 tokenizer，但足够用于稳定 CI 阈值。
- `require_ci` 缺失时默认是 warning；只有当 `fail_on` 包含 `warning` 时才会让 CI 失败。

## 输出格式

Markdown 输出适合人读：

```bash
prompt-context-gate check bundle.md -r context-rules.json -f markdown
```

JSON 输出适合自动化：

```json
{
  "findings": [
    {
      "severity": "error",
      "rule": "forbidden_paths",
      "message": "Forbidden path matched: .env.",
      "path": ".env",
      "line": null,
      "detail": ""
    }
  ]
}
```

CSV 输出适合表格和审计：

```csv
severity,rule,path,line,message,detail
error,forbidden_paths,.env,,Forbidden path matched: .env.,
```

SARIF 输出适合 GitHub Code Scanning 或其他支持 SARIF 2.1.0 的质量/安全平台：

```bash
prompt-context-gate check context-bundle.md -r context-rules.json -f sarif -o context-gate.sarif
```

## CI 用法

GitHub Actions 示例：

```yaml
name: Context Gate
on: [pull_request]
jobs:
  context-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e .
      - run: prompt-context-gate build --root . --manifest context-manifest.txt -f json -o build/context-bundle.json
      - run: prompt-context-gate check build/context-bundle.json -r context-rules.json -f markdown
```

如果命中 `fail_on` 中定义的严重级别，命令会返回 `2`，CI 将失败。

上传 SARIF 到 GitHub Code Scanning：

```yaml
permissions:
  contents: read
  security-events: write

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - run: python -m pip install git+https://github.com/yanqr213/prompt-context-gate.git
  - name: Check context bundle as SARIF
    run: |
      prompt-context-gate check context-bundle.md \
        -r context-rules.json \
        -f sarif \
        -o reports/context-gate.sarif
  - uses: github/codeql-action/upload-sarif@v3
    if: always()
    with:
      sarif_file: reports/context-gate.sarif
```

## 隐私与安全边界

- 本工具只读取你显式传入的 bundle 和规则文件。
- `build` 只读取你通过参数或 manifest 显式列出的仓库内文件。
- 不联网、不上传、不推送 GitHub。
- 不读取或请求 GitHub token、API key 或其他凭据。
- 敏感信息检查依赖规则中的正则表达式，不能保证发现所有秘密。请配合仓库 secret scanning、最小化上下文和人工复核。
- 发现敏感内容时，报告只显示文件、行号和规则，不打印匹配到的秘密值。

## English

`prompt-context-gate` is a local policy gate for AI coding context bundles. It is designed for engineering teams that send repository context, system prompts, and task briefs to Codex, Claude Code, ChatGPT, or similar AI coding agents.

The tool checks whether a bundle is too large, misses critical files, includes forbidden paths, contains secret-like patterns, leaves TODO/FIXME markers unresolved, exceeds per-file limits, or lacks README, test, and CI coverage.

Invalid `sensitive_patterns` are reported as `invalid_sensitive_pattern` error findings instead of aborting the whole check, so CI can point maintainers to the rule that needs repair.

### Install

```bash
python -m pip install -e .
```

You can also run it without installation:

```bash
PYTHONPATH=src python -m prompt_context_gate.cli --help
```

### Commands

```bash
prompt-context-gate init-rules -o context-rules.json
prompt-context-gate build --root . --manifest examples/manifest.txt -f json -o context-bundle.json
prompt-context-gate inspect examples/good-context.md -f json
prompt-context-gate check examples/good-context.md -r examples/rules.json -f markdown
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f sarif -o context-gate.sarif
```

`build` reads explicit file paths or a newline-delimited manifest, refuses paths outside `--root`, and writes a standard JSON or Markdown context bundle. A common workflow is:

```bash
prompt-context-gate build --root . --manifest context-manifest.txt -f json -o context-bundle.json
prompt-context-gate inspect context-bundle.json -f markdown -o reports/context-inspection.md
prompt-context-gate check context-bundle.json -r context-rules.json -f sarif -o reports/context-gate.sarif
```

`check` exits with:

- `0` when no configured failing severity is found.
- `1` for command or input errors.
- `2` when findings match `fail_on`.

### Rule File

Rules may be JSON or a small YAML subset. JSON is recommended for portability.

Key fields:

- `max_total_bytes`: maximum raw bundle size.
- `max_estimated_tokens`: local approximate token budget.
- `max_file_bytes`: maximum size for one included file.
- `required_paths`: glob patterns that must be present.
- `forbidden_paths`: glob patterns that must not be present.
- `sensitive_patterns`: Python regular expressions for secret-like content.
- Invalid `sensitive_patterns` produce `invalid_sensitive_pattern` findings and return exit code `2` when `fail_on` includes `error`.
- `todo_patterns`: markers such as `TODO` and `FIXME`.
- `require_readme`, `require_tests`, `require_ci`: coverage checks.
- `fail_on`: severities that should produce exit code `2`.

### Privacy and Security

This tool runs locally, does not require network access, and only reads files you pass to it. It does not request, print, upload, or push GitHub tokens. Secret detection is rule based and should be used alongside repository secret scanning and human review.

SARIF output can be uploaded with `github/codeql-action/upload-sarif@v3` so context bundle risks appear in GitHub Code Scanning.

## 测试

```bash
python -m unittest discover -s tests
```
