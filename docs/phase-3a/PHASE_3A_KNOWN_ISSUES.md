# Phase 3A Known Issues

## 1. No standard JSON Schema engine

Formal Draft 2020-12 files exist, but Runtime uses its own Validator. Exact limits are recorded in
`SCHEMA_RUNTIME_LIMITATIONS.md`.

## 2. Phase 2 example hash is symbolic

The Request example's repeated `e` hash is not its semantic digest. It passes structure/semantics and
correctly fails the separate integrity layer. Real requests must derive and persist the calculated
hash before use.

## 3. Cross-platform execution evidence is incomplete

The pure contracts are designed for Windows/POSIX behavior, and Windows tests cover both syntax
families. This run did not execute on a POSIX CI host, so cross-OS evidence is not yet complete.

## 4. Snapshot publication requires same-volume hard-link support

The writer uses an exclusive hard link for atomic no-overwrite publication. NTFS in this test
environment supports it. A filesystem without hard-link support will fail closed; there is no
non-atomic overwrite fallback.

## 5. Filesystem validation is not media validation

The contract checks existence, regular-file status, bytes, SHA, roots, and font presence binding. It
does not open media streams, verify codecs, run FFprobe, measure loudness, inspect glyph coverage, or
perform Post-QC. Those operations are intentionally outside Phase 3A.

## 6. No Release freeze orchestration entrypoint

The immutable Snapshot model/builder/writer exists, but no V4 Mapper or workflow command calls it.
Phase 3B must construct inputs from release-scoped evidence without modifying old Stage Manifests.

## 7. Bitwise video determinism remains unverified

The contract can request `semantic` or `bitwise`; no renderer is implemented and no codec/media run
occurred. Phase 3A makes no claim of bitwise H.264 equivalence.

## 8. Audio shape follows the frozen Phase 2 v1 decision

Final-mix identity comes from the asset binding and hash-bound Audio Manifest; duration and output
sample settings remain in Timeline/OutputSpec rather than being duplicated in `audio`. The reasoning
is recorded in `CONTRACT_DECISION_CONFLICTS.md`.
