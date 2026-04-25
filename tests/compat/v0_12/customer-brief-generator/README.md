# Customer Brief Generator

This example demonstrates IntentSpec command alignment, file input, and Markdown output through thin SL builtins.

```bash
slc check app.sl
slc build app.sl --out build/customer_brief.py
python build/customer_brief.py generate input.md brief.md
slc doctor app.sl
```
