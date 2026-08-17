# Phase 0 基线环境

- 记录时间：2026-07-31T17:21:45+08:00
- 仓库路径：`E:\AI\BookVideoFactory`
- 基线提交：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 提交时间：2026-07-22T02:59:58+08:00
- 提交说明：`Add dual-style VOX book-video workflow`
- 当前分支：`main`
- 克隆类型：浅克隆（`git rev-parse --is-shallow-repository` 为 `true`）

## Git 远程

| 名称 | Fetch / Push URL | 说明 |
| --- | --- | --- |
| `origin` | `https://github.com:443/jaxxchen003/book-video-factory.git` | 当前仍指向原作者仓库 |
| `upstream` | `https://github.com:443/jaxxchen003/book-video-factory.git` | 原作者仓库 |

当前没有用户个人 Fork URL，因此 `origin` 与 `upstream` 相同。这不影响只读基线验证，但长期开发前应把 `origin` 改为用户自己的 Fork。

## 操作系统与工具链

| 项目 | 已确认值 | 基线判断 |
| --- | --- | --- |
| 操作系统 | Windows 10.0.19045 SP0，AMD64 | 已记录 |
| 区域设置 | `zh-CN` | 已记录 |
| Python | 3.14.4，`C:\Python314\python.exe` | 满足项目 `>=3.11` 声明 |
| pip | 26.0.1 | 可用 |
| Pillow | 12.2.0 | 满足项目 `Pillow>=10.0` 声明 |
| setuptools | 未安装 | 仅影响构建/安装；不影响本轮源码测试 |
| Node.js | v24.15.0 | 可用 |
| npm | 11.12.1 | 可用 |
| FFmpeg | 8.1.2 full build | 可用 |
| FFprobe | 8.1.2 full build | 可用 |
| certifi | 2026.5.20 | 可用 |
| E 盘剩余空间 | 153.19 GiB | 高于 Doctor 的 10 GiB 阈值 |

FFmpeg 与 FFprobe 来自 WinGet 的 Gyan FFmpeg 8.1.2 full build。Node.js 位于 `D:\Program Files\nodejs`。

## 项目依赖判断

`skills/book-video-factory/runtime/book_video_factory/pyproject.toml` 声明：

- Python `>=3.11`
- 运行时依赖 `Pillow>=10.0`
- 构建后端依赖 `setuptools>=68`

Pillow 已安装且版本满足要求。官方 Phase 0 测试与 Doctor 都直接从源码运行，不需要构建 wheel 或安装包，因此本轮没有联网安装任何 Python 包，也没有安装大型模型。

## 可选能力现状

以下能力未安装或未配置，但在 `planning` Profile 中只应产生警告，不应阻塞：

- `voxcpm` 与 VoxCPM2 模型
- `whisper` / `whisper-cli`
- `hyperframes`
- `google.genai`
- `WEREAD_API_KEY`
- `FREESOUND_API_KEY`
- `GEMINI_API_KEY`

## 环境备注

- `python3` 被解析为 WindowsApps 别名；官方基线命令使用可正常运行的 `python`。
- Git 查询时出现 `C:\Users\SSS\.config\git\ignore` 无权访问警告。该警告未影响检出、Commit 读取或测试。
- 本轮未调用付费 API，未下载模型，也未把 `examples/` 资产用于生产。
