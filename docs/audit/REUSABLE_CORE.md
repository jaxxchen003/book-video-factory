# Reusable Core

稳定程度是本次审计基于耦合和测试保护作出的工程评估，不是上游维护者的版本承诺。

| 文件/模块 | 核心职责 | 稳定程度 | 测试覆盖 | 是否保留 | 后续风险 |
|---|---|---|---|---|---|
| `src/.../contracts.py` | Release Profile 结构、Renderer/画布/音视频合同 fail-closed 校验 | 高 | `test_workflow_contracts.py` | 保留 | Renderer 枚举当前写死两个值；新增 Adapter 需扩展合同而非绕过验证。 |
| `src/.../style_profiles.py` | Style → Release Profile / generation lane 映射与项目一致性 | 高 | bootstrap、factory、workflow tests | 保留 | Skill bootstrap 另有独立实现，存在逻辑漂移。 |
| `src/.../manifests.py` | SHA-256 artifact、不可变 Stage Manifest、审批事件 | 高 | `test_workflow_contracts.py`、`test_content_bridge.py` | 保留 | Renderer 目前不统一使用 Stage Manifest；需在编排层补契约，不能改写旧 Manifest。 |
| `src/.../gates.py` | 当前审批、Release 隔离、资产/QC/发布状态派生 | 高 | workflow/content bridge tests | 保留 | 内含原 V4 与 VOX 分支资产规则；新增 Renderer 必须保持 release-scoped 语义。 |
| `src/.../content_bridge.py` | 内容包导出/校验/不可变导入/激活/Traceability | 高 | `test_content_bridge.py` 广泛覆盖 | 保留 | 当前场景追溯明确绑定 V4 Scene Contract，不能直接复用于可变 Remotion Scene。 |
| `src/.../project.py` | 标准项目目录、`project.json`、reference FFprobe | 中高 | `test_factory.py` | 保留并统一入口 | 与 `bootstrap_workspace.py::create_project()` 重复；统一时需保持 clean-bootstrap 行为。 |
| `src/.../typography.py` | 标题像素测量、语义两行换行、字号收缩 | 中 | `test_typography.py`，但当前字体缺失导致 Error | 保留 | 算法是否全绿暂时无法验证；先解决字体契约再重构。 |
| `src/.../audio.py` | ASR 时间戳 splice 的纯函数 | 高 | `test_factory.py` | 保留 | V4 Renderer 自己实现了相似 splice，没有复用该函数，存在漂移。 |
| `src/.../voice.py` | Voice profile 路径解析与 VoxCPM request 构造 | 中高 | `test_factory.py` | 保留 | 具体配置仍绑定模型路径、MPS 与示例 reference。 |
| `src/.../scene_contract.py` | V4 12 场景到 V01–V15 的固定映射 | 高（对 V4） | renderer/content bridge tests | 保留为 V4 专属合同 | 不是通用场景抽象；不要把 12/15 强加给 VOX/Remotion。 |
| `src/.../weread.py` | WeRead client、匹配、标准化 Source Pack | 中 | `test_factory.py` 使用 fake client/数据 | 保留但修平台边界 | 无统一 Provider 接口；Windows 无环境变量时 `os.uname()` 崩溃；没有在线集成测试。 |
| `src/.../freesound.py` | Freesound client、许可过滤、候选 Manifest | 中 | `test_factory.py` policy/normalization | 保留候选层 | Windows credential fallback 同样使用 `os.uname()`；只应是候选检索，不是生产 BGM Provider。 |
| `schemas/*.schema.json` | Release、Stage、Approval、内容与 Traceability 数据合同 | 高 | Schema JSON 与对象测试 | 保留 | 部分 Schema 允许额外字段；Renderer Request/Result 还不存在。 |
| `scripts/workflow.py` | Core 的 CLI 门面 | 中高 | 间接覆盖底层 Core | 保留 | 没有编排 Renderer；错误码和 release-id 可选/必选边界需保持明确。 |
| `scripts/build_batch_video_v3.py::build_title_layer()` | 从 Profile 驱动标题安全区并输出 layout manifest | 中 | renderer contract + typography（受字体阻塞） | 迁入通用视觉层 | 当前函数位于具体 Renderer，并借用 V2 font loader。 |
| `build_final_video_v2.py` 的 FFmpeg helper | 静帧、montage、concat、overlay、audio mix、probe/loudness | 中低 | 只有 Scene Contract 直接测试；无 FFmpeg E2E | 有选择地抽取 | 文件同时含《兜底》专属逻辑；直接整体保留会继续污染通用层。 |

## 应保留的边界

```text
Project / StyleProfile / ReleaseProfile
  → Immutable Manifest / Hash-bound Approval
  → Derived Gate
  → Renderer Contract（待新增）
  → QC evidence
```

最有价值的核心不是现有视频模板，而是 Profile、Manifest、Approval、Gate 和内容追溯的 fail-closed 语义。后续 Renderer 抽象应适配这些合同，不能用 Renderer 自己写 `project.json.status` 代替。

## 不应误判为通用核心的内容

- V4 的 15 行、12 场景和 `V01–V15` 映射只对 `book-v4-bilingual-3x4` 合法。
- `build_final_video_v2.py` 的函数可复用，但文件整体不是 Reusable Core。
- `external_clip_timeline_v1` 是合同值，不是已实现的 Core Renderer。
- Showcase Manifest 是证据样例，不是执行引擎。

