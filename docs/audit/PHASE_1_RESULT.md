# Phase 1 执行结果

## 基本信息

- 仓库：`jaxxchen003/book-video-factory`
- 本地路径：`E:\AI\BookVideoFactory`
- 基线 SHA：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 当前 HEAD：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 当前分支：`main`
- origin：`https://github.com:443/jaxxchen003/book-video-factory.git`
- upstream：`https://github.com:443/jaxxchen003/book-video-factory.git`
- 是否浅克隆：是（`true`，可见提交数 1）
- 生产代码修改：否
- 测试/Profile/示例修改：否
- 付费或外部 API 调用：否
- 真实视频生成：否

## 仓库卫生

- Fork：未建立，`BLOCKED_FORK_SETUP`；GitHub CLI 未登录，未猜测用户名。
- 远程配置：未达到理想状态；`origin` 与 `upstream` 仍都指向原作者仓库。
- 历史补全：未完成，`BLOCKED_HISTORY_FETCH`；fetch 在 Git 执行前被 Codex 审批器内部参数错误拒绝，不能归因于代理或 GitHub。
- 工作区状态：`docs/` 未跟踪；本轮只新增 `docs/audit/*.md`，没有生产源码变更。
- Git 警告：无权读取 `C:\Users\SSS\.config\git\ignore`。

## 核心发现

1. 当前原风格真实主链是 `render_ready_v4.py → build_batch_video_v3.py --release-version v4 → build_final_video_v2.py helpers → v4_post_qc.py`。V3 文件名与 V2 分开，但实现仍直接强耦合 V2。
2. `src/book_video_factory/` 中的 Profile、Manifest、Approval、Gate、Content Bridge 是最可复用的核心；`project.json.status` 只是兼容缓存，不能替代 Release-scoped Gate。
3. VOX 的 `external_clip_timeline_v1`、Gemini API lane 和 Google Flow 在仓库内分别属于合同/编排/文档或人工步骤；没有可执行的本地 VOX Renderer，也没有 Gemini SDK 调用器。
4. V1/V2 明确绑定《兜底》；V4 虽可换书，仍硬编码 15 行、12 场景、voice/ASR/H2 文件名、停顿与 montage，并把画布/音频参数与 Profile 重复维护。
5. 现有测试强保护 Manifest/Gate/Release/内容桥，但不保护端到端 FFmpeg、`render_ready_v4`、`render_variant` 音频 graph 或 `v4_post_qc`；基线仍有 Windows Doctor Failure 和缺字体导致的 7 个 Error。

## 主 Runtime 入口

- 文件：官方安装入口为 `skills/book-video-factory/scripts/bootstrap_workspace.py`；原风格生产编排为复制后 Runtime 的 `scripts/render_ready_v4.py`。
- 函数/类：`bootstrap_workspace()/create_project()`；渲染侧 `ready()/main()`。
- 调用方式：先 bootstrap 创建 `book_video_factory/` 与 `book_video_warehouse/`，资产完成后执行 `render_ready_v4.py --warehouse ... [--release-id ...]`。
- 证据：`SKILL.md` First use、Style Profile `deterministic_local_renderer`、Release Profile `renderer: build_batch_video_v3` 以及脚本实际 subprocess 调用一致。

## 当前 Renderer

- Renderer 数量：3 个独立视觉 Renderer（V1、V2、V3/V4）+ 1 个 V5 release compositor；VOX contract 不计为实现。
- 主 Renderer：`build_batch_video_v3.py --release-version v4`。
- FFmpeg 入口：V4 pause splice 在 V3；视觉 base、overlay、音频 mix 与媒体指标主要在 `build_final_video_v2.py`。
- Pillow 入口：V3 的真实封面、Topic Cards、标题；V2 helper 的字幕/品牌与底层字体加载。
- QC 入口：Renderer smoke QC + `v4_post_qc.py` + `workflow.py evaluate`/`gates.py`。

## Reusable Core

- `contracts.py` / `style_profiles.py`：Style 与 Release Profile 合同。
- `manifests.py` / `gates.py`：不可变 artifact、哈希审批与 Release 隔离状态。
- `content_bridge.py`：内容资产快照、导入、Traceability 与 Gate。
- `project.py`：通用项目合同，但与 Skill bootstrap 存在重复实现。
- `typography.py`, `audio.py`, `voice.py`：可抽取媒体纯逻辑，其中 Typography 当前受缺字体阻塞。

## Legacy / Showcase

- V1 完全是《兜底》Showcase，不应成为后续基准。
- V2 的 main 绑定《兜底》，但其 helper 仍被当前 V4 生产调用，不能删除。
- `seed_v4_batch.py`、`build_sfx_auditions.py`、Voice 配置和 V5 ChatCut 合成器带明确批次/示例语义，应保留但隔离。
- `examples/` 是 Showcase 证据，不是 Provider 或 Renderer 实现。

## 高风险硬编码

- macOS 字体绝对路径、缺失的 SmileySans fallback、VoxCPM Unix 路径与 `mps` device。
- 《兜底》/晴山、具体封面/BGM、`doudi-*` 输出名和 Voice reference。
- V4 的锁定 voice/ASR/H2 路径、1.040 秒停顿、0.96 秒 montage、15 行/12 场景/8 卡。
- 720×960/30 FPS 与编码/QC目标在 Profile、Style、Renderer、Post-QC 多处重复。
- `render_ready_v4.py` 硬编码 `python3`，Windows 非交互可靠性未验证。

## Provider 现状

- 已实现：WeRead client、Freesound 候选检索、本地 VoxCPM TTS、本地 procedural BGM、Whisper CLI 调用、V4 Renderer、FFmpeg Audio Mix、QC/Gate。
- 部分实现：ASR 依赖未配置的外部 CLI；Freesound 不下载且默认仅非商业试听；WeRead/Freesound Windows credential fallback 有平台问题。
- 编排占位：Gemini API lane、`external_clip_timeline_v1`。
- 人工步骤：Codex Image、Google Flow、外部 clips、权利/审美/发布审批、ChatCut BGM。
- 结论：没有统一 Provider Adapter；当前主要是具体脚本、配置和文档的松散组合。

## Remotion 插入建议

- 推荐方案：目标架构为 B；Phase 2 首步采用 C。
- 最小插入点：以 `v2.render_base_video()` 当前产出的 silent base 为 Adapter 边界，让 Remotion 先只替换背景视觉 base，再继续使用现有 PNG overlay、FFmpeg audio 与 QC。
- 原因：这是当前唯一清晰的中间视频边界；完全视觉接管前必须先把 `render_variant()` 的 overlay 与 audio finalizer 拆开并测试。
- 风险：仓库无 Remotion 工程/测试；Node 可用不等于 Windows Remotion 已兼容；字体、帧时长、最后一帧、CFR 和颜色/像素差异都没有 golden baseline。

## Phase 2 前置条件

- [ ] Windows Doctor 与同类 Provider 平台判断修复或批准豁免
- [ ] 字体资源/配置/许可策略确定
- [ ] 56 项测试恢复全绿或有逐项批准豁免
- [ ] Renderer characterization tests
- [ ] Renderer Request/Result 契约
- [ ] Manifest/Timeline/Font/Audio artifact 字段确认
- [ ] V4 Post-QC 合同测试
- [ ] Legacy/Showcase 隔离 ADR
- [ ] 个人 Fork 可推送
- [ ] 基线 Commit 与修复 Commit 独立可对比

## 是否通过 Phase 1

结论：**Phase 1 只读审计通过，带仓库卫生阻塞；Phase 2 准入不通过。**

理由：Stage 1A 的 Fork 与历史阻塞已按指令明确记录；Stage 1B 已找到真实主入口、生产调用链、Reusable/Showcase 边界、Provider 状态、FFmpeg/Pillow/QC 位置、测试缺口和 Remotion 插入点；全部 14 份规定报告已生成，未修改生产代码或调用外部 API。未就绪项被明确列为阻塞或 `Unknown`，没有伪装成已实现能力。

## 下一轮建议

只启动 **Phase 1.5 基线可开发化**：建立个人 Fork 后，在独立修复分支仅处理 Windows 平台判断与字体资源/配置合同，以 56 项测试全绿为验收；该轮不接 Remotion、不重构 Renderer。

## 报告列表

1. `REPOSITORY_PRECHECK.md`
2. `REPOSITORY_HYGIENE_RESULT.md`
3. `ARCHITECTURE_MAP.md`
4. `RUNTIME_ENTRYPOINTS.md`
5. `PRODUCTION_CALL_CHAIN.md`
6. `REUSABLE_CORE.md`
7. `LEGACY_AND_SHOWCASE_CODE.md`
8. `HARDCODED_PATHS_AND_VALUES.md`
9. `PROVIDER_MAP.md`
10. `RENDERING_PIPELINE_MAP.md`
11. `TEST_COVERAGE_MAP.md`
12. `REMOTION_INSERTION_POINTS.md`
13. `PHASE_2_PREREQUISITES.md`
14. `PHASE_1_RESULT.md`

