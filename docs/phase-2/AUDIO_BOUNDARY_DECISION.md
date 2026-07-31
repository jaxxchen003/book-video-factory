# Audio 边界决策

## 方案比较

| 维度 | A. Renderer 只消费最终混音 | B. Renderer 消费 stems 并自行混音 | C. 必需最终混音 + 可选 stems |
|---|---|---|---|
| 确定性 | 高；混音只有一个权威产物 | 低到中；不同 Renderer 的增益、duck、响度实现会漂移 | 高；final mix 是音频真相，stems 不改变输出音频 |
| 响度/QC | 可在渲染前后对同一 mix 检查 | 每个 Renderer 都要实现/验证响度 | final mix 统一 QC；输出 mux 后再复核 |
| 复用现有 FFmpeg 混音 | 需把现有 graph 提升为上游 Audio Finalizer | 直接保留在旧 Renderer，但持续耦合 | 目标复用为 Finalizer；迁移期可受控兼容旧路径 |
| 未来视觉 Renderer | 接口最简单 | 被迫复制音频实现 | 只需同步/播放 final mix；需要波形时读取显式 stem |
| 波形/音频响应视觉 | 只能从 final mix 分析，分离旁白较难 | stems 天然可用 | 可选 stems 提供旁白/BGM 分析，但不能用于重新混音 |
| 回滚 | 音频与视觉可独立回滚 | 回滚必须连同混音实现 | 可回滚视觉；final mix 保持不变 |
| V4 迁移成本 | 中高；当前 `render_variant()` 未拆分 | 低；但把遗留耦合固化成核心 | 中；允许明确的 legacy 兼容扩展，不污染目标合同 |

## 唯一推荐

采用 **C：必需最终混音 + 可选 stems**。

更精确地说：对符合 Renderer Contract v1 的 final Request，`audio.final_mix_asset_id`
是必需字段，也是输出音频的唯一内容真相。Renderer 可以同步、mux 或按 OutputSpec 编码
该 mix，但不得改变旁白/BGM/SFX 的相对关系、ducking、增益或节目响度。

可选 stems 只允许用于：

- 波形、频谱或音频响应型视觉；
- 调试与 QC 证据；
- 明确声明不改变最终音频的 preview 辅助能力。

Renderer 使用 stems 需要 Capability（如 `waveform`），但 final 输出音频仍来自 final mix。

## Audio Manifest 与 Request

Audio 真相首先由 Release Manifest 引用的 Audio Manifest 保存，至少包括：

```text
schema_version
audio_manifest_id
project_id / release_id
timeline_timebase
final_mix {asset_id, duration_ticks, sample_rate, channels, sha256}
stems[] {asset_id, role, start_tick, duration_ticks, sha256}  # optional
mix_policy_id / revision
measured_loudness
rights_refs[]
```

RenderRequest 不复制 filter graph。它只记录：

- final mix asset ID；
- 可选 stem asset IDs 及其允许用途；
- `start_tick`/同步政策；
- Profile 规定的目标 codec/sample rate/loudness；
- Audio Manifest 的 portable ref 和 SHA。

凭据、临时 WAV、缓存目录和 subprocess 命令不得进入 Audio Manifest 或 Request Hash。

## 同步与时长

- final mix 从 Timeline tick 0 开始。
- final mix 的声明时长必须等于 Timeline 总时长；允许误差由 Profile 以 tick/frame 表达，
  不能由 Renderer 自行决定。
- final mix 缺失、Hash 不匹配、时长越界或声道/采样率不符合 Profile 时 fail-closed，使用
  `RENDER_AUDIO_INVALID`。
- final mix 推荐使用无损中间格式；最终 AAC 等编码由 OutputSpec 决定。
- Renderer 完成 mux 后的媒体仍必须进入 Post-QC 复核响度、静音段、峰值和 A/V sync。

## 当前 V4 的迁移例外

当前 `build_final_video_v2.py::render_variant()` 同时混合 voice/BGM/SFX 与视觉 overlay，
无法在不改生产逻辑的情况下立即满足目标边界。Phase 3 的旧链包装允许使用受控扩展：

```text
extensions["org.book-video-factory.legacy-v4"]
capability: audio_mixing
compatibility_status: temporary_non_target_boundary
```

该扩展必须显式列出输入 stems、Mix Profile/参数摘要与审批证据，并进入 Request Hash；
它不能成为新 Renderer 的默认方式，也不能允许静默改写混音。Characterization tests 建立后，
再把现有 graph 提升为独立 Audio Finalizer，移除兼容例外。

这项例外是迁移机制，不改变核心决策：目标 Renderer 只把 final mix 当作音频真相。
