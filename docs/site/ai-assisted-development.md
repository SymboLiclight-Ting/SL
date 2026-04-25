# AI-assisted Development

SL is designed to be easy for AI tools to inspect and modify.

Recommended workflow:

1. Keep application intent in an IntentSpec file.
2. Run `slc check` before asking an AI assistant to edit code.
3. Give the assistant diagnostics with file, line, column, message, and suggestion.
4. Run `slc fmt`, `slc test`, `slc schema`, and `slc doctor` after edits.
5. Review generated Python when debugging runtime behavior.

Do not treat generated code as the source of truth. Edit `.sl` files and rebuild.
