# Phase 2 Prerequisites

## 准入结论

当前 **不满足 Phase 2 Renderer 改造准入条件**。阻塞不在架构未知，而在仓库远程不安全、基线测试非绿、字体合同破损，以及 Renderer/QC 接口尚未形成可测试边界。

## 必须条件

| 条件 | 当前状态 | 准入要求 | 验证证据 |
|---|---|---|---|
| Windows Doctor | 未满足 | 修复 `os.uname()` 或由维护者明确批准带风险豁免；同类 WeRead/Freesound credential path 一并覆盖 | 正式 Doctor 退出 0；Windows unit test |
| 字体策略 | 未满足 | 确认再分发权后补齐实际 OTF，或改为用户显式配置且可靠 fail-closed；不能只留许可证文本 | 资源清单、字体 SHA/许可、fallback test |
| 基线测试 | 未满足 | 56 项按原 unittest 口径全绿，或每个未通过项有明确、时限和影响范围清楚的批准豁免 | 两组完整测试日志 |
| 主 Runtime 入口 | 已确认 | 以 `render_ready_v4 → build_batch_video_v3 → V2 helpers → v4_post_qc` 锁定现状基准 | 本审计调用链 + characterization tests |
| Legacy 隔离方案 | 未满足 | 保留 V1/V2 历史；把 V2 通用 helper 与《兜底》main 分界，不直接删除 | 文件分类表和迁移 ADR |
| Renderer 契约草案 | 未满足 | 定义 `RenderRequest`, `RenderResult`, renderer identity/version、输入 artifact hash、silent visual/final master 角色、错误语义 | Schema/类型 + contract tests |
| Manifest 字段 | 部分满足 | 复用 Stage Manifest 的 project/release/profile/artifact SHA；确认 timeline、scene manifest、font、audio、renderer metadata 字段 | Schema review + fixture |
| QC 契约 | 未满足 | Post-QC 从 Release Profile/RenderResult 读取目标；建立媒体 fixture 与 pass/fail tests | `v4_post_qc` tests |
| 音频/视觉边界 | 未满足 | 对 `render_variant()` 建 characterization test；至少可稳定包装 silent base 边界 | synthetic media test |
| 个人 Fork 可推送 | 未满足：`BLOCKED_FORK_SETUP` | `origin` 为用户 Fork、`upstream` 为原作者、创建并推送非 main 验证分支 | `git remote -v` + dry/safe push result |
| 基线 Commit 与修复 Commit 可对比 | 部分满足 | 保留基线 SHA `7ec7237...`，修复放独立 commit；不得混入 Renderer 改造 | Git log/diff |
| Git 历史 | 未满足但不阻塞审计 | 成功 unshallow，或明确批准在 shallow 基础上开发并记录限制 | `git rev-parse --is-shallow-repository` |
| Remotion 依赖与 Windows smoke | 未开始 | 仅在基线修复完成后，核验兼容 Node 的版本、Chrome、字体、最小静音渲染 | 独立实验日志，不改生产路径 |

## Renderer 契约最小草案

以下是 Phase 2 需要评审的字段集合，不是本轮实现：

```text
RenderRequest
  request_version
  project_id
  release_id
  release_profile_id + profile_revision + profile_sha256
  renderer_id + requested_renderer_version
  canvas {width, height, fps, pixel_format}
  duration_seconds
  timeline_manifest {path, sha256}
  visual_assets[] {role, path, sha256, rights_gate_ref}
  overlay_assets[] / caption_timing
  audio_assets[] {role, path, sha256}
  output_role + output_path

RenderResult
  renderer_id + renderer_version
  status
  outputs[] {role, path, bytes, sha256}
  media_probe {codec, width, height, fps, duration, audio}
  checks[]
  diagnostic_log
```

原则：路径必须位于项目允许目录，artifact 以 SHA-256 绑定；Renderer 不接受未批准的隐式默认资产，不把 `project.json.status` 作为审批来源。

## Manifest 决策点

进入编码前必须明确：

- V4 的固定 12 场景合同是否继续作为一种 Profile-specific Scene Manifest，而非全局 Schema。
- Caption 是由 Remotion 消费结构化 timing，还是继续用 Pillow PNG；迁移阶段需允许二者显式选择，禁止静默重复叠加。
- silent visual master 和 final muxed master 必须是不同 artifact role。
- Font 的逻辑角色、实际文件 SHA、许可/来源与 Renderer version 是否进入 Manifest。
- `v4_post_qc.py` 的 `release_id` 在可发布构建中应强制必填；preview 可显式无 Release。
- Renderer smoke QC、Post-QC、human approval 的职责要分开，不能用一个 `status: pass` 混同。

## 测试恢复顺序

1. 修 Windows Doctor 和 Provider credential platform test。
2. 修复/替换字体合同，使现有 Typography/Renderer contract 全绿。
3. 为 V2/V4 建立 synthetic media characterization tests。
4. 为 `v4_post_qc.py` 与 RenderResult/Stage Manifest 建合同测试。
5. 最后才创建 Remotion spike；legacy Adapter 与 spike 对同一 fixture 输出可比较结果。

## Legacy 隔离原则

- 不删除 V1/V2、Showcase、seed 或现有示例资产。
- 先提取纯函数/媒体步骤，再让旧 main 通过 Adapter 调用；避免一次移动造成调用路径断裂。
- `build_batch_video_v3.py` 的当前 V4 输出作为行为基线，直到新路径通过 Gate 和媒体测试。
- V5 ChatCut repair 保持 recipe，不作为新 Renderer 契约的默认实现。

## 唯一建议下一轮

执行一个独立的 **Phase 1.5 基线可开发化轮次**：先建立可推送个人 Fork，然后只修复 Windows 平台判断与字体资源/配置合同，使同一基线上的 56 项测试全绿；该轮不创建 Remotion 工程、不重构 Renderer。完成后再进入 Renderer 契约设计。

