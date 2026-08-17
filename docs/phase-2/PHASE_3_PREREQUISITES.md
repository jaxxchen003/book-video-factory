# Phase 3 准入与最小范围

## 唯一下一轮

下一轮只实施 **Renderer Contract v1 基础设施 + V4 兼容包装**。不接入 Remotion，不写
新视觉 Renderer，不拆音频 graph，不改生产模板视觉。

## 开始前必须满足

- Phase 2 设计文件完成评审并提交到 `design/renderer-contract-v1`。
- 分支推送到个人 Fork，工作区干净。
- Request/Result/Capability 示例通过 JSON 解析与合同一致性检查。
- 12 项强制决策没有未解决冲突。
- 维护者接受：Release Manifest 当前缺失，Phase 3 先新增最小 immutable release
  snapshot/freeze 机制，不把旧 `render_manifest.v4.json` 改名冒充。
- 73 项既有测试继续作为回归基线。

## Phase 3 允许实现

1. `render-request-v1`、`render-result-v1`、`renderer-capabilities-v1` 的正式 JSON Schema。
2. Python frozen dataclass、纯 validator、portable path/root resolver。
3. `canonical-json-v1` 与 Request Hash。
4. 最小 immutable Release Snapshot v1 writer/validator，复用现有 artifact SHA、Approval 和
   Release-scoped Gate 语义；不改写已有 Stage Manifest。
5. V4-to-Request mapper，覆盖本报告逐字段表。
6. `LegacyV4Renderer` facade：通过可注入 runner 调用未修改的现有 V4 链并收集 Result。
7. Attempt event、terminal Result、QC handoff 和 Stage Manifest 记录。
8. L1–L4 测试及 fake-runner facade tests；按环境允许增加最小 synthetic media test。

## Phase 3 禁止

- 创建 Remotion/Node/React 工程；
- 新实现视觉模板或 Renderer；
- 修改 `build_final_video_v2.py` 的 filter graph；
- 把 stems mixing 变成核心默认；
- 修改 Pillow 排版、Caption 像素或 V4 常量；
- 删除/移动/弃用 V1–V5、Showcase 或 Legacy 文件；
- 调用 Provider、外部 API、下载模型/字体或生成生产视频；
- 修改发布 Gate 语义或允许 `project.json.status` 绕过 Gate。

## 最小提交建议

建议保持可审查的逻辑提交：

1. `feat(contract): add renderer request result schemas and validation`
2. `feat(contract): map v4 release inputs into immutable render requests`
3. `feat(renderer): wrap legacy v4 chain behind renderer protocol`
4. `test(contract): cover hashing paths states and v4 mapping`

具体提交由下一阶段批准后执行；本轮不创建代码。

## Phase 3 验收

- 旧 V4 文件未被修改或移动；
- 原 CLI 仍可直接调用；
- 相同 V4 inputs 生成稳定 Request Hash；
- 每次重试有独立 Attempt/Result；
- 缺资产、Hash/Gate/Rights/Capability 问题 fail-closed；
- facade 使用 fake runner 可完整验证命令、输出收集与错误映射；
- Stage Manifest 绑定 Request/Result/输出 Hash；
- Post-QC 只通过 handoff 读取本次 Attempt；
- 全量旧测试和新增合同测试通过；
- 没有 Remotion 或新依赖进入生产路径。

## 后续而非 Phase 3

只有 V4 包装、characterization 和 QC handoff 稳定后，才单独设计：

- 把现有 audio graph 提升为 final-mix Audio Finalizer；
- 新旧视觉 Renderer 对同一 Request 的并行实验；
- 任何 Remotion 依赖、Chrome/Windows smoke 或实现代码。
