# Error Handling

SL uses explicit return types and generated Python diagnostics to keep application failures visible.

For HTTP routes, prefer a record such as:

```sl
type ErrorBody = {
  code: Text,
  message: Text,
}
```

Routes may return `Response<Result<T, ErrorBody>>` and use `response_ok` or `response_err` when that shape is useful.

For database changes, `slc migrate plan` is read-only. It reports structural differences but does not execute SQL.

For application tests, failing assertions include generated Python output and SL source locations when a source map is available.
