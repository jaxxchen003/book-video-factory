# Renderer Contract v1 Amendment: Legacy V4 Audio Mixing

## Conflict

Renderer Contract v1 normally requires a final RenderRequest to bind an existing
`final_mix_asset_id`. The legacy V4 chain does not have that asset before execution: it inserts the
intro pause and mixes narration, project BGM, and the approved H2 layer inside
`build_batch_video_v3.py` / `build_final_video_v2.py`.

Inventing a pre-render final mix ID would falsely claim that an asset exists. Modifying the old
audio graph would exceed Phase 3B. Phase 2 already documented a temporary, controlled legacy
exception, but Phase 3A's formal Request Schema had not encoded it.

## Amendment

`final_mix_asset_id` may be `null` only when every condition below is true:

1. `renderer.id` is exactly `org.book-video-factory.legacy-v4`;
2. the exact Renderer version and Capability document are hash-bound;
3. `renderer.required_capabilities` contains `audio_mixing`;
4. `audio.stem_usage` is `legacy_audio_mixing`;
5. the Request binds at least narration, BGM, and SFX stems, and their roles are
   `narration_stem`, `bgm_stem`, and `sfx_stem`;
6. the `org.book-video-factory.legacy-v4` extension is version `1.0`;
7. the extension's audio asset IDs exactly equal the core stem IDs;
8. its mix parameters use integer ticks, milli-LUFS, and milli-decibels—never floating-point JSON;
9. its audio Approval event IDs are non-empty and are a subset of the Request's satisfied events.

All other Preview and Final Requests still require an existing asset with role
`final_audio_mix`. A Renderer cannot opt into this exception by using an arbitrary extension.

## Version decision

The Schema remains `1.0` because this change implements the explicitly reserved v1 compatibility
case rather than changing the generic Renderer boundary. Existing conforming Requests remain
valid, and a non-legacy Request with `null` final mix remains invalid. The relaxation is encoded in
both JSON Schema conditionals and Python semantic validation.

## Exit condition

The exception must be removed from a future V4 migration when an upstream Audio Finalizer creates
and freezes a real final mix before Renderer selection. A new visual Renderer must not copy this
legacy extension.
