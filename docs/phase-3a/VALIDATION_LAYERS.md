# Validation Layers

The implementation keeps validation concerns separate so callers can fail at the appropriate
workflow boundary and tests can identify the exact contract violated.

## 1. Structure and serialization

The four `from_dict` functions reject missing/unknown top-level and identity-binding fields with a
`ContractValidationError` containing structured issues. The semantic validator additionally checks
unknown nested Timeline, Audio, Caption, Overlay, OutputSpec, Rights, Approval, determinism, and root
fields against the formal Schema policy.

No semantic default is inserted. Arrays become tuples and mappings become read-only mappings in the
frozen model.

## 2. Semantic validation

`validate_render_request()` verifies versions, stable enums, SHA format, declared roots, output
authorization, unique IDs, explicit determinism, extension namespaces, Timeline continuity and
references, final mix binding, Caption/word intervals, font binding, and OutputSpec duration.

Timeline uses 1000 integer ticks, half-open segments, no gap/overlap, and explicit `hold`; the first
segment cannot hold a nonexistent previous visual. There is no 15-line or 12-scene constant.

## 3. Portable path validation

`normalize_portable_path()` validates persistent syntax. `RootResolver` handles runtime physical
binding and safe `Path.resolve()` containment. This is independent of filesystem content checks.

## 4. Filesystem validation

`validate_request_filesystem()` resolves every input asset, requires a regular file, and checks both
byte length and SHA-256. A missing font uses `RENDER_FONT_UNAVAILABLE`; other missing files use
`RENDER_ASSET_MISSING`; content drift uses `RENDER_HASH_MISMATCH`.

It does not probe media codecs, call FFmpeg, or execute a renderer.

## 5. Gate and Rights validation

`validate_gate_rights()` requires Rights `allowed`, Rights scope equal to `render_mode`, explicit Gate
and Approval arrays, a nonempty approval event set when gates are required, and valid snapshot
hashes. Failure returns stable `RENDER_RIGHTS_BLOCKED` or `RENDER_GATE_BLOCKED` issues.

Release Snapshot creation separately requires `allowed` Rights, `approved` Approvals, and `passed`
Release Gates.

## 6. Capability validation

`validate_capabilities()` validates the capability document itself. `compare_capabilities()` is a
pure required/supported comparison. `validate_request_capabilities()` also binds renderer
ID/version, extension namespace/version, and any degradation plan's explicit approval event.
Unknown or unsupported values fail closed with `RENDER_CAPABILITY_UNSUPPORTED`.

No concrete renderer capability document is introduced by Phase 3A.

## 7. Integrity validation

`validate_request_hash()` and `validate_snapshot_hash()` recompute canonical semantic hashes. They do
not rewrite supplied values. Result validation requires output/hash indexes to match artifact truth.

## 8. Result state validation

`validate_render_result()` enforces terminal timestamps and state-specific rules:

- succeeded requires output, Probe, QC handoff, and no errors;
- failed/blocked/cancelled require structured errors and a primary code;
- pending/running cannot register terminal output;
- output and sidecar hashes must exactly match the derived index;
- log refs must remain portable.

Independent issues are returned together. Sorting uses fixed error priority, JSON-path field, code,
and message, so error order is deterministic.
