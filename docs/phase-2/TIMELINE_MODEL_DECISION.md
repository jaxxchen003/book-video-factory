# Timeline 模型决策

## 比较

| 维度 | A. Track/Clip 多轨 | B. Narration Segment 驱动 |
|---|---|---|
| 当前 V4 映射 | 需要先把 15 行/12 场景拆成多条轨道，信息增益有限 | 可直接映射现有 TimedLine、Scene 和 montage |
| Caption/旁白同步 | 灵活，但需要额外定义轨间优先级和冲突 | cue 与 segment 天然关联 |
| 复杂 B-roll/叠层 | 表达力更强 | v1 受限，通过 visual/overlay 引用表达 |
| 验证难度 | 重叠、gap、z-order、mix 规则复杂 | 有序、半开区间、显式 gap，容易 fail-closed |
| Renderer-neutral | 可以，但容易泄漏编辑器内部轨道概念 | 更接近业务语义，不绑定具体实现 |
| 首版风险 | 对当前需求过度设计 | 与书籍旁白驱动视频一致 |
| 未来扩展 | 原生 | 可通过新 Schema major 或受控 track extension 增加 |

## 唯一推荐

v1 采用 **B：Narration Segment 驱动模型**。

Segment 是业务节拍，不是视频编辑器 Clip。每个 segment 包含：

```text
segment_id
start_tick / end_tick
narration {cue_ids[] | null}
visual {kind, asset_ids[], motion}
caption_cue_ids[]
overlay_ids[]
transition {in, out}
metadata {script_line_ids[], scene_ids[]}
```

无旁白的 montage、停顿和 outro 仍必须建显式 segment，`narration` 为 `null`。禁止用
时间线空洞暗示“保持上一帧”，因为不同 Renderer 可能产生不同结果。

## 时间表示

- `timeline.timebase.ticks_per_second = 1000`，所有时间为 JSON integer。
- 区间统一为半开区间 `[start_tick, end_tick)`。
- `start_tick >= 0`，`end_tick > start_tick`。
- segments 按 start 排序，不重叠，必须从 0 连续覆盖到 `duration_ticks`；gap 要显式写
  `hold` segment。
- Caption/overlay/audio cue 必须位于 Timeline 总时长内；关联 segment 时还必须在该
  segment 内。
- tick 到 frame 使用 Request 固化的整数 round-half-up 规则：

```text
frame = floor((tick * fps_numerator * 2 + ticks_per_second * fps_denominator)
              / (2 * ticks_per_second * fps_denominator))
```

相邻 segment 共用同一边界计算，避免浮点平台差异和一帧缝隙。

## v1 合法视觉类型

- `still`：一个静态 asset，可带受控 motion；
- `sequence`：有序 asset IDs，用于 V4 montage；
- `video`：一个静音或已声明音轨策略的视频 asset；
- `hold`：明确保持前一视觉，首 segment 不允许；
- `solid`：Profile 定义的纯色/透明背景语义。

这些是核心语义，不暴露 filter graph、composition 或图层对象。

## Caption 与 Overlay

- Timeline 只引用 `caption_cue_ids`，文本和字级时间保存在 Request 的 `captions` 区域。
- Timeline 只引用 `overlay_ids`；overlay 的布局/字体角色在独立结构中定义。
- Renderer 不根据脚本行数重新推导 Caption 或 Scene。

## 未来多轨扩展

v1 不预埋任意 Track。真正出现以下证据时再设计 v2/受控 extension：

- 同时存在两个独立、持续重叠的视频层；
- 多语言 Caption 需要不同时间轴；
- 交互式图表或长期独立 overlay 不能归属单一 segment；
- 多路 audio automation 必须作为 Renderer 输入。

扩展前需要同一 Request 在至少两个 Renderer 上的行为实验。不能仅为了未来 Remotion
可能需要轨道而提前污染核心模型。
