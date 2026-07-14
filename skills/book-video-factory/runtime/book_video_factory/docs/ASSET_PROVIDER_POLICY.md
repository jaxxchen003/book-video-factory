# 人声、BGM 与图片供应策略

## 1. 品牌人声

P0 主引擎固定为本地 `OpenBMB/VoxCPM2`。VoxCPM2 不提供需要逐个选择的官方预设音色；它通过自然语言描述生成新音色，也支持使用授权音频进行可控克隆。

执行策略：

1. 使用 `config/voice_candidates.json` 的统一试听文案生成四个候选。
2. 人工选择后，将选中的合成试听保存为工厂级 reference，并创建唯一的 `brand_voice_profile.json`。
3. 所有生产旁白必须使用该 reference 的 VoxCPM2 Ultimate Cloning，同时传入 reference、prompt audio 与精确 prompt text；不能再次调用 Voice Design 假装复现同一音色。
4. seed 必须在模型加载完成后设置。它只负责生成可重复性，不能替代 reference 的说话人身份约束。
5. 所有生产旁白引用同一 profile，禁止在每条视频里临时改音色。
6. VoxCPM2 克隆仍不满意时，再评估 OpenVoice V2 或 CosyVoice；不克隆公众人物、参考视频作者或未授权个人。

生成试听：

```bash
python3 book_video_factory/scripts/generate_voice_auditions.py \
  --config book_video_factory/config/voice_candidates.json \
  --output-dir book_video_warehouse/projects/doudi-qingshan/05_voice_人声/auditions
```

## 2. BGM

P0 默认使用开放许可的现成音乐，不使用许可边界不清的“无版权音乐”。

许可 allowlist：

- `CC0` / Public Domain：优先，无署名要求。
- `CC BY`：允许商用，但交付清单和发布文案必须自动生成署名。

默认拒绝：

- 含 `NC`：不允许商业用途。
- 含 `ND`：不进入需要裁切、循环、淡化或 ducking 的流水线。
- `CC BY-SA`：会带来衍生作品同许可要求，P0 不自动采用。
- 仅写“royalty-free”“no copyright”但没有具体许可证与来源页面的素材。

供应源优先级：

1. Freesound APIv2：用于候选检索和内部试听。每条候选仍须逐条核验许可，只接受 CC0 或 CC BY；免费 API 条款仅允许非商业使用，因此**没有 Freesound/MTG 的商业 API 授权记录时，严禁将该来源下载、合成或发布到商业/可变现成片**。
2. Openverse Audio API：适合自动检索，但每个候选仍需回源核验许可证。
3. Incompetech：CC BY，可商用并要求明确署名；适合作为人工精选的稳定曲库。
4. Wikimedia Commons：只采纳文件页明确标记 CC0、Public Domain 或 CC BY 的录音。

每个 BGM 必须保存：源页面、作者、曲名、许可证、许可证 URL、下载时间、原始文件哈希、Content ID 风险记录和署名文本。

Freesound 候选检索命令（不会下载音频，也不会修改已有成片）：

```bash
python3 book_video_factory/scripts/freesound_music.py \
  --project book_video_warehouse/projects/<slug> \
  --intent '一本关于自我修复的克制、沉静片头氛围' \
  --query 'cinematic ambient piano' \
  --min-duration 55 --max-duration 360 --limit 12
```

`--intent` 记录创作意图，`--query` 使用简洁的英文检索关键词；不要把整段自然语言提示直接传给 Freesound 搜索。候选写入 `06_music_音乐/freesound-candidates.json`。其中 `provider_api_authorization.status` 不是 `commercial_authorized` 时，只能作为内部听感参考；它不能取代可公开发布的 BGM 资产与许可证清单。

## 3. GPT Image 2 图片

场景图、氛围图和重新设计的书封元素统一由 Codex 内置图像生成能力创建，并复制到当前书籍项目的 `03_images_生成图片/`。这条链路不使用本地 OpenAI API key；模型与工具版本写入每批图片的生成清单。生产约束：

- 生成尺寸采用 `1152×1536`，是 3:4 且两边均为 16 的倍数；渲染时缩放到 720×960。
- 草稿使用 `quality=low`，批准后的最终资产使用 `quality=medium` 或 `high`。
- 图片模型不生成书名、作者、字幕、账号名或任何水印；所有文字由视频渲染层叠加。
- 参考片只用于低饱和、黑色留白、人物构图和暖色锚点的风格引导，不复制人物身份、账号标识或原书封设计。
- `gpt-image-2` 当前不支持透明背景。P0 优先生成完整矩形画面；确需独立元素时使用纯色背景加本地抠图，并做边缘 QC。
- 每张图保存 prompt、model、size、quality、生成时间、版本、人工选择状态和估算成本。
- Codex 生成后的项目图片不得只留在 `$CODEX_HOME/generated_images/`；必须复制到书籍仓库后才能被脚本或时间线引用。

推荐基础 prompt 约束：

```text
3:4 vertical editorial portrait, black negative space, low saturation,
one subtle warm accent, cinematic soft light, restrained and reflective,
no text, no letters, no logo, no watermark, no recognizable public figure,
leave safe space for Chinese title and subtitles added later by the renderer.
```
