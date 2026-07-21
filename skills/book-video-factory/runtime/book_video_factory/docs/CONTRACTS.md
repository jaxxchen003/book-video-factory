# 图书视频工厂合同层

这一层把现有 V4/V5 渲染器包装成可审计执行引擎，不重写已经稳定的媒体合成代码。

## 对象边界

- `style_profile`：公开风格名称、稳定 machine ID、生成渠道、执行模式和风格专属审批。
- `release_profile`：画布、脚本/场景策略、标题安全区、编码规格和渲染器类型。
- `stage_manifest`：一次阶段运行的输入、输出、hash、检查、工具与 release ID。
- `approval_event`：人工审批决定以及审批时对应的文件 hash。
- `source_document / content_unit / claim / assembly_brief`：由 `content-system-backed` 模式以不可变 JSON 快照接入；不复制上游内容系统的主题、关系和去重实现。
- `traceability_map`：绑定 package、脚本、Claim、场景以及三类文件 hash。
- `release_manifest`：后续 freeze-release 阶段生成的不可覆盖交付清单。

## 真源规则

1. 原始来源与人工批准文件不得被生成脚本覆盖。
2. `project.json.status` 只是旧脚本兼容缓存。
3. 发布状态必须由当前文件、manifest 和 approval event 重新计算。
4. 审批事件绑定文件 hash；审批对象改变后旧审批自动失效。
5. manifest 与 release 使用新文件写入，不允许覆盖。
6. 内容快照和追溯图的当前选择通过 append-only activation event 记录，不能靠文件 mtime 猜测。

完整桥接格式与命令见 [内容资产系统桥接](CONTENT_SYSTEM_BRIDGE.md)。

## 两组内置 style / release contract

### 双语编辑模板图书视频（原风格）

- Style：`book-editorial-bilingual-v2`
- Release：`book-v4-bilingual-3x4`
- Renderer：`build_batch_video_v3`

- `720×960 / 30fps`
- 15 行双语脚本
- 12 张按 SHA-256 去重的 PNG 场景
- H.264 + AAC
- 标题左右各 56px 安全边距、最多两行、34–70px 动态字号

### VOX风格图书视频（新增风格）

- Style：`paper-collage-explainer-v1`
- Release：`book-vox-vertical-9x16-v1`
- Renderer contract：`external_clip_timeline_v1`（编排/导入，不是内置一键生成器）

- `720×1280 / 30fps` 本地母版
- 可变脚本行数和 manifest-defined MP4 visual beats
- Gemini API 或 Google Flow 生成渠道必须显式选择
- 48px 水平安全边距、120px 字幕底部安全区
- H.264 + AAC，旁白优先，约 −16 LUFS，真峰值上限 −1.2 dBFS

两个 profile 是独立合同，不把任一风格的场景数量、画幅或渲染器当成通用常量。旧项目没有 `style_profile_id` 时只为兼容回退到原风格。
