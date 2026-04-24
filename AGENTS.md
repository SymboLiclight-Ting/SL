# AGENTS.md

## Project Goal

SymbolicLight is a spec-native, AI-friendly application language.

The v0 compiler translates `.sl` applications into readable Python 3.11. The first product proof is a Todo API + CLI app with SQLite storage, JSON HTTP routes, CLI commands, and lightweight tests.

## Communication

- 默认使用简体中文进行解释、进度说明、代码讲解和报错分析。
- 标识符、命令、配置键、API 字段和文件名保持原文。
- 代码注释默认使用英文。

## Current Architecture

- `src/symboliclight/lexer.py` tokenizes `.sl`.
- `src/symboliclight/parser.py` builds the AST.
- `src/symboliclight/checker.py` validates v0 semantics.
- `src/symboliclight/codegen.py` emits single-file Python apps.
- `src/symboliclight/formatter.py` defines the official formatter.
- `src/symboliclight/cli.py` provides `slc check/build/run/test/fmt/doctor/init/new/add`.
- `examples/todo_app.sl` is the smoke-test app.
- `examples/issue_tracker.sl` covers imports, modules, enums, and `Option<T>`.

## v0 Language Scope

Supported:

- `app`
- `module`
- `import`
- `intent`
- `permissions from intent.permissions`
- `test from intent.acceptance`
- `enum`
- `type`
- `store`
- `fn`
- `command`
- `route`
- `test`
- `let`
- `return`
- `assert`
- `if` / `else`
- record and list literals
- field access and function calls
- `Option<T>` and `Result<T, E>` type references

Out of scope:

- frontend UI
- package manager
- macro system
- advanced generics
- package registry or version solver
- custom runtime service
- real LLM or agent runtime

## IntentSpec Relationship

IntentSpec is the upper contract layer. SymbolicLight is the implementation layer.

`.sl` files may declare:

```sl
intent "./todo.intent.yaml"
```

When IntentSpec is installed, `slc check` validates the referenced file. Without IntentSpec, validation is a warning unless `--strict-intent` is used.

## Change Rules

- Keep v0 small and application-focused.
- Do not reintroduce the archived `Draft/Checked/Approved/Authorized` agent-governance model into the mainline.
- Syntax changes must update `docs/spec.md`, `examples/todo_app.sl`, and tests together.
- Trust and boundary changes must update `docs/semantics.md`.
- Compatibility-impacting changes must update `docs/compatibility.md`.
- Codegen behavior changes must include tests that compile and run generated Python.
- Formatter changes must include snapshot-like tests or CLI coverage.
- Generated Python should stay readable and use the standard library where possible.

## Verification

Run:

```bash
pytest
$env:PYTHONPATH='src'; python -m symboliclight.cli check examples/todo_app.sl
$env:PYTHONPATH='src'; python -m symboliclight.cli check examples/issue_tracker.sl
$env:PYTHONPATH='src'; python -m symboliclight.cli build examples/todo_app.sl --out build/todo_app.py
python -m py_compile build/todo_app.py
python build/todo_app.py test
```
