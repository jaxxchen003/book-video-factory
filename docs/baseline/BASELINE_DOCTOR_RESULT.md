# Phase 0 Doctor 结果

- 记录时间：2026-07-31T17:21:45+08:00
- 基线提交：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`

## 官方命令

```powershell
python skills/book-video-factory/scripts/doctor.py --profile planning
```

## 正式结果

- 退出码：1
- 状态：`CRASHED`
- 是否生成正常 Doctor 汇总：否
- 根因：Windows 上不存在 `os.uname()`。

关键异常：

```text
File ".../scripts/doctor.py", line 48, in credential_available
    if os.uname().sysname != "Darwin" or not shutil.which("security"):
AttributeError: module 'os' has no attribute 'uname'
```

因此不能把本机正式 Doctor 结果写成 `ready`，也不能把它误判成凭据缺失或 FFmpeg 缺失。

## 补充诊断（非正式验收结果）

为了确认首个异常之后的检查状态，额外在单次 Python 进程中临时提供了只返回 `Windows` 的 `os.uname` 兼容对象。没有修改仓库文件。该补充运行得到 `planning: ready`，检查项如下：

| 检查 | 状态 | 说明 |
| --- | --- | --- |
| `python3` | READY | 解析到 WindowsApps 别名；Doctor 只检查路径存在 |
| FFmpeg | READY | 8.1.2 |
| FFprobe | READY | 8.1.2 |
| Node | READY | v24.15.0 |
| npm | READY | 11.12.1 |
| Pillow | READY | 12.2.0 |
| 磁盘空间 | READY | 153.19 GiB 可用 |
| `voxcpm` | WARN | 未安装，planning 非必需 |
| VoxCPM2 模型 | WARN | 未安装，planning 非必需 |
| `whisper` / `whisper-cli` | WARN | 未安装，planning 非必需 |
| `hyperframes` | WARN | 未安装，planning 非必需 |
| WeRead 凭据 | WARN | 未配置，planning 非必需 |
| Freesound 凭据 | WARN | 未配置，planning 非必需 |
| Freesound 商业授权标记 | WARN | 未配置，planning 非必需 |
| Codex 内置图像生成模式 | READY | 不需要本地 OpenAI API Key |

这个补充结果只能证明其余 planning 检查没有发现 Blocked 项，不能替代官方命令。正式 Doctor 验收仍为失败。

## 问题归类

- 项目问题：Doctor 使用 `os.uname()`，与 README 宣称的可移植 Windows 工作流不兼容。
- 环境警告：可选 TTS、ASR、HyperFrames、模型和凭据未配置。
- 非问题：FFmpeg、FFprobe、Node、npm、Pillow 和磁盘空间均已就绪。
