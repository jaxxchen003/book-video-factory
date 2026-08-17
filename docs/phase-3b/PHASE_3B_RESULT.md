# Phase 3B Result

## Status

Phase 3B implementation and pure-unit verification are complete.

Delivered:

- immutable V4 compatibility evidence and Release Snapshot collection;
- release-scoped Gate/Rights/Approval freezing;
- V4-to-RenderRequest mapping with no post-freeze path guessing;
- a narrowly controlled legacy audio-mixing contract amendment;
- exact Legacy V4 Capability declaration;
- atomic write-once Request, Attempt event, and Result persistence;
- injectable `LegacyV4Renderer` runner and Probe facade;
- output/sidecar/Probe collection and independent QC handoff;
- 13 synthetic tests and full 155/155 regression.

## Scope audit

No existing V1–V5, Showcase, FFmpeg graph, audio graph, Pillow layout, Provider, Gate evaluator,
Stage Manifest, or Post-QC implementation was modified. No Remotion, Node, React, dependency,
credential, absolute persisted path, or network behavior was added.

`render_manifest.v4.json` remains a legacy execution sidecar and is not treated as a Release
Snapshot. Renderer success remains distinct from Post-QC and publication approval.

## Next gate

Phase 3C may start only with explicit approval for a real-media smoke fixture. It should validate
the same Request through the facade, compare output semantics with the established chain, run
Post-QC outside the facade, and retain all Attempt/Result evidence.
