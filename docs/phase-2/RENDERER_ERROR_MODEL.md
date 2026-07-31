# Renderer 错误模型

## 原则

- 错误码稳定，版本升级不得改变既有码的含义。
- 人类可读消息可改进，但不得作为自动流程分支依据。
- 底层命令、堆栈和 stderr 单独保存为受控日志，不直接嵌入消息。
- 错误对象不得包含凭据、环境变量全集、绝对路径或未脱敏命令行。
- 一个 Result 可以包含多个错误，但必须有一个 `primary_error_code`。

## 状态语义

| Result 状态 | 使用条件 |
|---|---|
| `pending` | Attempt 已创建、未启动；通常作为 append-only event |
| `running` | 已启动；通常作为进度 event |
| `succeeded` | 输出、Hash、基础 Probe 与内部 checks 全部满足 |
| `failed` | 合同/输入数据、Renderer 进程、输出或 Probe 技术失败 |
| `blocked` | Gate、Rights、Capability 等外部/政策前置条件不满足，未渲染 |
| `cancelled` | 明确取消；不得把部分临时输出登记为成功 artifact |

## 稳定错误码

| 错误码 | 默认状态 | 阶段 | 可重试 | 含义 |
|---|---|---|:---:|---|
| `RENDER_INPUT_INVALID` | failed | validate | 否 | Schema、ID、root、portable path 或字段组合非法 |
| `RENDER_ASSET_MISSING` | failed | validate | 修复后 | 声明资产不存在 |
| `RENDER_HASH_MISMATCH` | failed | validate/collect | 否 | 输入或输出字节与绑定 SHA 不同 |
| `RENDER_CAPABILITY_UNSUPPORTED` | blocked | negotiate | 换 Renderer/批准降级后 | Renderer 不满足 Request 能力 |
| `RENDER_GATE_BLOCKED` | blocked | preflight | Gate 满足后 | 工作流 Gate 不允许本次模式 |
| `RENDER_RIGHTS_BLOCKED` | blocked | preflight | 权利审批后 | 权利证据缺失/失效 |
| `RENDER_TIMELINE_INVALID` | failed | validate | 修复后 | 倒序、重叠、gap、越界或 frame 映射非法 |
| `RENDER_AUDIO_INVALID` | failed | validate/render | 修复后 | final mix 缺失、时长/格式/同步不合法 |
| `RENDER_CAPTION_INVALID` | failed | validate/render | 修复后 | 文本来源、cue/word timing、安全区或行数非法 |
| `RENDER_FONT_UNAVAILABLE` | failed | validate | 安装/配置后 | 字体角色无法解析或 Hash 不匹配 |
| `RENDER_PROCESS_FAILED` | failed | render | 视原因 | Renderer 子进程/引擎非零退出或异常 |
| `RENDER_OUTPUT_MISSING` | failed | collect | 可重试 | 声称完成但预期输出不存在/为空 |
| `RENDER_PROBE_FAILED` | failed | probe | 可重试 | 无法解析输出媒体或基础 stream 缺失 |
| `RENDER_CANCELLED` | cancelled | any | 新 Attempt | 操作者/编排器取消 |

“修复后可重试”必须创建新的 `attempt_id`；不能覆盖原 Result。

## 错误对象

```json
{
  "code": "RENDER_ASSET_MISSING",
  "message": "Required visual asset is unavailable.",
  "stage": "validate",
  "retryable": false,
  "asset_id": "scene-01",
  "details": {"expected_role": "scene_visual"},
  "log_ref": {"root": "project", "path": "08_render_合成/attempts/attempt-001/logs/renderer.log"}
}
```

`details` 只允许 Schema 定义的脱敏字段。系统路径要转换为 root/path；若无法安全转换，
只写内部日志，不写 Result。

## 多错误优先级

预检按以下优先级选择 primary error：

1. Request/路径非法；
2. Gate/Rights blocked；
3. Capability unsupported；
4. Asset/Hash/字体；
5. Timeline/Audio/Caption；
6. Process/Output/Probe；
7. Cancelled 由取消事件覆盖正在运行的技术错误，但保留次要诊断。

验证阶段应尽量收集所有独立问题，减少逐个修复循环；但发现路径逃逸、Hash 被篡改或
凭据泄露风险时立即停止。
