# Facade V4 Run

## Frozen contract evidence

- Snapshot ID: `rsn_2d25159f86ef6bc28b7350ef`
- Snapshot SHA-256: `2d25159f86ef6bc28b7350efa6bf1e9140c4157dce700c65c45cba847cfc754b`
- Request ID: `rrq_eca9b5b6ca2b75dccb931330`
- Request SHA-256: `eca9b5b6ca2b75dccb931330d86a787348b07766aeb235d5239ca64d050bce16`
- Attempt ID: `phase3c-real-media-001`
- Renderer: `org.book-video-factory.legacy-v4` 1.0.0
- Result status: `succeeded`
- Runner exit code: 0

The facade invoked the existing V4 CLI through `LegacyV4Renderer`; it did not run Post-QC. The
Result was atomically persisted at the current Attempt path and retained renderer stdout/stderr.

## Output and evidence

- Output: `08_render_合成/v4/fixture-copy-b-facade-v4-bilingual-3x4.mp4`
- Bytes: 584,498
- SHA-256: `ac8a6e9e3b0375f42ae539153fcd254cd329b19dde5f9755517783a22e8b2069`
- Probe: H.264/AAC, 720×960, 30 FPS, one video and one audio stream
- Result sidecars: 7
- Request/timeline segments: 13/13
- Script lines: 15
- Renderer checks: output exists, nonzero, inputs stable, Probe readable, output spec match — all pass

## QC handoff

The handoff contains the current Attempt ID, Request hash, output asset ID, output specification,
Probe sidecar, renderer checks, rights hash, and approval hash. The external Smoke adapter verified
the Result output hash and mapped only that handoff to the unmodified Post-QC CLI. It did not scan
for a latest file or infer an output from another Attempt.
