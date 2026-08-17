# Contract Decision Conflicts

All identified differences were resolved before the affected implementation was finalized.

## 1. Python package location

Phase 3A suggested `book_video_factory/contracts/`, but the repository already has
`book_video_factory/contracts.py`. That existing module defines `ReleaseProfile` and is imported by
production scripts and tests. A same-named package could change import resolution and break the old
chain.

Decision: place the new infrastructure in `book_video_factory/renderer_contracts/`. The existing
module remains unchanged. Formal schemas use the repository's existing central `schemas/` directory.

## 2. Project, release, and snapshot identity shape

The Phase 3A checklist names `project_id`, `release_id`, and `release_snapshot_hash` as fields. The
frozen Phase 2 v1 JSON shape uses `project.id`, `release.id`, and `release.manifest_sha256`.

Decision: preserve the Phase 2 serialized shape so there is one v1 truth source. `RenderRequest`
exposes read-only semantic properties named `project_id`, `release_id`, and
`release_snapshot_hash`; it does not persist duplicate top-level values.

## 3. Audio metadata placement

The Phase 3A summary lists final-mix duration, sample rate, and channels under the audio contract.
The Phase 2 request example binds the final mix by asset ID and Audio Manifest hash, while sample
rate/channels are frozen in `output_spec.audio` and duration is frozen in both Timeline and
`output_spec.duration_ticks`.

Decision: retain the frozen Phase 2 v1 shape. The validator requires the final-mix asset, validates
timeline-zero synchronization, and checks Timeline/OutputSpec duration equality. The referenced,
hash-bound Audio Manifest remains the source for detailed mix metadata. Duplicating these values in
two Request locations was rejected because it would create drift.

## 4. Backslash handling

Phase 2 text says persisted paths use `/` and rejects backslashes. Phase 3A explicitly allows
normalizing `assets\audio\voice.wav` to `assets/audio/voice.wav`.

Decision: follow the newer Phase 3A instruction at the input boundary. Relative backslashes are
normalized before persistence; drive-qualified and UNC inputs are still rejected before
normalization. Serialized output always uses `/`.

## 5. Logical root kinds

Phase 2 examples use `project` and `runtime`; Phase 3A asks to discuss `workspace`, `project`,
`release`, `artifact`, and `output`.

Decision: the stable enum and validator recognize all seven discussed/current kinds:
`workspace`, `project`, `release`, `artifact`, `output`, `runtime`, and `font_resources`. A Request
must still explicitly declare every root it uses, and physical bindings remain runtime-only.

## 6. Placeholder example hashes

The Phase 2 examples use readable repeated characters rather than computed semantic hashes.

Decision: do not rewrite the closed Phase 2 artifacts. Structural/semantic validation and hash
integrity validation are separate layers. Tests prove both the example's intended structure and the
integrity layer's fail-closed behavior.
