# Phase 3B Known Issues

1. Real media parity is not proven. Phase 3B uses injectable fakes; an approved Phase 3C must run a
   production fixture and compare semantic outputs with the pre-facade V4 chain.
2. The legacy output path is Project/V4 fixed and does not contain `release_id`. Write-once
   protection therefore prevents two Releases from silently sharing or replacing that path.
3. A process that fails after creating fixed legacy outputs can leave partial files. The facade
   records the failed Attempt and never deletes or overwrites those files; an operator must
   quarantine them before a new Attempt.
4. Cross-platform H.264 output is declared semantically deterministic, not bitwise deterministic.
5. WAV duration freezing is intentionally stricter than legacy FFprobe acceptance: narration must
   have a readable WAV header.
6. The controlled `audio_mixing` exception remains technical debt and is valid only for the legacy
   V4 facade.
7. The facade still inherits the old chain's project-state and delivery-copy side effects. Phase 3B
   does not change them because modifying legacy behavior is explicitly out of scope.
