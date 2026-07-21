# VOX风格图书视频

Machine ID: `paper-collage-explainer-v1`

这是图书视频工厂新增的第二种风格，不替代原有的 `book-editorial-bilingual-v2`。它用 9:16 原创编辑型纸拼贴、证据导向图解和克制动画解释高信息密度概念；“VOX风格”只是便于用户识别的公开描述，不代表与 Vox Media 存在合作、授权或隶属关系。提示词不得要求复制任何具体节目、logo、片头、字体系统或专有品牌包装。

## 两种风格如何选择

| 公开名称 | Machine ID | 适合场景 | 核心交付 |
| --- | --- | --- | --- |
| 双语编辑模板图书视频（原风格） | `book-editorial-bilingual-v2` | 真实书封驱动、3:4、双语包装、确定性批量渲染 | 12 张批准静帧 + 本地旁白/字幕 + FFmpeg 母版 |
| VOX风格图书视频（新增风格） | `paper-collage-explainer-v1` | 9:16、高信息密度、视觉隐喻和解释型动画 | 每个信息变化一条 4–8 秒 visual beat + 本地旁白/字幕/音频母版 |

创建项目时必须显式选择 VOX 风格的生成渠道：

```bash
# Gemini API 程序化渠道
python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py \
  --workspace . --slug <slug> --book-title '<title>' --author '<author>' \
  --style-profile paper-collage-explainer-v1 \
  --generation-lane gemini-api

# Google Flow 手工导演渠道
python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py \
  --workspace . --slug <slug> --book-title '<title>' --author '<author>' \
  --style-profile paper-collage-explainer-v1 \
  --generation-lane google-flow
```

项目会绑定 `book-vox-vertical-9x16-v1` 发布配置。Skill 提供提示词、审批、导入、本地时间线、音频、QC 与交付编排；仓库当前不宣称内置“一键调用 Google 生成完整成片”的执行器。

当前 VOX 风格只支持 `single-book`。现有 `content-system-backed` 追溯仍绑定原风格的 V4 scene-line contract；在 manifest-based 追溯实现并通过测试前，初始化器会拒绝把 VOX 风格与该模式组合，避免生成伪追溯记录。

## 生成渠道

### Gemini API：程序化生成

仅在用户授权付费生成并提供 `GEMINI_API_KEY` 后使用；密钥只从环境读取，不写入项目、日志、manifest 或提示词。

- 默认模型：Gemini Omni Flash，API ID 为 `gemini-omni-flash-preview`，通过 Interactions API 调用。它是 preview 能力。
- Gemini Omni 不支持视频延长或首尾帧插值；需要首尾帧控制或视频延长时，改用 Veo 3.1，API ID 为 `veo-3.1-generate-preview`，通过 `generate_videos` 调用。
- Gemini Omni 没有独立 negative-prompt 参数；把限制写成普通提示词中的 `Do not ...` 约束。
- 英文提示词是最稳妥的生产默认；其他语言可用性需逐次验证。
- 超过内联响应限制的大文件使用供应商 URI 交付，并记录 URI/operation 与下载后哈希。
- 每次请求记录模型/API surface、提交时间、operation/job ID、完整提示词、输入资产哈希、输出哈希、供应商暴露的用量/费用和失败原因。不可获得的数据记为 `—`，不能猜零。

运行生成前：

```bash
python3 book_video_factory/scripts/doctor.py \
  --profile production \
  --project book_video_warehouse/projects/<slug>
```

官方依据：<https://ai.google.dev/gemini-api/docs/omni>、<https://ai.google.dev/gemini-api/docs/veo> 与 <https://ai.google.dev/gemini-api/docs/video>。

### Google Flow：手工导演与导出

Flow 是用户操作的创作工作台，本 Skill 不假设存在可编程 Flow API。

- 前提取决于当前地区、年龄、账号类型、合格 Google AI 方案和可用 credits；运行前在官方帮助页复核。
- 桌面 Chromium 是推荐环境，不表述为唯一支持方式。
- 只导入用户合法导出的文件；不读取或绕过登录、credits、区域或下载限制，也不把 UI 预览当成可发布资产。
- 每条片段保存 Flow prompt、输出日期、界面可见 credits、导出文件、SHA-256、`scene_id` 和人工审核结论。

官方依据：<https://support.google.com/flow/answer/16353333> 与 <https://support.google.com/labs/answer/16935308>。

## 风格圣经

### 画面语言

- 9:16 竖屏；主体在中央安全区，前景纸屑/中景主隐喻/背景档案纹理分层。
- 纸张撕边、丝网印刷颗粒、剪报、有限配色、清晰留白；每个项目先锁定 4–6 个主色和 1 个强调色。
- 用证据关系、尺度、路径、对比和因果变化组织画面，不用无信息的“漂亮拼贴”。
- 生成片段不放可读文字、字幕、logo 或仿制书封；标题、数据、引文和字幕在本地时间线统一排版。

### 动画语法

每个 4–8 秒 visual beat 只有一个主要信息变化、一个主隐喻和一个主动作：

- `reveal`：撕开纸层，露出隐藏路径或证据。
- `trace`：纸线/箭头沿路径生长，表达过程或因果。
- `compare`：两个剪纸对象缩放、对齐或错位，表达差异。
- `accumulate`：图表、台阶或容器逐层增长，表达积累。
- `transform`：同一对象在受控范围内改变状态，表达前后变化。
- `parallax`：前中后景轻微视差，增强层次，不抢叙事。

镜头只选轻推近、轻平移或固定机位之一。避免快速旋转、强闪烁、无控制 morph、复杂对白、多动作竞争和与口播无关的装饰运动。

## 核心工作流

1. **资料审计**：锁定书籍元数据、可归因资料、Claim 边界和风险说明；读者评论不能当事实证据。
2. **脚本与旁白锁定**：先批准中文脚本，再生成/录制授权旁白并取得真实 ASR 时间。把旁白拆为每 4–8 秒一次信息变化；不要先生成视频再强行拉伸口播。
3. **Gate 1 — 隐喻**：每段填写 `概念 → 可见关系 → 主动作 → 禁止项`，审批后再生图。
4. **Gate 2 — 首/尾帧或联系表**：检查焦点、安全区、材质、配色、隐喻重复、文字污染、解剖错误、logo 和可见水印。未通过不得生成完整片段。
5. **Gate 3 — 片段 QA**：通过选定渠道生成；检查时长、画幅、可解码性、动作连续性、尾帧漂移、嵌字、可见水印和 provenance。每条片段单独通过。
6. **规范化**：把批准素材转换为静音 720×1280 H.264 MP4，再以不变速方式规范化到 30 fps 本地时间线；默认不做光流补帧。
7. **Picture lock**：按旁白/ASR 时间组装 visual beats，加入本地标题、字幕、真实书封或品牌层。图片锁定后再进入最终音频混合。
8. **声音设计**：旁白优先；BGM 先过权利审查，再单独过 `bgm_review` 人耳审听；SFX 只强调关键转折。生成片段的原生音频默认移除。
9. **技术与人工 QC**：验证完整解码、720×1280、30 fps、H.264/AAC、A/V 时长、字幕安全区、约 −16 LUFS、真峰值上限、黑帧和输出哈希。
10. **交付与发布**：`local_master_review`、`publish` 分开审批。若做公开仓库案例，另建 `showcase_publish`，绑定压缩/遮盖后的预览哈希和权利范围。

完整 gate 定义以 [quality-gates.md](quality-gates.md) 为准。

## 单镜头提示词模板

提示词使用非品牌化描述，并把每条视频限制为一个可见动作：

```text
Purpose: <the single relationship the viewer must understand in this beat>.
Visual metaphor: <visible relationship among paper cutouts, objects, paths, or evidence shapes>.
Composition: vertical 9:16, main subject inside the central safe area, layered foreground / midground / background.
Material: original editorial paper-collage, torn paper edges, archival grain, restrained 4–6 color palette, deliberate negative space.
Primary action: <one reveal / trace / compare / accumulate / transform action>.
Camera: <locked / gentle push-in / gentle lateral move>, subtle layered parallax only.
Continuity: preserve subject identity, palette, lighting direction, paper texture, and spatial layout from the approved frame.
Do not include logos, readable text, subtitles, book-cover replicas, visible third-party watermarks, brand/program imitation, rapid rotation, flashing, uncontrolled morphing, multiple competing actions, or talking characters.
Audio: silent visual asset; narration, captions, BGM, and SFX are added in the local master.
```

若使用 Gemini Omni，不要把 `Avoid/Do not` 区域误当成不存在的独立 negative-prompt 参数；它属于普通提示词正文。

## 最低资产 manifest

每个生成片段至少记录：`release_id`、`scene_id`、`script_line_id`、`provider_lane`、`model_or_flow`、`api_surface`、`prompt`、`input_hashes`、`output_path`、`output_sha256`、`duration_seconds`、`width`、`height`、`fps`、`audio_policy`、`gate_1`、`gate_2`、`gate_3`、`reviewer`、`operation_or_export_evidence`、`cost_evidence`、`synthid_policy`。

字段或审批缺失时，片段不得视为可复用、可交付或可发布资产。
