# Book Video Factory Skill

An installable Codex skill for running a rights-aware, local-first workflow for Chinese book-review short videos. It creates an auditable workspace, guides the human approval gates, and records known run costs. It deliberately ships no book content, covers, music, SFX, voice samples, credentials, or production media.

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

- Copies a clean, media-free deterministic factory runtime and warehouse directory contract.
- Scaffolds idempotent project folders and a bilingual 15-line script template.
- Checks local planning/render dependencies without assuming macOS paths.
- Defines rights, source, caption, QC, and ChatCut handoff gates.
- Writes an append-only run-cost ledger that never invents token values.
- Derives fail-closed workflow state from immutable manifests and hash-bound approval events.
- Fits long book titles to a named release profile with measured safe margins and semantic wrapping.
- Supports `single-book` and `content-system-backed` projects. The latter imports immutable `dbs-content-system` snapshots and validates `source_document / content_unit / claim / assembly_brief` objects.
- Records an auditable script-line → Claim → content-unit/source plus scene traceability map, backed by one renderer scene contract.

## Example outputs / 示例成片

These are full pipeline outputs, not source material bundled with the Skill. Click a poster to open the browser-based video player, or [open the complete showcase](https://jaxxchen003.github.io/book-video-factory/demos.html).

| 《界限》 | 《不去讨好任何人》 |
| --- | --- |
| [![《界限》成片封面](examples/posters/boundaries.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [![《不去讨好任何人》成片封面](examples/posters/no-people-pleasing.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |
| [Play video · 49.6s](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [Play video · 50.7s](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |

| 《原生家庭》 | 《高敏感是种天赋》 |
| --- | --- |
| [![《原生家庭》成片封面](examples/posters/original-family.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [![《高敏感是种天赋》成片封面](examples/posters/highly-sensitive.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |
| [Play video · 56.7s](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [Play video · 57.8s](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |

The demo videos are maintained showcase outputs and are **not** licensed under this repository's MIT licence. Book covers, titles, quotations, trademarks, music, and other third-party elements remain the property of their respective rights holders. Verify your rights before reusing or redistributing a demo.

## Recommended toolchain / 各环节推荐工具与能力

The Skill is the operating contract and orchestration layer; it does not silently install providers, models, accounts, media, or credentials. Each provider can be replaced if the same inputs, provenance records, quality gates, and release contract are preserved.

| Production stage | Recommended tool or capability | What it is used for | Requirement / boundary |
| --- | --- | --- | --- |
| Topic discovery / 选题 | Authorized [WeChat Reading Skill](https://github.com/Tencent/WeChatReading), attributable public book metadata, public trend/search data, and Codex research | Build the topic queue, compare angles, collect book facts and evidence | WeRead is optional and credential-gated; never bypass login or platform controls |
| Evidence and rights / 资料与授权 | Source manifest, URL/file hash, licence/authorization record, and a human approval gate | Keep every cover, quotation, voice reference, BGM and SFX auditable | Required before an asset can enter the approved set |
| Story and bilingual copy / 脚本与双语文案 | Codex writing/reasoning plus human editorial review; native-level English review when publishing internationally | Hook, 15-line story structure, Chinese captions and matched English captions | AI output is a draft; factual claims, quotations and translation require review |
| Scene images / 场景图 | Codex image generation using GPT Image, or another approved image provider | Generate 12 distinct, topic-specific, text-free 3:4 scenes | Save prompt, model/provider, generation date and approval state; do not ask the model to fake a real cover |
| Book cover / 真实书封 | Authorized WeRead/publisher/user-supplied cover plus provenance metadata | Composite the real edition cover into selected scenes | Keep the cover separate from generated art and confirm reuse rights |
| Narration / 人声 | [OpenBMB VoxCPM2](https://github.com/OpenBMB/VoxCPM) locally, or an authorized human/cloud TTS provider | Produce a stable channel voice and project narration | Lock one approved voice reference; clone only voices with explicit permission |
| Timing and captions / 对齐与字幕 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper), Whisper-compatible ASR, or an editor transcript | Derive word/segment timing, SRT/ASS and bilingual caption cues | Timing must come from real narration audio; never invent timestamps |
| BGM and SFX / 音乐与音效 | One project-specific licensed track, user-owned audio, or an authorized music-generation capability; optional ChatCut music generation | Establish mood, intro rhythm and voice ducking | Record creator/provider, licence, source, hash and attribution; never copy reference-video audio |
| Typography and graphics / 字体与图层 | [Pillow](https://python-pillow.org/) plus the bundled OFL SmileySans fallback or an operator-configured CJK/English font | Render centered titles, bilingual captions, outlines and safe margins | The bundled fallback is replaceable; verify any replacement font licence and keep a local font manifest |
| Deterministic render / 合成 | [FFmpeg and FFprobe](https://ffmpeg.org/) | 3:4 composition, image motion, transitions, mixing, ducking, encoding and media inspection | Required for the local-render path |
| Orchestration / 流水线调度 | Codex + this Skill's bootstrap, doctor and quality-gate contracts | Move an approved topic through research, assets, voice, render, QC and delivery | Human gates remain at topic, script, rights and publish approval |
| Cost ledger / 成本记录 | `scripts/run_cost.py` plus provider telemetry | Append image jobs, voice seconds, render seconds, retries and known Codex token counts | Missing telemetry is recorded as `—`, never guessed as zero |
| QC / 质检 | FFprobe, release manifests, source checks and human audio/visual review | Validate codec, audio stream, duration, captions, safe areas, provenance and versioning | Local QC must pass before editor handoff or publication |
| Fine edit / 精修 | Optional ChatCut project | Make scoped rhythm, subtitle, audio and motion adjustments on an editable timeline | Import only after local QC; export a new derivative and never overwrite the local master |

Minimum planning only needs Codex and Python 3.11+. A full local render normally needs Python 3.11+, FFmpeg/FFprobe, Pillow, one permitted image capability, one permitted narration path, an ASR timing path, an authorized BGM/SFX source, and enough disk space. Run `doctor.py` to distinguish planning-ready from render-ready.

## What you provide

You must provide or explicitly authorize all real-world media and accounts: book sources/covers, narration method or voice reference, BGM/SFX, image generation account, optional WeRead access, optional ChatCut account, and a publishing decision. Review the [first-run guide](skills/book-video-factory/references/first-run.md) before production.

## Bootstrap without Codex

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace .
python3 skills/book-video-factory/scripts/doctor.py --profile planning
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-first-book --book-title 'Example Book' --author 'Example Author'
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

The upstream system remains authoritative for audits, content-unit extraction, theme maps, relationships, deduplication, canonical versions, and topic assembly. The video factory only consumes a validated snapshot and never rewrites the upstream system.

## Safety and licence boundary

The MIT licence applies only to this repository's code and documentation. It does not grant rights to third-party books, covers, quotations, fonts, music, sound effects, voice recordings, generated assets, platforms, or provider models. Do not use this workflow to bypass platform access controls or to clone a voice without permission.

## Development checks

```bash
python3 -m unittest discover -s skills/book-video-factory/tests -v
python3 -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
```

When the Codex Skill Creator is available, also run its `quick_validate.py` against this repository root.
