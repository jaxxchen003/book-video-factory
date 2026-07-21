# First production run

## What installation gives you

This skill gives Codex a portable operating contract plus the deterministic factory runtime: renderer scripts, release profiles, schemas, dependency diagnostics, title safe-area logic, immutable manifests, hash-bound approvals, and the cost ledger. It does not contain a voice, cover, BGM, SFX, reference video, book text, external credentials, or a publishing account.

## Choose a style before rendering

- **双语编辑模板图书视频（原风格）** — `book-editorial-bilingual-v2`. Requires the V4 3:4 contract, a real cover with provenance, a 15-line Chinese/English script, and 12 approved distinct text-free stills (`S01`–`S12`).
- **VOX风格图书视频（新增风格）** — `paper-collage-explainer-v1`. Requires a `single-book` project, an explicit `gemini-api` or `google-flow` lane, approved narration timing, and a manifest-defined set of 4–8-second visual beats. It does not require exactly 12 clips.

Both styles require an approved topic/book match, attributable evidence, authorized narration, real timing data, permitted BGM/SFX with provenance, technical QC, local-master review, and a separate publish decision. Cover rights and native-English review apply when those elements are delivered.

## Supported paths

- **Local renderer path:** install Python 3.11+, Pillow, FFmpeg/FFprobe, and a permitted ASR/TTS implementation. Keep tool paths/configuration in the workspace, not in the Skill.
- **VOX / Gemini API path:** select `--style-profile paper-collage-explainer-v1 --generation-lane gemini-api`, keep `GEMINI_API_KEY` in the environment only, and run `doctor.py --profile production --project <project>` before generation.
- **VOX / Google Flow path:** select `--generation-lane google-flow`, work in the user's eligible Google account, and import only legitimate exports with prompt, credits, and hash provenance. Flow is not treated as a programmable API.
- **Editor-first path:** use ChatCut only if the user has installed/authenticated it. Keep the local master and subtitle file before importing. If ChatCut is unavailable, continue with local files and explain the missing polish step.
- **Research fallback:** if WeRead or another credentialed source is unavailable, use attributable public metadata or user-provided sources and record the source limitation. Never circumvent access controls.
- **Content-system-backed path:** use the original style with `--mode content-system-backed`, import a validated `dbs-content-system` JSON snapshot, and attach traceability after the script and V4 scene manifest exist. The current VOX profile rejects this mode until its manifest-based traceability contract is implemented.

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
