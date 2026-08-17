# Phase 1.5 已知问题

## 已解除的流程阻塞

### P15-GIT-001：Codex 进程不能写入 `.git`

- 状态：已解除，不再阻塞。
- 原因：Codex 对 `.git` 写入需要提升权限；自动审批器返回内部参数错误
  `Unknown parameter: input[22].namespace`，在 Git 执行前拒绝 `git add`。
- 处理：用户在本机终端完成两个代码提交，分别为 `5b4782f` 和 `04e6529`；代码已通过
  SSH push 推送到个人 Fork。报告作为第三个独立文档提交定稿。

### P15-GIT-002：GitHub CLI 认证在进程间不一致

- 用户终端已成功创建 Fork，且 `gh api user` 返回 `mit-mary`。
- Codex 隔离进程后续带代理访问得到 HTTP 401。
- 原因暂时无法验证；可能是临时环境 token 或凭据上下文不同。
- SSH `git push` 已成功，远程可写验收通过；CLI 认证差异不再阻塞本阶段。

## 非阻塞但需记录

### P15-ENV-001：Git 全局 ignore 警告

Codex 隔离进程无权读取 `C:\Users\SSS\.config\git\ignore`。用户终端提交与 push 未受
影响；在 Codex 进程内，用户级 ignore 规则可能不生效。

### P15-ENV-002：`python3` 是 WindowsApps 别名

Doctor 将其视为可发现，但未证明所有非交互 Runtime 脚本都能可靠执行该别名。
后续 Renderer 编排契约轮次应考虑使用 `sys.executable`，本轮按禁止边界未修改。

### P15-ENV-003：可选生产工具未配置

VoxCPM、Whisper、HyperFrames、VoxCPM2 模型和 Provider 凭据仍为 WARN。它们不阻塞
planning 和 Phase 2 合同设计，但会阻塞真实生产能力。

### P15-FONT-001：仓库仍不内置字体

这是路线 B 的明确设计，不是遗漏。当前 Windows 有受控系统候选；其他平台必须配置
显式字体或 `BOOK_VIDEO_FONT_DIRS`。无字体时会 fail-closed。

### P15-TEST-001：媒体端到端缺口仍存在

FFmpeg 端到端、音频 filter graph、V4 编排和 Post-QC 测试仍不足。它们属于下一阶段
Renderer 契约前置测试，不应在本轮顺手重构。

## 未发生

- 未接入 Remotion；
- 未重构 V2/V3/V4 业务链；
- 未调用付费或外部 API；
- 未下载模型或字体；
- 未生成视频；
- 未修改 `examples/`；
- 未提交字体/媒体二进制或真实密钥。
