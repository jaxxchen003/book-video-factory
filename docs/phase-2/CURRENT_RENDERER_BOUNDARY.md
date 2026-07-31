# 当前 Renderer 边界

## 结论

当前 V4 没有显式 `RenderRequest`、`RenderResult` 或独立 Renderer 接口。所谓 Renderer
实际是一个以项目目录为隐式输入、同时承担音频预处理、时间线构建、Pillow 图层、
FFmpeg 合成、基础 QC、交付复制和兼容状态写回的脚本集合。

可由源码完整确认的主链是：

```text
render_ready_v4.py
  → build_batch_video_v3.py --release-version v4
      → import build_final_video_v2.py as v2
  → v4_post_qc.py
  → workflow.py evaluate（不是 render_ready_v4 自动调用）
```

`external_clip_timeline_v1` 只存在于 Profile、Gate 和文档，不存在仓库内执行器，不能
算作已经实现的 Renderer。

## 当前隐式输入

`render_ready_v4.py::ready()` 仅按固定路径判断一部分资产存在：

| 输入 | 当前位置/规则 | 当前问题 |
|---|---|---|
| Project | `project.json` | 只提供身份/工作流；`status` 是兼容缓存，不是 Gate 真相源 |
| Script | `02_story_script_故事脚本/script.v2.bilingual.json` | 固定 15 行；文件名与行数泄漏到 Renderer |
| Scenes | `03_images_生成图片/approved/v4/S01..S12.png` | 固定 12 张；Renderer 自行检查 SHA 去重，但不绑定 Release Manifest |
| Cover | `.../cover/cover_manifest.json` 及其本地文件 | readiness 只检查 Manifest 存在，实际封面选择逻辑另有 fallback |
| Voice | `05_voice_人声/v3-b-locked-master.wav` | 文件名绑定版本/批次语义 |
| ASR | `05_voice_人声/asr-v3/v3-b-locked-master.json` | ASR 是计时依据，但当前没有独立 Audio Manifest |
| BGM | 恰好一个 `06_music_音乐/v4-*-original-bgm.mp3` | 由 glob 选择；权利记录未进入渲染输入对象 |
| SFX | `06_music_音乐/H2-用户确认原片高频音效层.wav` | `ready()` 未检查，Renderer 中途才失败 |
| Style | `config/video_style_v2.json` | 字体、布局、混音值与 Release Profile 重复 |
| Release Profile | `book-v4-bilingual-3x4.json` | 只校验一部分排版值；没有完整驱动 Runtime 常量 |
| Release ID | `render_ready_v4 --release-id` 可选 | 未传时仍可渲染和 Post-QC，但不可形成发布级 Release 绑定 |

当前输入不可变性只在 Stage Manifest、Approval 和部分内容桥路径中存在；Renderer 不会在
开始前把所有实际输入与 SHA 固化为一个独立请求。

## 当前执行职责

### `render_ready_v4.py`

- 扫描项目、跳过不完整项目；
- 用固定输出名判断是否已渲染；
- 通过硬编码 `python3` 启动 Renderer 和 Post-QC；
- 不自动写 render Stage Manifest，也不调用最终 workflow evaluate。

### `build_batch_video_v3.py`

- 加载脚本、Style 与 V4 Release Profile；
- 在旁白中插入 1.040 秒停顿并移动 ASR 时间；
- 对 15 行文案进行 ASR 对齐；
- 生成真实书封合成、8 张 Topic Card、标题/品牌/字幕 PNG；
- 调用 V2 helper 构建场景时间线、SRT 和静音 base；
- 调用 V2 `render_variant()` 叠图、混音和编码；
- 复制交付文件，写 `render_manifest.v4.json` 和 `qc_report.v4.json`；
- 直接更新 `project.json.status/current_stage/final_output` 兼容字段。

### `build_final_video_v2.py`

V4 实际复用的关键函数是：

- `create_scene_timeline()`：固定 V4 Scene-Line 合同；
- `render_still_clip()` / `render_montage()` / `render_base_video()`：静音画面；
- `render_caption_layer()` / `render_brand_layer()`：Pillow 图层；
- `render_variant()`：画布规范、PNG overlay、旁白/BGM/SFX 混音、H.264/AAC 编码；
- `probe()` / `loudness()`：基础媒体检查。

关键事实是 `render_variant()` 同时做视觉和音频，因此当前不存在可直接调用的
“纯视觉 Renderer”或“纯音频 Finalizer”边界。

### `v4_post_qc.py`

- 再次按固定路径读取脚本、12 场景、封面、BGM、Voice/ASR；
- FFprobe 检查 720×960 与 AAC；
- 写 release-aware `09_qc_质检/v4_release_gate.json`；
- 技术通过与公开发布权利分开，但 H2 权利 Hold 是字面量追加；
- 尺寸、15 行、12 场景没有从 Profile/Result 读取。

## 当前隐式输出

| 输出 | 当前角色 | 与新契约的关系 |
|---|---|---|
| `07_timeline_时间线/v4/render_manifest.v4.json` | 混合了时间线、输入路径、部分 SHA 和输出路径 | 不是不可变 Release Manifest；同路径会被覆盖，需拆为 Timeline/Request/Result |
| `07_timeline_时间线/v4/base-v2-3x4.mp4` | 静音视觉中间件 | 可映射为 `silent_visual_master` sidecar，但不是所有 Renderer 必需输出 |
| `08_render_合成/v4/*.mp4` | 本地渲染结果 | 映射为 Result output artifact |
| `10_delivery_交付/v4/*.mp4` | 复制后的交付候选 | 应由编排/Release freeze 决定，不由 Renderer 自行复制 |
| `09_qc_质检/qc_report.v4.json` | Renderer 内部基础 QC | 映射为基础 Probe/内部 checks，不代替 Post-QC |
| `09_qc_质检/v4_release_gate.json` | release-scoped Post-QC | 消费 RenderResult 的 QC handoff，而非重新猜测全部输入 |
| stdout JSON | 项目、输出、QC 状态 | 不能替代持久化 Result |

## 现有 Manifest 事实

- 已实现的是不可变 Stage Manifest、哈希绑定 Approval、内容快照和 Traceability。
- Runtime 文档提到未来 `release_manifest`/freeze-release，但仓库没有实现或 Schema。
- Showcase 中的 `delivery-manifest.json` 只有清洗后的引用，仓库内没有通用创建器。
- 因此 Phase 2 只能设计 Release Manifest 与 Request 的关系，不能假设它已经存在。

## 目标切口

新边界放在 Gate/Release 输入固化与实际执行之间：

```text
Project + Profile + approved artifacts + approvals
  → immutable Release Manifest（未来 freeze-release 真相源）
  → independently persisted RenderRequest（一次执行投影）
  → Renderer Protocol
  → immutable terminal RenderResult
  → orchestrator writes Stage Manifest
  → Post-QC + derived Gate
```

旧 V4 命令保持可直接运行，直到兼容包装路径具备同等输入验证、结果收集和回归测试。
