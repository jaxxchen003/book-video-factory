# 稳定生产工作流

## 入口

在 Codex 中使用全局 `$book-video-factory` Skill。Skill 只负责判断、审批与异常处理；确定性步骤只调用本目录脚本。

## 双风格版本化链路

```text
原风格：topic -> source -> script -> 12 stills -> voice/timing -> render -> QC -> publish
VOX风格：topic -> source audit -> script/voice/timing -> metaphor -> frames -> clips -> picture lock -> audio -> QC -> publish
```

每个箭头都必须产生 manifest 或 `run_cost` 事件。任何修改均创建新 release，不覆盖已有交付。

当前支持两种入口模式：

- `single-book`：从一本已批准图书启动单项目生产。
- `content-system-backed`：接收上游内容系统生成的 `assembly_brief` 与内容单元 ID；上游仍负责来源、主题、关系和去重。

这里的入口模式与视觉风格是两个维度。原风格支持两种入口；VOX 风格当前只支持 `single-book`，因为内置 content-system traceability 仍绑定 V4 scene-line contract。

状态不是人工写入的字符串，而是由 `workflow.py evaluate` 重新计算：

```text
draft → topic_approved → source_audited → script_reviewed
→ assets_ready → timeline_verified → qc_passed → ready_to_publish
```

音乐供应也遵循同一原则：先以 `music brief` 检索候选并保存许可清单，再经人工听感与来源授权门确认后，才可下载/冻结为成片 BGM。Freesound 免费 API 候选只允许进入非商业试听门，不能越过公开发布门。

## 原风格 V4 不变量

- 真实书封及来源记录。
- 每项目 12 张独立 `approved/v4/S01..S12.png`；字节重复直接失败。
- 每项目 1 个独立生成 BGM。
- 用户确认的 H2 片头层记录路径及 SHA-256。
- 本地 QC pass 后才能进入 ChatCut。
- 标题必须通过 `book-v4-bilingual-3x4` profile 的 56px 左右安全边距检查；最多两行，溢出直接失败。

## VOX 风格不变量

- 项目必须记录 `paper-collage-explainer-v1` 和显式 `gemini-api` / `google-flow` lane。
- 旁白和真实 ASR 时间先锁定；每次信息变化对应一个 4–8 秒 visual beat。
- `gate_1_metaphor`、`gate_2_still`、`gate_3_clip_qa` 分开审批，片段由 manifest 定义数量并逐项校验 hash。
- 生成片段进入本地时间线前必须静音；按不变速原则规范化为 720×1280、30fps H.264。
- `bgm_rights` 与 `bgm_review` 分开；通过版权检查不等于通过人耳创意审听。
- `local_master_review` 与 `publish` 分开；公共仓库案例另需 hash-bound `showcase_publish`。

## Manifest 与审批

检查当前派生状态：

```bash
python3 book_video_factory/scripts/workflow.py evaluate \
  --project book_video_warehouse/projects/<slug> \
  --release-id <release-id>
```

记录人工审批时必须绑定当前文件 hash：

```bash
python3 book_video_factory/scripts/workflow.py approve \
  --project book_video_warehouse/projects/<slug> \
  --release-id <release-id> --gate script --decision approved \
  --reviewer '<reviewer>' \
  --subject 02_story_script_故事脚本/script.v2.bilingual.json
```

审批后如果文件发生变化，审批自动失效。状态评估只使用指定 release 的审批；QC 也必须记录相同 `release_id`。阶段 manifest 使用 `manifest-stage` 创建，已存在的 manifest 拒绝覆盖。

## 成本记录

先回填已有项目：

```bash
python3 book_video_factory/scripts/run_cost.py --warehouse book_video_warehouse backfill
```

新增运行时，在每个有外部/模型用量的阶段记录已知值：

```bash
python3 book_video_factory/scripts/run_cost.py --warehouse book_video_warehouse record \
  --project <slug> --stage script.generate --codex-model <model> \
  --input-tokens <n> --cached-input-tokens <n> --output-tokens <n>
```

没有可获得的 token 数据时保留为空；不得用推测值填充。报告命令：

```bash
python3 book_video_factory/scripts/run_cost.py --warehouse book_video_warehouse report
```

报告把有 `10_delivery_交付/v4/` 成片的项目作为当前批次，给出图片、音乐、人声和成片时长的均值；历史项目不参与均值。`—` 是未获得的真实 token 数据，不是零消耗。若需精确 Codex token 成本，应在调用层把输入、缓存输入、输出 usage 原样传入 `record`，再由台账计算均值。

## ChatCut 精修

ChatCut 是已通过本地 QC 的 master 后处理与人工审阅层，不是项目真源。每次精修使用新的 style/release revision，记录 ChatCut project id、导入 asset id、修改清单、导出路径和审核人；不得覆盖原风格 `10_delivery_交付/v4/` 或 VOX 风格的任何已批准本地 master。
