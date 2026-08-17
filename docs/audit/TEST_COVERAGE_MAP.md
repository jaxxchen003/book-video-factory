# Test Coverage Map

## Phase 0 已确认结果

本轮按只读限制没有重新运行测试。以下是 `docs/baseline/BASELINE_TEST_RESULT.md` 在同一 HEAD 上记录的事实：

| 组 | 执行数 | 通过结果记录 | Failure | Error | skipped |
|---|---:|---:|---:|---:|---:|
| Skill / bootstrap | 8 | 7 | 1 | 0 | 0 |
| Runtime | 48 | 41 | 0 | 7 | 0 |
| 合计 | 56 | 48 | 1 | 7 | 0 |

7 个 Error 中有 4 个是同一测试方法的 4 个 subtest。按 unittest 原生结果记录口径保持为 48/1/7；不能把它改写为“仅 5 个测试失败”而不说明计数口径。

## 核心模块映射

| 模块 | 测试文件 | 测试内容 | 当前状态 | 能否保护后续重构 |
|---|---|---|---|---|
| Skill bootstrap | `skills/.../tests/test_bootstrap.py` | clean workspace copy、幂等项目创建、双 Style/lane、mode 冲突、slug、成本聚合 | 7 通过；Doctor 子测试 Failure | 能保护安装和初始化合同；不能保护媒体链 |
| Doctor | `test_bootstrap.py` | planning Profile 可运行 | **Failure**：Windows `os.uname()` | 当前明确阻止把 Windows Doctor 宣称为可用 |
| Project / Style | `test_factory.py`, `test_workflow_contracts.py` | 项目目录、Style/Profile 映射、冲突拒绝 | 通过 | 能保护 Profile 选择和 fail-closed 行为 |
| WeRead normalization | `test_factory.py` | 精确作者匹配、source type、fake collection 输出 | 通过 | 能保护纯逻辑；不能证明在线 API/credential 可用 |
| Voice request | `test_factory.py` | clone 必带 reference、voice design 不伪称 identity | 通过 | 能保护 request contract；不能保护 VoxCPM 推理或 Windows device |
| ASR splice | `test_factory.py` | 跨 cut word 截断与后续时间移动 | 通过 | 能保护 `audio.py`；V4 自有重复实现没有直接使用该函数 |
| Freesound policy | `test_factory.py` | license allowlist、候选标准化、非商业 Manifest | 通过 | 能保护候选/权利策略；不能证明远端 API 可用 |
| Release Profile / Schema | `test_workflow_contracts.py` | Schema JSON、V4/VOX/Profile 验证、安全区 fail-closed | 通过 | 是，新增 Renderer 必须扩展这些合同 |
| Manifest / Approval | `test_workflow_contracts.py` | 不可变、SHA、symlink、审批 stale | 通过 | 强保护，应该保持 |
| Release-scoped Gate | `test_workflow_contracts.py` | 同时戳 fail-closed、Release 隔离、QC release match、status 不可绕过 | 通过 | 强保护，应该保持 |
| Content Bridge | `test_content_bridge.py` | package validation/export/import、幂等、symlink、activation、Traceability、Gate | 通过 | 强保护现有 V4 内容合同 |
| Scene Contract | `test_renderer_contract.py`, `test_content_bridge.py` | V4 场景—行映射一致 | 通过 | 可保护 V4 行为；不是通用 Remotion 场景合同 |
| 字体 fallback | `test_renderer_contract.py` | 系统字体缺失时返回 bundled SmileySans | **Error**：OTF 不存在 | 只能证明仓库资源合同破损 |
| Typography | `test_typography.py` | 长标题安全区、语义换行、字号权衡 | **6 条 Error 记录中的其余部分，根因同为字体缺失** | 当前无法判断算法本身通过或失败 |

## Windows Doctor Failure

正式命令在 `runtime/.../scripts/doctor.py::credential_available()` 无条件访问 `os.uname()`，Windows 抛 `AttributeError`。此外源码审计确认 `weread.py::load_api_key()` 与 `freesound.py::load_secret()/credential_available()` 有同类平台判断；Provider 的无环境变量路径也有潜在 Windows 崩溃风险，现有测试没有覆盖。

## 字体导致的 7 个 Error

仓库 `resources/fonts/` 只有 `README.md` 和 `SmileySans-OFL.txt`，缺少测试和 Style 配置声明的 `SmileySans-Oblique.otf`。因此：

- 1 条 Renderer fallback Error；
- 长标题测试的 4 个 subtest Error；
- 语义换行与字号权衡各 1 条 Error。

这些 Error 在调用 Pillow 打开字体时发生，**当前结果不能证明标题排版算法失败**，也不能把它们忽略为“本机缺字体”，因为仓库声明自身应提供 fallback。

## 已有绿测试能保护什么

- Profile / Style 映射和项目初始化。
- Manifest 不可变性、SHA-256 artifact、Approval stale/revocation 语义。
- Release 隔离和派生 Gate，阻止 `project.json.status` 绕过。
- Content Bridge package 与脚本—Claim—V4 Scene Traceability。
- WeRead/Freesound 的纯数据和权利策略。
- Voice Request 与独立 ASR splice 纯函数。
- V4 Scene-Line mapping。

## Renderer 路径缺口

未发现以下自动测试：

- `render_ready_v4.py` 的资产筛选、子进程编排和 Windows `python3` 行为。
- `build_batch_video_v3.py::main()` 的端到端或最小 FFmpeg fixture。
- `build_final_video_v2.py::render_still_clip/render_montage/render_base_video/render_variant()` 的媒体输出验证。
- `filter_complex` 的音频路由、ducking、loudnorm、时长和声道测试。
- Pillow caption/brand/topic card 的像素回归测试。
- `v4_post_qc.py` 的通过/失败/Release 绑定测试。
- V4 Renderer 自动写 Stage Manifest 的测试；当前实现本来也没有该统一动作。
- `external_clip_timeline_v1` 执行测试；对应实现不存在。
- Remotion 测试；仓库没有 Remotion 工程。

## Phase 2 测试底线

在替换视觉实现前，应先锁定三类 characterization test：

1. 小型静态资产 → silent base 的分辨率、FPS、帧数/时长与最后一帧保持。
2. silent base + synthetic voice/BGM/SFX → final master 的 stream、时长、响度和音频路由。
3. RenderResult → Stage Manifest → QC → Release Gate 的 hash/release 一致性。

这些测试应使用自行生成的微型 fixture，不依赖 Showcase 视频、付费 API 或缺失字体。

