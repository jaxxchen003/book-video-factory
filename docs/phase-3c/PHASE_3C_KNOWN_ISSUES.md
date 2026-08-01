# Phase 3C Known Issues

1. The legacy V4 fixed output path is not release-scoped. Isolated Project roots remain mandatory;
   the facade correctly refuses a pre-existing target.
2. V4 requires 12 unique scenes and 15 lines, so a literal three-scene fixture is impossible without
   changing forbidden legacy constants. Phase 3C uses three visual motif families expanded to 12
   unique assets.
3. V4 requires one BGM. The fixture therefore generates and locally encodes its own BGM instead of
   omitting it.
4. The local master passes technical QC but is not approved for public release because the generated
   H2 input has no external rights-clearance record. This is an intentional release hold.
5. Bitwise equality was observed with FFmpeg 8.1.2 on this machine, but only semantic equality is a
   cross-environment contract.
6. The smoke covers one short fixture and one fail-before-run case; it is not evidence for batch
   throughput, diverse books, or production publication.
