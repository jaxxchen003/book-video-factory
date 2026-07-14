# 生产仓库契约

每本书对应 `book_video_warehouse/projects/<slug>/` 下的一个独立项目。目录编号就是流水线顺序。

```text
00_topic_选题/
01_research_资料搜集/
  raw/                 # 原始接口响应，便于追溯
  normalized/          # 标准化资料包
  sources/             # 人工补充的来源与授权记录
02_story_script_故事脚本/
03_images_生成图片/
  prompts/
  generated/
  approved/
04_copy_文案/
05_voice_人声/
06_music_音乐/
07_timeline_时间线/
08_render_合成/
  preview/
  final/
09_qc_质检/
10_delivery_交付/
manifests/
  stages/               # 每次阶段运行的不可覆盖 manifest
logs/
  approval_events/      # 绑定文件 hash 的人工审批事件
```

## 关键文件

- `project.json`：项目身份、工作模式、release profile 与兼容状态缓存；它不是发布状态真源。
- `00_topic_选题/reference.json`：原片路径和 ffprobe 媒体规格。
- `01_research_资料搜集/raw/*.json`：微信读书接口原始结果。
- `01_research_资料搜集/normalized/book_source_pack.json`：脚本阶段唯一读取的标准资料包。
- `02_story_script_故事脚本/script.draft.json` 与 `script.approved.json`：草稿和人工批准稿分离。
- `07_timeline_时间线/render_manifest.json`：画面、字幕、旁白和音乐的时间映射。
- `09_qc_质检/qc_report.json`：机器检查与人工审批结果。
- `10_delivery_交付/delivery_manifest.json`：最终交付文件、哈希和授权状态。
- `manifests/stages/<stage>/*.json`：阶段输入、输出、hash、检查与生产工具。
- `logs/approval_events/*.json`：审批人、决定、审批对象及当时文件 hash。

生成媒体目录默认不进入 Git；清单、脚本、资料与质检报告可以版本管理。所有阶段只读取前序产物并写入自己的目录，不覆盖人工批准文件。工作流状态由 gate evaluator 根据当前文件、manifest 与 approval event 重新计算；手工修改 `project.json.status` 不会获得发布权限。
