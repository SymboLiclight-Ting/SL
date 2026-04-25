# SymbolicLight 全生命周期开发规划

本文档描述 SymbolicLight 从 0% 到 100% 成熟度的开发路线，并标注当前项目所处位置。

SymbolicLight 是正式项目名。开发者入口统一使用 SL、`slc`、`.sl`。

## 当前进度快照

截至当前仓库状态：

- 当前版本状态：`v0.9.0-rc1` 本地发布候选，另有 post-RC review polish 提交。
- 当前实现基线：`12b1aeb Polish v0.9 review diagnostics`，本规划文档更新提交位于其后。
- 当前 tag：`v0.9.0-rc1`，仍指向 `3e9c196 Implement v0.9 DX stabilization`，未移动。
- 当前工作树：干净。
- 发布状态：已完成本地 release check 和 post-RC review 收口，未上传 TestPyPI 或 PyPI。
- 下一 release 动作：如果继续发布候选，应从当前 HEAD 打 `v0.9.0-rc2`，不要移动已有 `v0.9.0-rc1`。

按“成熟语言 100%”口径估算：

```text
当前整体成熟度：约 50%
当前公开试用准备度：约 88%
当前 v0.9 release candidate 完成度：约 100%
```

这三个数字代表不同层级：

- 整体成熟度看的是能否成为稳定、可长期使用、生态完整的应用开发语言。
- 公开试用准备度看的是外部开发者能否安装、跑示例、理解定位、提交反馈。
- v0.9 release candidate 完成度看的是当前阶段目标是否完成。

## 100% 成熟定义

SymbolicLight 达到 100% 成熟度时，应满足以下条件：

- 语言核心稳定，语法和语义进入 v1.0 兼容期。
- `slc` 工具链稳定，错误信息清晰，生成代码可读、可调试、可回指 `.sl`。
- 标准应用能力可用，覆盖 CLI、HTTP、SQLite、Postgres、JSON、config、test、file、time、uuid。
- IntentSpec 集成稳定，能把需求、权限、验收和实现对齐。
- IDE 体验可用，VS Code 插件、LSP、formatter、hover、definition、diagnostics、symbols 稳定。
- 至少 8 到 10 个真实样板应用证明 SL 的表达力和维护性。
- 有清晰文档站、教程、迁移指南、release 流程和安全发布策略。
- 有包分发方案，至少支持 PyPI 安装，后续可考虑独立二进制分发。
- 有兼容性测试套件，历史示例、旧语法迁移和生成代码行为都能回归。
- 社区贡献路径清晰，包括 issue 模板、贡献指南、代码规范和路线图。

## 进度总览

| 成熟度 | 阶段 | 状态 | 核心目标 |
| --- | --- | --- | --- |
| 0% 到 5% | 项目定位 | 已完成 | 从 agent 治理语言转向 spec-native application language |
| 5% 到 12% | 编译器骨架 | 已完成 | Python 实现 `slc`，能 parse/check/build |
| 12% 到 20% | Todo MVP | 已完成 | `.sl` 编译 Todo API + CLI 到 Python |
| 20% 到 30% | v0.2 Core Freeze | 已完成 | module、enum、Option、Result、formatter、compat docs |
| 30% 到 36% | v0.3 Reliable Compiler | 已完成 | parser recovery、strict checker、source map、cache、CLI polish |
| 36% 到 40% | v0.4 Standard App Kit | 已完成 | typed route body、Response、fixtures、schema、config、stdlib thin wrappers |
| 40% 到 42% | v0.5 到 v0.8 Public Preview Hardening | 已完成 | LSP、gallery、IntentSpec、small-admin、schema diff、release RC |
| 42% 到 50% | v0.9 DX Stabilization | 当前完成 | comment-preserving formatter、LSP polish、compat fixtures、doctor JSON |
| 50% 到 60% | v0.10 Production App Kit | 下一阶段 | Postgres、migration plan、auth helpers、larger real apps |
| 60% 到 70% | v0.11 Ecosystem Preview | 未开始 | docs site、plugin examples、package story、template gallery |
| 70% 到 80% | v0.12 Beta | 未开始 | compatibility suite、security review、cross-platform install |
| 80% 到 90% | v0.13 Release Candidate | 未开始 | syntax freeze candidate、API freeze candidate、migration guides |
| 90% 到 100% | v1.0 Stable | 未开始 | compatibility guarantee、stable docs、public release |

## 0% 到 5%：项目定位

状态：已完成。

目标：

- 明确 SymbolicLight 不是 Python、Rust、TypeScript 的通用替代品。
- 明确 SL 是 spec-native、AI-friendly 的应用开发语言。
- 明确 IntentSpec 是上层需求和验收契约，SL 是下层实现语言。
- 明确 v0 目标是 CLI 和后端应用，而不是前端 UI、宏系统、复杂泛型或 agent runtime。

已完成：

- 项目方向从早期 agent governance 模型转为应用语言。
- `Draft/Checked/Approved/Authorized` 设计移入历史语境，不作为主线 v0 语义。
- 命名统一为 SymbolicLight、SL、`slc`、`.sl`。

验收标准：

- README 能在一分钟内解释项目定位。
- 新开发者不会误以为 SL 是通用语言或 agent runtime。
- 示例优先展示真实应用，而不是语言炫技。

## 5% 到 12%：编译器骨架

状态：已完成。

目标：

- 建立 Python package 项目结构。
- 实现 lexer、parser、AST、checker、codegen、CLI。
- 以 Python 3.11 标准库为唯一生成目标。

已完成：

- `src/symboliclight/lexer.py`
- `src/symboliclight/parser.py`
- `src/symboliclight/ast.py`
- `src/symboliclight/checker.py`
- `src/symboliclight/codegen.py`
- `src/symboliclight/cli.py`
- `pyproject.toml` 和 `slc` console script。

验收标准：

- `slc check <file.sl>` 可运行。
- `slc build <file.sl> --out build/app.py` 可生成 Python。
- 生成 Python 可 `py_compile`。

## 12% 到 20%：Todo MVP

状态：已完成。

目标：

- 用 `.sl` 写一个真实可运行的 Todo API + CLI。
- 证明 SL 的基本价值：更少样板、更结构化、更适合 AI 修改。

已完成：

- `examples/todo_app.sl`
- `type`
- `store`
- `command`
- `route`
- `test`
- SQLite-backed store。
- JSON HTTP response。
- CLI subcommand。

验收标准：

- `slc check examples/todo_app.sl` 成功。
- `slc build examples/todo_app.sl --out build/todo_app.py` 成功。
- `python -m py_compile build/todo_app.py` 成功。
- `python build/todo_app.py test` 成功。
- 生成 app 可执行 `add`、`list`、`serve`。

## 20% 到 30%：v0.2 Core Freeze Candidate

状态：已完成。

目标：

- 稳住 v0 核心语义，避免语言方向漂移。
- 明确模块、类型、函数边界、formatter 和兼容策略。

已完成：

- `module`
- `import "./file.sl" as alias`
- `enum`
- `Option<T>`
- `Result<T, E>`
- `List<T>`
- `Id<T>`
- 纯 `fn` 边界检查。
- `command`、`route`、`store` 的职责边界。
- `slc fmt`
- `docs/compatibility.md`
- Todo 和 Issue Tracker 示例。

关键修复：

- HTTP `PUT`、`PATCH`、`DELETE` route 生成 handler。
- nested module import codegen。
- formatter 遇到 `//` comment 时拒绝重写，避免删除用户意图。

验收标准：

- v0.2 示例全量通过 check/build/test。
- checker 能阻止明显的边界误用。
- formatter 不会静默损坏注释。

## 30% 到 36%：v0.3 Reliable Compiler

状态：已完成。

目标：

- 把 `slc` 从“能生成”提升到“可靠工具链”。
- 提升 parser、checker、diagnostics、source map、cache。

已完成：

- `ParseResult`
- `CheckResult`
- 多语法错误恢复。
- 更严格的 import alias、qualified reference、named args 检查。
- record literal、enum、Option、Result 检查。
- source map sidecar。
- generated runtime 的 `.sl` backreference。
- incremental check cache。
- `slc check --json`
- `slc check --no-cache`
- `slc build --no-source-map`

验收标准：

- 一个文件多个语法错误能一次输出多个 diagnostics。
- semantic diagnostics 带 code、location、suggestion。
- Python traceback 可辅助定位到 `.sl`。
- cache 对 import 变化会失效。

## 36% 到 40%：v0.4 Standard App Kit

状态：已完成。

目标：

- 补齐后端和 CLI 应用闭环。
- 不扩大语言野心，只增加应用开发必须能力。

已完成：

- typed route body。
- `Response<T>`。
- `response(status, body, headers)`。
- store helpers：`count`、`exists`、test-only `clear`。
- `slc schema`。
- `fixture`。
- golden test。
- typed `config`。
- `env`、`env_int`。
- thin builtins：`uuid`、`now`、`read_text`、`write_text`。
- Notes API 示例。

验收标准：

- typed request body 能生成 HTTP JSON 解析逻辑。
- malformed JSON 返回 `400`。
- schema JSON deterministic。
- fixtures 在 test 中隔离加载。
- config 从环境变量读取。

## 40% 到 42%：v0.5 到 v0.8 Public Preview Hardening

状态：已完成到 `v0.8.0-rc1`，并被 v0.9 兼容 fixtures 覆盖。

这一段是当前项目的实际落点。它不是成熟语言的终点，而是一个可公开试用的本地发布候选。

### v0.5 Public Developer Preview

已完成：

- VS Code 语法包。
- `slc lsp`。
- diagnostics、hover、definition、document symbols、formatting。
- `slc init`
- `slc new api`
- `slc add route`
- example gallery。
- local playground。

关键修复：

- playground 对 `module` 输入返回 diagnostics，不崩溃。
- LSP `file://` URI 跨平台处理。
- hover 按当前 route 推断 `request.body.field`。
- checker 拒绝 Python keyword 生成非法 Python。
- checker 拒绝用户 command 与内置 `serve`、`test` 冲突。

### v0.6 IntentSpec And Release Hardening

已完成：

- IntentSpec-aware `slc doctor`。
- route、command alignment。
- permissions from `intent.permissions`。
- `test from intent.acceptance`。
- offline acceptance bridge。
- `scripts/release_check.py`。
- wheel install smoke。
- Customer Brief Generator 示例。

关键修复：

- route handler name 使用安全生成规则。
- duplicate route 检查。
- SQLite identifier quote。
- formatter string escaping。

### v0.7 Real App Validation

已完成：

- Small Admin Backend 示例。
- `request.header(name: Text) -> Option<Text>`。
- explicit auth helper pattern。
- `doctor --db` read-only drift inspection。
- 多 store、多 route、多 command 压测。

关键修复：

- generated runtime 在 schema drift 时不覆盖旧 hash。
- Response 内 record literal 目标类型校验。
- Id ergonomics 诊断和 store id 输入校验。

### v0.8 Ecosystem Hardening

已完成：

- summary schema diff。
- `try_update(id, record) -> Option<T>`。
- `response_ok`。
- `response_err`。
- `ErrorBody` 推荐模式。
- 自定义 error record 名称支持。
- `doctor --db` 即使 hash 匹配也检查真实结构。
- imported store record type 可参与 schema diff。
- release-facing wording polish。
- `doctor_drift_smoke.py`。
- `v0.8.0-rc1` 本地 tag。
- fresh tag checkout release 演练。

验收标准：

- `python scripts/release_check.py` 通过。
- fresh tag checkout 通过 release check。
- 本地 wheel 安装后 installed `slc` 可跑 gallery。
- 不上传 TestPyPI/PyPI。

## 42% 到 50%：v0.9 DX Stabilization

状态：当前已完成到 `v0.9.0-rc1`，并有 post-RC review polish 提交。

核心目标：

- 不继续扩语法。
- 把开发者体验和兼容性做扎实。
- 让外部开发者第一次试用时不容易踩坑。

已完成：

- comment-preserving formatter，覆盖文件头注释、item 前注释、statement 前注释和 trailing comment。
- formatter 幂等测试和含注释格式化回归。
- LSP hover 扩展到 type、enum variant、store helper、function、command、config field、route body field。
- LSP definition 扩展到本文件和 imported module 中的 type、enum、fn、store、command、route。
- LSP document symbols 覆盖 app、module、type、enum、config、store、fixture、fn、command、route、test。
- LSP formatting 复用 comment-preserving formatter。
- `slc fmt` 不再因为 `//` comment 拒绝整个文件。
- `slc doctor --json`，供 AI 工具、CI 和 editor tooling 消费。
- `doctor --json` 稳定输出 `source`、`unit`、`diagnostics`、`summary`、`intent`、`schema`、`cache`、`source_map`。
- `schema.drift` 稳定枚举：`not_checked`、`not_initialized`、`up_to_date`、`structural_drift`、`hash_drift`、`unable_to_inspect`。
- v0.6、v0.7、v0.8 compatibility fixtures。
- `docs/site/` Markdown 文档站骨架。
- `pyproject.toml` 升级到 `0.9.0rc1`。
- 本地 tag `v0.9.0-rc1`。
- post-RC review polish，移除 release-facing 诊断中的旧版本字样。

已验证：

- `pytest -q`。
- `python -m compileall -q src playground scripts`。
- `python scripts\release_check.py`。
- fresh tag checkout release 演练。
- 本地 wheel install smoke。

推迟到后续：

- `slc explain <diagnostic-code>`。
- `slc examples list`。
- `slc examples copy <name> <dir>`。
- VS Code extension 打包脚本和 marketplace 发布。
- Playground 示例选择。
- hosted documentation publishing。

明确不做：

- 不做 Postgres。
- 不做 auth middleware。
- 不做自动 migration。
- 不做宏。
- 不做复杂泛型。

验收标准：

- 带注释 `.sl` 文件可安全格式化并保留注释。
- VS Code 打开 gallery 示例时 diagnostics、hover、definition 可用。
- `doctor --json` 输出稳定 schema。
- v0.6、v0.7、v0.8 示例仍可 check/build/test。
- post-RC review 中的 schema drift、imported store type、`response_err` 自定义 error record、runtime drift metadata 覆盖风险已复核。

完成后成熟度估计：

```text
整体成熟度：约 50%
公开试用准备度：约 88%
```

发布状态：

- `v0.9.0-rc1` 已存在，不应移动。
- 当前 HEAD 在 `v0.9.0-rc1` 之后包含 `12b1aeb Polish v0.9 review diagnostics`。
- 如果要继续 release candidate，应打 `v0.9.0-rc2`，并从该 tag 重新跑 fresh release 演练。

## 50% 到 60%：v0.10 Production App Kit

状态：未开始。

核心目标：

- 让 SL 能写更接近生产的后端小应用。
- 保持标准库克制，不做大而全框架。

必须做：

- Postgres first-class backend，SQLite 继续保留。
- DB URL typed config。
- migration plan 输出。
- migration diff 更细粒度。
- generated SQL preview。
- transaction helper。
- pagination pattern。
- typed query parameters。
- route status helper。
- structured error response pattern。
- request query helper。
- request path helper，前提是明确 path param 语义。

建议做：

- password hashing wrapper，但不实现完整 auth 系统。
- API token helper，但不做 session middleware。
- OpenAPI export，优先从 `slc schema` 扩展。
- `slc doctor --ci`。

明确不做：

- 不自动执行破坏性 migration。
- 不做 ORM 式复杂 query builder。
- 不做完整用户登录系统。
- 不做前端框架。

验收标准：

- 一个中等复杂 admin API 可用 SL 编写。
- Postgres 示例可 check/build/test。
- migration plan 对新增表、新增列、删除列、类型变化有稳定输出。
- generated Python 仍可读。

完成后成熟度估计：

```text
整体成熟度：约 60%
公开试用准备度：约 90%
```

## 60% 到 70%：v0.11 Ecosystem Preview

状态：未开始。

核心目标：

- 让项目看起来像可以被外部开发者认真试用的生态。
- 建立可重复的安装、学习、贡献和模板路径。

必须做：

- 文档站。
- Quick Start tutorial。
- Language Tour。
- App Kit Guide。
- IntentSpec Integration Guide。
- Migration And Database Guide。
- Error Handling Guide。
- AI-assisted Development Guide。
- Gallery 文档化。
- VS Code extension 本地打包。
- GitHub issue templates。
- CONTRIBUTING.md。
- SECURITY.md。

建议做：

- `slc new` 模板更多样。
- `slc doctor` CI 示例。
- GitHub Actions 示例。
- release notes 自动生成脚本。
- docs search。

明确不做：

- 不承诺 v1.0 兼容。
- 不开放包管理器。
- 不做 registry。

验收标准：

- 新用户能在 10 分钟内安装、运行 Todo、修改 route、跑 test。
- 外部贡献者能按 CONTRIBUTING.md 跑完整测试。
- 文档和实现不冲突。

完成后成熟度估计：

```text
整体成熟度：约 70%
公开试用准备度：约 94%
```

## 70% 到 80%：v0.12 Beta

状态：未开始。

核心目标：

- 准备进入稳定前的 beta 阶段。
- 开始严肃处理兼容性、跨平台、安装和安全边界。

必须做：

- compatibility suite。
- migration fixtures。
- Windows、macOS、Linux CI。
- Python 3.11 和 3.12 验证。
- package install smoke。
- generated Python security review。
- path/file builtins 安全边界。
- HTTP body size 限制。
- JSON parsing failure consistency。
- SQLite/Postgres error mapping。
- CLI exit code 稳定。

建议做：

- signed release artifacts。
- SBOM。
- dependency audit。
- benchmark suite。
- generated Python formatting consistency。

明确不做：

- 不引入 JIT。
- 不做 native compiler。
- 不做 runtime service。

验收标准：

- 每次 release 都能在三平台通过。
- 所有 gallery 和 compatibility fixtures 通过。
- 安装包可以在干净环境中稳定使用。
- security review 没有 P0/P1 未解决项。

完成后成熟度估计：

```text
整体成熟度：约 80%
公开试用准备度：约 96%
```

## 80% 到 90%：v0.13 Release Candidate

状态：未开始。

核心目标：

- 冻结 v1.0 候选语法。
- 冻结核心 CLI 行为。
- 冻结核心标准库 API。

必须做：

- syntax freeze candidate。
- checker rule freeze candidate。
- standard library core freeze candidate。
- generated Python contract freeze candidate。
- diagnostics code freeze candidate。
- docs freeze candidate。
- migration guide from v0.8 到 v0.13。
- deprecation policy。
- release branch strategy。

建议做：

- `slc fix` 迁移辅助。
- deprecation warnings。
- language server performance pass。
- formatter idempotency proof tests。

明确不做：

- 不再做大语法变化。
- 不再引入会破坏 v1.0 的实验特性。

验收标准：

- 真实项目升级路径清晰。
- 旧示例迁移成本可接受。
- 所有 diagnostics code 有文档。
- formatter 连续运行结果一致。

完成后成熟度估计：

```text
整体成熟度：约 90%
公开试用准备度：约 98%
```

## 90% 到 100%：v1.0 Stable

状态：未开始。

核心目标：

- 发布稳定语言。
- 建立明确兼容承诺。
- 允许外部团队基于 SL 做长期项目。

必须做：

- v1.0 spec。
- v1.0 semantics。
- v1.0 compatibility policy。
- stable CLI contract。
- stable diagnostics schema。
- stable formatter。
- stable generated Python contract。
- stable app kit core。
- complete install docs。
- complete tutorial docs。
- complete migration docs。
- release artifacts。
- public announcement package。

v1.0 兼容承诺：

- v1.x 不破坏已标记 stable 的语法。
- v1.x 不破坏 stable CLI exit code 和 JSON schema。
- v1.x 不破坏 stable generated Python runtime contract。
- 实验特性必须明确标记。
- 废弃周期必须有 warning 和迁移指南。

验收标准：

- 至少 8 到 10 个真实样板应用通过 release check。
- 至少 2 个非 Todo 的较完整应用被反复维护过。
- 文档覆盖安装、语法、标准库、IntentSpec、数据库、测试、发布。
- CI 覆盖三平台。
- 开发者能从零安装并在 30 分钟内写出一个小 API。
- 项目可以公开开源并接受外部 issue。

完成后成熟度估计：

```text
整体成熟度：100%
公开试用准备度：100%
```

## 当前剩余风险清单

这些不是当前阻塞项，但会影响成熟度。

### 语言层风险

- `Option<T>` 和 `Result<T, E>` 还缺少更舒适的解包和控制流。
- `Id<T>` ergonomics 已改善，但复杂 API 参数仍可能显得笨。
- record literal 目标类型校验已经增强，但需要更多嵌套结构测试。
- path params、query params 尚未形成完整语义。

### 工具链风险

- formatter 已支持常见 `//` comment 保留，但还不是完整 trivia engine，复杂嵌套注释布局仍需更多 fixture。
- LSP 仍是 preview，复杂项目性能、增量分析和语义能力不足。
- source map 是 best-effort，不是完整调试器级映射。
- cache 机制需要更多跨平台和大项目验证。

### 应用框架风险

- SQLite 已可用，但 Postgres 尚未开始。
- migration 只检查和提示，不会生成完整可执行迁移方案。
- auth 只有显式 header helper，没有 middleware、session、password hashing。
- HTTP runtime 基于 Python stdlib，适合原型和小应用，不适合高性能生产服务。

### 生态风险

- 还没有正式包发布。
- 只有 Markdown 文档站骨架，还没有 hosted docs。
- VS Code extension 未发布 marketplace。
- 还没有外部用户反馈。
- 还没有真实长期项目验证。

## 下一步推荐

最推荐的下一阶段是 v0.10 Production App Kit，但在进入 v0.10 前应先决定是否打 `v0.9.0-rc2`。

优先级：

1. 如需发布候选，从当前 HEAD 打 `v0.9.0-rc2`，重新执行 fresh tag release 演练。
2. v0.10 开始前，冻结 v0.9 的 compatibility fixtures，作为后续回归基线。
3. 设计 migration plan 输出，不自动改数据库。
4. 设计 Postgres 最小集成边界，避免把 SL 变成大而全 ORM。
5. 基于 gallery 反馈梳理 route、command、store ergonomics 的高频痛点。

v0.10 的成功标准：

- 至少一个更接近生产的后端样板使用 typed config、DB、auth helper、schema doctor 和 tests。
- Postgres 或 migration plan 至少完成一个，不同时硬上两个高风险方向。
- v0.6 到 v0.9 compatibility fixtures 继续通过。
- `slc doctor` 和 release check 能覆盖新生产能力的失败路径。
- 文档明确告诉用户哪些能力可试用，哪些仍是实验性能力。
