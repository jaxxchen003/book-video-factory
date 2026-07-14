# 图书号短视频流水线工厂

这个目录只保存可复用能力：程序、脚本、模板契约、依赖说明和运行文档。每一本书的实际资料与媒体产物保存在相邻的 `book_video_warehouse/`，避免把工厂代码和生产素材混在一起。

## 已实现的工程基座

- 标准项目目录初始化，支持重复执行而不覆盖已有产物。
- 参考视频元数据探测与来源登记。
- 微信读书公开资料采集：书籍搜索、详情、目录、热门划线、公开点评。
- 原始接口响应与标准化 `book_source_pack.json` 双份保存。
- 本机依赖自检：FFmpeg、VoxCPM2、Whisper、HyperFrames、Node、微信读书凭证和磁盘空间。
- 批准稿到成片的一键构建：ASR 字级对齐、镜头时间线、中文字幕图层、轻推镜、BGM ducking、最终混音和媒体 QC。
- V2 品牌模板：固定钩子片头、8 张主题卡高速切换、真实书封合成、居中出版物字体、中英双语字幕、分段音乐增益，以及 3:4/9:16/clean 多版本交付。
- 独立单元测试，不依赖现有人物视频项目的历史素材。
- `single-book` 与 `content-system-backed` 双模式；后者消费 `dbs-content-system` 的不可变内容资产快照。
- `source_document / content_unit / claim / assembly_brief` 对象校验，以及脚本—Claim—场景全链路追溯。
- 统一 V4 scene-line 合同，消除场景计划与真实渲染时间线漂移。

## 快速开始

```bash
python3 book_video_factory/scripts/doctor.py

python3 book_video_factory/scripts/init_project.py \
  --warehouse book_video_warehouse \
  --slug doudi-qingshan \
  --book-title 兜底 \
  --author 晴山 \
  --reference-video '/path/to/reference-video.mp4'

python3 book_video_factory/scripts/collect_weread.py \
  --project book_video_warehouse/projects/doudi-qingshan \
  --title 兜底 \
  --author 晴山

python3 book_video_factory/scripts/build_final_video.py \
  book_video_warehouse/projects/doudi-qingshan

python3 book_video_factory/scripts/build_final_video_v2.py \
  book_video_warehouse/projects/doudi-qingshan
```

如果选题来自上游内容资产系统，初始化时增加 `--mode content-system-backed`，再用 `scripts/content_bridge.py` 导入 package 并附加 traceability。详见 [内容资产系统桥接](docs/CONTENT_SYSTEM_BRIDGE.md)。

正式渲染要求项目内已有 `script.approved.json`、锁定版旁白、ASR 字级时间戳、12 张批准镜头和已登记授权的 BGM。脚本会输出预览片、正式成片、SRT、渲染清单、音乐署名文件与 QC 报告，并把交付包复制到 `10_delivery_交付/`。

V2 还要求 `script.v2.bilingual.json`、带停顿的 V2 锁定旁白、真实书封来源记录和 V2 写实书本底图。所有 V2 产物写入独立的 `v2/` 目录，不覆盖 V1。

微信读书密钥优先从 `WEREAD_API_KEY` 读取；如果未设置，脚本会只读 macOS Keychain 中 service 为 `codex-weread-api-key` 的条目。脚本不会打印或保存密钥。

Freesound BGM 凭据同样只从 `FREESOUND_API_KEY` 或 macOS Keychain 读取。`freesound_music.py` 只写入候选与许可证证据，不下载音频；Freesound 免费 API 的非商业限制会在候选清单和 `doctor.py` 中明确标记，不能直接用于公开/可变现成片。

完整目录说明见 [仓库契约](docs/WAREHOUSE_CONTRACT.md)，参考片拆解见 [参考片 1 风格规格](docs/REFERENCE_1_STYLE_SPEC.md)，实际操作见 [运行手册](docs/RUNBOOK.md)。

稳定使用方式、V4 不变量、成本台账和 ChatCut 精修边界见 [稳定生产工作流](docs/STABLE_WORKFLOW.md)。

人声、BGM 与 GPT Image 2 的统一供应策略见 [资产供应策略](docs/ASSET_PROVIDER_POLICY.md)。
