# Windows Doctor 修复

## 根因

Runtime Doctor、WeRead 和 Freesound 的凭据检查分别直接调用 `os.uname()`。
Windows Python 不提供该接口，因此在检查可选凭据时抛出 `AttributeError`，正式
planning Doctor 无法输出汇总。

## 修复方案

新增 `src/book_video_factory/credentials.py`，集中实现：

- `is_macos()`：使用 `platform.system() == "Darwin"`；
- `macos_security_executable()`：仅在 macOS 且 `security` 可发现时返回路径；
- `credential_available()`：先检查环境变量，再只读探测 macOS Keychain；
- `load_secret()`：先读取环境变量，再读取 macOS Keychain，找不到时返回 `None`。

以下调用方改为复用该模块：

- `scripts/doctor.py`
- `src/book_video_factory/weread.py`
- `src/book_video_factory/freesound.py`

全仓搜索已不再发现 `os.uname()`。

## 平台语义

### Windows

- 不调用 `security`。
- 无凭据时返回缺失，不抛平台异常。
- planning Profile 把 WeRead/Freesound 缺失保持为 WARN。
- 不把缺失凭据伪造成 READY。

### macOS

- 仍使用 `security find-generic-password -s <service>` 探测是否存在。
- 读取 secret 时仍增加 `-w`。
- `security` 不存在时返回缺失，不执行错误的子进程。
- Keychain 返回非零时保持“凭据缺失”语义。

### Linux

- 不调用 macOS `security`。
- 无环境变量时返回缺失，不抛异常。

## 安全边界

- 未打印、记录或提交任何真实凭据。
- 可用性检查把 stdout/stderr 丢弃，不读取 secret。
- 只有 Provider 确实需要值时才调用 `load_secret()`。
- 未调用 WeRead、Freesound 或其他外部 API。

## 回归保护

新增 `tests/test_credentials.py` 共 7 项，覆盖：

- Windows 缺失凭据；
- Linux 缺失凭据；
- macOS 有/无 `security`；
- macOS Keychain 命令成功/失败；
- 环境变量优先且不触发 Keychain；
- WeRead/Freesound 在 Windows 上明确失败而非崩溃。

既有 bootstrap 测试继续通过正式 Doctor 子进程验证 planning Profile。

## 结果

正式命令：

```powershell
python skills/book-video-factory/scripts/doctor.py --profile planning
```

结果：退出码 0，`overall: ready`。可选工具、模型和凭据缺失保持 WARN。

