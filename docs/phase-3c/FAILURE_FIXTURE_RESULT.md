# Failure Fixture Result

## Case

`fixture-copy-c-failure` pre-created the exact fixed output path with a 32-byte guard payload before
calling `LegacyV4Renderer`.

## Observed behavior

- Result status: `failed`
- Primary error: `RENDER_INPUT_INVALID`
- Runner called: no
- Guard size before/after: 32/32 bytes
- Guard SHA-256 before/after: `19e84ec3c04741f98b6d68b3c9f6696285a2bcd6d73b962cde1d1389e6fa1131`
- Output overwritten or deleted: no
- Failure Result persisted: yes
- Evidence retained: yes

The case therefore fails closed before process launch and proves that the facade does not overwrite
or remove a pre-existing fixed output.
