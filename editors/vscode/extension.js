const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate() {
  client = new LanguageClient(
    "symboliclight",
    "SL Language Server",
    {
      command: "slc",
      args: ["lsp"],
      transport: TransportKind.stdio
    },
    {
      documentSelector: [{ scheme: "file", language: "symboliclight" }],
      synchronize: {
        fileEvents: []
      }
    }
  );
  client.start();
}

function deactivate() {
  if (!client) {
    return undefined;
  }
  return client.stop();
}

module.exports = { activate, deactivate };
