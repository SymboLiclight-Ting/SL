from pathlib import Path
import json
import py_compile

from symboliclight.cli import load_checked_unit, main


ROOT = Path(__file__).resolve().parents[1]


def test_cli_check_build_and_test(tmp_path: Path) -> None:
    source = ROOT / "examples" / "todo_app.sl"
    output = tmp_path / "todo_app.py"

    assert main(["check", str(source)]) == 0
    assert main(["build", str(source), "--out", str(output)]) == 0
    py_compile.compile(str(output), doraise=True)
    assert Path(str(output) + ".slmap.json").exists()
    assert main(["test", str(source)]) == 0


def test_cli_notes_example_v04_regression(tmp_path: Path) -> None:
    source = ROOT / "examples" / "notes_api.sl"
    output = tmp_path / "notes_api.py"
    schema = tmp_path / "notes_schema.json"

    assert main(["check", str(source)]) == 0
    assert main(["schema", str(source), "--out", str(schema)]) == 0
    assert main(["build", str(source), "--out", str(output)]) == 0
    py_compile.compile(str(output), doraise=True)
    assert main(["test", str(source)]) == 0


def test_cli_gallery_examples_v05_regression(tmp_path: Path) -> None:
    for name in ["todo-api-cli", "notes-api", "issue-tracker", "customer-brief-generator"]:
        source = ROOT / "examples" / "gallery" / name / "app.sl"
        output = tmp_path / f"{name}.py"
        schema = tmp_path / f"{name}.schema.json"

        assert main(["check", str(source)]) == 0
        assert main(["build", str(source), "--out", str(output)]) == 0
        py_compile.compile(str(output), doraise=True)
        assert main(["test", str(source)]) == 0
        assert main(["schema", str(source), "--out", str(schema)]) == 0
        assert main(["doctor", str(source)]) == 0


def test_cli_doctor_reports_intent_route_command_and_permission_diff(tmp_path: Path, capsys) -> None:
    source = tmp_path / "app.sl"
    intent = tmp_path / "app.intent.yaml"
    source.write_text(
        """
app DoctorDemo {
  intent "./app.intent.yaml"

  type Item = {
    id: Id<Item>,
    title: Text,
  }

  store items: Item

  command add(title: Text) -> Item {
    return items.insert({ title: title })
  }

  route GET "/items" -> List<Item> {
    return items.all()
  }
}
""",
        encoding="utf-8",
    )
    intent.write_text(
        """
version: "0.1"
kind: "IntentSpec"

# sl: route GET /missing
# sl: command add
# sl: command remove

metadata:
  name: "doctor-demo"
  title: "Doctor Demo"
  owner: "symboliclight"

task:
  goal: "Check doctor diffs."
  audience:
    - "Application developer"
  priority: "medium"

permissions:
  web: false
  filesystem:
    read: true
    write: false
  network: false

output:
  format: "markdown"
  language: "en"
  max_words: 500
  sections:
    - "Run"

tests:
  - name: "Doctor smoke"
    assert:
      - type: "required_sections"

""",
        encoding="utf-8",
    )

    assert main(["doctor", str(source)]) == 0
    output = capsys.readouterr().out

    assert "intent missing routes: GET /missing" in output
    assert "intent extra routes: GET /items" in output
    assert "intent commands: 1/2 matched" in output
    assert "intent missing commands: remove" in output
    assert "permissions.web is false" in output
    assert "filesystem.write is false" in output
    assert "permission network: ok" in output


def test_cli_test_runs_intent_acceptance(tmp_path: Path, capsys) -> None:
    source = tmp_path / "app.sl"
    intent = tmp_path / "app.intent.yaml"
    source.write_text(
        """
app AcceptanceDemo {
  intent "./app.intent.yaml"

  permissions from intent.permissions

  command ping() -> Text {
    return "pong"
  }

  route GET "/ping" -> Text {
    return "pong"
  }

  test from intent.acceptance
}
""",
        encoding="utf-8",
    )
    intent.write_text(
        """
version: "0.1"
kind: "IntentSpec"

# sl: route GET /ping
# sl: command ping

permissions:
  web: true
  filesystem:
    read: false
    write: false
  network: false

metadata:
  name: "acceptance-demo"
  title: "Acceptance Demo"
  owner: "symboliclight"

task:
  goal: "Check IntentSpec acceptance wiring."
  audience:
    - "Application developer"
  priority: "medium"

output:
  format: "markdown"
  language: "en"
  max_words: 100
  sections:
    - "Run"

tests:
  - name: "Smoke"
    assert:
      - type: "required_sections"
""",
        encoding="utf-8",
    )

    assert main(["test", str(source)]) == 0
    output = capsys.readouterr().out

    assert "ok - intent acceptance: 1 assertion(s) checked" in output


def test_cli_test_fails_intent_acceptance_on_missing_route(tmp_path: Path, capsys) -> None:
    source = tmp_path / "app.sl"
    intent = tmp_path / "app.intent.yaml"
    source.write_text(
        """
app AcceptanceDemo {
  intent "./app.intent.yaml"

  route GET "/actual" -> Text {
    return "ok"
  }

  test from intent.acceptance
}
""",
        encoding="utf-8",
    )
    intent.write_text(
        """
version: "0.1"
kind: "IntentSpec"

# sl: route GET /missing

permissions:
  web: true

metadata:
  name: "acceptance-demo"
  title: "Acceptance Demo"
  owner: "symboliclight"

task:
  goal: "Check IntentSpec acceptance wiring."
  audience:
    - "Application developer"
  priority: "medium"

output:
  format: "markdown"
  language: "en"
  max_words: 100
  sections:
    - "Run"

tests:
  - name: "Smoke"
    assert:
      - type: "required_sections"
""",
        encoding="utf-8",
    )

    assert main(["test", str(source)]) == 1
    captured = capsys.readouterr()

    assert "intent acceptance failed: missing route GET /missing" in captured.err


def test_cli_schema_and_doctor_report_v04_status(tmp_path: Path, capsys) -> None:
    source = tmp_path / "app.sl"
    output = tmp_path / "schema.json"
    source.write_text(
        """
app SchemaDemo {
  type CreateTodo = {
    title: Text,
  }

  type Todo = {
    id: Id<Todo>,
    title: Text,
  }

  store todos: Todo

  route POST "/todos" body CreateTodo -> Response<Todo> {
    let item = todos.insert({ title: request.body.title })
    return response(status: 201, body: item)
  }
}
""",
        encoding="utf-8",
    )

    assert main(["schema", str(source), "--out", str(output)]) == 0
    schema = json.loads(output.read_text(encoding="utf-8"))
    assert schema["routes"][0]["body"]["$ref"] == "#/definitions/CreateTodo"
    assert schema["routes"][0]["response"]["$ref"] == "#/definitions/Todo"

    assert main(["doctor", str(source)]) == 0
    doctor = capsys.readouterr().out
    assert "route schemas: 1/1 request bodies typed" in doctor


def test_cli_schema_includes_imported_enums(tmp_path: Path) -> None:
    source = ROOT / "examples" / "issue_tracker.sl"
    output = tmp_path / "issue_schema.json"

    assert main(["schema", str(source), "--out", str(output)]) == 0
    schema = json.loads(output.read_text(encoding="utf-8"))

    assert schema["enums"]["models.Status"]["enum"] == ["open", "closed"]
    assert schema["definitions"]["models.Issue"]["properties"]["status"]["$ref"] == "#/enums/models.Status"


def test_cli_build_can_skip_source_map(tmp_path: Path) -> None:
    source = ROOT / "examples" / "todo_app.sl"
    output = tmp_path / "todo_app.py"
    source_map = Path(str(output) + ".slmap.json")

    assert main(["build", str(source), "--out", str(output)]) == 0
    assert source_map.exists()
    assert main(["build", str(source), "--out", str(output), "--no-source-map"]) == 0

    assert output.exists()
    assert not source_map.exists()


def test_cli_build_imported_app_after_cached_check(tmp_path: Path) -> None:
    source = ROOT / "examples" / "issue_tracker.sl"
    output = tmp_path / "issue_tracker.py"

    assert main(["check", str(source)]) == 0
    assert main(["build", str(source), "--out", str(output)]) == 0

    py_compile.compile(str(output), doraise=True)


def test_cli_fmt_doctor_init_new_and_add_route(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "tiny.sl"
    source.write_text(
        'app Tiny { type Item = { id: Id<Item>, title: Text, } store items: Item route GET "/items" -> List<Item> { return items.all() } }',
        encoding="utf-8",
    )

    assert main(["fmt", str(source)]) == 0
    assert main(["fmt", str(source), "--check"]) == 0
    assert main(["doctor", str(source)]) == 0
    assert main(["add", "route", "GET", "/health", str(source)]) == 0
    assert main(["fmt", str(source), "--check"]) == 0

    project = tmp_path / "demo"
    assert main(["init", str(project)]) == 0
    assert (project / "src" / "app.sl").exists()
    assert (project / "intent" / "app.intent.yaml").exists()
    assert (project / ".gitignore").exists()
    assert main(["check", str(project / "src" / "app.sl")]) == 0

    monkeypatch.chdir(tmp_path)
    assert main(["new", "api", "sample"]) == 0
    sample_source = tmp_path / "sample" / "src" / "app.sl"
    sample_output = tmp_path / "sample" / "build" / "app.py"
    sample_schema = tmp_path / "sample" / "build" / "schema.json"
    assert sample_source.exists()
    assert main(["check", str(sample_source)]) == 0
    assert main(["build", str(sample_source), "--out", str(sample_output)]) == 0
    py_compile.compile(str(sample_output), doraise=True)
    assert main(["test", str(sample_source)]) == 0
    assert main(["schema", str(sample_source), "--out", str(sample_schema)]) == 0
    assert main(["doctor", str(sample_source)]) == 0


def test_cli_add_route_refuses_commented_files(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    original = """
// keep this note
app Commented {
  route GET "/ok" -> Text {
    return "ok"
  }
}
""".lstrip()
    source.write_text(original, encoding="utf-8")

    assert main(["add", "route", "GET", "/health", str(source)]) == 1
    assert source.read_text(encoding="utf-8") == original


def test_cli_fmt_refuses_to_drop_comments(tmp_path: Path) -> None:
    source = tmp_path / "commented.sl"
    original = """
// keep this intent note
app Commented {
  route GET "/note" -> Text {
    return "ok"
  }
}
""".lstrip()
    source.write_text(original, encoding="utf-8")

    assert main(["fmt", str(source)]) == 1
    assert source.read_text(encoding="utf-8") == original


def test_cli_fmt_preserves_escaped_strings(tmp_path: Path) -> None:
    source = tmp_path / "escaped.sl"
    source.write_text(
        'app Escaped { test "strings" { assert "a\\"b" == "a\\"b" assert "line\\nbreak" == "line\\nbreak" } }',
        encoding="utf-8",
    )

    assert main(["fmt", str(source)]) == 0
    formatted = source.read_text(encoding="utf-8")

    assert '\\"' in formatted
    assert "\\n" in formatted
    assert main(["check", str(source), "--no-cache"]) == 0


def test_cli_check_json_outputs_machine_readable_diagnostics(tmp_path: Path, capsys) -> None:
    source = tmp_path / "bad.sl"
    source.write_text(
        """
app Bad {
  store items: Missing
}
""",
        encoding="utf-8",
    )

    assert main(["check", str(source), "--json"]) == 1
    output = capsys.readouterr().out
    diagnostics = json.loads(output)

    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["code"]
    assert diagnostics[0]["suggestion"]


def test_cli_build_failure_does_not_overwrite_output(tmp_path: Path) -> None:
    source = tmp_path / "bad.sl"
    output = tmp_path / "app.py"
    output.write_text("keep me", encoding="utf-8")
    source.write_text(
        """
app Bad {
  store items: Missing
}
""",
        encoding="utf-8",
    )

    assert main(["build", str(source), "--out", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "keep me"


def test_check_cache_hits_and_invalidates_imports(tmp_path: Path) -> None:
    module = tmp_path / "models.sl"
    module.write_text("module models { fn ok() -> Bool { return true } }", encoding="utf-8")
    source = tmp_path / "app.sl"
    source.write_text(
        """
app CacheDemo {
  import "./models.sl" as models

  test "ok" {
    assert models.ok() == true
  }
}
""",
        encoding="utf-8",
    )

    _, first_diagnostics, first_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    _, second_diagnostics, second_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    module.write_text("module models { fn ok() -> Bool { return false } }", encoding="utf-8")
    _, third_diagnostics, third_hit = load_checked_unit(source, strict_intent=False, use_cache=True)

    assert not first_hit
    assert second_hit
    assert not third_hit
    assert first_diagnostics == second_diagnostics
    assert not [diagnostic for diagnostic in third_diagnostics if diagnostic.severity == "error"]


def test_check_cache_invalidates_when_missing_import_is_created(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    source.write_text(
        """
app CacheDemo {
  import "./models.sl" as models
}
""",
        encoding="utf-8",
    )

    _, first_diagnostics, first_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    _, second_diagnostics, second_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    (tmp_path / "models.sl").write_text("module models { fn ok() -> Bool { return true } }", encoding="utf-8")
    _, third_diagnostics, third_hit = load_checked_unit(source, strict_intent=False, use_cache=True)

    assert not first_hit
    assert second_hit
    assert not third_hit
    assert any("Import file not found" in diagnostic.message for diagnostic in first_diagnostics)
    assert first_diagnostics == second_diagnostics
    assert not [diagnostic for diagnostic in third_diagnostics if diagnostic.severity == "error"]


def test_check_cache_invalidates_when_missing_intent_is_created(tmp_path: Path) -> None:
    source = tmp_path / "app.sl"
    source.write_text(
        """
app CacheDemo {
  intent "./app.intent.yaml"
}
""",
        encoding="utf-8",
    )

    _, first_diagnostics, first_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    _, second_diagnostics, second_hit = load_checked_unit(source, strict_intent=False, use_cache=True)
    (tmp_path / "app.intent.yaml").write_text('version: "0.1"\nkind: "IntentSpec"\n', encoding="utf-8")
    _, third_diagnostics, third_hit = load_checked_unit(source, strict_intent=False, use_cache=True)

    assert not first_hit
    assert second_hit
    assert not third_hit
    assert any("IntentSpec file not found" in diagnostic.message for diagnostic in first_diagnostics)
    assert first_diagnostics == second_diagnostics
    assert not any("IntentSpec file not found" in diagnostic.message for diagnostic in third_diagnostics)
