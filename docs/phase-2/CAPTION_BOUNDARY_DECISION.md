# Caption 边界决策

## 唯一真相源

Caption 文本的真相源是人工批准脚本，不是 ASR 输出，也不是 Renderer 生成的 PNG/SRT。

```text
approved script text
  + local ASR word timing（只提供时间证据）
  + reviewed alignment/corrections
  → versioned Caption Track
  → RenderRequest caption cues
  → Renderer-specific pixels/components
```

ASR 文字与批准稿冲突时，保留批准稿文字；对齐失败必须人工修正或 Blocked，禁止为了
匹配 ASR 而静默改文案。

## v1 Caption Track

每条 track 至少保存：

```text
track_id
language
text_source_asset_id / text_source_sha256
timing_source_asset_id / timing_source_sha256
alignment_revision
cues[]
style
```

每个 cue：

```text
cue_id
segment_id
start_tick / end_tick
text
granularity                 # phrase | sentence
words[]                     # optional
  word_id / text / start_tick / end_tick
highlight {mode, states[]}  # optional semantic state
```

时间统一使用 Timeline 的整数 tick 和半开区间。Cue 必须位于 Timeline 内，若绑定
segment 还必须位于该 segment 内。Word 时间必须有序、不越出 cue；缺少 word timing
时不能请求 `word_highlight` Capability。

## 修正文稿与 ASR 的关系

- `text_source_asset_id` 绑定批准脚本及其 Hash。
- `timing_source_asset_id` 可指向 ASR JSON，但 ASR 仅是 timing provenance。
- 人工调整必须生成新的 Caption Track revision，记录调整理由与审阅 Approval。
- 脚本 Hash 改变后旧 Caption Track 立即 stale；不能只改 SRT。
- Phrase/Sentence 时间是渲染最低要求；Word 时间可选。
- 多语言 track 各自保存批准文本，不能假设英文是中文的自动翻译结果。

## Renderer-neutral 样式

Caption 样式保存业务约束，不保存 Pillow/React/具体组件：

- `font_role`：逻辑字体角色；实际字体资产与 SHA 在 Release Manifest/Request assets；
- `safe_area`：左右/上下像素或 Profile-relative region；
- `max_lines`、`line_break_policy`、`overflow_policy=fail`；
- 对齐、文字方向、语言；
- `highlight` 的 inactive/active semantic token；
- background、stroke 等使用 Profile token ID，而非运行时对象。

Renderer 必须声明 `captions`，请求逐字高亮时还要声明 `word_highlight`。字体缺失、文本
越界、最大行数无法满足时使用 `RENDER_FONT_UNAVAILABLE` 或
`RENDER_CAPTION_INVALID` fail-closed。

## 当前 V4 映射

| 当前对象 | 新合同角色 |
|---|---|
| `script.v2.bilingual.json` 的 `zh/en` | Caption 文本真相 |
| Whisper word JSON | timing source artifact |
| `TimedLine` | Caption cue 的迁移表示 |
| `align_lines()` 结果 | 经审查的 cue start/end |
| `subtitles.v2.*.srt` | RenderResult sidecar，不是真相源 |
| `overlays/.../Vxx.png` | Legacy Renderer 的派生像素资产，不进入通用 Caption Schema |
| `render_caption_layer()` | Legacy 实现细节 |

VOX Style 已声明 `approved_script_plus_local_asr_timing`，与此决策一致；外部生成 clips
不得嵌入不可控字幕，避免与本地 Caption Track 重复。

## Preview/Final

Preview 和 Final 共用 Caption Schema。Preview 可以按 Profile 使用较低分辨率，但不能
放宽文本来源、时间合法性、字体可用性或安全区 fail-closed 规则。Final 必须记录语言
审阅状态；若发布所需审阅尚未完成，Post-QC/Gate 应保留 hold，但 Renderer 不得伪报
Approval，也不应把依赖本次输出的 publish Gate 当作渲染前置条件。
