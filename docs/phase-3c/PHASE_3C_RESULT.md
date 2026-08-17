# Phase 3C Execution Result

## Basic information

- Repository: `mit-mary/book-video-factory`
- Baseline SHA: `a9f1f95`
- Current HEAD: the Git commit containing this report (not embedded to avoid a self-referential hash)
- Phase 3C branch: `test/legacy-v4-real-media-smoke`
- Fixture: `legacy-v4-real-media-smoke` v1
- Source narration duration: 8 seconds
- Output duration: 11.533333 seconds container / 11.520000 seconds audio
- Resolution: 720×960
- FPS: 30

## Scope

- Legacy V4 modification: no
- Facade modification: no production facade change; test-only Smoke Adapter added
- Remotion: not integrated
- Provider: not called
- External assets: not used
- Commercial project: not used

## Baseline run

- CLI: direct unmodified `build_batch_video_v3.py --release-version v4`
- Exit: 0
- Output: 584,498-byte H.264/AAC MP4
- SHA-256: `ac8a6e9e3b0375f42ae539153fcd254cd329b19dde5f9755517783a22e8b2069`
- Probe: pass
- Post-QC: local master pass; public release held for H2 rights evidence

## Facade run

- Snapshot: `rsn_2d25159f86ef6bc28b7350ef`
- Request: `rrq_eca9b5b6ca2b75dccb931330`
- Attempt: `phase3c-real-media-001`
- Result: succeeded
- Output: 584,498-byte H.264/AAC MP4
- SHA-256: `ac8a6e9e3b0375f42ae539153fcd254cd329b19dde5f9755517783a22e8b2069`
- Probe: pass
- Handoff: complete and hash-consistent
- Post-QC: external adapter pass; conclusion equivalent to baseline

## Semantic comparison

- Container: equivalent
- Video codec: equivalent
- Resolution: equivalent
- FPS: equivalent
- Duration: equal, 0 ms difference within 34 ms tolerance
- Audio: equivalent AAC / 48 kHz / stereo
- Streams: one video and one audio on each path
- Business structure: 13 timeline segments, 15 lines, complete sidecars
- Post-QC: equivalent
- Bitwise equality: observed but not required

## Failure fixture

- Type: fixed output already exists
- Fail-closed: yes, before Runner invocation
- Partial output: no process-created partial output
- Existing output: preserved byte-for-byte
- Quarantine: not triggered; Attempt-specific non-trigger evidence retained

## Tests

- Original baseline: 155
- Current total: 159/159 pass
- New tests: 4/4 pass
- Real-media smoke: pass twice
- Failures: 0
- Errors: 0
- Unexpected skips: 0

## Blockers

No confirmed blocker.

## Phase 3C decision

**Pass.** Both real-media paths succeeded on identical frozen semantic input, media semantics and
Post-QC conclusions match, contract evidence is complete, and the controlled failure is fail-closed.

## New renderer experiment decision

**Allowed as a bounded experiment, not as a production replacement.** It must remain behind the
existing contract and pass the frozen-fixture gate before scope expands.

## Single next recommendation

Build one contract-conformance skeleton for the next renderer and verify it against this frozen
fixture; do not start Audio Finalizer or Web work in parallel.
