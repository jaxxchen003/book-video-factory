# Contract Implementation Map

## Public package

Implementation root:

```text
skills/book-video-factory/runtime/book_video_factory/src/book_video_factory/renderer_contracts/
```

| Module | Responsibility |
|---|---|
| `enums.py` | Stable Render mode/status, Capability, error, Timeline, Caption, and root enums |
| `errors.py` | Frozen structured `RenderIssue`, aggregate validation exception, snapshot write error |
| `models.py` | Frozen Request, Result, Capability, artifact, binding, and Release Snapshot models |
| `serialization.py` | Strict `to_dict`/`from_dict` functions and exact Phase 2 round-trip behavior |
| `paths.py` | Portable relative path normalization and runtime-only `RootResolver` |
| `canonical.py` | `canonical-json-v1`, semantic Request/Snapshot hash, derived IDs |
| `validation.py` | Structural, semantic, filesystem, Gate/Rights, Capability, Result, and Hash layers |
| `release_snapshot.py` | Snapshot construction, content-addressed filename, atomic write-once persistence |
| `__init__.py` | Deliberate public API; contains no renderer or execution entrypoint |

## Formal schemas

The repository's existing central Schema location is used:

```text
skills/book-video-factory/runtime/book_video_factory/schemas/
├── render-request-v1.schema.json
├── render-result-v1.schema.json
├── renderer-capabilities-v1.schema.json
└── release-snapshot-v1.schema.json
```

All four declare JSON Schema Draft 2020-12, `$id`, title, description, required fields, hash
patterns, and explicit unknown-field policy.

## Stable serialization API

```text
render_request_to_dict / render_request_from_dict
render_result_to_dict / render_result_from_dict
capabilities_to_dict / capabilities_from_dict
release_snapshot_to_dict / release_snapshot_from_dict
```

Deserialization returns frozen objects. Missing or unknown top-level/binding fields raise
`ContractValidationError` containing stable `RenderIssue` objects rather than raw `KeyError` or
implementation exception text.

## Scope exclusions

No V4 mapper, `LegacyV4Renderer`, renderer protocol implementation, fake runner, FFmpeg/Pillow
change, provider call, Stage Manifest change, Remotion/Node/React project, or media generation was
added.
