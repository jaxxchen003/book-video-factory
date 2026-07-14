# 内容资产系统桥接

`book-video-factory` 支持两种模式：

- `single-book`：从一本书的资料包直接生产单条视频。
- `content-system-backed`：消费 `dbs-content-system` 已审计、已拆分、已装配的内容资产快照。

桥接是单向的：上游负责来源审计、内容单元抽取、主题地图、关系、去重、`canonical` 与选题装配；视频工厂只验证并保存一个不可覆盖快照，再把脚本、Claim 和场景接到该快照。视频工厂不会回写或重新实现上游的主题推荐和去重算法。

## 桥接包对象

一个 `content_system_package` 包含四类对象：

1. `source_documents`：来自上游 `来源注册表.csv` 的来源记录，并增加原始副本 SHA-256。只保存上游相对路径，不保存可分发绝对路径。
2. `content_units`：完整保留 `QST / CON / OPI / CAS / SOL` 的 frontmatter、正文、上游相对路径和文件 SHA-256。
3. `claims`：由观点或案例字段确定性物化，例如 `OPI.core_claim` 对应 `CLM:OPI-20260714-001:core_claim`；Claim 不是上游新增本体。
4. `assembly_brief`：把上游 Markdown 装配稿结构化为目标受众、装配理由、五类调用单元、建议结构和表达骨架。

正式生产要求五类主单元均不为空、装配引用 `canonical: true` 单元，且 Claim 状态为 `reviewed` 或 `approved`。不完整草稿可以导入保存，但 `production_eligible=false`，不能通过来源闸门。

## Fail-closed 校验

导入器会拒绝：

- `SRC-*` 占位符、绝对路径或 `../` 路径；
- 重复对象 ID、孤儿 source/unit/claim 引用；
- 内容单元 ID 前缀与中文 `type` 不一致；
- 装配桶类型错配或引用非 canonical 单元；
- 未知关系类型。当前仅允许 `回应 / 解释 / 证明 / 冲突`，上游历史抽取器中的 `承接` 不会被静默改写；
- Claim 文本偏离其来源字段；
- 场景清单偏离渲染器真实的 V4 scene-line 合同；
- 追溯图漏掉脚本行、引用未知 Claim/场景，或使用未审核 Claim。

## 命令

创建内容系统模式项目：

```bash
python3 book_video_factory/scripts/init_project.py \
  --warehouse book_video_warehouse \
  --slug my-topic \
  --book-title '书名' \
  --author '作者' \
  --mode content-system-backed
```

从现有 `dbs-content-system` 根目录确定性导出 JSON 快照。这个命令只解析来源注册表、内容单元 frontmatter/正文和装配稿链接，不执行主题推荐、关系推断或去重：

```bash
python3 book_video_factory/scripts/content_bridge.py export-dbs \
  --content-root /path/to/content-system \
  --assembly /path/to/content-system/06-选题装配/topic.md \
  --output /path/to/content-package.json
```

导出器会递归带上被 `relationships.target` 引用的内容单元，计算来源副本、单元文件和装配稿 SHA-256，并从 `OPI.core_claim` 确定性物化 Claim。它不伪造上游没有的 URL、页码或获取时间。

然后验证与导入快照：

```bash
python3 book_video_factory/scripts/content_bridge.py validate-package \
  --package /path/to/content-package.json

python3 book_video_factory/scripts/content_bridge.py import-package \
  --project book_video_warehouse/projects/my-topic \
  --package /path/to/content-package.json
```

导入相同语义内容是幂等操作；同一 `package_id` 的不同内容 hash 会创建新目录，不覆盖旧快照。当前激活版本通过 append-only activation event 记录，因此可以重新导入旧 hash 完成可审计回滚。

场景生成并写入 `scene_manifest.json` 后，附加脚本—Claim—场景追溯图：

```bash
python3 book_video_factory/scripts/content_bridge.py attach-traceability \
  --project book_video_warehouse/projects/my-topic \
  --map /path/to/traceability.json

python3 book_video_factory/scripts/content_bridge.py status \
  --project book_video_warehouse/projects/my-topic \
  --require traceability
```

## 追溯链

```text
script_line_id
  -> claim_id
    -> content_unit_ids
      -> source_document_ids
  -> scene_id
    -> scene_manifest file/hash/prompt
```

`hook` 和 `reveal_cue` 可显式使用 `editorial_no_claim`，但必须写 `editorial_note`；其余脚本角色必须是 `claim_backed`。追溯图会绑定 package、脚本和场景清单 hash，任一对象变化都会使当前追溯状态失效。

附加成功只代表结构校验通过。必须由人工复核 Claim 与脚本文本的语义一致性，并把附加后的追溯图作为 `traceability` 审批 subject：

```bash
python3 book_video_factory/scripts/workflow.py approve \
  --project book_video_warehouse/projects/my-topic \
  --release-id <release-id> --gate traceability --decision approved \
  --reviewer '<reviewer>' \
  --subject 02_story_script_故事脚本/traceability/<release-id>/<attached-map>.json
```

## 审批绑定

`content-system-backed` 模式下：

- `source` 审批必须把当前 `package.json` 快照作为 subject；
- `script` 审批必须把当前 `script.v2.bilingual.json` 作为 subject；
- `traceability` 审批必须把当前附加追溯图作为 subject；
- 只有 package 合格、脚本审批有效、12 张资产就绪、traceability 有效且人工追溯审批有效时，状态才能进入 `assets_ready`。
- 使用 `workflow.py evaluate --release-id <release-id>`；不同 release 的审批、追溯与 QC 永远不能拼接。

所有 snapshot、activation event、stage manifest 和 approval event 都保留；`project.json.status` 不能推进状态机。
