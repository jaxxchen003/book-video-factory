# QC Handoff 契约

## 决策

QC 分为四层，不能用一个 `status: pass` 混同：

1. Orchestrator preflight；
2. Renderer 内部验证与基础 Probe；
3. 独立 Post-QC；
4. Release Gate / 人工审批。

Renderer 成功只表示产生了符合基础输出合同的媒体，不表示内容、权利或发布已批准。

## 职责划分

| 检查 | Preflight | Renderer | Post-QC | Gate |
|---|:---:|:---:|:---:|:---:|
| Request Schema/版本 | 主 | 再验证 | 读取 | — |
| 路径不绝对、无 `..`、root 合法 | 主 | 再验证 | — | — |
| 输入存在/Hash | 主 | 再验证 | 可抽查 | 通过 Manifest 关联 |
| 渲染范围内的 Gate/rights snapshot 允许执行 | 主 | 不查询外部状态 | — | 最终派生 |
| Capability | 主 | 再验证 | — | — |
| Timeline/Caption/Audio 范围 | 主 | 再验证 | 媒体结果复核 | — |
| 输出文件存在、非零 | — | 主 | 再验证 | — |
| 基础 Probe 可读 | — | 主 | 再运行/比较 | — |
| width/height/FPS/codec/duration | 基于 Profile 期望 | 基础比较 | 权威技术判定 | 消费结果 |
| 黑帧/冻结帧 | — | 可选 warning | 主 | 消费结果 |
| 静音/A-V sync/响度/真峰值 | 输入基础检查 | 基础流检查 | 主 | 消费结果 |
| 字幕越界/安全区/缺字 | 请求级验证 | 基础/实现内 | 主，含抽帧/布局证据 | 消费结果 |
| Voice/visual/audio 等渲染前权利 | 不满足则 Blocked | 不做业务判断 | 报告证据，不批准 | 最终复核 |
| 翻译审阅、local master review、publish Approval | 不作为同一输出的前置 Gate | 不做业务判断 | 报告 hold/证据，不批准 | 主 |

## `qc_handoff`

成功或可分析的失败 Result 应包含：

```text
qc_handoff
  release_id
  request_hash
  attempt_id
  output_asset_ids[]
  output_spec_snapshot
  media_probe_ref
  renderer_checks[]
  expected_post_qc_profile_id
  rights_snapshot_hash
  approval_snapshot_hash
```

`media_probe_ref` 指向 Result sidecar；所有路径使用 portable root/path，且 sidecar 自身有
SHA。`output_spec_snapshot` 必须等于 Request 中经 Profile 验证的值。

Post-QC 先校验 Request/Result/输出 Hash 关联，再执行媒体检查。任何关联不一致使用
`RENDER_HASH_MISMATCH` 或独立 QC 错误，不能继续评估为 pass。

## Renderer 内部状态

- `succeeded`：输出存在，基础 Probe 成功，Renderer 级 error checks 全部通过；
- `failed`：输入合同、进程、输出或 Probe 失败；
- `blocked`：权利/Gate/Capability 等可操作前置条件不满足，未开始媒体生成；
- `cancelled`：收到取消请求并停止；可能存在未授权为输出的临时文件。

`pending`/`running` 是 Attempt 过程状态，建议写 append-only event；terminal
`render-result.json` 只写一次。

## Post-QC 输出

Post-QC 报告必须 release-scoped，并至少记录：

- Request/Result/Attempt ID 和 Hash；
- 实际 Probe 与目标 Profile；
- 分辨率、编码、FPS、时长、帧数；
- 黑帧、冻结帧、静音、A/V sync、响度、真峰值；
- Caption 安全区/溢出/缺字检查；
- warnings、errors、证据 sidecars；
- `local_master_status`，以及与它分离的 rights/business holds。

Gate evaluator 读取 Post-QC、Manifest 和 Approval 派生状态。Renderer 或 Post-QC 都不得
直接把 `project.json.status` 当作发布真相。

## V4 迁移

当前 `qc_report.v4.json` 中的 dimensions/loudness 可映射为 Renderer checks；
`v4_release_gate.json` 映射为 Post-QC。其 720×960、15 行、12 场景字面量下一阶段应从
Request/Profile snapshot 读取，但 Phase 2 不修改脚本。
