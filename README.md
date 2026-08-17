# Book Video Factory Skill

[简体中文](README.zh-CN.md) · **English**

An installable Codex skill for running a rights-aware, local-first workflow for Chinese book-review short videos. It offers two separate styles: the original **Bilingual Editorial Book Video** and the new **VOX-style Book Video**, while keeping evidence, generation provenance, human approvals, costs, and release decisions auditable.

The repository deliberately ships no reusable book content, covers, music, SFX, voice samples, credentials, or hidden production assets. The videos under `examples/` are maintained showcase derivatives and are not part of the MIT-licensed source package.

## Install

```bash
npx skills add jaxxchen003/book-video-factory --skill book-video-factory -g -y
```

Open a new Codex task in an empty workspace and say:

```text
Use $book-video-factory to bootstrap a workspace and create my first book-video project for <book title> by <author>.
```

The Skill is available on the next turn after installation.

## What it does

- Copies a clean, media-free deterministic runtime and warehouse directory contract.
- Scaffolds idempotent project folders and a bilingual script template.
- Supports `single-book` and `content-system-backed` evidence packages.
- Links script lines to Claims, source material, scene contracts, and immutable manifests.
- Separates technical QC from human reviews for story, visual metaphor, BGM, rights, native-language copy, and publication.
- Derives fail-closed release state from file hashes and release-scoped approval events.
- Writes an append-only cost ledger without inventing missing provider usage.
- Preserves the local master as the source of truth; ChatCut remains an optional fine-edit derivative layer.

## Style profiles

Choose one profile before generating assets. Do not silently mix their aspect ratio, typography, asset, or approval contracts.

| Public style | Machine ID | Output | Core asset contract |
| --- | --- | --- | --- |
| Bilingual Editorial Book Video (original) | `book-editorial-bilingual-v2` | 3:4 bilingual master, optional 9:16 derivative | Real authorized cover, 12 approved stills, local narration, bilingual captions, deterministic FFmpeg render |
| VOX-style Book Video (new) | `paper-collage-explainer-v1` | 9:16 voice-led editorial explainer | One 4–8 second visual beat per information change; separate metaphor, frame, clip, BGM, local-master, and publish approvals |

Read the complete [`paper-collage-explainer-v1` workflow](skills/book-video-factory/references/paper-collage-explainer.md) before selecting the new profile.

“VOX-style” is a descriptive public label only. It does not claim affiliation with Vox Media and is not an instruction to imitate a named publisher, show, logo, or proprietary brand package. Generation prompts use non-branded editorial paper-collage descriptors.

The built-in VOX-style profile currently supports `single-book` projects. `content-system-backed` remains available to the original style because its traceability implementation is still tied to the V4 scene-line contract.

### Gemini API or Google Flow

The VOX-style profile has two explicit generation lanes. The local factory still owns narration timing, captions, BGM, SFX, QC, manifests, and the final master. The current repository is an orchestration-and-import workflow; it does not claim to bundle a one-click Google video generator.

| Lane | Use it when | Dependency and boundary |
| --- | --- | --- |
| `gemini-api` | You need reproducible programmatic generation, operation tracking, or batch processing | User-authorized `GEMINI_API_KEY`, current Google Gen AI SDK, approved quota/cost. Use `gemini-omni-flash-preview` through the Interactions API; use `veo-3.1-generate-preview` through `generate_videos` for first/last-frame control or extension. Never write the key to prompts, logs, or manifests. |
| `google-flow` | A human director wants to iterate each visual beat in Google's creative UI | Current account/region eligibility, an eligible Google AI plan, available credits, a user-operated browser, and authorized exports. Flow is a manual UI lane; this Skill does not assume a programmable Flow API. |

For either lane, record the prompt, model or Flow label, input/output hashes, operation or export evidence, exposed cost/credits, reviewer, and scene ID. Generated audio is stripped before the project-owned local mix unless it has a separate explicit approval.

### Core VOX-style workflow

1. Lock attributable evidence and approve a concise Chinese script.
2. Record/generate authorized narration, derive real ASR timing, and split it into one 4–8 second information change per visual beat.
3. Gate 1: approve `concept → visible metaphor → animation action → prohibitions`.
4. Gate 2: approve the first/last frame or contact sheet.
5. Gate 3: generate through Gemini API or Google Flow and inspect duration, ratio, watermark, text pollution, motion continuity, and decodability.
6. Normalize approved clips to silent 720×1280 H.264 media on the 30 fps local timeline without changing speed.
7. Lock picture to narration/ASR timing; add local captions, authorized BGM, SFX, and project branding. Review BGM rights and creative fit separately.
8. Run technical QC and bind visual, audio, local-master, rights, and publication decisions to immutable hashes.

## Example outputs / 示例成片

These are full-pipeline showcase outputs, not source material bundled with the Skill. Click a poster to open the browser player, or [open the complete showcase](https://jaxxchen003.github.io/book-video-factory/demos.html).

### Featured VOX-style case: 《超越百岁》

[![《超越百岁》VOX风格图书视频](examples/posters/chaoyue-baisui-paper-collage.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#chaoyue-baisui)

[VOX-style Book Video · `paper-collage-explainer-v1` · Play · 82.7s · 9:16](https://jaxxchen003.github.io/book-video-factory/demos.html#chaoyue-baisui)

This public web preview is derived from the user-approved r5 local master. The source master remains immutable and is **not** recorded as production-publish-approved; the sanitized repository derivative has a separate operator approval. For the repository showcase, the real cover region at the beginning was replaced and the video was web-compressed. See the [case provenance manifest](examples/manifests/chaoyue-baisui-paper-collage.json) and [sanitized gate summary](examples/manifests/chaoyue-baisui-r5-gate-summary.json). Provider-account terms were not independently verified by this repository, and inclusion does not license the book, title, translation, music, or any third-party material for reuse.

| 《界限》 | 《不去讨好任何人》 |
| --- | --- |
| [![《界限》成片封面](examples/posters/boundaries.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [![《不去讨好任何人》成片封面](examples/posters/no-people-pleasing.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |
| [Play video · 49.6s](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [Play video · 50.7s](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |

| 《原生家庭》 | 《高敏感是种天赋》 |
| --- | --- |
| [![《原生家庭》成片封面](examples/posters/original-family.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [![《高敏感是种天赋》成片封面](examples/posters/highly-sensitive.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |
| [Play video · 56.7s](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [Play video · 57.8s](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |

The demo videos are maintained showcase outputs and are **not** licensed under this repository's MIT licence. Book covers, titles, quotations, trademarks, music, and other third-party elements remain the property of their respective rights holders. Verify your rights before reusing or redistributing a demo.

## Recommended toolchain

The Skill is the operating contract and orchestration layer; providers remain replaceable when the same inputs, provenance, approval gates, and release contract are preserved.

| Production stage | Recommended tool or capability | Requirement / boundary |
| --- | --- | --- |
| Topic and evidence | Authorized WeChat Reading Skill, attributable public metadata, user-supplied sources, Codex research | Never bypass login or platform controls; reader reviews are viewpoints, not factual evidence |
| Story and bilingual copy | Codex writing/reasoning plus human editorial review | Claims and quotations require source review; English stays `needs_native_review` until approved |
| Editorial stills | Codex image generation with GPT Image or another approved provider | Save prompt, model, date, hash, and approval; never generate a fake real-world book cover |
| VOX-style visual beats | Gemini API with `gemini-omni-flash-preview` / `veo-3.1-generate-preview`, or user-operated Google Flow | Requires user authorization, provider cost/credit approval, immutable prompts and operation/export provenance |
| Narration | Local VoxCPM2, authorized human voice, or approved cloud TTS | Clone only voices with explicit permission and record the authorization |
| Timing and captions | faster-whisper, Whisper-compatible ASR, or editor transcript | Derive timing from the real narration; never invent timestamps |
| Book cover | Authorized publisher/retailer/user-supplied cover plus provenance metadata | Keep it separate from generated art and clear reuse rights before public release |
| BGM and SFX | Licensed, user-owned, or authorized generated audio; optional ChatCut music | Record creator/provider, licence or authorization, source/hash, and attribution |
| Typography and graphics | Pillow, bundled OFL SmileySans fallback, or an operator-configured font | Verify replacement-font licences and preserve safe areas |
| Deterministic render | FFmpeg and FFprobe | Required for local composition, normalization, mixing, encoding, and media inspection |
| QC and release | Release manifests, source checks, technical probes, and human review | Local QC is not publication approval; rights and publish gates remain separate |

Minimum planning needs Codex and Python 3.11+. A full local render normally also needs FFmpeg/FFprobe, Pillow, approved image/video generation, a narration path, ASR timing, authorized audio, and enough disk space. Run `doctor.py` to distinguish planning-ready from render-ready.

## What you provide

You must provide or explicitly authorize real-world media and accounts: book sources/covers, narration method or voice reference, BGM/SFX, image/video generation accounts, optional WeRead access, optional Gemini API or Google Flow access, optional ChatCut access, and the final publishing decision. Review the [first-run guide](skills/book-video-factory/references/first-run.md) before production.

## Bootstrap without Codex

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace .
python3 skills/book-video-factory/scripts/doctor.py --profile planning
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-first-book --book-title 'Example Book' --author 'Example Author'
```

The command above creates the original style. A VOX-style project must select its generation lane explicitly:

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-vox-book --book-title 'Example Book' --author 'Example Author' \
  --style-profile paper-collage-explainer-v1 \
  --generation-lane gemini-api

# Or use: --generation-lane google-flow
```

For a project backed by an upstream content asset system:

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-topic --book-title 'Example Book' --author 'Example Author' \
  --mode content-system-backed

python3 book_video_factory/scripts/content_bridge.py export-dbs \
  --content-root /path/to/content-system \
  --assembly /path/to/content-system/06-选题装配/topic.md \
  --output /path/to/content-package.json
python3 book_video_factory/scripts/content_bridge.py validate-package \
  --package /path/to/content-package.json
python3 book_video_factory/scripts/content_bridge.py import-package \
  --project book_video_warehouse/projects/my-topic \
  --package /path/to/content-package.json
```

The upstream system remains authoritative for audits, content-unit extraction, relationships, deduplication, canonical versions, and topic assembly. The video factory consumes a validated snapshot and never rewrites the upstream system.

## Safety and licence boundary

The MIT licence applies only to this repository's code and documentation. It does not grant rights to books, covers, quotations, fonts, music, sound effects, voices, generated outputs, platforms, or provider models. Do not bypass platform access controls, expose credentials, imitate a protected brand/program identity, or clone a voice without permission.

## Development checks

```bash
python3 -m unittest discover -s skills/book-video-factory/tests -v
python3 -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
```

When Codex Skill Creator is available, also run its `quick_validate.py` against `skills/book-video-factory`.

[https://www.star-history.com/?repos=jaxxchen003%2Fbook-video-factory&type=date&legend=top-left](https://www.star-history.com/?repos=jaxxchen003%2Fbook-video-factory&type=date&legend=top-left)
