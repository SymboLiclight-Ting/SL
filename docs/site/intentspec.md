# IntentSpec

IntentSpec is the upper contract layer. SL is the implementation layer.

An app may declare:

```sl
intent "./app.intent.yaml"
permissions from intent.permissions
test from intent.acceptance
```

`slc doctor` compares optional SL hints in IntentSpec comments with the implementation:

```yaml
# sl: route GET /items
# sl: command add
```

`slc test` runs the offline IntentSpec acceptance bridge when an app declares `test from intent.acceptance`.

