# Baseline V4 Run

## Execution

- CLI: `C:\Python314\python.exe E:\AI\BookVideoFactory\skills\book-video-factory\runtime\book_video_factory\scripts\build_batch_video_v3.py C:\Users\SSS\AppData\Local\Temp\book-video-factory-phase3c-20260801-run2\fixture-copy-a-baseline --release-version v4`
- CWD: `E:\AI\BookVideoFactory\skills\book-video-factory\runtime\book_video_factory`
- Injected environment keys: `BOOK_VIDEO_TITLE_FONT`, `BOOK_VIDEO_CHINESE_FONT`, `BOOK_VIDEO_ENGLISH_FONT`
- Base environment: inherited; values were not persisted
- Exit code: 0
- Renderer wall time: approximately 5.8 seconds

## Output

- File: `08_render_合成/v4/fixture-copy-a-baseline-v4-bilingual-3x4.mp4`
- Bytes: 584,498
- SHA-256: `ac8a6e9e3b0375f42ae539153fcd254cd329b19dde5f9755517783a22e8b2069`
- Container: `mov,mp4,m4a,3gp,3g2,mj2`
- Video: H.264, 720×960, 30/1 FPS, yuv420p, 11.533333 seconds
- Audio: AAC, 48 kHz, stereo, 11.520000 seconds
- Streams: one video and one audio
- Timeline segments: 13
- Script lines: 15

## Post-QC

The unmodified `v4_post_qc.py` was invoked after rendering and exited 0. The local master status
was `pass`; all six technical checks passed. `public_release_allowed` remained `false` because the
generated H2 fixture intentionally has no external rights-clearance record. That release hold is
expected and is not a renderer failure.
