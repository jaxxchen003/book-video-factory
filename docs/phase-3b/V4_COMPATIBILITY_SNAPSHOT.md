# V4 Compatibility Release Snapshot

## Boundary

`collect_v4_release()` creates a new, immutable compatibility evidence document and Release
Snapshot. It does not rename, read as truth, or overwrite legacy `render_manifest.v4.json`.

The collector is local and fail-closed. It performs no Provider, API, or network call and does not
run FFmpeg, Pillow rendering, or Post-QC.

## Frozen inputs

The Snapshot binds:

- Project Manifest, Style Profile, Release Profile, video style, and three legacy code sources;
- the approved 15-line bilingual script and ordered `V01`–`V15` contract;
- 12 present and byte-unique `S01`–`S12` PNG assets;
- real-cover Manifest and the exact cover file selected by legacy V4;
- source narration WAV, ASR word timing, the single V4 BGM, and approved H2 stem;
- title, Chinese, and English font assets under injected logical roots;
- current Approval event files for the explicit Release;
- canonical artifact byte lengths and SHA-256 indexes.

Required pre-render gates are `script`, `timing`, `visual_rights`, `cover_rights`, `bgm_rights`,
`sfx_rights`, and `voice_rights`. Every Approval must be current, match the explicit Release, and
cover all files assigned to its gate. `english_native` and `publish` remain post-render publication
gates and do not block the same render that creates the local master.

## Timing evidence

ASR-to-script alignment characterizes the locked V4 behavior in this order:

1. exact ordered matching;
2. the existing ordered fuzzy policy;
3. the existing proportional fallback.

The collector then freezes the V4 intro edit: remove 20 ms at the end of V02, insert 1040 ms of
silence, and shift following timing by 1020 ms. Montage duration is 960 ms and Outro duration is
2500 ms. Source narration duration is read from the WAV header with the Python standard library.

All persisted timing uses integer milliseconds and `integer_round_half_up_v1`. The compatibility
evidence and Request contain no floating-point value.

## Mapper rule

`map_v4_snapshot_to_request()` accepts a validated Snapshot, its portable ref, injected root
bindings, and a Capability ref. It reads only SHA-bound evidence and Snapshot assets. It does not
glob the Project, select another cover/BGM/font, or recompute approvals after freeze.

The mapped Timeline has 13 continuous segments: the 12 named V4 scenes plus an explicit Montage.
It covers `[0, duration_ticks)` without gaps or overlaps. Bilingual captions are two tracks so the
Chinese and English font assets are independently bound. The Book segment binds both S03 and the
real cover as layered input rather than pretending the derived composite already exists.
