# 图书视频工厂 Skill

**简体中文** · [English](README.md)

这是一个可安装的 Codex Skill，用于运行“权利可审计、本地母版优先”的中文图书短视频工作流。它提供两个相互独立的风格：原有的**双语编辑模板图书视频**，以及新增的**VOX风格图书视频**；资料证据、生成来源、人工审批、成本和发布决定都留存在可复核文件中。

仓库不会暗含或自动分发图书正文、书封、音乐、音效、人声样本、账号凭证或隐藏素材。`examples/` 中的视频仅是维护中的案例展示衍生版，不属于 MIT 许可授权的源码素材。

## 安装

```bash
npx skills add jaxxchen003/book-video-factory --skill book-video-factory -g -y
```

安装后，在一个空目录中开启新的 Codex 任务并输入：

```text
使用 $book-video-factory 初始化工作区，并为《<书名>》作者 <作者> 创建第一个图书短视频项目。
```

Skill 会在安装后的下一轮任务中可用。

## 它能做什么

- 复制干净、无媒体内容的确定性运行时和仓库目录契约。
- 幂等创建项目目录与双语脚本模板。
- 支持 `single-book` 和 `content-system-backed` 两种资料模式。
- 建立“脚本行 → Claim → 原始资料 → 场景契约 → 不可变 manifest”的追溯关系。
- 将技术 QC 与脚本、视觉隐喻、BGM、权利、母语审校和发布等人工审批分开。
- 从文件哈希和 release 级审批事件推导 fail-closed 发布状态。
- 追加记录运行成本；供应商未提供的数据记为 `—`，不猜测为零。
- 保留本地母版作为事实源；ChatCut 只作为可选的精修衍生层。

## 风格类型

生成素材前必须明确选择一个风格，不要静默混用画幅、字体、素材和审批契约。

| 公开名称 | Machine ID | 输出 | 核心素材契约 |
| --- | --- | --- | --- |
| 双语编辑模板图书视频（原风格） | `book-editorial-bilingual-v2` | 3:4 双语母版，可生成 9:16 衍生版 | 有授权的真实书封、12 张批准静帧、本地旁白、双语字幕、确定性 FFmpeg 合成 |
| VOX风格图书视频（新增风格） | `paper-collage-explainer-v1` | 9:16 口播驱动的编辑型知识讲解 | 每次信息变化一条 4–8 秒 visual beat；隐喻、首尾帧/联系表、片段、BGM、母版和发布分别审批 |

选择新风格前，请阅读完整的 [`paper-collage-explainer-v1` 工作流](skills/book-video-factory/references/paper-collage-explainer.md)。“VOX风格”只是公开描述，不代表与 Vox Media 存在合作或隶属关系，也不能据此模仿具体节目、logo 或专有品牌包装；生成提示词使用非品牌化编辑型纸拼贴描述。

内置 VOX 风格目前只支持 `single-book`。`content-system-backed` 仍由原风格使用，因为现有追溯实现绑定 V4 scene-line contract；在新的 manifest-based 追溯实现并通过测试前，系统会拒绝把两者组合。

### Gemini API 与 Google Flow 如何选择

VOX 风格提供两条明确的画面生成路线。无论选择哪条，旁白定时、字幕、BGM、SFX、QC、manifest 和最终母版都由本地图书视频工厂负责。当前仓库是“编排与导入”工作流，不宣称内置一键 Google 视频生成器。

| 路线 | 适用情况 | 依赖与边界 |
| --- | --- | --- |
| `gemini-api` | 需要可复现的程序化生成、operation 追踪或批量处理 | 用户授权的 `GEMINI_API_KEY`、当前 Google Gen AI SDK，以及已批准的配额与费用。使用 Interactions API 的 `gemini-omni-flash-preview`；需要首尾帧控制或延长时使用 `generate_videos` 的 `veo-3.1-generate-preview`。密钥不得写入提示词、日志或 manifest。 |
| `google-flow` | 导演希望在 Google 创作界面逐条尝试 visual beat | 当前账号/地区资格、合格 Google AI 方案、可用 credits、用户操作的浏览器和合法导出文件。Flow 是人工 UI 路线，不假设存在可编程 API。 |

两条路线都要记录：完整提示词、模型或 Flow 标签、输入/输出哈希、operation 或导出证据、界面可见费用/credits、审核人和 `scene_id`。除非音频另有独立授权，生成片段的原生音频会在本地混音前移除。

### VOX 风格核心工作流

1. 锁定可归因资料并批准简洁中文脚本。
2. 生成/录制授权旁白，取得真实 ASR 时间，再拆成每 4–8 秒一次信息变化的 visual beat。
3. Gate 1：审批“概念 → 可见隐喻 → 动画动作 → 禁止项”。
4. Gate 2：审批首尾帧或联系表。
5. Gate 3：通过 Gemini API 或 Google Flow 生成，检查时长、画幅、水印、文字污染、动作连续性和可解码性。
6. 将通过的片段规范化为静音 720×1280 H.264 素材，并在不变速的前提下进入 30 fps 本地时间线。
7. 以已批准旁白和 ASR 时间锁定画面，再统一添加本地字幕、已授权 BGM、SFX 和项目品牌层；BGM 权利与创意审听分别审批。
8. 运行技术 QC，并把画面、声音、本地母版、权利和发布决定绑定到不可变哈希。

## 示例成片

下面是完整流水线的案例输出，不是 Skill 内置的可复用源素材。点击海报可以进入浏览器播放器，也可以[打开完整案例页](https://jaxxchen003.github.io/book-video-factory/demos.html)。

### VOX风格图书视频案例：《超越百岁》

[![《超越百岁》VOX风格图书视频](examples/posters/chaoyue-baisui-paper-collage.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#chaoyue-baisui)

[VOX风格图书视频 · `paper-collage-explainer-v1` · 播放 · 82.7 秒 · 9:16](https://jaxxchen003.github.io/book-video-factory/demos.html#chaoyue-baisui)

这个网页预览来自用户审批通过的 r5 本地母版。原母版保持不可变，且**没有**被记录为生产发布通过；仓库展示衍生版另有独立的操作者发布审批。展示版仅做网页压缩，并替换了开头的真实书封区域。详细来源和哈希见[案例 provenance manifest](examples/manifests/chaoyue-baisui-paper-collage.json)与[脱敏门禁摘要](examples/manifests/chaoyue-baisui-r5-gate-summary.json)。本仓库未独立核验供应商账户条款，案例公开展示也不等于授权他人复用图书、书名、译文、音乐或任何第三方元素。

| 《界限》 | 《不去讨好任何人》 |
| --- | --- |
| [![《界限》成片封面](examples/posters/boundaries.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [![《不去讨好任何人》成片封面](examples/posters/no-people-pleasing.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |
| [播放 · 49.6 秒](https://jaxxchen003.github.io/book-video-factory/demos.html#boundaries) | [播放 · 50.7 秒](https://jaxxchen003.github.io/book-video-factory/demos.html#no-people-pleasing) |

| 《原生家庭》 | 《高敏感是种天赋》 |
| --- | --- |
| [![《原生家庭》成片封面](examples/posters/original-family.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [![《高敏感是种天赋》成片封面](examples/posters/highly-sensitive.jpg)](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |
| [播放 · 56.7 秒](https://jaxxchen003.github.io/book-video-factory/demos.html#original-family) | [播放 · 57.8 秒](https://jaxxchen003.github.io/book-video-factory/demos.html#highly-sensitive) |

这些案例视频不属于仓库 MIT 许可证的授权范围。书封、书名、引用、商标、音乐和其他第三方元素的权利归各自权利人所有，复用或再分发前必须自行确认权利。

## 推荐工具链

Skill 是操作契约和编排层；只要保持相同的输入、来源记录、审批闸门和交付契约，各供应商能力都可以替换。

| 生产环节 | 推荐工具或能力 | 要求与边界 |
| --- | --- | --- |
| 选题与资料 | 已授权的微信读书 Skill、可归因公开元数据、用户提供的资料、Codex 研究 | 不绕过登录或平台控制；读者评论只能作为观点，不能当作事实证据 |
| 脚本与双语文案 | Codex 写作/推理和人工编辑审查 | 事实与引用必须核对来源；英文在母语审校前保持 `needs_native_review` |
| 编辑型静帧 | Codex 自带 GPT Image 或其他已批准图片供应商 | 记录提示词、模型、日期、哈希和审批；不得生成仿冒真实书封 |
| VOX 风格 visual beats | Gemini API 的 `gemini-omni-flash-preview` / `veo-3.1-generate-preview`，或用户操作的 Google Flow | 需要用户授权、成本/credits 审批，以及不可变的提示词与 operation/导出来源记录 |
| 旁白 | 本地 VoxCPM2、已授权真人声音或批准的云 TTS | 仅克隆明确授权的声音，并保存授权记录 |
| 对齐与字幕 | faster-whisper、兼容 Whisper 的 ASR 或编辑器转录 | 时间必须来自真实旁白音频，禁止编造时间戳 |
| 真实书封 | 出版社/零售平台/用户提供的书封及来源元数据 | 与生成素材分开管理，公开发布前确认复用权利 |
| BGM 与 SFX | 有许可、用户自有或授权生成的音频；可选 ChatCut 音乐 | 记录创作者/供应商、许可或授权、来源/哈希和署名要求 |
| 字体与图层 | Pillow、内置 OFL SmileySans 兜底字体或操作者配置字体 | 检查替换字体许可证并保持安全区 |
| 确定性合成 | FFmpeg 与 FFprobe | 用于本地合成、规范化、混音、编码和媒体检查 |
| QC 与发布 | release manifest、来源检查、技术探针和人工审查 | 本地 QC 不等于发布批准；权利和发布闸门必须单独处理 |

仅做规划时需要 Codex 与 Python 3.11+。完整本地合成通常还需要 FFmpeg/FFprobe、Pillow、已批准的图片/视频生成能力、旁白方案、ASR 对齐、已授权音频和足够磁盘空间。运行 `doctor.py` 可以区分 planning-ready 与 render-ready。

## 你需要提供什么

你必须提供或明确授权所有现实媒体与账号：图书资料/书封、旁白方式或声音参考、BGM/SFX、图片/视频生成账号、可选微信读书权限、可选 Gemini API 或 Google Flow 权限、可选 ChatCut 权限，以及最终发布决定。首次制作前请阅读[首次运行指南](skills/book-video-factory/references/first-run.md)。

## 不通过 Codex 初始化

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace .
python3 skills/book-video-factory/scripts/doctor.py --profile planning
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-first-book --book-title '示例书名' --author '示例作者'
```

上面的命令创建原风格项目。VOX 风格必须显式选择生成渠道：

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-vox-book --book-title '示例书名' --author '示例作者' \
  --style-profile paper-collage-explainer-v1 \
  --generation-lane gemini-api

# 或使用：--generation-lane google-flow
```

如果项目由上游内容资产系统提供资料：

```bash
python3 skills/book-video-factory/scripts/bootstrap_workspace.py --workspace . \
  --slug my-topic --book-title '示例书名' --author '示例作者' \
  --mode content-system-backed

python3 book_video_factory/scripts/content_bridge.py export-dbs \
  --content-root /path/to/content-system \
  --assembly /path/to/content-system/06-选题装配/topic.md \
  --output /path/to/content-package.json
python3 book_video_factory/scripts/content_bridge.py validate-package \
  --package /path/to/content-package.json
python3 book_video_factory/scripts/content_bridge.py import-package \
  --project book_video_warehouse/projects/my-topic \
  --package /path/to/content-package.json
```

上游系统继续负责资料审计、内容单元提取、关系、去重、canonical 版本和选题装配；图书视频工厂只消费已验证快照，不反向改写上游。

## 安全与许可边界

MIT 许可证只覆盖本仓库的代码与文档，不会授予图书、书封、引用、字体、音乐、音效、人声、生成产物、平台或模型的权利。不要绕过平台访问控制、暴露凭证、仿冒受保护的品牌/节目视觉身份，或克隆未授权声音。

## 开发检查

```bash
python3 -m unittest discover -s skills/book-video-factory/tests -v
python3 -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
```

如果环境中存在 Codex Skill Creator，再对 `skills/book-video-factory` 运行 `quick_validate.py`。
