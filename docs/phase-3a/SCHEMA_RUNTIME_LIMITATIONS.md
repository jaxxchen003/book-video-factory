# JSON Schema Runtime Limitations

## Exact status

```text
+ Formal JSON Schema files are provided for Request, Result, Capability, and Release Snapshot.
+ Runtime uses its own standard-library Python deserializer and layered Validator.
- No standard JSON Schema engine is integrated.
```

The repository intentionally did not add `jsonschema`, Pydantic, or another third-party dependency.
Therefore Phase 3A does not claim that Runtime executes every JSON Schema Draft 2020-12 keyword.

## What Runtime enforces now

- exact top-level and identity-binding fields during deserialization;
- nested unknown-field policy for Request semantic objects;
- types/enums required for model construction and contract semantics;
- stable SHA format and semantic recomputation;
- portable paths and safe physical resolution;
- Timeline, Audio, Caption, Capability, Gate/Rights, Result, and Snapshot relationships;
- exact Phase 2 example round-trip.

## What remains for a future phase

- running a standards-conformant Draft 2020-12 engine against arbitrary external payloads;
- checking every annotation/composition keyword through that engine;
- a schema/model parity generator or CI diff tool;
- compatibility testing of future minor Schema versions.

Until a standard engine is explicitly approved, callers must use the supplied `from_dict` and
validation APIs rather than treating successful `json.loads()` as contract acceptance.
