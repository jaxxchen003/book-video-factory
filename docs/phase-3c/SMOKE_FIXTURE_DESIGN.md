# Smoke Fixture Design

## Safety boundary

The CLI accepts only a directory containing an exact `SMOKE_FIXTURE.json` marker with
`production_use: false`. Initialization requires an empty directory, and a root containing
`project.json` is rejected. The adapter never deletes artifacts.

The verified run used:

`C:\Users\SSS\AppData\Local\Temp\book-video-factory-phase3c-20260801-run2`

All assets were generated locally. There were no Provider, network, model-download, external
asset, `examples/`, commercial-project, or Remotion calls.

## Generated semantic input

- Resolution: 720×960
- FPS: 30
- Narration source: 8-second, 48 kHz, stereo, 16-bit PCM WAV
- Narration structure: three synthesized tonal sections in one WAV
- Visual structure: three geometric motif families expanded into 12 byte-unique PNG files
- Script: 15 ASCII bilingual cue records
- Timing: hand-authored word timing covering the 8-second narration
- H2: generated 0.96-second PCM WAV
- BGM: generated 32-second PCM WAV, locally encoded to MP3 because V4 requires one BGM
- Cover: generated geometric PNG
- Fonts: configured local Windows fonts, with hashes frozen into the facade Request

## Explicit specification reconciliation

The instruction's preferred three scenes and three narration segments conflict with the
unmodified V4 contract, which requires 12 unique topic scenes and 15 script lines. Because Phase
3C forbids changing V4 constants or templates, the fixture uses three visual motif families to
generate 12 unique scene assets and three audio sections inside one source WAV while preserving
the required 15 cues. This is a documented compatibility constraint, not a claim that V4 consumed
only three scene files.

## Isolation

- `fixture-copy-a-baseline`: direct V4 CLI
- `fixture-copy-b-facade`: Snapshot → Request → LegacyV4Renderer
- `fixture-copy-c-failure`: pre-existing fixed-output failure

The three projects contain identical semantic input hashes and never share fixed output paths.
The CLI produces both `phase-3c-smoke-report.json` and `phase-3c-smoke-report.md`.
