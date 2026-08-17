# Immutable Release Snapshot v1

## Role

Release Snapshot v1 freezes approved, rights-cleared inputs before Request creation. It is not a
Stage Manifest, the legacy `render_manifest.v4.json`, a RenderRequest, or a RenderResult. No existing
manifest is renamed or modified.

The frozen model contains project/release identity, Profile binding, content-addressed artifacts,
Timeline/audio/caption sources, Rights, Approvals, Release Gates, source manifests, and metadata.
Every artifact has byte length, SHA-256, portable ref, source artifact ID, and rights reference.

## Semantic identity

```text
snapshot_hash = sha256(canonical-json-v1(snapshot semantic payload))
snapshot_id   = "rsn_" + snapshot_hash[:24]
filename      = release-snapshot-v1-<snapshot_hash>.json
```

`snapshot_id`, `snapshot_hash`, `created_at`, and metadata are excluded from semantic hashing.
Changing an artifact hash changes the Snapshot hash; changing only creation time or notes does not.

## Fail-closed creation

`create_release_snapshot()` refuses creation unless:

- artifact IDs and derived hash index agree;
- every artifact has source and rights binding;
- source bindings have ID/version/portable ref/SHA;
- Rights status is `allowed`;
- Approval status is `approved`;
- Release Gate status is `passed`;
- derived ID and semantic hash are valid.

## Atomic write-once behavior

`write_release_snapshot()`:

1. validates semantics and hash before writing;
2. emits canonical UTF-8 bytes to an exclusive temporary file in the destination directory;
3. flushes and `fsync`s the file;
4. publishes it with an exclusive same-volume hard link, which is atomic and cannot replace an
   existing path;
5. removes the temporary link;
6. reads the final bytes, deserializes, and revalidates semantic hash;
7. returns an existing file only when its bytes are identical;
8. fails if the same content-addressed path contains different bytes.

There is deliberately no non-atomic overwrite fallback. Tests cover idempotency, tampering,
canonical bytes, temporary cleanup, read-back validation, and preservation of a neighboring Stage
Manifest.
