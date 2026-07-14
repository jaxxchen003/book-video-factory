# Release quality gates

## Project contract

- `project.json` exists and identifies the topic, book, workflow mode, and release profile. Its status field is a compatibility cache, not the publish-state source of truth.
- Each stage writes a manifest or an append-only cost event.
- A revision writes a new release directory; no existing delivery is overwritten.
- `workflow.py evaluate` derives the current state from files, hashes, manifests, and approval events; direct JSON edits cannot advance a gate.

## Editorial and rights gates

- Claims have source evidence and editorial review.
- The cover record identifies source URL, acquisition date, rights/usage decision, and reviewer.
- BGM/SFX provenance identifies creator, licence or user authorization, source URL/file hash, and attribution text.
- Voice design/clone records user authorization. Do not clone a public figure, another creator, or an unconsenting person.
- English copy remains `needs_native_review` until a reviewer approves it.

## V4-style asset and delivery gates

- Exactly 12 distinct approved scene files are present as `S01.png` through `S12.png`.
- Every scene is topic-specific, text-free, and free of a copied book-cover design or watermark.
- The local master is 3:4, includes an audio stream, has readable bilingual captions, and respects title/subtitle safe areas.
- A delivery manifest lists local master, subtitles, source records, QC result, and release decision.
- A failed rights, native-review, or publish gate blocks the `ready_to_publish` state even when technical rendering succeeds.

## ChatCut handoff gate

- Import only a locally QC-passed master and its subtitle file.
- Record the editor project ID, edit summary, export path, reviewer, and revision label.
- Keep the local master immutable and publish the ChatCut export as a distinct derivative version.
