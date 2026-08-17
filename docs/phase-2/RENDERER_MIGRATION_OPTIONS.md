# Renderer 迁移方案比较

## 方案

| 维度 | 1. 完全替换 V4 | 2. 新契约包装旧 FFmpeg 链 | 3. 新旧 Renderer 并行 | 4. 只抽契约后直接实现新 Renderer |
|---|---|---|---|---|
| 侵入程度 | 最高 | 低；旧函数不改，以 facade 固化输入/收集结果 | 中高；需要双路编排、比对和维护 | 高；新实现与契约同时落地 |
| 回归风险 | 最高；音频、字幕、视觉一起变化 | 最低；输出行为先保持 | 中；并行可比较但分支逻辑复杂 | 高；当前无媒体 E2E 基线 |
| Legacy 依赖 | 一次切断，V2/V5 易受影响 | 明确保留，逐步缩小依赖 | 长期保留两套 | 旧链作为旁路但容易失去维护 |
| 测试成本 | 大量 golden/media tests 前置 | 先做 mapper/validator/结果收集与 characterization | 双路像素/音频对比成本高 | 新 Renderer tests + 旧链回归同时需要 |
| 回滚 | 困难 | 最清晰：直接调用原 CLI | 可切换，但状态/产物容易混淆 | 可以回旧 CLI，但新路径投入较大 |
| Audio 边界 | 可重做但风险大 | 先用受控 legacy 扩展；后续拆 Finalizer | 两套混音可能漂移 | 可遵守 final mix，但需先建设 Audio Finalizer |
| 未来 Renderer 接入 | 表面最快，基础不稳 | 契约先稳定，再接入 | 可以试验但早期复杂 | 快，但容易为首个新实现过拟合 |

## 唯一推荐

推荐 **方案 2：新契约包装旧 FFmpeg 链**。

推荐对象是当前真实 V4 主链，而不是整个 `build_final_video_v2.py` 文件：

```text
V4 sources + approvals
  → deterministic V4-to-Request mapper
  → Request validation/capability negotiation
  → LegacyV4Renderer facade
  → unchanged build_batch_video_v3.py --release-version v4
  → collect output/probe as RenderResult
  → Stage Manifest + Post-QC
```

Phase 2 只设计，不实现 facade。

## 为什么不是其他方案

- 方案 1 同时改变最缺测试的视觉、字幕、音频和 QC，无法区分架构进步与媒体回归。
- 方案 3 在尚无稳定 Request/Result 时并行，会复制隐式路径和 Gate 缺口；并行比较适合
  契约落地后的实验阶段，不是第一迁移步。
- 方案 4 会让第一个新 Renderer 反向塑造核心合同，并跳过已投入使用的 V4 行为基线。

## 旧 V4 保留与回滚

1. 不删除、不移动、不改名 V1/V2/V3/V4/V5 文件。
2. 原命令保持可运行：

```text
python3 book_video_factory/scripts/build_batch_video_v3.py <project> --release-version v4
python3 book_video_factory/scripts/v4_post_qc.py --project <project> --release-id <id>
```

3. 新路径写入 request/attempt-scoped 目录，不覆盖旧 `v4` 交付。
4. Facade 必须支持 dry validation；真正执行前持久化 Request。
5. 失败时写 terminal Result，不修改已批准输入或伪造成功 Stage Manifest。
6. 回滚只切换 Orchestrator 入口，不回滚 Manifest/Approval 历史。
7. 直到 characterization、V4 mapping、Result/Stage/QC tests 全绿，旧 CLI 才能被标记为
   compatibility-only；本轮不标记 deprecated。

## 受控技术债

包装阶段允许 `org.book-video-factory.legacy-v4` 扩展表达当前固定 pause、montage、stems
混音和输出名。所有字段进入 Request Hash、由 Capability 声明，并有移除条件：

- Audio Finalizer 独立并通过等价测试；
- V4 常量迁入 Profile/Release/Timeline；
- Post-QC 不再重复字面量；
- 新旧路径对同一 fixture 的时长、stream、Caption timing 和音频指标等价。

该扩展不是给未来 Renderer 继承的核心 API。
