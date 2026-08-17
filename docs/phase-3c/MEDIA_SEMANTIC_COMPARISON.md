# Media Semantic Comparison

| Property | Baseline | Facade | Result |
| --- | --- | --- | --- |
| Container | mov/mp4 family | mov/mp4 family | pass |
| Video streams | 1 | 1 | pass |
| Audio streams | 1 | 1 | pass |
| Video codec | h264 | h264 | pass |
| Resolution | 720×960 | 720×960 | pass |
| FPS | 30/1 | 30/1 | pass |
| Pixel format | yuv420p | yuv420p | pass |
| Rotation | none | none | pass |
| SAR / DAR | absent / absent | absent / absent | pass |
| Audio codec | aac | aac | pass |
| Sample rate | 48000 | 48000 | pass |
| Channels/layout | 2/stereo | 2/stereo | pass |
| Container duration | 11.533333 s | 11.533333 s | pass |
| Duration delta | — | 0 ms | pass, tolerance 34 ms |
| Timeline segments | 13 | 13 | pass |
| Script lines | 15 | 15 | pass |

Both files are 584,498 bytes and have SHA-256
`ac8a6e9e3b0375f42ae539153fcd254cd329b19dde5f9755517783a22e8b2069` in this environment.
This repeatable bitwise equality is recorded as evidence but is not a Phase 3C requirement or a
portable guarantee across FFmpeg builds.
