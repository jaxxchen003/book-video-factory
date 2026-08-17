# V4 到 Renderer Contract v1 映射

## 映射前提

当前 V4 没有 Release Manifest。下一阶段映射器必须先从 Project/Profile、现有批准事件和
实际资产构造不可变 compatibility release snapshot，再生成 Request。任何路径只是候选；
必须通过存在性、project-root、Hash、rights 和 release scope 验证后才能进入 Request。

## 逐字段映射

| 当前数据/常量 | 文件/变量 | 新契约位置 | 真相源 | 迁移方式 |
|---|---|---|---|---|
| Project ID | `project.json.project_id` | `request.project.id` | Project Manifest | Direct map |
| Project Manifest | `project.json` | `request.project.manifest_ref/sha256` | Project Manifest | Direct map |
| Release ID | `render_ready_v4 --release-id`，当前可选 | `request.release.id` | Release Manifest | Move to Release Manifest；final 强制非空 |
| Release Profile ID | `project.json.workflow.release_profile_id` | `request.profile.id` | Project/Style mapping | Direct map |
| Profile revision/hash | `book-v4-bilingual-3x4.json` | `request.profile.revision/ref/sha256` | Release Profile | Direct map |
| Renderer 名 | Profile `renderer=build_batch_video_v3` | `request.renderer.id/version` | Release policy + Orchestrator | Keep temporarily；映射为 legacy facade identity |
| 15 行台词 | `script.v2.bilingual.json.lines` + Profile `script.line_count=15` | `assets[approved_script]`、Caption cues、Timeline metadata | 批准脚本；数量政策来自 Profile | Direct map；Remove duplication |
| 12 个场景 | `scene_contract.py`、`S01..S12.png`、Profile `scene_count=12` | `assets[]` + segment visual refs | Release Manifest；V4 mapping policy 来自 Profile-specific scene contract | Direct map；Remove duplication |
| V01–V15 ↔ S01–S12 | `V4_SCENE_LINE_CONTRACT` | segment `metadata.script_line_ids/scene_ids` | V4-specific mapping policy | Keep temporarily；不得提升为全局 Schema |
| Timeline scene 名 | `V4_TIMELINE_SCENES` (`HOOK/BOOK/...`) | `timeline.segments[].segment_id/metadata` | V4 mapper | Move to Timeline |
| Voice 文件 | `05_voice_人声/v3-b-locked-master.wav` | Release asset + Audio Manifest narration stem | Release Manifest | Move to Release Manifest |
| ASR 文件 | `05_voice_人声/asr-v3/v3-b-locked-master.json` | Caption timing source asset | Release Manifest/Caption Track | Move to Release Manifest |
| Voice 暂停后文件 | `v3-b-locked-master-paused.wav` | compatibility audio edit artifact | Audio Manifest | Keep temporarily |
| ASR 暂停后文件 | `asr-v3-paused/...json` | versioned Caption timing artifact | Caption Track | Keep temporarily |
| 停顿切点 | `cue_end`、`cut_end=cue_end+0.020` | explicit audio edit/cue boundaries | V4 Timeline/Audio policy | Move to Timeline |
| 插入静音 | `inserted_silence=1.040` | explicit visual-only/pause segment duration | V4 Release/Profile policy | Move to Timeline |
| 时间移动 delta | `1.040 - 0.020` | mapper 派生，不单独持久化为真相 | Timeline derivation | Remove duplication |
| Montage 起点 | `V02.end + 0.04` | montage segment `start_tick` | reviewed Timeline | Move to Timeline |
| Montage 时长 | `MONTAGE_SECONDS=0.96`、Style 同值 | montage segment duration；V4 Profile policy | Release Profile | Move to Profile；Remove duplication |
| 8 张 Topic Card | `topics[:8]` / `len(cards) < 8` | montage segment `visual.kind=sequence` + asset IDs | Release Manifest + V4 Profile | Move to Release Manifest |
| 默认 Topic 文本 | `default_topics()` | approved overlay/content assets | 批准脚本或 Release asset | Keep temporarily；未来去除隐式默认 |
| Outro 时长 | `OUTRO_SECONDS=2.5` | explicit outro segment | Release Profile/Timeline | Move to Profile |
| 总时长 | `voice_duration + OUTRO_SECONDS` | `timeline.duration_ticks`、OutputSpec duration | Timeline | Move to Timeline |
| BGM 文件 | `glob("v4-*-original-bgm.mp3") == 1` | Audio Manifest stem + Release asset | Release Manifest | Move to Release Manifest |
| H2 文件 | `H2-用户确认原片高频音效层.wav` | Audio Manifest stem + rights ref | Release Manifest | Move to Release Manifest |
| H2 SHA | `provision_user_approved_h2()` | asset `sha256` | Release Manifest | Direct map |
| 当前 Voice/BGM/SFX 混音 | `v2.render_variant()` | legacy extension；目标为上游 final mix asset | Audio Manifest/Audio Finalizer | Renderer-specific option；Keep temporarily |
| BGM offset | Style `bgm_start_offset_seconds=18.0` | Audio Mix Profile | Audio Profile | Move to Profile |
| BGM target LUFS | Style `bgm_target_lufs=-22` | Audio Mix Profile | Audio Profile | Move to Profile |
| Montage boost | Style `montage_boost_db=14` | Audio Mix Profile | Audio Profile | Move to Profile |
| Final LUFS/true peak | Style/Profile `-15/-1.2` | OutputSpec audio policy + Post-QC expected spec | Release Profile | Move to Profile；Remove duplication |
| Duck threshold/ratio/attack/release | `render_variant()` 字面量 | legacy extension，后续 Audio Mix Profile | Audio Profile | Renderer-specific option；Keep temporarily |
| 画幅 | `WIDTH=720/HEIGHT=960` + Release/Style 重复 | `output_spec.width/height` | Release Profile | Direct map；Remove duplication |
| FPS | `FPS=30` + Release/Style 重复 | `output_spec.fps` | Release Profile | Direct map；Remove duplication |
| Video codec/pixel format | `libx264/yuv420p` + Profile `h264` | `output_spec.video/pixel_format` | Release Profile/Encoding policy | Move to Profile |
| Audio codec/rate/channels | `aac/192k/48000/stereo` | `output_spec.audio` | Release Profile/Encoding policy | Move to Profile |
| CRF/preset | V2 helper 字面量 | legacy renderer extension；未来 Encoding Profile | Release Profile extension policy | Renderer-specific option |
| 字体角色 | Style `fonts.title/chinese/english` | Caption/Overlay `font_role` + asset binding | Release Profile + Release Manifest resolved font | Move to Release Manifest |
| 字体解析优先级 | `fonts.resolve_font_path()` | Orchestrator preflight/asset binding | Runtime font contract | Direct map；Renderer 只消费已绑定字体 |
| 标题安全区/字号 | Style `title_layout` 与 Release typography | OutputSpec/Profile snapshot + overlay layout token | Release Profile | Direct map；Remove duplication |
| Caption 文本 | script `zh/en` | Caption Track cues | 批准脚本 | Direct map |
| Caption 时间 | `TimedLine.start/end` | Cue integer ticks | Caption Track | Move to Timeline |
| Caption PNG | `overlays/.../Vxx.png` | Result sidecar 或 legacy derived asset | Legacy Renderer | Keep temporarily；不是核心真相源 |
| SRT | `subtitles.v2.*.srt` | Result sidecar | Caption Track 的派生产物 | Direct map |
| 真实封面 | cover Manifest + `compose_real_cover()` | cover input asset；composite 为 derived sidecar/input | Release Manifest | Move to Release Manifest |
| Title/author | `script["book"]` | Project snapshot + title overlay semantic content | Project Manifest/批准脚本 | Direct map |
| 静音 base | `07_timeline_时间线/v4/base-v2-3x4.mp4` | optional Result sidecar role `silent_visual_master` | Legacy Renderer Result | Direct map |
| 渲染输出 | `08_render_合成/v4/<slug>-v4-bilingual-3x4.mp4` | `request.output.target` + Result output artifact | Request/Result | Direct map |
| Delivery 复制 | `10_delivery_交付/v4/...` | freeze/delivery 阶段，不属于 Renderer | Release workflow | Remove duplication；Renderer 不直接交付 |
| `render_manifest.v4.json` | V3 `manifest` dict | 分拆为 Release snapshot、Request、Timeline、Result | 各对象自己的真相源 | Remove duplication；Keep temporarily 供旧链 |
| Renderer smoke QC | `qc_report.v4.json` | Result checks/metrics/probe | Renderer Result | Direct map |
| Post-QC 输入 | `v4_post_qc.py` 再猜固定路径 | `result.qc_handoff` + Request/Profile snapshot | Result/Request | Direct map；Remove duplication |
| Post-QC 输出 | `v4_release_gate.json` | release-scoped Post-QC artifact | Post-QC | Direct map |
| Release rights holds | translation/cover/H2 字面量 | rights snapshot + Gate policy | Approval/Style/Release Manifest | Move to Release Manifest |
| `project.json.status` 写回 | V3 `state.update(...)` | 无核心映射；仅 compatibility cache | Gate evaluator 才是真状态 | Keep temporarily；未来移除写回 |
| `python3` 子进程 | `render_ready_v4.py` | ExecutionContext runner | Runtime orchestration | Remove duplication；不得进入 Request |

## V4 Mapper 顺序

1. 加载 Project/Style/Release Profile，验证三者一致。
2. 强制要求显式 `release_id`。
3. 收集当前 Release 的 Approval/Gate/rights，不跨 Release 合并。
4. 验证 15 行、12 场景、Voice/ASR/BGM/H2/字体/封面并计算 SHA。
5. 构造 write-once compatibility release snapshot。
6. 按现有 `align_lines()`/Scene Contract 的已锁定行为生成整数 tick Timeline 和 Caption
   Track；不让 Renderer 再推导。
7. 固化 legacy Renderer identity/Capability/extension。
8. 计算 Request Hash 并 exclusive persist。
9. Facade 调用旧链，收集输出/Probe/日志为独立 Attempt Result。

Phase 2 不执行这些步骤；表格只定义下一阶段行为。

## Unknown

- 当前项目实际是否都有与 H2 对应的独立 `sfx_rights` Approval，需要真实 warehouse fixture
  验证。
- 现有 `render_manifest.v4.json` 在所有生产项目中的字段是否一致，仓库没有 fixture 集合。
- 旧 V4 的编码输出在 Windows/POSIX 是否 bitwise 一致未知，只能先验证 semantic equivalence。
