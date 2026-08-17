# Renderer Contract v1

## 1. 目标与非目标

Renderer Contract v1 是 Renderer-neutral、可持久化、可测试和可渐进迁移的执行边界。
它把“已批准、已绑定 Hash 的 Release 输入”转换为一次明确的渲染请求，并把一个执行
Attempt 的产物、Probe、错误与 QC handoff 记录为结果。

本合同不实现 Renderer，不创建 Adapter，不接入 Remotion，不修改 FFmpeg/Pillow/音频
链，也不替代现有 Profile、Stage Manifest、Approval 或 Gate。

核心 Schema 禁止出现实现内部对象，例如 filter graph、composition/component、字体
运行时对象或 subprocess command。实现专属配置只能放入受控 `extensions`。

## 2. 对象关系与真相源

```text
Project Manifest
  └── workflow → Style Profile → Release Profile

approved assets + Stage Manifests + Approval events
  └── freeze-release（仓库尚未实现）
        → immutable Release Manifest
              └── project/release/profile/assets/rights/hashes
                    → immutable RenderRequest
                          └── renderer selection + execution snapshot
                                → Render Attempt (independent attempt_id)
                                      → terminal RenderResult
                                            → Stage Manifest
                                                  → Post-QC → Gate
```

### Project Manifest

权威保存 `project_id`、书籍元数据和工作流选择。当前 `project.json.status` 只是兼容缓存，
不能批准渲染或发布。

### Style/Release Profile

- Style Profile 保存风格身份、生成渠道和 Gate policy。
- Release Profile 保存 width/height/FPS、编码目标、排版/音频政策和场景策略。
- Profile 不保存某次 Release 的具体资产路径或凭据。

### Release Manifest

Release Manifest 是未来 freeze-release 阶段的不可覆盖输入真相源，至少应保存：

```text
schema_version / manifest_id / manifest_version
project_id / release_id
project_manifest_ref + sha256
style_profile {id, revision/hash/ref}
release_profile {id, revision/hash/ref}
artifacts[] {asset_id, role, portable ref, bytes, sha256, media_type}
timeline/caption/audio manifest refs + hashes
rights refs / approval event IDs / gate snapshot hash
frozen_at / producer
```

当前仓库没有该实现或 Schema。现有 `render_manifest.v4.json` 可覆盖且混合执行结果，不能
冒充 Release Manifest。Phase 3 可以先构建显式的 V4 compatibility release snapshot，
但必须记录这是迁移产物，不能倒写旧 Manifest。

### RenderRequest

Request 是 Release Manifest 的一次不可变执行投影：它复制 Renderer 真正需要的确定值，
同时绑定来源 Manifest/Profile 的 SHA。复制值不是第二真相源；创建 Request 时必须逐项
验证一致，分歧时拒绝持久化。

### RenderResult

Result 只描述一个 Attempt。重试必须生成新 `attempt_id` 和新 Result；不得覆盖失败记录。
Renderer 成功不代表 Post-QC 或发布 Gate 通过。

## 3. 路径与 Root 模型

持久化 JSON 不保存物理绝对路径。所有文件引用使用：

```json
{"root": "project", "path": "03_images_生成图片/approved/v4/S01.png"}
```

规则：

- JSON 路径统一为 `/` 分隔的 portable relative path；
- 禁止绝对路径、drive/UNC、空 path、`.`/`..` segment、NUL 和反斜杠；
- root 必须在 Request `roots` 中声明；
- v1 允许 `project`、`runtime` 和经 Profile 允许的 `font_resources` 等逻辑 root；
- root 到本机 `Path` 的物理绑定由执行上下文注入，不序列化、不进入 Request Hash；
- symlink/reparse point 解析后必须仍位于绑定 root；
- 输入 root 只读；输出只能写 Request 授权的 project-relative target；
- 临时目录属于 Attempt execution context，不进入持久化 Request/Manifest/Hash。

## 4. RenderRequest v1

### 顶层字段

| 字段 | v1 | 说明 |
|---|---|---|
| `schema_version` | 必填 | 固定 `1.0` |
| `request_id` | 必填 | 独立 ID；不等同 request hash |
| `request_hash` | 必填 | 按第 9 节计算，不包含自身 |
| `project` | 必填 | Project ID、Manifest ref/hash |
| `release` | 必填 | Release ID、Manifest ID/version/ref/hash |
| `render_mode` | 必填 | `preview` 或 `final` |
| `renderer` | 必填 | 精确 ID/version、Capability snapshot 与 required capabilities |
| `profile` | 必填 | Release Profile ID/revision/ref/hash |
| `roots` | 必填 | 逻辑 root 声明，不含物理路径 |
| `output_spec` | 必填 | Profile 的经验证执行快照 |
| `output` | 必填 | artifact role 与允许的 portable target |
| `timeline` | 必填 | v1 Narration Segment 模型 |
| `audio` | 必填 | Audio Manifest 绑定、final mix 与可选 stems |
| `captions` | 必填 | 可为空 tracks，但结构必须存在 |
| `assets` | 必填 | 本次实际可读资产及 SHA |
| `overlays` | 必填 | 可为空；引用资产/逻辑样式，不含运行时对象 |
| `rights` | 必填 | rights snapshot/ref/hash 与执行允许状态 |
| `approvals` | 必填 | 所需/满足 Approval event IDs 与 snapshot hash |
| `determinism` | 必填 | time/frame、seed、locale、级别要求 |
| `metadata` | 可选 | created_at/created_by/notes；不影响媒体语义 |
| `extensions` | 必填 | 可为空对象；受控命名空间 |

### Project 与 Release 绑定

`project.id` 必须等于 Project Manifest 内的 `project_id`。`release.id` 必须等于 Release
Manifest 的 `release_id`。Final 模式下 Release Manifest、渲染范围内的 rights 和前置
approvals 都必须存在且允许执行；Preview 也必须有明确 release scope，不能用 `null`
混入 final 流程。依赖本次输出的 `local_master_review`/`publish` 不可能是同一 Request 的
前置 Gate，只能在 Result/Post-QC 后评估。

`release.manifest_version` 是数据格式/修订；`release.id` 是业务 Release 身份，不能互换。

### Renderer 绑定

```text
renderer.id
renderer.version                 # final 必须精确版本，不允许 floating range
renderer.capability_document_ref
renderer.capability_document_sha256
renderer.required_capabilities[]
renderer.degradation_plan        # optional, explicit and approved
```

Renderer 选择由 Orchestrator 根据 Release policy 或显式 CLI 请求作出并固化到 Request；
Renderer 不能自行改用另一个实现。

### OutputSpec

至少包含：

```text
width / height
fps {numerator, denominator}
pixel_format
container
video {codec, profile/policy}
audio {codec, sample_rate, channels}
duration_ticks
artifact_role
```

这些值来自 Release Profile。Request 保存执行快照并验证 Profile SHA/值；不是新的配置
真相源。Preview 可由同一 Profile 的具名 preview policy 派生，不能任意降规格。

### Assets

每个 asset：

```text
asset_id                  # Request 内唯一稳定 ID
role
ref {root, path}
bytes
sha256
media_type
source_manifest_artifact_id
rights_ref                # required for governed media
```

Timeline/Audio/Caption/Overlay 只通过 `asset_id` 引用文件，避免重复路径和 Hash。Request
开始和结束时都检查输入 Hash，检测到变化则失败，不登记成功输出。

### Timeline

- 使用 `ticks_per_second=1000` 和整数 tick；
- segments 连续、非重叠、覆盖 `[0, duration_ticks)`；
- visual-only pause/montage/outro 是显式 segment；
- Timeline 引用 asset/caption/overlay IDs，不让 Renderer 重新推导 15/12 合同；
- 细则见 `TIMELINE_MODEL_DECISION.md`。

### Audio

- final Request 必须引用 Audio Manifest 和 final mix asset；
- stems 可选且只用于声明用途；
- Renderer 不得重新混音 final mix；
- 当前 V4 包装的临时例外只能进入受控 legacy extension；
- 细则见 `AUDIO_BOUNDARY_DECISION.md`。

### Captions 与 Overlays

- Caption 文本绑定批准脚本，ASR 只提供 timing provenance；
- Cue/word 使用整数 tick，字体用逻辑 role + 资产 Hash；
- Overlay 是 renderer-neutral 语义，例如 title/brand/caption region；
- PNG、组件或具体排版对象只是实现派生产物，不进入核心模型。

### Rights 与 Approvals

Request 不复制 reviewer 私密信息，只绑定：

```text
policy_version
snapshot_ref + sha256
required_gate_ids[]
satisfied_event_ids[]
status: allowed | blocked
scope: preview | final
```

任一渲染前必需审批 stale、Release 不匹配或 render-scope rights blocked 时，Orchestrator
不启动 Renderer，并写 `blocked` Result。Renderer 可以再验证 snapshot，但不能查询/补写
Approval。Release policy 还应列出 post-render Gate；它们不进入本次
`required_gate_ids`，由 Result/Post-QC 之后的 Gate evaluator 处理。

## 5. RenderResult v1

### 顶层字段

| 字段 | v1 | 说明 |
|---|---|---|
| `schema_version` | 必填 | 固定 `1.0` |
| `request_id` / `request_hash` | 必填 | 精确绑定 Request |
| `attempt_id` | 必填 | 每次执行独立 |
| `status` | 必填 | pending/running/succeeded/failed/blocked/cancelled |
| `renderer` | 必填 | 实际 ID/version/capability hash，必须与 Request 相容 |
| `started_at` | 条件必填 | running/terminal；UTC |
| `finished_at` | terminal 必填 | pending/running 为空 |
| `output` | 必填 | artifact 数组；失败可为空 |
| `sidecars` | 必填 | SRT、layout、probe、provenance 等，可为空 |
| `media_probe` | 条件必填 | succeeded 必须存在，可 inline + sidecar ref |
| `warnings` | 必填 | 稳定 code + 可读 message |
| `errors` | 必填 | 错误对象；succeeded 必须为空 |
| `primary_error_code` | 条件必填 | failed/blocked/cancelled |
| `metrics` | 必填 | duration、frame count、elapsed、资源指标；不含 secrets |
| `input_hashes` | 必填 | Request/Manifest/Profile/assets 的派生核对摘要 |
| `output_hashes` | 必填 | 与 output/sidecars artifact hash 一致的派生摘要 |
| `qc_handoff` | 条件必填 | succeeded 或有可分析输出时 |
| `logs` | 必填 | 脱敏 portable refs，可为空 |
| `extensions` | 必填 | 可为空；同样受 Capability 约束 |

`output`/`sidecars` 中的 artifact 对象是输出 Hash 真相；`output_hashes` 是便于 QC 的派生
索引，二者不一致时 Result 非法。`input_hashes` 同理不能覆盖 Request 中的值。

### 状态机

```text
pending → running → succeeded
                  → failed
                  → cancelled
pending → blocked
pending → cancelled
```

pending/running 建议写 append-only Attempt event；terminal Result write-once。进程崩溃且
没有 terminal Result 时，由 Orchestrator 生成 `failed/RENDER_PROCESS_FAILED` Result，
不得把“缺结果”解释为仍在运行。

## 6. Capability 与降级

- required capabilities 从 Request 内容推导并固化。
- Capability 缺失默认 `blocked/RENDER_CAPABILITY_UNSUPPORTED`。
- Renderer 不得静默降级。
- 唯一例外是 Request 已包含具名、Approval-bound `degradation_plan`；Final 默认不允许。
- 详情见 `RENDERER_CAPABILITY_MODEL.md`。

## 7. QC 边界

Renderer 内部负责输入、Capability、Timeline、输出存在和基础 Probe；独立 Post-QC 负责
完整媒体、Caption 与业务检查；Gate 组合 Approval/rights/QC 派生状态。详见
`QC_HANDOFF_CONTRACT.md`。

## 8. 持久化与目录建议

建议路径（均为 project-relative）：

```text
07_timeline_时间线/render-requests/<release-id>/<request-id>.json
08_render_合成/attempts/<request-id>/<attempt-id>/events/*.json
08_render_合成/attempts/<request-id>/<attempt-id>/render-result.json
08_render_合成/attempts/<request-id>/<attempt-id>/logs/*
09_qc_质检/<release-id>/<attempt-id>/post-qc.json
```

Request 和 terminal Result 使用 exclusive create。输出 target 已存在时默认失败；只有
Request 明确声明且目标是本 Attempt 的可覆盖临时文件时才能替换，持久化 artifact 不允许。

## 9. Request Hash

### Canonicalization

使用 `canonical-json-v1`：

- UTF-8；
- object key 按 Unicode code point 排序；
- 无多余空白；
- `ensure_ascii=false` 的 JSON string 语义；
- 禁止 float/NaN/Infinity，时间与比例都用 integer/rational；
- SHA-256 输出小写十六进制。

### 包含

- schema version；
- Project/Release ID、Manifest ID/version/ref/hash；
- render mode；
- Renderer ID/version、Capability hash、required capabilities、批准降级；
- Profile ID/revision/ref/hash 和 OutputSpec；
- 逻辑 roots、持久化 output target；
- Timeline、Audio、Captions、Assets、Overlays；
- rights/approval snapshot hashes 与 event IDs；
- determinism；
- 所有受控 extensions。

### 排除

- `request_id`、`request_hash`；
- `metadata.created_at/created_by/notes`；
- root 的本机物理绑定；
- Attempt ID、时间戳、PID、host name；
- temp/work/cache/log directory；
- Result、Probe 和运行指标。

因此相同语义请求在 Windows/POSIX 上得到相同 Hash，临时目录变化不影响 Hash；改变
持久化输出 target、Renderer 版本、输入资产或审批快照会改变 Hash。

## 10. Determinism

Request 至少绑定：

```text
canonicalization: canonical-json-v1
timeline_rounding: integer-round-half-up-v1
random_seed: integer | null
locale: explicit
timezone: UTC
required_level: semantic | bitwise
```

当前 V4 尚无跨 OS/codec 版本的 bitwise 证据，只能暂定 `semantic`：stream spec、时长、
Timeline、Caption 和可接受媒体指标一致。Renderer 必须在 Capability 中声明实际级别；
Request 要求高于能力时 Blocked，不能伪报确定性。

## 11. 版本与扩展策略

- 核心 `schema_version` 使用 `major.minor`。
- minor 只增加可选字段/枚举的兼容成员；major 才能改变必填字段或语义。
- v1 核心默认拒绝未知顶层字段，防止拼写被忽略。
- Renderer/Capability/Profile/Release Manifest 各自独立版本，并用 Hash 固化。
- `extensions` key 使用 reverse-DNS namespace；value 必须含自己的 `schema_version`。
- Renderer 必须在 Capability 文档声明支持的 namespace/version；未知扩展 fail-closed。
- 扩展不能覆盖核心字段，不能含凭据、绝对路径、临时对象或秘密日志。

## 12. 未来 Remotion 接入点

未来若批准 Remotion 实验，它只在 `Renderer Protocol` 后成为一个 Adapter：

```text
validated RenderRequest
  → capability negotiation
  → selected Renderer Adapter
  → attempt-scoped output + RenderResult
  → common Post-QC/Gate
```

约束：

- Adapter 只消费 Request 和 runtime-only RootBindings，不直接 glob 项目目录或重新解释
  `project.json`；
- composition/component/bundler 等选择只属于该 Adapter 的受控 extension 和 Capability，
  不增加核心字段；
- 使用同一 Timeline、Caption、final mix、asset Hash、Attempt/Result 和 QC handoff；
- 不在 Adapter 内查询 Provider、Approval 或发布状态；
- 不得因实现方便把 audio mixing 重新变成核心职责；
- 初期若只产出 `silent_visual_master`，它必须作为显式 compatibility sidecar/Capability，
  再由已验证 Finalizer 装配，不能伪报完整 `local_master`；
- 旧 V4 facade 与未来 Adapter 通过相同协议选择，回滚只改变 Orchestrator 选择，不改
  Release/Approval 历史。

本节只定义插槽；Phase 2 未创建工程、依赖、组件或 Renderer 实现。

## 13. Python 接口草案（仅文档）

```python
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Mapping, Protocol


@dataclass(frozen=True)
class PortableRef:
    root: str
    path: PurePosixPath


@dataclass(frozen=True)
class ArtifactBinding:
    asset_id: str
    role: str
    ref: PortableRef
    bytes: int
    sha256: str
    media_type: str


@dataclass(frozen=True)
class RendererIdentity:
    renderer_id: str
    renderer_version: str
    capability_sha256: str


@dataclass(frozen=True)
class RenderRequest:
    schema_version: Literal["1.0"]
    request_id: str
    request_hash: str
    project_id: str
    release_id: str
    release_manifest_version: str
    render_mode: Literal["preview", "final"]
    renderer: RendererIdentity
    profile_id: str
    profile_revision: int
    output_spec: Mapping[str, Any]
    timeline: Mapping[str, Any]
    audio: Mapping[str, Any]
    captions: Mapping[str, Any]
    assets: tuple[ArtifactBinding, ...]
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class RenderIssue:
    code: str
    message: str
    stage: str


@dataclass(frozen=True)
class RenderResult:
    schema_version: Literal["1.0"]
    request_id: str
    request_hash: str
    attempt_id: str
    status: Literal[
        "pending", "running", "succeeded", "failed", "blocked", "cancelled"
    ]
    renderer: RendererIdentity
    outputs: tuple[ArtifactBinding, ...]
    report_ref: PortableRef
    primary_error_code: str | None = None


@dataclass(frozen=True)
class RenderExecutionContext:
    # Runtime-only: never serialized or hashed.
    root_bindings: Mapping[str, Path]
    work_dir: Path
    attempt_id: str


class Renderer(Protocol):
    def capabilities(self) -> Mapping[str, Any]: ...
    def validate(
        self, request: RenderRequest, context: RenderExecutionContext
    ) -> tuple[RenderIssue, ...]: ...
    def render(
        self, request: RenderRequest, context: RenderExecutionContext
    ) -> RenderResult: ...
```

相较指令中的最小草案，持久化 Request 不直接保存 `Path`；物理路径只存在于
`RenderExecutionContext`。Result 支持多个 output，并显式绑定 request hash 与 Renderer
实际版本。

## 14. 必须决策登记

| # | 问题 | v1 决策 |
|---:|---|---|
| 1 | Request 是否独立持久化 | 是，write-once，并有独立 request_id/hash |
| 2 | Request 与 Release Manifest | Request 是 Manifest 的验证投影，Manifest 才是资产真相源 |
| 3 | Renderer 是否只消费最终混音 | 是；必需 final mix + 可选只读 stems；旧 V4 有受控临时例外 |
| 4 | Timeline | Narration Segment 驱动，显式 visual-only segment |
| 5 | Caption 时间位置 | versioned Caption Track；Request 固化本次 cues/来源 hash |
| 6 | Preview/Final | 共用 Schema，用 `render_mode` 与 Profile policy 区分 |
| 7 | Capability 不足 | 默认 Blocked；只有显式 Approval-bound degradation 可执行 |
| 8 | QC | Renderer 内部基础检查；Post-QC 和 Gate 在外部 |
| 9 | 旧 V4 | 包装保留，不废弃，不修改本轮生产逻辑 |
| 10 | Renderer-specific 配置 | 仅 `extensions` reverse-DNS namespace，Capability 显式声明 |
| 11 | Request Hash | 包含所有媒体语义、输入/版本/审批/输出目标；排除运行元数据和临时目录 |
| 12 | Render Attempt | 每次独立 attempt_id，重试不覆盖 |

## 15. 暂时无法验证

- Release Manifest/freeze-release 尚未实现；精确 Schema 与既有 delivery manifest 的合并
  方式需要 Phase 3 代码实验。
- 当前 V4 是否能跨 Windows/POSIX 产生 bitwise 相同 H.264 尚无证据；v1 不作此承诺。
- 新视觉 Renderer 的具体 Capability constraints 需要未来独立 spike；本轮不安装依赖。
- 字幕像素/音频等价阈值缺少维护者批准的 golden media，需要 Phase 3 fixture 实验。
