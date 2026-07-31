# Doctor 回归结果

## 正式命令

```powershell
python skills/book-video-factory/scripts/doctor.py --profile planning
```

没有使用进程内 `os.uname` monkeypatch，也没有伪造凭据或依赖。

## 结果

- 退出码：0
- Profile：`planning`
- Overall：`ready`
- 是否崩溃：否

## READY

- `python3`：可发现 WindowsApps 可执行别名；
- FFmpeg / FFprobe：可发现；
- Node / npm：可发现；
- Pillow：已安装；
- Codex 内置图像生成模式：ready；
- 磁盘空间：ready。

## WARN

- VoxCPM CLI；
- Whisper / Whisper CLI；
- HyperFrames；
- VoxCPM2 本地模型；
- WeRead 凭据；
- Freesound 候选搜索凭据；
- Freesound 商业 API 授权标记。

这些能力对 planning Profile 不是必需项。缺失凭据仍为 WARN，没有误报 READY，也没有
输出环境变量值。

## 平台回归

新单元测试模拟 Windows、Darwin 和 Linux：

- Windows/Linux 不调用 `security`；
- Darwin 保留原 Keychain 探测语义；
- `security` 不存在或返回非零时返回缺失；
- 环境变量存在时不访问 Keychain。

## 已知限制

Doctor 对 `python3` 仍只检查 `shutil.which()`。WindowsApps 别名在所有非交互子进程中
是否可靠执行仍未单独验证；该问题不再导致 planning Doctor 崩溃，也不属于本轮两个
基线根因之一。

## 结论

Windows Doctor 根因已修复，正式 planning 验收通过。

