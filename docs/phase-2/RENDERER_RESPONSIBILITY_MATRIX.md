# Renderer 责任矩阵

## 对象边界

| 对象/组件 | 唯一职责 | 不负责 |
|---|---|---|
| Project Manifest (`project.json`) | Project ID、书籍元数据、工作流/Style/Release Profile 选择 | 发布状态、资产清单、Renderer 临时状态 |
| Style Profile | 风格身份、生成渠道、工作模式与需要的审批 Gate | 具体一次 Release 的文件路径或 Hash |
| Release Profile | 画布、FPS、编码目标、排版/音频政策、场景策略 | Project/Release ID、具体资产、临时目录 |
| Release Manifest（待实现） | 某 Release 已批准输入资产、Hash、权利/审批引用及 Profile 绑定 | Renderer 选择的运行时细节、Attempt 状态 |
| RenderRequest | 从 Release Manifest 投影出的不可变一次执行说明，绑定确切 Renderer/Profile/输入 Hash | 成为新的资产真相源、保存凭据或进程对象 |
| Orchestrator | 选择 Renderer、加载/验证真相源、Capability 协商、持久化 Request、启动 Attempt、写 Stage Manifest | 私自改写已批准输入、在 Renderer 内隐式补 Gate |
| Audio preparation/mix | 生成母版级最终混音及可选 stems，记录响度/Hash | 视觉布局、Renderer 私有降级 |
| Caption preparation | 从批准稿生成结构化 cue；用 ASR 只定位时间；绑定字体/安全区策略 | 让 ASR 文本覆盖批准稿、输出 Pillow/React 专属对象 |
| Renderer | 验证 Request、Capability、路径和 Hash；生成请求指定的媒体；保存基础 Probe 和 Result | 查询 Provider、修改 Profile/Manifest、做发布审批、静默降级 |
| Renderer internal checks | 输入可读、Capability、Timeline、输出存在、基础 FFprobe/结构 | 黑帧/静音/完整响度/业务 Gate 的最终判定 |
| Post-QC | 分辨率、编码、时长、黑帧、静音、响度、字幕越界及 Release 规则 | 重新渲染、修改输入、替代人工 Approval |
| Gate evaluator | 组合不可变 Manifest、Approval、Post-QC，派生发布状态 | 信任 `project.json.status` 或 Renderer 自报 `pass` |
| RenderResult | 记录一个 Attempt 的输出、Hash、Probe、错误、指标与 QC handoff | 修改 Release 真相源或声明发布已批准 |

## 字段真相源

| 字段 | 权威来源 | Request 中的处理 |
|---|---|---|
| `project_id` | Project Manifest | 复制并绑定 Project Manifest SHA |
| `release_id` | Release Manifest | 复制并绑定 Release Manifest SHA |
| `profile_id/revision` | Release Manifest 指向的 Release Profile | 记录 ID、revision、Profile SHA 和 portable ref |
| width/height/FPS/codec/安全区 | Release Profile | `output_spec` 是经验证的执行快照；不允许与 Profile 分歧 |
| Style 与审批策略 | Style Profile | Request 仅记录所需/满足的审批证据 ID |
| 资产路径/bytes/SHA | Release Manifest | 选择性复制到 `assets[]`；必须逐项相等 |
| Timeline | 已批准 Timeline artifact；迁移期由 V4 mapper 确定性生成 | Request 固化结构或绑定 artifact；不得由 Renderer 重算业务节拍 |
| Caption 文本 | 批准脚本 | Request cue 绑定脚本 asset/hash；ASR 只提供 timing provenance |
| Caption 时间 | 批准的 Caption/Timeline artifact | Request 使用整数 tick 固化 |
| 最终混音 | Audio Manifest/Release Manifest | `audio.final_mix_asset_id` 必需；stems 可选 |
| Renderer 选择 | Orchestrator 按 Release policy 或 CLI 请求作出 | Request 固化 `renderer.id/version`；Renderer 不自行替换 |
| preview/final | 操作者/工作流 | Request 固化 `render_mode`，两者共用 Schema |
| 凭据 | 环境/进程 Secret Store | 绝不进入 Profile、Manifest、Request、Result 或日志 |
| Attempt ID | Orchestrator | 每次执行独立生成；重试不能复用 |

Request 中的执行快照不是第二真相源。创建 Request 时必须验证其值等于所引用 Profile/
Manifest；验证失败则不允许持久化。

## 生命周期与写权限

| 阶段 | 可写对象 | 规则 |
|---|---|---|
| Freeze Release | 新 Release Manifest | write-once；资产/Approval 改变必须新 Release |
| Prepare Render | 新 RenderRequest | write-once；相同语义可有不同 request_id，但 request_hash 相同 |
| Start Attempt | Attempt event | 独立 attempt_id；pending/running 以 append-only event 表达 |
| Render | Attempt 工作目录 | 只能写 Request 授权的输出/日志 root，不覆盖输入 |
| Finish Attempt | terminal RenderResult | write-once；成功、失败、Blocked、Cancelled 都保存 |
| Record Stage | 新 Stage Manifest | 由 Orchestrator 写入，输入含 Request，输出含 Result/媒体 |
| Post-QC | 新 release-scoped QC artifact | 不覆盖 Result；通过 `qc_handoff` 关联 |

## Preview 与 Final

二者共用 `RenderRequest`/`RenderResult` Schema，通过 `render_mode` 区分：

- `preview` 可以使用 Profile 明确允许的低成本输出规格，但仍必须校验路径、Hash、Timeline
  和权利边界；它不能被 Gate 当作发布母版。
- `final` 必须绑定 Release ID、渲染前所需审批/权利证据、确定性输入和最终混音。
  `local_master_review`/`publish` 等依赖输出的 Gate 只能发生在 RenderResult/Post-QC 之后。
- Preview 到 Final 不是就地升级；应生成新的 Request 和 Attempt。
