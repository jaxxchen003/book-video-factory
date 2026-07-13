# Book Video Factory Skill

An installable Codex skill for running a rights-aware, local-first workflow for Chinese book-review short videos. It creates an auditable workspace, guides the human approval gates, and records known run costs. It deliberately ships no book content, covers, music, SFX, voice samples, credentials, or production media.

## Install

```bash
npx skills add jaxxchen003/book-video-factory -g
```

Open a new Codex task in an empty workspace and say:

```text
Use $book-video-factory to bootstrap a workspace and create my first book-video project for <book title> by <author>.
```

The Skill is available on the next turn after installation.

## What it does

- Creates a clean factory/warehouse directory contract.
- Scaffolds idempotent project folders and a bilingual 15-line script template.
- Checks local planning/render dependencies without assuming macOS paths.
- Defines rights, source, caption, QC, and ChatCut handoff gates.
- Writes an append-only run-cost ledger that never invents token values.

## What you provide

You must provide or explicitly authorize all real-world media and accounts: book sources/covers, narration method or voice reference, BGM/SFX, image generation account, optional WeRead access, optional ChatCut account, and a publishing decision. Review the [first-run guide](skills/book-video-factory/references/first-run.md) before production.

## Bootstrap without Codex

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace .
python3 skills/book-video-factory/scripts/doctor.py --profile planning
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-first-book --book-title 'Example Book' --author 'Example Author'
```

## Safety and licence boundary

The MIT licence applies only to this repository's code and documentation. It does not grant rights to third-party books, covers, quotations, fonts, music, sound effects, voice recordings, generated assets, platforms, or provider models. Do not use this workflow to bypass platform access controls or to clone a voice without permission.

## Development checks

```bash
python3 -m unittest discover -s skills/book-video-factory/tests -v
```

When the Codex Skill Creator is available, also run its `quick_validate.py` against this repository root.
