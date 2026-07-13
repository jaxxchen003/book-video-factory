---
name: book-video-factory
description: Create or operate a portable, auditable Chinese book-review short-video workflow from a clean local workspace. Use when starting a book-video factory, turning an approved book topic into a 3:4 bilingual short-video package, collecting rights-aware sources, generating a script/assets/voice/BGM plan, recording run cost, or preparing a local master for optional ChatCut fine editing.
---

# 图书号短视频工厂

## First use

1. Resolve `SKILL_ROOT` as the directory containing this `SKILL.md`; do not assume a particular user home directory, operating system, brand, voice, font, or credential.
2. In an empty or new workspace, run:

   ```bash
   python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py --workspace .
   python3 <SKILL_ROOT>/scripts/doctor.py --profile planning
   ```

3. Create a project only after the user approves the book/topic:

   ```bash
   python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py \
     --workspace . --slug <slug> --book-title '<title>' --author '<author>'
   ```

4. Read `references/first-run.md` before generating the first production package. Read `references/quality-gates.md` before declaring a release ready.

## Working model

- Keep reusable workflow/configuration in `book_video_factory/` and project-specific evidence/media in `book_video_warehouse/`.
- Treat all book covers, quotations, BGM, voice references, reference videos, generated assets, and credentials as user-owned/project-local inputs. Never ship, download, clone, or reuse a hidden default asset.
- Create a new release directory for every revision. Preserve the local master as the source of truth; ChatCut is an optional editable polish layer.
- Keep human gates for topic approval, script approval, source/rights approval, native-language review, and publish approval.

## Production sequence

1. **Topic and evidence** — collect public, attributable book metadata. If a WeRead credential or another data source is unavailable, record the limitation and use user-supplied/publicly attributable evidence; do not bypass logins or platform restrictions.
2. **Script** — create a concise Chinese script plus an English production draft. Keep claims tied to evidence and mark the English version `needs_native_review` until approved.
3. **Assets** — obtain a real cover with provenance, 12 topic-specific scenes without embedded text, a permitted BGM with attribution, and either a user-authorized narration reference or an explicitly approved synthetic voice design.
4. **Voice and timing** — generate/record narration only with authorization. Create a timing map with a permitted local ASR tool or an editor transcript; never silently invent timestamps.
5. **Render** — build a 3:4 local master with centered title treatment, bilingual captions, safe margins, and project-specific music/SFX. Use an original/generated SFX or a user-supplied file with recorded rights; never copy a reference video's audio.
6. **QC and delivery** — run technical checks, verify all release gates, write a manifest and cost events, then optionally import the passed local master into ChatCut for fine editing.

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
