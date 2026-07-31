# Legacy and Showcase Code

本报告只分类和提出隔离建议，不删除或移动任何文件。

| 文件/目录 | 分类 | 绑定对象 | 硬编码证据 | 主流程仍调用 | 建议 |
|---|---|---|---|---|---|
| `scripts/build_final_video.py` | Legacy Generic + Showcase Specific | 《兜底》/晴山、V1 素材 | 固定标题、作者、Outro、macOS STHeiti、`Long Road Ahead B.mp3`、`doudi-approved-v1-*` | 否 | 保留为历史样例，明确标记 legacy；不要作为 Adapter 基础。 |
| `scripts/build_final_video_v2.py` | Legacy Generic + Showcase Specific | 《兜底》V2 | 固定 `doudi-weread-t9.jpg`、`book-mockup-blank.png`、书名作者、BGM、splice 时间、输出前缀 | **是**，V3/V4 直接 import | 不能删除；先从中提取通用 FFmpeg/字幕/音频函数，再隔离案例 main。 |
| `scripts/build_batch_video_v3.py` | Runtime Generic + V4 Profile Specific | 15 行/12 场景原风格 | 固定输入名、Scene Contract、停顿、montage、H2 文件和 720×960 | 是，原风格主 Renderer | 保留为行为基线；Phase 2 用契约包裹，逐步迁移硬编码。 |
| `scripts/compose_v5_from_chatcut_bgm.py` | Release-specific compositor | 已有 V4 visual contract + ChatCut BGM | `06_music_音乐/v5`、默认 `v5.1`、V4 base/overlay 路径、720×960、固定 mix | 不在 V4 主链；独立批处理 | 保留为特定修复流程，隔离在 recipe/compositor 层，不提升为通用 Renderer。 |
| `scripts/seed_v4_batch.py` | Showcase Specific | 2026-07-13 批次的 10 本书 | 完整嵌入书目、双语脚本、视觉 Prompt、批准文本、日期与 batch 文件名 | 仅人工批次入口 | 保留审计价值；迁出通用 Runtime 或明确放入 examples/recipes（后续单独决策）。 |
| `scripts/build_sfx_auditions.py` | Showcase Specific | H1/H2 参考片试听 | 固定 reference-original 路径、时间窗、BGM、素材名 | 否 | 保留证据，隔离；不得被生产默认路径调用。 |
| `scripts/regenerate_v5_voice_batch.py` | Showcase/Batch Specific | V5 批次与锁定音色 | 固定批次目录、模型会话与输出约定 | 不在 V4 编排链 | 待确认使用频率后隔离；不要删除。 |
| `config/brand_voice_profile.json` | Showcase Specific config | 《兜底》选出的 B 女声 | 固定 prompt、reference SHA、`doudi-qingshan` audition、日期、MPS | TTS 默认配置可能使用 | 迁为用户/warehouse Profile；仓库仅保留脱敏模板。 |
| `config/voice_candidates.json` | Showcase Specific fixture/config | 《兜底》试听文案 | 固定文案、候选描述、seed、MPS、模型目录 | Audition 脚本读取 | 保留为示例模板但去除“全局生产默认”含义。 |
| `config/video_style_v2.json` | Legacy/V4 config | macOS + 原风格 | macOS 字体绝对路径、缺失的 SmileySans fallback、固定视觉/音频值 | 是 | 不删除；Phase 2 拆为平台字体策略和 Release/Profile 参数。 |
| `examples/videos`, `examples/posters` | Showcase Specific | 多个成片案例 | 二进制展示资产 | 否 | 原样保留；不纳入 Runtime 测试夹具。 |
| `examples/manifests/chaoyue-baisui-*` | Showcase Specific evidence | 《超越百岁》纸片拼贴案例 | 固定项目/Release/SHA/日期/审批事件 | 否 | 保留为发布证据样例；不可反推 Provider 已实现。 |
| README 中 V1/V2 quick start | Documentation Only / Legacy guidance | `doudi-qingshan` | 示例命令固定《兜底》与旧 Renderer | 用户可能照做 | 后续文档轮次标注历史示例，并指向 V4 主入口。 |

## 分类边界说明

- `Legacy Generic` 不等于无用。V2 是最典型反例：其 `main()` 是 Showcase，但函数仍承载当前生产 Renderer 的核心视觉和音频实现。
- `Deprecated` 需要明确弃用证据。本仓库文档没有为上述文件统一给出正式 deprecated 标记，因此本报告没有仅凭版本号擅自标为 Deprecated。
- `examples/manifests` 能证明某个 Showcase 产物与审批记录存在，不能证明本仓库包含生成它的全部工具。

## Unknown

- `boundaries`、`highly-sensitive`、`no-people-pleasing`、`original-family` 四个 Showcase 视频缺少配套生产 Manifest；其确切 Renderer 版本为 **Unknown**。
- `compose_v5_from_chatcut_bgm.py` 在当前上游日常生产中的使用频率为 **Unknown**。
- 因仓库仍为浅克隆，哪些脚本已被维护者口头或历史提交弃用为 **Unknown**。

