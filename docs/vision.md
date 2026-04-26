# Vision

SymbolicLight is a spec-native, AI-friendly application language for building typed CLI and backend apps with less glue code.

The language is built around one observation: AI can write code quickly, but real projects still need clear application structure, stable interfaces, tests, and readable generated artifacts.

## Naming

SymbolicLight is the formal project and brand name. SL is the developer-facing language name used in examples, tutorials, and everyday references.

The compiler is `slc`, and source files use the `.sl` extension.

SL should make application code:

- easier for humans to review,
- easier for AI tools to generate and repair,
- easier to connect to task specifications,
- easier to test from the start.

## Positioning

SymbolicLight is not an AI agent runtime and not a governance DSL.

It is an application language for:

- small backend services,
- local-first tools,
- CLI applications,
- JSON APIs,
- data-backed workflows.

SL compiles to readable Python 3.11 so generated apps can run on the existing Python ecosystem.

## Core Bet

SymbolicLight should feel like writing the useful parts of an application directly:

- data model,
- modules and explicit imports,
- storage,
- commands,
- HTTP routes,
- tests,
- intent linkage.

It should avoid early complexity such as macros, advanced generics, full package management, or custom runtimes.

## Relationship With IntentSpec

IntentSpec is the upper contract layer.

SymbolicLight is the implementation layer.

IntentSpec answers:

- What is the task?
- What permissions are allowed?
- What output or acceptance contract applies?

SymbolicLight answers:

- What data exists?
- What commands and routes exist?
- What executable behavior implements the application?

## Non-Goals For v0

- No frontend framework.
- No package manager.
- No macros.
- No advanced generics.
- No borrow checking.
- No agent runtime.
- No real LLM APIs.
- No custom database engine.
- No package registry or dependency solver.
