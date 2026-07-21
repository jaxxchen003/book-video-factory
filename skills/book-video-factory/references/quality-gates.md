# Release quality gates

## Project contract

- `project.json` must identify the book/topic, workflow mode, `style_profile_id`, `release_profile_id`, and generation lane. A missing `style_profile_id` is treated as the original `book-editorial-bilingual-v2` only for backward compatibility.
- The two built-in styles are independent contracts: the original **双语编辑模板图书视频** and the new **VOX风格图书视频**. Never combine their frame, asset, renderer, or approval assumptions silently.
- Each stage writes an immutable manifest or append-only cost event. Each revision uses a new `release_id` and delivery directory; an approved master is never overwritten.
- `workflow.py evaluate --project <project> --release-id <release-id>` resolves the release profile from the project, then derives state from files, hashes, QC, and approval events. Direct edits to `project.json.status` cannot advance a gate, and approvals from different releases are never combined.

## Common editorial and rights gates

- `topic` — a human approves the topic and intended audience.
- `source` or `source_audit` — every factual claim and quotation has attributable evidence; reader comments remain opinions, not book facts.
- `script` — approval binds to the current script hash. Any script edit invalidates the decision.
- `voice_rights` — narration or voice-clone authorization is recorded. Never clone a public figure, another creator, or an unconsenting person.
- `bgm_rights` / `sfx_rights` — provenance records creator/provider, licence or user authorization, source URL or file hash, attribution requirements, and account-terms caveats.
- `cover_rights` — required when a real book cover or cover-derived frame is used. A generated imitation is never accepted as a substitute for the real cover.
- `english_native` — required only when English copy or subtitles are delivered; keep English marked `needs_native_review` before approval.
- `publish` — a human approval bound to the exact delivery output hash. Technical QC or local-master approval is not publication approval.

## Content-system-backed gates

- The package preserves source registry rows, source-copy hashes, complete content-unit fields/body, materialized Claims, and a structured assembly brief.
- Only `回应 / 解释 / 证明 / 冲突` relationships are accepted. Unknown types are rejected rather than silently normalized.
- All five main unit types are present for a production-eligible assembly, selected units are canonical, and used Claims are reviewed or approved.
- The source approval binds the active package snapshot; traceability covers every script line exactly once and uses the active renderer scene contract.
- A human `traceability` approval binds the attached map hash. Automated structural validation cannot approve semantic Claim-to-script links.
- `single-book` projects remain compatible and do not inherit these additional content-system gates.

## Style A — 双语编辑模板图书视频（原风格）

Machine ID: `book-editorial-bilingual-v2`  
Release profile: `book-v4-bilingual-3x4`

- Exactly 12 distinct approved stills exist as `S01.png` through `S12.png`.
- Every still is topic-specific, text-free, and free of a copied cover design or visible watermark.
- The real cover has provenance and a passed `cover_rights` decision.
- The local master is 720×960, 3:4, 30 fps, H.264/AAC, includes readable bilingual captions, and respects the configured title/subtitle safe areas.
- The V4 QC report carries the same `release_id` as its approvals and reports `local_master_status: pass`.
- Required publish approvals are `script`, `cover_rights`, `bgm_rights`, `sfx_rights`, `voice_rights`, `english_native`, and `publish`, in addition to the state-sequence approvals for topic, source, and timing.

## Style B — VOX风格图书视频（新增风格）

Machine ID: `paper-collage-explainer-v1`  
Release profile: `book-vox-vertical-9x16-v1`

“VOX风格” is a user-facing descriptive label for an original editorial explainer treatment. It does not claim affiliation with Vox Media and must not be used as an instruction to copy a named program, logo, brand package, or proprietary graphic system. Generation prompts use non-branded visual descriptors.

The built-in VOX profile currently supports `single-book` only. The existing `content-system-backed` traceability implementation is tied to the original V4 scene-line contract and fails closed for VOX projects.

### Editorial and visual gates

1. `source_audit` — the evidence pack and claim boundaries are reviewed.
2. `script` — narration is concise, voice-led, and split into one information change per 4–8-second visual beat.
3. `timing` — narration and ASR timing are locked before full clip generation. Do not stretch narration to fit generated footage after the fact.
4. `gate_1_metaphor` — each beat states `concept → visible metaphor → main action → prohibited elements`. One primary metaphor and one primary motion per beat.
5. `gate_2_still` — approve the first frame, optional last frame, or contact sheet. Check focal hierarchy, 9:16 safe area, paper texture, palette continuity, repeated metaphors, anatomy, embedded text, logos, and visible watermarks.
6. `gate_3_clip_qa` — approve every generated clip and its manifest. Verify scene ID, prompt, provider/model or Flow label, input/output hashes, duration, dimensions, decodability, continuity, QA decision, and cost/credits evidence.

### Clip and motion contract

- Generated clips are 9:16 H.264 MP4 visual beats. The asset manifest, rather than a universal scene count, defines how many clips the release uses.
- Clip IDs and hashes are unique; every referenced file exists and its recorded SHA-256 matches.
- Generated clips contain no embedded captions and are absent of audio or stripped before local assembly. Generated native audio is not treated as the final mix source.
- Acceptable motion grammar includes paper-layer reveal, cutout slide, path trace, chart growth, object comparison, restrained parallax, and gentle push-in. Avoid rapid orbiting, uncontrolled morphing, flash cuts, decorative motion unrelated to narration, and multiple competing actions.
- Invisible provider provenance such as SynthID is allowed and must not be removed or tampered with. Reject visible third-party watermarks or ownership marks.

### Local timeline, picture lock, and audio gates

- Normalize provider clips to the 720×1280, 30 fps local timeline without changing playback speed. Inspect cadence; optical-flow interpolation is off by default.
- Keep titles within 48 px horizontal margins. Keep subtitles inside the 48 px horizontal and 120 px bottom safe areas defined by the release profile; fail closed on overflow.
- `timing` binds the narration/ASR map. `local_master_review` binds the exact H.264/AAC master after picture lock.
- `bgm_rights` validates provenance; `bgm_review` is a separate human listening decision for mood, repetition, speech masking, transitions, and ending. A rights-valid track can still fail creative review.
- `audio_qc` targets approximately −16 LUFS integrated, accepts the project-approved delivery range, and keeps true peak at or below the configured −1.2 dBFS ceiling. Confirm no clipping, missing channel, abrupt cut, or inaudible narration.
- Technical QC checks full decode, 720×1280, constant 30 fps delivery, H.264/AAC, A/V duration agreement, black frames, caption safe area, and output hash.

### Publish and showcase gates

- Required production approvals are `source_audit`, `script`, `gate_1_metaphor`, `gate_2_still`, `gate_3_clip_qa`, `timing`, `voice_rights`, `bgm_rights`, `bgm_review`, `sfx_rights`, `audio_qc`, `local_master_review`, and `publish`.
- `cover_rights` is added when a real cover or cover-derived frame is present. `english_native` is added when English is delivered.
- A public repository demo is a separate derivative. Require `showcase_publish` bound to the preview hash, plus a sanitized gate summary that records source-manifest/event hashes, redactions, transcoding, rights scope, unresolved production gates, and the distinction between source local-master approval and public-showcase approval. State provider-account rights as operator attestations unless independently verified.

## ChatCut handoff gate

- Import only a locally QC-passed master and its subtitle file.
- Record the editor project ID, edit summary, export path, reviewer, revision label, and any generated BGM asset/provenance.
- Keep the local master immutable and publish the ChatCut export as a distinct derivative version.
