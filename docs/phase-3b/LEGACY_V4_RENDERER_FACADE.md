# LegacyV4Renderer Facade

## Execution

`LegacyV4Renderer` wraps the unmodified `build_batch_video_v3.py <project>
--release-version v4` entrypoint. The command, physical roots, environment, and temporary execution
state are runtime-only and do not enter the Request Hash.

The facade injects the three Request-bound font paths into the existing `BOOK_VIDEO_*_FONT`
environment variables. It verifies the Request, semantic Hash, Capability document, all input
files, and three frozen legacy source hashes before starting. The output and every required legacy
sidecar must be absent because persistent targets use fail-if-exists semantics.

Runner and media Probe are protocols. Unit tests inject fakes; the default implementations are
available for a separately approved real-media Phase 3C.

## Attempt lifecycle

Each execution has an independent `attempt_id` and write-once directory:

```text
<attempts>/<attempt_id>/
├── events/000-pending.json
├── events/001-running.json       # only after preflight
├── events/002-<terminal>.json
├── logs/renderer.stdout.log
├── logs/renderer.stderr.log
├── probe/media-probe.json        # successful Probe only
└── render-result-v1.json
```

Request, Attempt event, and terminal Result persistence use canonical JSON and exclusive
publication. A retry requires a new `attempt_id`; no prior Result is overwritten.

## Collection and QC handoff

Success requires:

- zero runner exit status;
- unchanged input bytes after execution;
- non-empty requested local master;
- legacy render Manifest, renderer QC, three SRT files, and title-layout sidecar;
- a readable Probe matching codec, dimensions, FPS, pixel format, sample rate, channels, and
  duration within one frame.

The Result binds output and sidecar SHA-256 values and creates the Phase 2 `qc_handoff` snapshot.
It does not call `v4_post_qc.py`, approve `local_master_review`, change publication Gates, or claim
that Renderer success equals publish readiness.
