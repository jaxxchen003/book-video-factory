---
name: book-video-factory
description: Create or operate a portable, auditable Chinese book-review short-video workflow from a clean local workspace. Use when starting a book-video factory, choosing between the original 3:4 bilingual editorial style and the new 9:16 VOX-style book-video workflow, importing dbs-content-system source documents and QST/CON/OPI/CAS/SOL content units, linking script claims to evidence and scenes, using approved Gemini API or Google Flow assets, collecting rights-aware media, recording run cost, or preparing a local master for optional ChatCut fine editing.
---

# 图书视频工厂

## First use

1. Resolve `SKILL_ROOT` as the directory containing this `SKILL.md`; do not assume a particular user home directory, operating system, brand, voice, font, or credential.
2. In an empty or new workspace, run:

   ```bash
   python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py --workspace .
   python3 <SKILL_ROOT>/scripts/doctor.py --profile planning
   ```

   Bootstrap copies the bundled deterministic runtime into `book_video_factory/`; it does not download hidden media or depend on the maintainer's machine.

3. Create a project only after the user approves the book/topic:

   ```bash
   python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py \
     --workspace . --slug <slug> --book-title '<title>' --author '<author>'
   ```

   If the topic comes from a structured content asset system, add `--mode content-system-backed`. This mode requires a validated content package and traceability map before assets can pass their gate.

4. Read `references/first-run.md` before generating the first production package. Read `references/quality-gates.md` before declaring a release ready.

## Working model

- Keep reusable workflow/configuration in `book_video_factory/` and project-specific evidence/media in `book_video_warehouse/`.
- Treat all book covers, quotations, BGM, voice references, reference videos, generated assets, and credentials as user-owned/project-local inputs. Never ship, download, clone, or reuse a hidden default asset.
- Create a new release directory for every revision. Preserve the local master as the source of truth; ChatCut is an optional editable polish layer.
- Keep human gates for topic approval, script approval, source/rights approval, native-language review, and publish approval.

## Style profiles

Select one style profile before making assets; never silently mix their frame, typography, or review contracts.

- **双语编辑模板图书视频（原风格）** — machine ID `book-editorial-bilingual-v2`. Deterministic 3:4 bilingual template with a real cover, 12 approved stills, local narration, rendered captions, and an optional 9:16 derivative.
- **VOX风格图书视频（新增风格）** — machine ID `paper-collage-explainer-v1`. A 9:16, voice-led editorial paper-collage explainer made from 4–8-second visual beats. It is a descriptive public label, not an affiliation claim or permission to imitate a named publisher/program. Read [references/paper-collage-explainer.md](references/paper-collage-explainer.md) before selecting it.

The original style is the backward-compatible default. For VOX style, create the project with `--style-profile paper-collage-explainer-v1` and explicitly choose one generation lane:

- **`gemini-api`** — programmatic lane. Requires a user-authorized `GEMINI_API_KEY`, the current Google Gen AI SDK, provider cost/quota approval, and an immutable operation/output record. Use `gemini-omni-flash-preview` through the Interactions API by default; use `veo-3.1-generate-preview` through `generate_videos` when first/last-frame control or video extension is required.
- **`google-flow`** — manual creative lane. Requires current account/region eligibility, an eligible Google AI plan, available credits, and a user-operated browser session. Do not assume Flow exposes a programmable API; import only user-authorized exports and record prompts, visible credits, hashes, and manual-run provenance.

The VOX-style path is currently an orchestration-and-import workflow. Do not claim this repository bundles a one-click Google video generator.
The current `dbs-content-system` scene-traceability contract is V4-specific, so `content-system-backed` is supported by the original style only; VOX style is fail-closed to `single-book` until a manifest-based traceability contract is implemented and tested.

## Production sequence

1. **Topic and evidence** — collect public, attributable book metadata. If a WeRead credential or another data source is unavailable, record the limitation and use user-supplied/publicly attributable evidence; do not bypass logins or platform restrictions.
2. **Script, voice, and timing** — create and approve a concise Chinese script plus any English production draft. Generate/record narration only with authorization; derive timestamps from actual audio via permitted ASR or an editor transcript. Never invent timing. VOX style locks this timing before full clip generation.
3. **Style-specific assets** — the original style obtains a real cover plus 12 approved text-free stills. VOX style approves one metaphor, then a first/last frame or contact sheet, then each generated visual beat; prompts use non-branded editorial descriptors.
4. **Picture lock** — map approved assets to the locked narration. Normalize VOX clips to silent 720×1280 H.264 at the local 30 fps timeline without speed changes; inspect cadence and keep optical flow off by default.
5. **Audio and render** — add project-owned narration, local captions, permitted BGM and SFX. BGM rights approval and creative `bgm_review` are separate decisions. Never copy a reference video's audio.
6. **QC and delivery** — run technical and human gates, bind approvals to hashes, write manifests and cost events, then optionally import the passed local master into ChatCut for fine editing.

## Workflow contracts

- `project.json.workflow.style_profile_id` selects the visual workflow; its mapped `release_profile_id` selects the renderer/output contract. Existing projects without a style ID fall back to the original style only for compatibility.
- Use `config/release_profiles/book-v4-bilingual-3x4.json` for the original style and `config/release_profiles/book-vox-vertical-9x16-v1.json` for VOX style; never treat either style's dimensions or assets as universal constants.
- Use `scripts/workflow.py evaluate --project <project> --release-id <release-id>` to resolve the project profile and derive a release-scoped state. `project.json.status` is not an approval mechanism, and approvals from different releases are never combined.
- Record human decisions with `scripts/workflow.py approve`; approvals bind to the reviewed file hash and become stale after edits.
- Use `scripts/workflow.py manifest-stage` for immutable stage manifests with input/output hashes.
- Long titles are pixel-measured, semantically wrapped to at most two lines, and fail closed if they cannot fit the configured safe area.
- Keep `dbs-content-system` upstream: it owns source audits, `QST / CON / OPI / CAS / SOL`, theme maps, relationships, deduplication, canonical versions, and assembly. Do not reproduce those algorithms in this Skill.
- For `content-system-backed`, use `scripts/content_bridge.py export-dbs`, `validate-package`, `import-package`, `attach-traceability`, and `status`. `export-dbs` is serialization only; it does not perform upstream semantic work. Imports and active-version changes are append-only and hash-bound.
- A valid bridge package contains `source_document / content_unit / claim / assembly_brief`; the traceability map connects every script line to reviewed Claim evidence or an explicit editorial exemption, and to the renderer's actual scene contract. A human `traceability` approval bound to that map is required before `assets_ready`.

## Required release gates

- Do not use a generated imitation as a book cover. Record the actual cover source and rights/usage status.
- Do not reuse copyrighted music, sound effects, reference-video audio, a person's voice, public-figure likeness, or account branding without explicit rights.
- Require 12 non-duplicate numbered stills (`S01`–`S12`) only for the original V4-style delivery. VOX style uses its approved clip manifest and does not impose a universal scene count.
- For VOX style, keep `source_audit`, `gate_1_metaphor`, `gate_2_still`, `gate_3_clip_qa`, `bgm_review`, `audio_qc`, `local_master_review`, and `publish` as distinct hash-bound gates. Apply `cover_rights` and `english_native` only when those elements are delivered.
- Accept invisible provider provenance such as SynthID; do not remove or tamper with it. Reject visible third-party watermarks.
- Never invent token counts. Record only usage values exposed by the relevant provider.

## Cost ledger

Use the bundled append-only ledger for known usage and operational facts:

```bash
python3 <SKILL_ROOT>/scripts/run_cost.py record \
  --warehouse book_video_warehouse --project <slug> --stage assets.generate \
  --images 12 --note 'Approved scene images'
python3 <SKILL_ROOT>/scripts/run_cost.py report --warehouse book_video_warehouse
```

`—` in a report means the usage was not available; it is not zero cost.

## ChatCut handoff

Use ChatCut only after local QC passes. Import the local master and subtitle file, make scoped editorial changes, and export `v4-chatcut-<revision>` without overwriting the local master. Record the project ID, edits, reviewer decision, and export path in the project delivery manifest.
