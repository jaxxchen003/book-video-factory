# 运行手册

## 1. 环境自检

```bash
python3 book_video_factory/scripts/doctor.py --json
```

`blocked` 表示当前阶段必需项缺失；`warn` 表示后续阶段能力未就绪但不阻塞项目初始化或资料采集。

## 2. 初始化一本书

```bash
python3 book_video_factory/scripts/init_project.py \
  --warehouse book_video_warehouse \
  --slug doudi-qingshan \
  --book-title 兜底 \
  --author 晴山 \
  --reference-video '/absolute/path/reference.mp4'
```

命令可重复执行。已存在的 `project.json` 不会被覆盖；参考片探测结果会写入选题目录。

## 3. 采集微信读书资料

```bash
python3 book_video_factory/scripts/collect_weread.py \
  --project book_video_warehouse/projects/doudi-qingshan \
  --title 兜底 \
  --author 晴山
```

采集顺序固定为搜索书籍、精确匹配书名/作者、获取详情、目录、全书热门划线和公开点评。原始响应保存在 `raw/`，后续脚本只使用 `normalized/book_source_pack.json`。

## 4. 后续生产闸门

资料包生成后，按以下顺序推进：

1. 从资料包生成传播角度与 `script.draft.json`。
2. 人工核验引用和观点，生成 `script.approved.json`。
3. 生成无文字氛围图，并人工选择到 `approved/`。
4. 使用 VoxCPM2 生成已批准旁白；使用已授权 BGM。
5. 根据最终人声生成字幕时间锚点和时间线。
6. FFmpeg 渲染 3:4 预览片，运行媒体、字幕、安全区和授权 QC。
7. 人工批准后写入 `final/` 与 `10_delivery_交付/`。

任何上游内容变化都生成新版本，不直接覆盖人工批准产物。

## 5. 从批准素材生成正式成片

项目内的批准稿、锁定版旁白、ASR 字级时间戳、批准图片和 BGM 全部就绪后运行：

```bash
python3 book_video_factory/scripts/build_final_video.py \
  book_video_warehouse/projects/doudi-qingshan
```

脚本以批准文案为字幕真值，只使用 ASR 做时间定位。默认输出 720×960、30fps 的 H.264/AAC MP4，并生成：

- `07_timeline_时间线/render_manifest.approved-v1.json`
- `07_timeline_时间线/subtitles.approved-v1.srt`
- `08_render_合成/preview/doudi-approved-v1-preview.mp4`
- `08_render_合成/final/doudi-approved-v1-final.mp4`
- `09_qc_质检/qc_report.approved-v1.json`
- `10_delivery_交付/` 下的完整交付包

只需要重建字幕图层和时间线、暂不渲染视频时，可追加 `--skip-render`。

## 6. V2 品牌双语模板

V2 在 V1 之外独立生成，不覆盖任何已交付成片：

```bash
python3 book_video_factory/scripts/build_final_video_v2.py \
  book_video_warehouse/projects/doudi-qingshan
```

V2 的固定结构为：

1. 人物冷开场并立即进入钩子旁白。
2. “它来自——”后保留受控停顿。
3. 停顿期间高速切换 8 张自有主题卡，并使用与卡片逐帧同步的机械时钟 tick；最后一拍增加轻量落点。
4. 落到本期真实书封，随后显示顶部居中的书名和作者。
5. 正文使用中文宋体主字幕和英文衬线副字幕。
6. BGM 从第一帧开始，片头切换段动态增益，正文由人声 sidechain ducking。

交付目录 `10_delivery_交付/v2/` 包含：

- `doudi-v2-bilingual-3x4.mp4`
- `doudi-v2-bilingual-9x16.mp4`
- `doudi-v2-clean-3x4.mp4`
- `doudi-v2-clean-9x16.mp4`
- 中、英、双语三套 SRT
- 真实封面来源记录、音乐署名和 V2 渲染清单

只生成真实书封、主题卡、双语字幕图层和时间线时，使用 `--prepare-only`。

英文脚本的 `translation_status` 为 `production_draft_needs_native_review` 时，可以内部预览和测试，但正式海外商业发布前仍应完成母语审校。
