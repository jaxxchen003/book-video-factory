# Remotion Insertion Points

## 当前事实

- 仓库没有 `package.json`、Remotion 源码、组件或测试。
- `DEPENDENCIES.md` 只把 Node/npm 描述为使用 HyperFrames/Remotion 时的依赖。
- Phase 0 证明 Node v24.15.0 与 npm 11.12.1 可执行，但没有验证任何 Remotion 版本、Chrome 下载、Windows 渲染或编码行为。
- 当前视觉与音频的关键耦合点是 `build_final_video_v2.py::render_variant()`。

因此本报告只分析边界，不代表 Remotion 已可安装或已验证兼容。

## 三个方案比较

| 维度 | 方案 A：完全替代视觉 Renderer | 方案 B：Remotion 负责全部视觉，FFmpeg 负责音频与最终编码 | 方案 C：Remotion 生成中间视频，现有 Runtime 负责装配与 QC |
|---|---|---|---|
| 侵入程度 | 高；重写 scene、caption、title、motion、编码衔接 | 中高；必须把 `render_variant()` 拆成视觉与 audio finalizer | 低到中；先让 Adapter 替代 `render_base_video()` 的 silent base 输出 |
| 可复用 Core | Profile/Manifest/Gate/QC；少量 Pillow 逻辑可能丢失 | Core 全保留；Typography 可转为布局数据，FFmpeg audio 保留 | Core、现有 PNG overlay、FFmpeg audio/QC 最大化保留 |
| 现有视觉复用 | 低 | 中；需用 React 重做标题/字幕/品牌 | 高；首阶段可继续由现有 PNG overlay 完成 |
| 测试风险 | 最高；当前无视觉 E2E 基线 | 中高；需新增 JS 视觉 + Python/FFmpeg 边界测试 | 最低但仍需 silent base characterization test |
| Windows 风险 | 未验证；Node 可用不等于 Remotion render 可用 | 未验证；还增加跨进程/中间文件边界 | 未验证，但回滚点最清晰，可与旧 base 对比 |
| 音频能力 | 若也迁音频，会丢失成熟 FFmpeg graph；若不迁则接近 B | 保留现有 loudnorm/duck/amix，但先拆 audio-only finalizer | 直接复用现有 `render_variant()` 的音频与 overlay graph |
| QC 复用 | 可复用 FFprobe/Gate，但输出行为差异最大 | 高 | 最高 |
| 示例资产耦合 | 可借机清理，但一次改动过大 | 可通过 RenderRequest 清理 | 首步仍保留 V4 15/12 合同，风险可控 |
| 推荐程度 | 不推荐作为 Phase 2 首步 | 推荐的目标架构 | **推荐的 Phase 2 最小落地路径** |

## 基于源码的结论

指令要求默认优先评估 B，但源码显示 B 目前没有可直接插入的 audio-only 边界：`render_variant()` 同时执行 PNG overlay、画布规范和全部混音。如果直接让 Remotion 输出完整视觉，再调用它，会重复叠加标题/字幕/品牌；如果绕开它，又会复制或丢失成熟的 FFmpeg 音频逻辑。

因此建议分两层表达：

- **目标架构：方案 B。** Remotion 输出完整、无声的视觉母版；FFmpeg 只做旁白/BGM/SFX、最终编码与 QC。
- **Phase 2 第一落地：方案 C。** 先让 Remotion Adapter 只替换当前 `v2.render_base_video()` 的 silent base，现有 `render_variant()` 继续叠加 Pillow PNG 和混音。验证等价后，再拆出 audio-only finalizer，演进到 B。

这不是预设 B，而是由现有耦合位置和测试缺口推导出的两阶段迁移。

## 最小侵入点

当前边界：

```text
v2.create_scene_timeline(...)
  → v2.render_base_video(project, timeline, cards, timeline_dir)
  → silent base: 07_timeline_时间线/v4/base-v2-3x4.mp4
  → v2.render_variant(base, overlays, voice, bgm, sfx, ...)
```

Phase 2 可新增一个 Adapter，在不改变上游 Manifest/Gate 的前提下实现：

```text
RenderRequest
  ├── release_profile
  ├── timeline / scene manifest
  ├── approved visual artifacts + hashes
  ├── duration / fps / canvas
  └── output path
        ↓
VisualRendererAdapter
  ├── ffmpeg_legacy_v1
  └── remotion_visual_v1
        ↓
RenderResult
  ├── silent_visual_master
  ├── stream metadata
  ├── duration / frame_count
  ├── artifact SHA-256
  └── renderer identity/version
```

首阶段 Remotion 输出必须满足：无音轨或明确静音、720×960、30 FPS、CFR、总时长与 timeline 一致、最后画面覆盖 Outro、H.264/yuv420p（或由下一步可靠规范化）。然后仍交给原 `render_variant()`。

## 演进到方案 B 前必须拆出的边界

1. 把 `render_variant()` 拆为 `compose_visual_overlays()` 与 `mix_audio_and_finalize()`，并先用测试证明输出等价。
2. 让 Remotion 消费 title layout、caption timing、brand/style token，而不是重新解释任意 `project.json`。
3. 让 `v4_post_qc.py` 从 Release Profile 和 RenderResult 读取尺寸/codec，不再字面量检查。
4. Renderer 必须返回 artifact，再由编排层写不可变 Stage Manifest；Renderer 不直接把 `project.json.status` 当作真状态。
5. 保留 legacy Adapter 作为回滚/对照，直到视觉和音频 characterization tests 全绿。

## 方案 A 的具体风险

- 当前 Pillow 标题安全区、语义换行和 caption 输出尚未建立像素基线，直接重做难以判定回归。
- FFmpeg audio graph 是已投入生产的隐性合同，但没有独立测试；完全替换时最容易一起改坏。
- V2 helper 同时被 V3/V4 与 V5 compositor 使用，一次移除会扩大影响面。
- 现有 Gate 和 Profile 可保留，但需要大量新 glue，不属于“最小侵入”。

## Unknown

- 适配 Node 24 的具体 Remotion 版本、bundler 与 Chrome 运行要求：**Unknown**，需在允许安装依赖的 Phase 2 单独核验。
- Windows 上的首次 Chrome 下载、GPU/软件渲染、字体加载与并发性能：**Unknown**。
- 现有 Showcase 对帧级视觉等价的可接受阈值：**Unknown**，需要用户/维护者给出验收样片或 golden frames。

