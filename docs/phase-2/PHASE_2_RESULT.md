# Phase 2 Renderer 契约设计结果

## 基本信息

- 仓库：`mit-mary/book-video-factory`
- 分支：`design/renderer-contract-v1`
- Phase 2 基线：`e6e986edf58f7477516069a8d4a9345b60ea3fe0`
- 基线来源：`fix/windows-baseline-readiness`；本轮未合并或改写 `main`
- 本轮性质：纯设计文档
- 生产 Runtime 修改：无
- Remotion/Node/React：未接入、未创建
- 新依赖、外部 API、视频生成：无

## 当前 Renderer 边界

已确认真实主链：

```text
render_ready_v4.py
→ build_batch_video_v3.py
→ build_final_video_v2.py helpers
→ v4_post_qc.py
```

现状不是独立 Renderer API：项目目录和固定路径是隐式 Request；`render_variant()` 同时
完成 PNG overlay、stems 混音和最终编码；`render_manifest.v4.json` 可覆盖且混合输入/
时间线/结果；Post-QC 再次猜测固定路径和 720×960/15/12 字面量。

仓库只有 Stage Manifest/Approval/Gate/Traceability 的实现，没有已实现的 immutable
Release Manifest/freeze-release。该缺口已明确记录，没有用 Showcase 或旧 render manifest
伪造完成状态。

## 契约关键决策

1. Request 独立、write-once 持久化，并有独立 request_id/hash。
2. Release Manifest 是资产/Hash/权利真相；Request 是验证后的执行投影。
3. Audio 采用必需 final mix + 可选 stems；Renderer 不私自混音。
4. Timeline v1 采用 Narration Segment，而不是通用多轨。
5. Caption 文本来自批准稿，ASR 只提供时间；Caption Track 保存 cue/word timing。
6. Preview/Final 共用 Schema，以 `render_mode` 和 Profile policy 区分。
7. Capability 不足默认 Blocked；降级必须预先写入 Request 并绑定 Approval。
8. Renderer 只做输入/Capability/Timeline/输出/基础 Probe；完整 Post-QC 与 Gate 在外。
9. 旧 V4 先包装、不废弃，保留原 CLI 回滚。
10. 实现专属配置只进入 reverse-DNS `extensions`，并由 Capability 声明。
11. Request Hash 覆盖所有媒体语义/输入/版本/审批/持久化 target，排除临时目录和运行元数据。
12. 每次 Render Attempt 有独立 ID；重试不能覆盖结果。

## 推荐迁移方案

唯一推荐：**新契约包装旧 FFmpeg V4 链**。

Phase 3 先实现 Schema、validator、Hash、immutable release snapshot、V4 mapper 与
LegacyV4Renderer facade；旧 `build_batch_video_v3.py --release-version v4` 保持不变。
这条路径提供最清晰的回滚点，也避免第一个新 Renderer 反向污染核心合同。

## 验收清单

- [x] Phase 1.5 文档提交已推送
- [x] 工作区干净后开始 Phase 2
- [x] 未修改生产 Runtime
- [x] 未接入 Remotion
- [x] 已确认真实 Renderer 边界
- [x] 已定义 Request、Result、Capability 和错误模型
- [x] 已决定 Timeline、Audio、Caption、QC 边界
- [x] 已完成 V4 逐字段映射
- [x] 已比较四个迁移方案并给出唯一推荐
- [x] 已设计测试策略
- [x] 核心契约不绑定具体媒体/前端实现
- [x] 未引入新依赖
- [x] 已明确下一阶段最小实现范围

## 文档验证

- 必需 Markdown：15/15 存在；JSON 示例：3/3 存在。
- 三份 JSON 均通过 PowerShell `ConvertFrom-Json` 解析。
- SHA/Request Hash 字段均为 64 位小写十六进制。
- 所有 JSON `path` 均为 portable relative path；未发现 drive、UNC、绝对路径或 `..`。
- Request 的 asset/cue/Capability 引用完整；Timeline/OutputSpec 时长一致。
- Result 的 Request/Renderer/输出 Hash/QC handoff 与示例 Request 一致。
- 14 个稳定错误码、13 项 Capability、6 个状态和 8 个迁移方式术语均存在。
- Markdown code fence 配对，无尾随空白。
- Git 变更只包含 `docs/phase-2/`；没有 Runtime 或依赖变化。

本轮没有重新运行 73 项代码测试，因为没有修改代码；Phase 1.5 的 73/73 是进入本轮的
已验证基线，不把它伪装成本轮重新执行的结果。

## Phase 2 是否通过

结论：**设计验收通过。**

通过范围只包含 Renderer Contract v1 设计和示例。提交/推送这些文档是本轮 Git 收尾；
在文档分支推送并确认工作区干净前，不启动 Phase 3 实现。

## 唯一下一轮

执行 `PHASE_3_PREREQUISITES.md` 定义的“Renderer Contract v1 基础设施 + V4 兼容包装”。
不得同时创建 Remotion 工程、修改音频 filter graph、重做视觉模板或接入 Provider。

## 报告文件

```text
docs/phase-2/
├── PHASE_1_5_CLOSURE.md
├── CURRENT_RENDERER_BOUNDARY.md
├── RENDERER_CONTRACT_V1.md
├── RENDERER_RESPONSIBILITY_MATRIX.md
├── RENDERER_CAPABILITY_MODEL.md
├── TIMELINE_MODEL_DECISION.md
├── AUDIO_BOUNDARY_DECISION.md
├── CAPTION_BOUNDARY_DECISION.md
├── QC_HANDOFF_CONTRACT.md
├── V4_TO_RENDERER_CONTRACT_MAP.md
├── RENDERER_MIGRATION_OPTIONS.md
├── RENDERER_ERROR_MODEL.md
├── RENDERER_CONTRACT_TEST_STRATEGY.md
├── PHASE_3_PREREQUISITES.md
├── PHASE_2_RESULT.md
└── schemas/
    ├── render-request-v1.example.json
    ├── render-result-v1.example.json
    └── renderer-capabilities-v1.example.json
```
