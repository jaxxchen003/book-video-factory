# Phase 3A Test Result

## Environment and scope

Tests ran locally on Windows from the repository root. They used Python standard library and existing
repository dependencies only. No network, provider, external API, model/font download, FFmpeg
execution, production asset, or media generation was used.

## Pre-implementation baseline

```text
python -m unittest discover -s skills/book-video-factory/tests -v
Ran 8 tests: OK

python -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
Ran 65 tests: OK

Original total: 73/73
Failure: 0; Error: 0; Skip: 0
```

## New Phase 3A suite

```text
test_renderer_contract_core.py
Ran 69 tests: OK
Failure: 0; Error: 0; Skip: 0
```

Coverage includes:

- frozen models and all required stable enums;
- exact Request/Result/Capability/Snapshot round-trip;
- missing/unknown/Unicode fields;
- JSON Schema parse and required metadata;
- Windows drive, UNC, POSIX absolute, `..`, NUL, Unicode and symlink escape paths;
- canonical Unicode bytes, golden SHA, no BOM/newline, float rejection;
- semantic Request/Snapshot hash inclusion and runtime metadata exclusion;
- Timeline gaps, first hold, asset references, Audio final mix, Caption word timing and fonts;
- Rights/Gate fail-closed and stable multi-error ordering;
- Capability support, unknown values, renderer identity and extension version negotiation;
- Result state, output presence, Probe, errors and hash-index consistency;
- matching/mismatching filesystem asset hashes;
- Snapshot derived ID, write-once idempotency, tamper rejection, atomic temp cleanup, and Stage
  Manifest preservation.

## Final regression

```text
Repository suite:  8/8 passed
Runtime suite:   134/134 passed (65 original + 69 new)
Combined:        142/142 passed
Failure: 0
Error:   0
Skip:    0
```

The actual symlink escape case executed successfully on this Windows environment; it was not
skipped.
