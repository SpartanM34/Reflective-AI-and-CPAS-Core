# Message Manifest Schema

`cpas_autogen.message_logger` records each message an agent sends. Messages are appended to `examples/message_manifest.json` using the schema below:

```json
{
  "threadToken": "<conversation thread token>",
  "timestamp": "<ISO-8601 UTC time>",
  "instance": "<agent name>",
  "seedToken": "<seed token JSON>",
  "contentHash": "<sha256 of the message>",
  "fingerprint": "<epistemic fingerprint value>"
}
```

The manifest is referenced during continuity checks to verify that message ordering and identity information remain consistent across sessions. When the file grows beyond the size limit, it is automatically rotated and a new manifest is started.
