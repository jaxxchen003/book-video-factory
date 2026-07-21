---
name: book-video-factory
description: Create or operate a portable, auditable Chinese book-review short-video workflow from a clean local workspace. Use when starting a book-video factory, producing a 3:4 bilingual package or a 9:16 editorial paper-collage explainer, importing dbs-content-system source documents and QST/CON/OPI/CAS/SOL content units, linking script claims to evidence and scenes, using approved Gemini API or Google Flow assets, collecting rights-aware media, recording run cost, or preparing a local master for optional ChatCut fine editing.
---

# 图书号短视频工厂

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

- **`book-editorial-bilingual-v2`** — deterministic 3:4 bilingual template with real cover, approved stills, local narration, rendered captions, and optional 9:16 derivative.
- **`paper-collage-explainer-v1`** — 9:16 editorial paper-collage explainer. Split narration into one 4–8 second concept/visual-metaphor unit at a time; approve the metaphor, still/contact sheet, and generated clip separately. Read [references/paper-collage-explainer.md](references/paper-collage-explainer.md) before selecting this profile.

For `paper-collage-explainer-v1`, choose one generation lane explicitly:

- **Gemini API** — programmatic lane. Requires a user-authorized `GEMINI_API_KEY`, the current Google Gen AI SDK, provider cost/quota approval, and an immutable operation/output record. Use Gemini Omni Flash by default; use Veo 3.1 when first/last-frame control or Veo extension is required.
- **Google Flow** — manual creative lane. Requires an eligible Google AI subscription and desktop Chromium session. Do not assume Flow exposes a programmable API; download/export only user-authorized outputs and record prompts, credits exposed by the UI, asset hashes, and manual-run provenance.

## Production sequence

1. **Topic and evidence** — collect public, attributable book metadata. If a WeRead credential or another data source is unavailable, record the limitation and use user-supplied/publicly attributable evidence; do not bypass logins or platform restrictions.
2. **Script** — create a concise Chinese script plus an English production draft. Keep claims tied to evidence and mark the English version `needs_native_review` until approved.
3. **Assets** — obtain a real cover with provenance, 12 topic-specific scenes without embedded text, a permitted BGM with attribution, and either a user-authorized narration reference or an explicitly approved synthetic voice design.
4. **Voice and timing** — generate/record narration only with authorization. Create a timing map with a permitted local ASR tool or an editor transcript; never silently invent timestamps.
5. **Render** — build a 3:4 local master with centered title treatment, bilingual captions, safe margins, and project-specific music/SFX. For `paper-collage-explainer-v1`, normalize approved silent 9:16 clips into a separate timeline, then add project-owned narration, captions, BGM, and SFX locally. Use an original/generated SFX or a user-supplied file with recorded rights; never copy a reference video's audio.
6. **QC and delivery** — run technical checks, verify all release gates, write a manifest and cost events, then optionally import the passed local master into ChatCut for fine editing.

## Workflow contracts

- Use `config/release_profiles/book-v4-bilingual-3x4.json` as the named V4 contract instead of treating V4 dimensions and bilingual layout as universal constants.
- Use `scripts/workflow.py evaluate --release-id <release-id>` to derive a release-scoped workflow state. `project.json.status` is not an approval mechanism, and approvals from different releases are never combined.
- Record human decisions with `scripts/workflow.py approve`; approvals bind to the reviewed file hash and become stale after edits.
- Use `scripts/workflow.py manifest-stage` for immutable stage manifests with input/output hashes.
- Long titles are pixel-measured, semantically wrapped to at most two lines, and fail closed if they cannot fit the configured safe area.
- Keep `dbs-content-system` upstream: it owns source audits, `QST / CON / OPI / CAS / SOL`, theme maps, relationships, deduplication, canonical versions, and assembly. Do not reproduce those algorithms in this Skill.
- For `content-system-backed`, use `scripts/content_bridge.py export-dbs`, `validate-package`, `import-package`, `attach-traceability`, and `status`. `export-dbs` is serialization only; it does not perform upstream semantic work. Imports and active-version changes are append-only and hash-bound.
- A valid bridge package contains `source_document / content_unit / claim / assembly_brief`; the traceability map connects every script line to reviewed Claim evidence or an explicit editorial exemption, and to the renderer's actual scene contract. A human `traceability` approval bound to that map is required before `assets_ready`.

## Required release gates

- Do not use a generated imitation as a book cover. Record the actual cover source and rights/usage status.
- Do not reuse copyrighted music, sound effects, reference-video audio, a person's voice, public-figure likeness, or account branding without explicit rights.
- Require 12 non-duplicate numbered scene files (`S01`–`S12`) for a V4-style delivery.
- Do not mark native English review, cover rights, BGM attribution, or user approval as complete when they are absent.
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
