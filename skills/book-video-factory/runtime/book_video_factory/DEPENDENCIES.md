# 依赖与本地安装位置

P0 的项目初始化与微信读书采集以 Python 标准库为主；TLS 会优先使用当前 Python 已安装的 `certifi` CA 包，缺失时回退到 macOS/Homebrew 系统 CA 文件，绝不关闭证书校验。视频、语音和字幕阶段使用外部程序，统一由 `scripts/doctor.py` 检查。

| 能力 | 程序/依赖 | 当前约定 |
| --- | --- | --- |
| 视频探测、合成、音频母带 | `ffmpeg`, `ffprobe` | 必需，PATH 可执行 |
| 中文旁白 | VoxCPM2 `voxcpm` | CLI：`~/.local/bin/voxcpm` |
| VoxCPM2 权重 | VoxCPM2 ModelScope snapshot | `~/.local/share/voxcpm-models/VoxCPM2-modelscope` |
| 字幕时间锚点 | `whisper` / `whisper-cli` / `faster-whisper` | 成片阶段至少一个可用 |
| 动态模板候选 | `hyperframes` | P0 可选；FFmpeg 是确定性主渲染器 |
| JS 模板运行时 | `node`, `npm` | 使用 HyperFrames/Remotion 时必需 |
| 资料采集 | 微信读书 Agent Gateway | `WEREAD_API_KEY` 或 macOS Keychain |
| BGM 候选检索 | Freesound APIv2 | `FREESOUND_API_KEY` 或 macOS Keychain；免费 API 仅限非商业候选研究，商业发布须另有 Freesound API 授权 |
| 场景图与书封元素 | Codex 内置图像生成（GPT Image 2） | 由当前 Codex 任务生成并复制到项目仓库，不需要本地 `OPENAI_API_KEY` |
| VOX 风格视频（API lane） | `google-genai`、Gemini API | 仅 `--generation-lane gemini-api` 需要；`GEMINI_API_KEY` 只从环境读取。Omni 使用 `gemini-omni-flash-preview` / Interactions API；首尾帧或延长使用 `veo-3.1-generate-preview` / `generate_videos` |
| VOX 风格视频（Flow lane） | Google Flow 用户界面 | 仅 `--generation-lane google-flow` 需要；账号、地区、方案和 credits 由用户在官方界面确认，不假设可编程 Flow API |

## 安全约束

- API key、Cookie、登录态不得写入本目录或 `book_video_warehouse/`。
- `google-genai` 是 VOX API lane 的可选依赖，不加入本地渲染核心依赖；`doctor.py --profile production --project <project>` 会按项目所选 lane 检查。
- 不使用下载参考视频的人声做声音克隆；克隆音色必须有账号主体的明确授权。
- P0 只采集书籍元信息、热门短划线和公开点评，不下载或保存整本正文。
- 图片、BGM、书封和引用必须在项目清单中登记来源与授权状态。
