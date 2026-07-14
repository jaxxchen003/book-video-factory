# First production run

## What installation gives you

This skill gives Codex a portable operating contract plus the deterministic factory runtime: renderer scripts, release profiles, schemas, dependency diagnostics, title safe-area logic, immutable manifests, hash-bound approvals, and the cost ledger. It does not contain a voice, cover, BGM, SFX, reference video, book text, external credentials, or a publishing account.

## Minimum inputs before rendering

1. A topic and an approved book/title/author match.
2. Evidence records and a cover source record.
3. A 15-line Chinese script and English production draft.
4. Twelve approved, distinct, text-free scene images (`S01`–`S12`).
5. An authorized narration method and a timing map.
6. One permitted BGM plus attribution/provenance.
7. A project-specific original or rights-cleared intro SFX.

## Supported paths

- **Local renderer path:** install Python 3.11+, Pillow, FFmpeg/FFprobe, and a permitted ASR/TTS implementation. Keep tool paths/configuration in the workspace, not in the Skill.
- **Editor-first path:** use ChatCut only if the user has installed/authenticated it. Keep the local master and subtitle file before importing. If ChatCut is unavailable, continue with local files and explain the missing polish step.
- **Research fallback:** if WeRead or another credentialed source is unavailable, use attributable public metadata or user-provided sources and record the source limitation. Never circumvent access controls.
- **Content-system-backed path:** create the project with `--mode content-system-backed`, import a validated `dbs-content-system` JSON snapshot, and attach traceability after the script and scene manifest exist. The Skill preserves upstream relative paths and hashes but never edits the upstream content system.

## Content-system bridge sequence

```bash
python3 book_video_factory/scripts/content_bridge.py export-dbs \
  --content-root /path/to/content-system \
  --assembly /path/to/content-system/06-选题装配/topic.md \
  --output /path/to/package.json
python3 book_video_factory/scripts/content_bridge.py validate-package --package /path/to/package.json
python3 book_video_factory/scripts/content_bridge.py import-package \
  --project book_video_warehouse/projects/<slug> --package /path/to/package.json
python3 book_video_factory/scripts/content_bridge.py attach-traceability \
  --project book_video_warehouse/projects/<slug> --map /path/to/traceability.json
python3 book_video_factory/scripts/workflow.py approve \
  --project book_video_warehouse/projects/<slug> --release-id <release-id> \
  --gate traceability --decision approved --reviewer '<reviewer>' \
  --subject 02_story_script_故事脚本/traceability/<release-id>/<attached-map>.json
python3 book_video_factory/scripts/content_bridge.py status \
  --project book_video_warehouse/projects/<slug> --require traceability
```

See `book_video_factory/docs/CONTENT_SYSTEM_BRIDGE.md` in the bootstrapped runtime for the package contract and fail-closed rules.

## First-run review questions

- Is the user entitled to use the cover, quotations, BGM, sound effect, voice reference, and reference style?
- Are medical, mental-health, financial, or legal claims framed as non-diagnostic editorial commentary rather than advice?
- Has a native reviewer approved the English copy if this will be published internationally?
- Are all provider usage/cost figures sourced from real provider telemetry rather than inferred from output files?
