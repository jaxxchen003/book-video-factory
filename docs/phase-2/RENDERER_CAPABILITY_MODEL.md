# Renderer Capability 模型

## 决策

Capability 是 Renderer 的版本化声明，工作流在创建 Request 前完成协商。Renderer 不得
因为能力不足而私自删除字幕、简化转场、忽略音轨或换用别的资产。

默认规则：**Capability 不足时 Blocked。** 只有 Request 明确包含由工作流批准的降级
计划，且 Renderer 声明支持该计划时，才可执行降级。Final 模式不得使用未绑定 Approval
的降级。

## v1 能力集合

| Capability | 含义 | v1 参数示例 |
|---|---|---|
| `still_images` | 静态图片作为视觉源 | 格式、最大尺寸 |
| `layered_images` | 多图层与透明度/层级 | alpha、blend modes |
| `video_clips` | 视频片段作为视觉源 | codec、音轨剥离策略 |
| `captions` | 结构化 cue 渲染 | language、phrase/sentence timing |
| `word_highlight` | 基于 word timing 的高亮 | highlight states |
| `camera_motion` | 受控 pan/zoom/hold | 支持的 motion names |
| `vector_overlays` | 矢量图形/图表 | format/feature subset |
| `audio_playback` | 把既有 final mix 同步到输出 | codec/sample rate |
| `audio_mixing` | 从 stems 生成 mix | 非核心要求；仅显式声明的兼容实现 |
| `waveform` | 从 final mix 或显式 stem 生成视觉波形 | source roles |
| `transitions` | 片段间转场 | transition IDs |
| `preview` | 支持 preview 模式 | 可接受的 Profile policy |
| `deterministic_render` | 相同绑定输入与环境声明可复现 | determinism level |

核心 Capability 名称只描述可观察能力，不出现 FFmpeg filter、React component、Pillow
对象或某个 Remotion composition。

## 声明结构

Capability 文档独立版本化并计算 SHA-256。Request 记录：

```text
renderer.id
renderer.version
renderer.capability_document_ref
renderer.capability_document_sha256
renderer.required_capabilities[]
```

每项能力使用统一结构：

```json
{
  "supported": true,
  "version": "1.0",
  "constraints": {},
  "determinism": "deterministic"
}
```

`determinism` 允许：

- `deterministic`：输入、版本和声明环境一致时应产生相同媒体语义；
- `seeded`：还必须绑定 seed；
- `best_effort`：只允许明确批准的 preview，不能成为 final 默认。

## 协商算法

1. Orchestrator 从 Timeline、Caption、Audio 和 OutputSpec 推导 required capabilities。
2. 验证 Capability 文档 ID、版本和 Hash。
3. 对每项能力验证 `supported` 与 constraints。
4. 能力充足：把 required capabilities 固化到 Request。
5. 能力不足：默认生成 `blocked` Result，错误码
   `RENDER_CAPABILITY_UNSUPPORTED`。
6. 若工作流提出降级，必须先生成具名 `degradation_plan`，列明丢失的能力、替代行为、
   影响范围和 Approval event ID；然后创建新的 Request。
7. Renderer 只能执行 Request 中已经批准的计划，不能在运行中发明新计划。

## 受控扩展

Renderer-specific 配置只允许出现在顶层 `extensions`：

- key 使用 reverse-DNS 风格命名空间，例如 `org.book-video-factory.legacy-v4`；
- value 必须是对象并包含自己的 `schema_version`；
- Capability 文档必须声明支持该命名空间及版本；
- 未知、版本不兼容或未声明的扩展 fail-closed；
- 扩展内容进入 Request Hash；
- 扩展不能覆盖核心字段的语义，也不能携带凭据、绝对路径或临时目录。

迁移期旧 V4 的 stems 混音参数可以进入受控 legacy namespace，但不得扩散到核心
`audio` Schema。目标实现仍以预混 final mix 为权威输入。
