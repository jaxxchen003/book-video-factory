# Runtime Entrypoints

## 入口清单

| 入口 | 文件 | 函数/类 | 调用方式 | 状态 | 说明 |
|---|---|---|---|---|---|
| 官方首次安装 | `skills/book-video-factory/scripts/bootstrap_workspace.py` | `bootstrap_workspace()`, `create_project()`, `main()` | `python3 <SKILL_ROOT>/scripts/bootstrap_workspace.py --workspace ...` | Implemented | `SKILL.md` 的首选入口；复制 bundled Runtime 并创建 warehouse，可同时创建项目。 |
| Runtime 项目初始化 | `runtime/.../scripts/init_project.py` | `main()` → `project.initialize_project()` | `python3 book_video_factory/scripts/init_project.py ...` | Implemented | 复制后工作区内的直接 CLI。 |
| Python 包初始化 | `src/book_video_factory/project.py` | `initialize_project()` | Python import | Implemented | Runtime 测试直接调用；与 bootstrap 中的 `create_project()` 有重复逻辑。 |
| Research | `scripts/collect_weread.py` | `main()` → `collect_book_source_pack()` | CLI | Implemented | 会调用外部 WeRead Gateway；本轮未调用。 |
| 内容系统桥 | `scripts/content_bridge.py` | 多子命令 | CLI | Implemented | export/validate/import/traceability/status；原风格 content-system-backed。 |
| Manifest / Approval / Gate | `scripts/workflow.py` | `main()` | `evaluate`, `approve`, `manifest-stage` | Implemented | Release ID 由调用方传入；没有单独 `create release` 入口。 |
| V4 批量编排 | `scripts/render_ready_v4.py` | `ready()`, `main()` | `--warehouse`, `--slug`, `--release-id` | Implemented | 当前原风格最接近“一键生产”的编排入口。子进程硬编码 `python3`。 |
| 当前原风格 Renderer | `scripts/build_batch_video_v3.py` | `main()` | `<project> --release-version v4` | Implemented / current | Release Profile `book-v4-bilingual-3x4` 指向它；内部强依赖 V2。 |
| V4 Post-QC | `scripts/v4_post_qc.py` | `probe()`, `main()` | `--project [--release-id]` | Implemented | FFprobe + 资产/权利 Hold 报告；无直接测试。 |
| 工作流最终 Gate | `scripts/workflow.py` + `gates.py` | `evaluate_workflow_state()` | `workflow.py evaluate ...` | Implemented | 由 Manifest、审批和 QC 证据派生 `ready_to_publish`。 |
| V1 Renderer | `scripts/build_final_video.py` | `main()` | `<project>` | Legacy / Showcase | 固定《兜底》、晴山、macOS 字体和输出名。 |
| V2 Renderer | `scripts/build_final_video_v2.py` | `main()` | `<project>` | Legacy Generic + Showcase | 仍被 V3/V4 作为函数库直接调用，不能简单视为停用。 |
| V5.x 合成器 | `scripts/compose_v5_from_chatcut_bgm.py` | `compose()`, `main()` | `--warehouse ...` | Implemented compositor | 从已有 V4 silent base/Manifest 恢复图层并替换 ChatCut BGM；不是独立视觉 Renderer。 |
| VOX Renderer contract | Profile/Schema 中的 `external_clip_timeline_v1` | 无 | 无本地 CLI | Orchestration Only | Gate 可验证外部导入资产，但仓库内无执行器。 |
| TTS | `scripts/generate_narration.py` | `main()` | `--profile --script --output` | Implemented, environment-bound | 本地 VoxCPM2；模型目录与 `mps` 配置不适合当前 Windows 默认环境。 |
| ASR | `scripts/transcribe_narration.py` | `main()` | `--audio --out` | Partially Implemented | 调外部 `whisper` CLI，输出字级 JSON。 |
| BGM candidate | `scripts/freesound_music.py` | `main()` | `--project --intent` | Implemented candidate search | 只检索/记录候选，不下载；默认不得用于商业发布。 |

`pyproject.toml` 没有定义 `[project.scripts]`，因此没有已安装后的 console-script 入口；当前全部依赖脚本路径调用。

## 重点结论

### 官方推荐入口

官方工作区入口是 `skills/book-video-factory/scripts/bootstrap_workspace.py`。它把 `runtime/book_video_factory/` 复制为用户工作区中的 `book_video_factory/`，再创建本地 `book_video_warehouse/`。

### 测试实际调用入口

- `skills/.../tests/test_bootstrap.py` 直接加载并调用 bootstrap 脚本函数，也通过薄包装执行 Doctor。
- Runtime 测试把 `src/` 加入 import path，直接调用 `initialize_project()`、Profile、Manifest、Gate、内容桥、WeRead/Freesound normalization、Voice 和 Typography。
- `test_renderer_contract.py` 直接 import `build_final_video_v2`，而不是测试 `build_batch_video_v3.main()`。

### Showcase 使用入口

README 快速开始仍展示 V1/V2 的《兜底》命令。`seed_v4_batch.py`、`build_sfx_auditions.py` 和 V5 ChatCut 合成器是明显的批次/案例生产入口，不应作为通用 API。

### 是否存在多个并行 Runtime

没有两个独立 Python 包，但存在两套项目初始化实现：Skill 层 `bootstrap_workspace.py::create_project()` 与 Runtime 包 `project.initialize_project()`。两者维护相近但并非同一份逻辑，是漂移风险。

渲染侧同时保留 V1、V2、V3/V4 和 V5 合成器；VOX 另有仅合同存在的外部路径。因此“一个 Runtime、多个并行执行入口”比“多个独立 Runtime”更准确。

### 后续改造基准

后续 Renderer 抽象应以：

```text
render_ready_v4.py
  → build_batch_video_v3.py --release-version v4
  → build_final_video_v2.py 的通用函数
  → v4_post_qc.py
  → workflow.py evaluate
```

作为现状基准，同时保留 `contracts.py`、`manifests.py`、`gates.py` 与 Release Profile 合同。不能以 README 中的 V1/V2 示例命令作为新架构基准。

