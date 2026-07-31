# Hardcoded Paths and Values

## 判定口径

本报告不把所有数字都当成缺陷。Release Profile 中经过合同验证的 `720×960`、30 FPS、15 行、12 场景属于合法 Profile 值；当同一值又在 Renderer、Style 和 Gate 中重复、或无法由 Profile 驱动时，才形成漂移风险。测试临时值单独归类，不列为生产风险。

## 绝对路径与平台绑定

| 位置 | 硬编码 | 风险 | Phase 2 处理位置 |
|---|---|---|---|
| `build_final_video.py` | `/System/Library/Fonts/STHeiti Light.ttc`, `STHeiti Medium.ttc` | 高；Windows/Linux 不存在 | 字体 Profile + 平台 resolver |
| `config/video_style_v2.json` | macOS Songti、Times New Roman 绝对路径 | 高；默认配置不便携 | Profile 中用逻辑字体角色；环境/CLI 提供实际路径 |
| `config/video_style_v2.json` | `resources/fonts/SmileySans-Oblique.otf` fallback | 高；仓库实际缺失，7 条 Error | 字体 Manifest/安装前置条件，fail-closed |
| TTS scripts/config | `~/.local/share/voxcpm-*` 与 VoxCPM 模型目录 | 中高；Unix 布局假设 | 环境变量或 CLI，Profile 只记录逻辑模型 ID |
| `brand_voice_profile.json`, `voice_candidates.json` | `device: mps` | 高；当前 Windows 无 MPS | CLI/环境自动探测，Manifest 记录实际 device |
| `render_ready_v4.py` | 子进程可执行名 `python3` | 中；WindowsApps 别名仅“路径存在”，可靠性未验 | `sys.executable` 或 CLI 注入 |
| Doctor/WeRead/Freesound | 无条件使用 `os.uname()` | 高；Windows Python 抛 `AttributeError` | 独立修复轮次用跨平台判断；本轮不改 |

## 仓库相对但绑定示例的路径

| 位置 | 路径/文件 | 风险 | 抽离目标 |
|---|---|---|---|
| V2 | `.../cover/doudi-weread-t9.jpg` | 高，具体书封 | Manifest artifact |
| V2 | `03_images_生成图片/v2/book-mockup-blank.png` | 高，特定模板资产 | Style/Profile asset ref |
| V1/V2 | `06_music_音乐/Long Road Ahead B.mp3` | 高，具体音乐 | Manifest + rights record |
| V4 | `05_voice_人声/v3-b-locked-master.wav` | 高，版本名泄漏到通用入口 | RenderRequest/Manifest |
| V4 | `05_voice_人声/asr-v3/v3-b-locked-master.json` | 高 | RenderRequest/Manifest |
| V4 | `06_music_音乐/H2-用户确认原片高频音效层.wav` | 高，案例命名和权利语义耦合 | Manifest artifact + approval |
| V4 | `03_images_生成图片/approved/v4/S01..S12.png` | 中；对 V4 合法但应由 Manifest枚举 | Release Manifest |
| V5 compositor | `07_timeline_时间线/v4/base-v2-3x4.mp4` 及 overlay 路径 | 高，跨版本内部路径合同 | Renderer Result / visual artifact manifest |
| Voice profile | `book_video_warehouse/projects/doudi-qingshan/...` | 高，具体本地项目 | 用户本地 Profile/Manifest |
| SFX audition | `reference-original/H1...`, `H2...` | 高，未打包参考资产 | 保留在 Showcase recipe，不进入通用 Runtime |

## 具体书名、作者与台词

| 位置 | 内容 | 分类 | 风险与处理 |
|---|---|---|---|
| V1/V2 Renderer | `《兜底》`, `晴山`、固定 Outro/署名 | Showcase Specific | 高；Renderer 必须从 Script/Project Manifest 读取 |
| `brand_voice_profile.json` | “真正能为人生兜底的……” prompt | Showcase Specific | 中高；Voice reference prompt 应跟 reference 一起留在用户 Profile |
| `voice_candidates.json` | 同一《兜底》试听文案 | Showcase fixture | 中；模板可保留占位，不应作为全局生产值 |
| `seed_v4_batch.py` | 10 本书、脚本、作者、视觉 Prompt | Showcase batch | 不迁入 Profile；整个批次 recipe 隔离 |
| Runtime tests | `兜底`、`样书`、`作者` | Test / Fixture | 低；不是生产硬编码，不要求抽离 |

## 固定时间、数量与场景合同

| 位置 | 值 | 判定 | 推荐归属 |
|---|---|---|---|
| V2 | `VOICE_CUT_START=4.48`, `VOICE_CUT_END=4.52`, `VOICE_INSERTED_SILENCE=1.04` | 高风险，案例音频 splice | Timeline/Audio Edit Manifest |
| V4 | `inserted_silence=1.040`, cut 后 0.020 秒 | 高风险，当前脚本节奏假设 | RenderRequest 或 Timeline Manifest |
| V4 | `MONTAGE_SECONDS=0.96` | 中高；Profile 未声明 | Release Profile |
| V4 | `OUTRO_SECONDS=2.5` | 中；视觉/音频合同 | Release Profile |
| V4 | 15 行、12 场景、8 张 topic cards | 对 V4 合法，但 Renderer 与 Profile双写 | Profile/Scene Manifest 单一真源 |
| `scene_contract.py` | V01–V15 到固定场景映射 | V4 专属合法合同 | 保持 V4-specific；新 Renderer 用独立 Manifest |
| SFX audition | 固定试听时间窗与 BGM offset | Showcase Specific | 留在 recipe，不迁入全局 Profile |

## 固定坐标、字体大小和安全区

| 位置 | 证据 | 风险 | 推荐归属 |
|---|---|---|---|
| V1 | Pillow 标题、标签、字幕、Outro 的固定 y/边距/字号 | 高；单书模板 | Legacy 隔离 |
| V2 | `render_title_layer`, `render_caption_layer`, `render_brand_layer` 内大量固定坐标/字号 | 中高；多画布函数仍含模板假设 | Style Profile / visual layout contract |
| V4 | Topic card、真实封面、标题/作者图层固定坐标；标题字号部分由 Profile 驱动 | 中；混合了合法模板与脚本字面量 | 可保持模板默认，但 Profile 为唯一真源 |
| Release Profile | 标题 margin 56、宽 608、字号 70–34、最多两行 | 合法配置 | 保持在 Profile 并由合同验证 |
| VOX Release Profile | 标题/字幕 margin、bottom safe area | 合法配置但无 Renderer 消费证据 | 保持；状态标记 Orchestration Only |

## 固定视频与音频参数

| 位置 | 值 | 风险 | 推荐归属 |
|---|---|---|---|
| V3/V4 Renderer | `WIDTH=720`, `HEIGHT=960`, `FPS=30` | 中；与 Release Profile重复 | Release Profile，Renderer 从请求读取 |
| V2 FFmpeg | libx264、CRF 17/18、preset、yuv420p、AAC 192k/48k | 中；部分不是 Profile 字段 | Encoding Profile |
| V2 audio graph | BGM LUFS、ducking threshold/ratio、attack/release、fade、montage boost | 中高；Style JSON 与代码共同决定 | Audio Mix Profile + tested filter builder |
| V4 Post-QC | 720×960、AAC 与 15/12 再次字面量检查 | 中；可能与 Profile漂移 | QC 从 Release Profile/RenderResult 读取 |
| V5 compositor | 720×960、-22/-16 LUFS、14 dB boost、-1.5 dBFS | 高，release recipe 参数 | Release-specific Manifest |

## 固定输出名与状态

| 位置 | 内容 | 风险 | 推荐归属 |
|---|---|---|---|
| V1 | `doudi-approved-v1-preview/final.mp4` | 高 | CLI output/RenderRequest |
| V2 | `doudi-v2-*`、固定 delivery path | 高 | project slug + release ID |
| V4 | `<slug>-v4-bilingual-3x4.mp4` | 低到中；可预测但 version 字面量 | RenderResult，由 release ID/profile派生 |
| V4 Renderer | 直接写 `project.json.status/current_stage/final_output` | 中高；绕开不可变 Stage Manifest 语义 | 编排层兼容写；Gate 仍是唯一真状态 |
| seed batch | `2026-07-13-v4-batch-10` 等 | Showcase Specific | 留在批次 Manifest |

## 固定 Provider 与凭据策略

- WeRead Gateway URL 与 Freesound API endpoint 是具体 Provider Adapter 内的合法默认，但仓库没有抽象 Provider interface；更换来源需要改调用脚本/模块。
- VoxCPM2 固定为当前 TTS 实现，Profile 可表达模式但缺少 provider registry。
- Gemini/Flow 只是 Style config 与文档分支，不能列为已实现 Provider。
- 凭据从环境变量或 macOS Keychain 读取是合理策略；问题是 `os.uname()` 使 Windows fallback 在缺少环境变量时先崩溃。

## Phase 2 抽离优先级

1. 先定义 `RenderRequest`/`RenderResult`，把输入路径、输出、Release ID、Profile、Timeline/Scene Manifest 从脚本字面量中移出。
2. 让 Renderer 和 Post-QC 只从 Release Profile 读取画布、FPS、行/场景规则与编码目标。
3. 把 V2 的音频 filter graph 参数迁入可验证的 Audio Mix Profile。
4. 把字体角色解析成平台无关策略；没有合法字体时明确 fail-closed。
5. 将《兜底》、批次 seed、H1/H2 audition 和 ChatCut 修复脚本隔离为 recipe/showcase，不删除历史证据。

