# Phase 3B Prerequisites

## Phase 3A gate

Phase 3B may start only after the Phase 3A branch is committed, pushed, and clean, with the final
regression still at 142/142 or higher.

Required evidence:

- four formal Schemas parse;
- Request/Result/Capability examples round-trip;
- a real derived Request hash passes integrity validation;
- Release Snapshot creation/write-once tests pass;
- original 73 tests remain green;
- no third-party dependency or forbidden renderer code entered Phase 3A.

## Only allowed next scope

Phase 3B should implement:

1. V4 release input collection into the immutable compatibility Release Snapshot;
2. V4-to-RenderRequest mapping based on `V4_TO_RENDERER_CONTRACT_MAP.md`;
3. `LegacyV4Renderer` facade around the unmodified existing chain;
4. injectable runner characterization without production media by default;
5. independent Attempt/Result collection and QC handoff;
6. tests proving stable mapping, fail-closed input handling, and no legacy behavior drift.

## Preconditions for the mapper

- explicit `release_id`;
- release-scoped Approval/Gate/Rights evidence;
- Project/Style/Release Profile consistency;
- all candidate assets resolved through Root bindings and SHA-bound;
- no path guessing after the Snapshot is frozen;
- existing V4 constants read/characterized, not promoted into the generic v1 Schema;
- persistent Request and Result paths use exclusive write semantics.

## Still prohibited

- Remotion/Node/React;
- a new visual Renderer;
- real media smoke unless separately approved as Phase 3C;
- FFmpeg filter graph, audio mix, Pillow layout or V4 constant changes;
- Provider/network calls;
- renaming the legacy Render Manifest as a Release Snapshot;
- rebase, force push, or silent migration of old outputs.

If Phase 3B discovers a mismatch that requires changing the frozen v1 contract, it must record and
review the decision before implementing that field; it must not hide it in a legacy extension.
