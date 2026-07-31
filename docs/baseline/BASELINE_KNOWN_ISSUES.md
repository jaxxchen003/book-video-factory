# Phase 0 已知问题

- 记录时间：2026-07-31T17:21:45+08:00
- 基线提交：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`

## 项目问题

### P0-PROJ-001：Doctor 在 Windows 上崩溃

- 严重度：高
- 状态：已复现，未修复
- 证据：正式 Doctor 命令退出 1；bootstrap 测试失败。
- 根因：`os.uname()` 不是 Windows Python API。
- 影响：无法获得正式 planning Doctor 报告，也不能宣称 Windows planning-ready。
- 后续建议：使用 `platform.system()` 或 `sys.platform` 做平台判断，并添加 Windows 测试。

### P0-PROJ-002：仓库缺少声明的 SmileySans 字体文件

- 严重度：高
- 状态：已确认，未修复
- 证据：资源 README 和测试都引用 `SmileySans-Oblique.otf`，但 Git 只跟踪 README 与 OFL 文本。
- 影响：7 条 unittest Error 记录；系统字体缺失时兜底失败；标题排版测试无法执行。
- 后续建议：核对字体再分发权利后补齐 OTF，或调整实现与测试，使用户显式配置授权字体并可靠 fail-closed。

## 环境与仓库设置问题

### P0-ENV-001：没有用户个人 Fork

- 严重度：中
- 状态：待用户提供 Fork URL
- 事实：`origin` 与 `upstream` 都指向 `jaxxchen003/book-video-factory`。
- 影响：无法安全推送自己的后续改造分支；不影响本地只读审计。
- 后续建议：创建个人 Fork 后把 `origin` 改为个人仓库，保留 `upstream` 指向原作者。

### P0-ENV-002：当前为浅克隆

- 严重度：低
- 状态：已记录
- 影响：当前 SHA 和源码完整，基线测试不受影响；Phase 1 若需追溯历史引入点，可能需要补全历史。

### P0-ENV-003：Git 全局 ignore 文件读取警告

- 严重度：低
- 状态：已记录
- 现象：`C:\Users\SSS\.config\git\ignore` 无权访问。
- 影响：未影响当前 `git status`、Commit 读取或测试。

### P0-ENV-004：缺少 setuptools 构建依赖

- 严重度：低
- 状态：未安装
- 影响：当前源码测试不受影响；执行 `pip install` 或构建包时需要 `setuptools>=68`。
- 处理原则：Phase 0 不为了未执行的打包任务额外安装依赖。

### P0-ENV-005：可选生产工具尚未配置

- 严重度：中（对 Phase 4），低（对 Phase 0/1）
- 状态：预期警告
- 缺少：VoxCPM2、Whisper、HyperFrames、相关模型及 WeRead/Freesound/Gemini 凭据。
- 影响：不阻塞 planning 与 Phase 1 审计，但会阻塞后续真实音频、对齐或 Provider 流程。

### P0-ENV-006：`python3` 是 WindowsApps 别名

- 严重度：低
- 状态：待后续验证
- 事实：Doctor 仅用 `shutil.which` 判断并把该别名视为 READY；本轮可靠命令入口是 `python`。
- 风险：路径存在不等于别名在所有非交互环境中均可执行。

## 当前不存在的问题

- Python 版本满足项目要求。
- Pillow 版本满足项目要求。
- FFmpeg、FFprobe、Node 和 npm 可用。
- 磁盘空间充足。
- 未发现测试或 Doctor 失败由付费 API、凭据或大型模型缺失直接造成。
