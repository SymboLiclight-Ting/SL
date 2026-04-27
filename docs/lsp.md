# SL Language Server

`slc lsp` starts the local SL language server over JSON-RPC stdio.

Supported capabilities:

- diagnostics from the parser and checker,
- hover for route body fields, inferred local values, record fields, types, enum variants, store helpers, function and command return types, config fields, and simple expression targets,
- go to definition for local values, record fields, local and imported types, enums, functions, stores, commands, routes, and selected qualified references,
- document symbols for app, module, type, enum, config, store, fixture, function, command, route, and test declarations,
- whole-document formatting through the official comment-preserving formatter.

The server is intentionally dependency-free and reuses the existing compiler modules. It does not define independent language semantics.
