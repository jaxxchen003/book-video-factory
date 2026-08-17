# Phase 1.5 执行结果

## 基本信息

- 仓库：`jaxxchen003/book-video-factory`
- 本地路径：`E:\AI\BookVideoFactory`
- 基线 SHA：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 代码实现 HEAD：`04e652978f76c4af2d85391c37703a13445f9ede`
- 当前分支：`fix/windows-baseline-readiness`
- origin：`git@github.com:mit-mary/book-video-factory.git`
- upstream：`git@github.com:jaxxchen003/book-video-factory.git`
- Fork：`mit-mary/book-video-factory`，已建立
- 是否浅克隆：否

## 修改范围

- Doctor：用共享跨平台凭据模块替换 `os.uname()`，覆盖 Doctor/WeRead/Freesound。
- 字体合同：路线 B，显式配置 + 受控系统候选 + 可选合法 fallback + fail-closed。
- 测试：新增 17 项并强化字体合同测试；总计 73 项。
- 生产 Renderer 业务/视觉链修改：否
- Renderer 文件内字体解析入口修改：是，仅限允许的字体合同范围
- Remotion 接入：否
- 外部付费 API：否

## Doctor 修复

- 根因：Windows Python 不支持 `os.uname()`。
- 修复方案：`platform.system()` 集中判断，环境变量优先，macOS 才使用 `security`。
- Windows：不崩溃；无凭据为 WARN/缺失。
- macOS：保留 Keychain 探测/读取语义。
- Linux：不调用 `security`，不抛平台异常。
- 正式 Doctor 退出码：0
- 正式 Doctor 状态：`planning: ready`

## 字体合同

- 选择路线：B，显式字体配置合同
- 字体来源：用户授权路径或操作系统受控候选；当前不内置字体
- 授权：保留 SmileySans OFL 历史文本，但不把它误报为缺失 OTF 的来源证明
- 是否提交二进制：否
- 配置优先级：环境变量 → Profile 显式路径 → 系统候选 → 合法 bundled fallback
- 无字体时行为：抛 `FontConfigurationError`，拒绝渲染

## 测试结果

- 原基线：56 项，48 通过，1 Failure，7 Error
- 本轮原测试槽位：56 项全部通过；字体合同测试按路线 B 更新
- 新增测试：17 项全部通过
- 总计：73 项全部通过
- Failure：0
- Error：0
- Skip：0

## Git 状态

- Doctor/凭据提交：`5b4782fca28ff2b3e153275626bb2f9e846e8d87`
- 字体合同提交：`04e652978f76c4af2d85391c37703a13445f9ede`
- 代码工作区：提交后仅剩 `docs/` 报告目录待独立定稿提交
- 是否可推送：是；SSH push 已实际验证
- 代码是否已推送：是；远端分支 `origin/fix/windows-baseline-readiness` 与代码 HEAD 一致
- `git diff --check`：通过

## 已知问题

1. GitHub CLI 认证在用户终端与 Codex 隔离进程间表现不一致；原因暂无法验证，但 SSH
   push 已验证，不再阻塞。
2. `python3` WindowsApps 别名、可选生产工具和媒体端到端测试仍是后续已知项。

## 是否通过 Phase 1.5

结论：**通过。**

理由：Fork、远程、完整历史、独立分支、Doctor、字体合同、73 项测试和正式 Doctor
均已满足；两个代码提交已形成并成功推送到个人 Fork。报告目录保持为独立的第三个
文档提交，不与代码提交混合。

## 是否允许进入 Phase 2

结论：完成并推送本报告的独立文档提交后，允许进入 Phase 2。

Phase 2 仅进入 Renderer 契约设计轮次；本结论不授权同时启动 Provider、Web、Remotion
或生产 Renderer 重构。

## 唯一下一轮建议

将 `docs/` 作为第三个独立提交推送并核对工作区清洁；随后只进入 Phase 2 Renderer
契约设计轮次。
