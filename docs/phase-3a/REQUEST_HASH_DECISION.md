# Semantic Request Hash Decision

## Algorithm

```text
request_hash = sha256(canonical-json-v1(semantic_payload))
request_id   = "rrq_" + request_hash[:24]
```

`request_id` is derived only after the semantic digest is known and never participates in that
digest.

## Included

The semantic payload retains every persisted field capable of changing the requested media or its
authorized destination:

- Project/Release Manifest identity and SHA;
- Renderer ID/version, Capability document SHA, required capabilities, and approved degradation;
- Profile binding and OutputSpec;
- logical root declarations and persistent output target;
- Timeline, audio, captions, assets, overlays;
- rights/approval bindings;
- determinism settings;
- all controlled extensions.

Tests prove that changing a persistent output target changes the hash. Asset/Profile/Renderer,
approval and extension values are in the same retained semantic tree and therefore also affect it.

## Excluded

- `request_id` and `request_hash`;
- non-semantic `metadata`;
- Attempt ID and start/finish timestamps;
- temp/work/cache/log paths and log collection;
- PID, hostname, retry count, UI state;
- runtime-only physical `root_bindings`.

The Request Schema rejects these runtime-only fields. The canonical helper also excludes them when
it is used on an intermediate builder payload, so accidental execution context cannot influence the
digest.

## Integrity layer

Semantic validation does not silently replace a supplied hash. `validate_request_hash()` separately
recomputes it and returns `RENDER_HASH_MISMATCH` on disagreement. This separation lets the Phase 2
placeholder example remain a structural fixture while real persisted requests fail closed.
