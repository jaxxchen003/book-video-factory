# Renderer Contract 测试策略

## 目标

下一轮先证明合同、路径、Hash、映射和状态机正确，再允许真实媒体实现接入。测试不调用
外部 API，不依赖 Showcase 视频，不需要真实书名或生产凭据。

## 测试层次

| 层 | 测试对象 | 是否运行媒体工具 |
|---|---|:---:|
| L1 Schema/纯验证 | Request/Result/Capability、错误码、版本 | 否 |
| L2 Path/Hash | root binding、escape/symlink、canonical hash | 否 |
| L3 V4 Mapper | 15/12、资产/Approval/Profile 到 Request | 否，使用微型文件 fixture |
| L4 Renderer Protocol | fake Renderer、Capability、状态/Attempt | 否 |
| L5 Legacy facade characterization | 旧 V4 命令构造、结果收集 | 默认 fake runner；独立媒体测试可启用 |
| L6 Synthetic media/QC | stream、时长、音频、字幕边界 | 是，仅本地 synthetic fixture |

## Request 验证用例

### 合法

- 合法最小 final Request：一个 segment、一张 still、final mix、无 Caption/Overlay。
- 合法 preview Request：同一 Schema，Profile 存在具名 preview policy。
- Unicode project-relative path 在 Windows/POSIX 解析到相同 logical ref。
- 可选 stems 存在但只用于 waveform，不改变 final mix。
- 已批准 degradation plan 与 Capability 匹配。

### 必填与版本

- 每个必填字段逐一缺失。
- 不支持的 major version fail-closed。
- 支持的 minor optional field 被旧 validator 明确拒绝或按兼容策略处理，不能静默忽略。
- 未知顶层字段、拼写错误字段和未知 enum。

### 路径安全

- POSIX absolute、Windows drive、UNC、反斜杠。
- `../asset`、`a/../../asset`、`.`、空 segment、NUL。
- root 未声明、输出写入只读 runtime root。
- project 内 symlink/reparse point 指向 root 外。
- Unicode normalization 与大小写敏感差异不改变 portable JSON，但物理解析按平台 fail-closed。

### Timeline

- segment 倒序、重叠、零/负时长。
- 隐式 gap；要求用显式 `hold` segment。
- 首 segment 使用 `hold`。
- segment 末端超过 `duration_ticks`。
- Caption/overlay/audio cue 越界或绑定错误 segment。
- tick→frame 在 .5 边界使用固定 round-half-up。
- 30/1、30000/1001 FPS rational mapping。

### Assets/Profile

- 缺资产、零字节、不匹配 bytes。
- SHA 格式错误与实际 Hash 不匹配。
- Profile ID/revision/hash 不匹配。
- OutputSpec width/height/FPS/codec 与 Profile 分歧。
- 字体缺失、无法打开或 resolved font Hash 改变。
- 输入在运行前后发生变化。

### Audio/Caption

- final Request 缺 final mix。
- final mix 时长、采样率、声道或 Hash 不合法。
- stems 越界或用于未声明 Capability。
- Caption text source hash stale。
- ASR 文本与批准稿不同但 cue 保持批准文本。
- Word timing 倒序/越界；请求 word highlight 但无 word timing。
- 最大行数、安全区和 overflow fail-closed。

### Gate/Capability

- Gate/rights snapshot 为 blocked。
- Approval event 属于另一 release 或已 stale。
- Capability 不支持 still/video/caption/word highlight/audio playback。
- Renderer 试图静默丢弃能力时测试失败。
- 显式降级缺 Approval、namespace 或 capability version 时 Blocked。

## Result/Attempt 用例

- succeeded：必须有 output、Probe、Hash、finished_at、QC handoff，errors 为空。
- failed：允许 output 为空，必须有 primary error 与 terminal time。
- blocked：不启动 fake runner，错误为 Gate/Rights/Capability 类。
- cancelled：新 Attempt 可重试，原 Result 不覆盖。
- pending/running event 合法；terminal Result write-once。
- 重试同一 Request 生成不同 attempt_id、相同 request_hash。
- 输出缺失、空文件、Hash mismatch、Probe 失败对应稳定错误码。
- `output_hashes`/`input_hashes` 派生索引与 artifact 真相不一致时拒绝。
- 日志路径 portable，错误消息不含环境 secret 或绝对路径。

## Request Hash 用例

固定 golden JSON bytes 和 SHA，验证：

- 相同语义与 key 顺序变化产生相同 Hash；
- Windows/POSIX physical root binding 变化不影响 Hash；
- Unicode 路径按约定 UTF-8 保持稳定；
- temp/work/cache/log directory、PID、host、attempt_id 不影响 Hash；
- metadata 时间/创建者不影响 Hash；
- 资产 SHA、Profile/Renderer 版本、Timeline tick、Approval snapshot、extension 或持久化
  output target 任一改变都会改变 Hash；
- float/NaN/Infinity 被 canonicalizer 拒绝。

## V4 Mapper 用例

- 15 行、12 唯一场景成功映射。
- 少/多台词、少场景、重复 scene bytes、Scene-Line mapping 分歧。
- Voice/ASR/H2/BGM/cover/font 任一缺失。
- BGM glob 为 0 或大于 1。
- pause/montage/outro 精确映射为连续 integer-tick segments。
- Caption 文本来自 script，时间来自 aligned timing。
- Release ID 缺失、Approval 混入其他 Release、rights hold。
- 与 Profile 重复的 720×960/30/15/12 只能从 Profile 产生一次，mapper 检测漂移。
- 旧输出已存在时 `fail_if_exists`，不覆盖。

## Synthetic media characterization

合同纯测试全绿后才增加：

1. 纯色/自生成小 PNG + 1 kHz/静音 WAV，构建数秒媒体；
2. 验证 width/height/FPS/frame count/duration/最后一帧；
3. final mix mux 后验证 codec、采样率、声道、A/V sync；
4. 人工构造黑帧、静音、错误响度、Caption 越界作为 Post-QC fail fixture；
5. 对旧 V4 facade 使用 fake runner 为默认，真实媒体测试独立标记且不依赖生产资产。

字体 fixture 必须有明确测试许可或由测试环境显式提供；不能再次提交来源不明字体。

## 通过门槛

- 所有 L1–L4 测试跨 Windows/POSIX 通过；
- 没有网络、付费 API、真实密钥和 Showcase 二进制依赖；
- 错误码/状态/Hash 有 golden tests；
- V4 mapper 的所有固定输入都有覆盖；
- L5/L6 失败时不能启用新编排入口；
- 旧 V4 CLI 保持可运行和可回滚。
