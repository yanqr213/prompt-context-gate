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
- 支持 JSON 规则文件，也支持一个轻量 YAML 子集。
- 检查总字节预算、估算 token 预算、单文件大小、必需路径、禁止路径、敏感正则、TODO/FIXME、README/测试/CI 覆盖。
- 输出 Markdown、JSON、CSV。
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
```

执行检查：

```bash
prompt-context-gate check examples/good-context.md -r examples/rules.json -f markdown
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f json
prompt-context-gate check examples/risky-context.json -r examples/rules.json -f csv -o report.csv
```

退出码：

- `0`：没有命中 `fail_on` 中定义的严重级别。
- `1`：命令或输入错误。
- `2`：检查发现应使 CI 失败的问题。

## Context Bundle 格式

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
      - run: prompt-context-gate check context-bundle.md -r context-rules.json -f markdown
```

如果命中 `fail_on` 中定义的严重级别，命令会返回 `2`，CI 将失败。

## 隐私与安全边界

- 本工具只读取你显式传入的 bundle 和规则文件。
- 不联网、不上传、不推送 GitHub。
- 不读取或请求 GitHub token、API key 或其他凭据。
- 敏感信息检查依赖规则中的正则表达式，不能保证发现所有秘密。请配合仓库 secret scanning、最小化上下文和人工复核。
- 发现敏感内容时，报告只显示文件、行号和规则，不打印匹配到的秘密值。

## English

`prompt-context-gate` is a local policy gate for AI coding context bundles. It is designed for engineering teams that send repository context, system prompts, and task briefs to Codex, Claude Code, ChatGPT, or similar AI coding agents.

The tool checks whether a bundle is too large, misses critical files, includes forbidden paths, contains secret-like patterns, leaves TODO/FIXME markers unresolved, exceeds per-file limits, or lacks README, test, and CI coverage.

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
prompt-context-gate inspect examples/good-context.md -f json
prompt-context-gate check examples/good-context.md -r examples/rules.json -f markdown
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
- `todo_patterns`: markers such as `TODO` and `FIXME`.
- `require_readme`, `require_tests`, `require_ci`: coverage checks.
- `fail_on`: severities that should produce exit code `2`.

### Privacy and Security

This tool runs locally, does not require network access, and only reads files you pass to it. It does not request, print, upload, or push GitHub tokens. Secret detection is rule based and should be used alongside repository secret scanning and human review.

## 测试

```bash
python -m unittest discover -s tests
```
