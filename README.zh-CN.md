# SymbolicLight 中文文档

[English README](README.md)

SymbolicLight Language，简称 SL，是一门 spec-native、AI-friendly 的应用开发语言，用于用更少的胶水代码构建带类型的 CLI 和后端应用。

它面向希望代码更容易被人类和 AI 工具生成、审查、测试与维护的开发者。SL v1.0 聚焦显式的数据模型、存储、HTTP 路由、CLI 命令、测试，以及和任务规格的对齐。

SymbolicLight 不试图取代 Python、Rust 或 TypeScript。它的第一目标更窄：

> 用一个紧凑的源文件表达应用意图、数据模型、存储、路由、命令和测试。

SL 会编译为可读的 Python 3.11，因此生成的应用可以运行在现有 Python 生态之上。

## 命名约定

- 正式项目名和品牌名：SymbolicLight。
- 面向开发者的语言名：SL。
- 编译器命令：`slc`。
- 源文件扩展名：`.sl`。

在项目、网站、发布和定位文案中使用 SymbolicLight。在开发者文档、示例、教程和日常语言引用中使用 SL。

## 当前稳定基线

SL v1.0 支持：

- `app` 声明。
- `module` 声明和显式 `import "./file.sl" as name`。
- `intent "./file.intent.yaml"` 关联 IntentSpec 契约。
- `permissions from intent.permissions` 和 `test from intent.acceptance` 声明。
- `enum` 声明和 `type` record 声明。
- app 和 module 内的纯 `fn` 声明。
- `Option<T>` 和 `Result<T, E>` 类型引用。
- 基于 SQLite 或可选 Postgres 的 `store` 声明。
- 编译为 CLI 子命令的 `command` handler。
- 编译为 JSON HTTP 路由的 `route GET/POST/PUT/PATCH/DELETE` handler。
- typed route body 和 `Response<T>` status response。
- `fixture` 声明和 golden tests。
- typed `config` 声明。
- SQLite helper，例如 `count`、`exists` 和仅测试使用的 `clear`。
- 通过 `slc schema` 生成 JSON schema。
- 编译为轻量 Python assertions 的 `test` block。
- 通过 `slc fmt` 进行官方格式化。
- source-map sidecar 和 best-effort `.sl` runtime backreference。
- 增量 `slc check` cache 复用。
- 通过 `slc check --json` 输出 JSON diagnostics。
- 通过 `slc doctor --json` 输出机器可读 doctor 报告。
- 通过 `slc migrate plan` 输出只读 migration plan。
- 通过 `slc lsp` 提供本地 LSP 支持。
- `editors/vscode` 下的本地 VS Code 语法、snippets 和 language-server wiring。
- `playground/` 下的本地 playground。
- IntentSpec-aware `slc doctor` route、command 和 permission alignment hints。
- 对声明了 `test from intent.acceptance` 的 app，通过 `slc test` 运行 IntentSpec acceptance checks。
- 通过最小 `request.header(...)` helper 进行 route auth checks。
- 通过 `slc doctor --db` 进行 schema drift inspection。
- 通过 `symboliclight[postgres]` 提供可选 Postgres runtime 支持。
- 常见 `//` comment 位置的 comment-preserving formatting。
- 通过 `scripts/release_check.py` 进行可重复 release smoke checks。
- 通过 `slc new api --template` 生成 starter API templates。
- docs、VS Code 和 release notes maintenance checks。

## 快速开始

从本地 checkout 安装开发版本：

```bash
pip install -e ".[dev]"
```

构建本地 v1.0 package 后，可以直接安装 wheel：

```bash
python -m build
pip install dist/symboliclight-1.0.0-py3-none-any.whl
slc check examples/todo_app.sl
slc check examples/todo_app.sl --json
slc build examples/todo_app.sl --out build/todo_app.py
slc schema examples/notes_api.sl --out build/notes_schema.json
slc fmt examples/todo_app.sl --check
slc doctor examples/todo_app.sl
slc doctor examples/todo_app.sl --json
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite
slc doctor examples/gallery/small-admin-backend/app.sl --db build/admin.sqlite --json
slc migrate plan examples/gallery/project-ops-api/app.sl --db build/project_ops.sqlite
slc check examples/gallery/project-ops-api/app_postgres.sl
slc new api my-api --template todo --backend sqlite
slc new api ops-api --template project-ops --backend postgres
slc lsp
python build/todo_app.py test
python build/todo_app.py add "Buy milk"
python build/todo_app.py list
python build/todo_app.py serve
```

SQLite 生成应用只使用 Python 标准库：`argparse`、`sqlite3`、`http.server` 和 `json`。Postgres 生成应用需要安装 `symboliclight[postgres]`。

## 10 分钟试用路径

```bash
slc check examples/todo_app.sl
slc build examples/todo_app.sl --out build/todo_app.py
python build/todo_app.py test
python build/todo_app.py add "Buy milk"
slc new api my-api --template todo --backend sqlite
slc check my-api/src/app.sl
```

如果想按教程写第一个 app，可以阅读 [Build a Todo App](docs/site/tutorial.md)。如果想快速看语法概览，可以阅读 [Language Tour](docs/site/language-tour.md)。

## 示例

```sl
app TodoApp {
  intent "./todo.intent.yaml"

  type Todo = {
    id: Id<Todo>,
    title: Text,
    done: Bool,
  }

  store todos: Todo

  command add(title: Text) -> Todo {
    return todos.insert({ title: title, done: false })
  }

  route GET "/todos" -> List<Todo> {
    return todos.all()
  }
}
```

typed request body 和 status response：

```sl
route POST "/notes" body CreateNote -> Response<Note> {
  let note = notes.insert({ title: request.body.title, body: request.body.body })
  return response(status: 201, body: note)
}
```

多文件 app 使用显式 import：

```sl
module models {
  enum Status { open, closed }

  type Issue = {
    id: Id<Issue>,
    title: Text,
    status: Status,
    assignee: Option<Text>,
  }

  fn is_open(status: Status) -> Bool {
    return status == Status.open
  }
}
```

```sl
app IssueTracker {
  import "./models.sl" as models

  store issues: models.Issue

  command create(title: Text) -> models.Issue {
    return issues.insert({ title: title, status: models.Status.open })
  }

  route GET "/open" -> Bool {
    return models.is_open(models.Status.open)
  }
}
```

## 与 IntentSpec 的关系

IntentSpec 描述任务意图、权限、输出契约和验收测试。

SymbolicLight 实现应用。

二者关系是：

```text
IntentSpec = 要构建什么，以及如何验收
SymbolicLight = 应用实现
```

普通 `slc check` 中，IntentSpec 校验是可选的。如果安装了 `intentspec` package，SL 会校验被引用的 intent 文件。缺少 IntentSpec 支持时会报告 warning，除非启用 `--strict-intent`。

当 app 声明 `test from intent.acceptance` 时，`slc test` 会在生成应用自身测试通过后运行 v0.6 offline acceptance bridge。它会检查 SL route 和 command hints、permission mismatches，以及 IntentSpec output contract 中的 `required_sections` assertions。

## 常用命令

```bash
slc check <file.sl>
slc check <file.sl> --json
slc check <file.sl> --no-cache
slc build <file.sl> --out build/app.py
slc build <file.sl> --out build/app.py --no-source-map
slc schema <file.sl> --out build/schema.json
slc run <file.sl> -- add "Buy milk"
slc test <file.sl>
slc fmt <file.sl>
slc doctor <file.sl>
slc doctor <file.sl> --json
slc doctor <file.sl> --db path/to/app.sqlite
slc doctor <file.sl> --db path/to/app.sqlite --json
slc migrate plan <file.sl> --db path-or-url
slc new api <name> --template todo --backend sqlite
slc new api <name> --template project-ops --backend postgres
slc lsp
slc init <dir>
slc new api <name>
slc add route GET /items <file.sl>
```

## Release Check

```bash
python scripts/release_check.py --skip-package
python scripts/docs_check.py
python scripts/vscode_check.py
python scripts/freeze_check.py
python scripts/example_matrix.py
python -m build
python scripts/package_smoke.py --gallery
python scripts/release_notes.py --from v0.13.0-rc2 --to HEAD --out build/release-notes-v1.0.0.md
python scripts/release_check.py
```

对本地 `v1.0.0` 基线，应在 clean worktree 上运行完整 release check。该检查会构建本地 wheel，把它安装到临时环境中，用 installed `slc` 跑 gallery，执行一个 `doctor --db` fixture，验证存储的 schema hash 匹配但 SQLite 结构缺少列的情况，运行 migration-plan smoke checks，并回归 prior v0.x examples 的 compatibility fixtures。以上命令不会执行 GitHub、TestPyPI 或 PyPI 上传。

## 项目状态

这个仓库已经准备为本地 v1.0 stable baseline。项目目标是让 typed backend 和 CLI app 保持紧凑、可测试、AI-friendly，同时仍然生成可读、可运行的 Python。公开再分发需要项目 owner 在审查本地 release artifacts 后另行决定。
