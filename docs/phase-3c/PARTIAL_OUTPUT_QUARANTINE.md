# Partial Output Quarantine

The selected controlled failure occurs before Runner invocation. Consequently, no process-created
partial media exists to move, and quarantine is intentionally not triggered.

The pre-existing guard output remains in place with the same byte count and SHA-256. A dedicated
evidence directory is retained at:

`fixture-copy-c-failure/failed-output-quarantine/phase3c-failure-existing-output`

Its `QUARANTINE_NOT_TRIGGERED.json` records the original relative path, before/after size and hash,
and the reason for preserving the file in place. No cleanup, deletion, or overwrite logic was added
to the facade. If a future Runner-started failure creates partial output, that output must be moved
to its Attempt-specific quarantine before another Attempt is allowed.
