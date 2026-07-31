# 测试回归结果

## 基线

Phase 0 在 SHA `7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b` 记录：

- 原测试方法：56；
- unittest 结果记录：48 通过、1 Failure、7 Error；
- skipped：0；
- Failure：Windows Doctor `os.uname()`；
- Error：缺失 SmileySans OTF，其中 4 条来自同一测试方法的 subtest。

## 本轮命令

```powershell
python -m unittest discover -s skills/book-video-factory/tests -v
python -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
```

## 本轮结果

| 测试组 | 方法数 | 通过 | Failure | Error | Skip | 退出码 |
|---|---:|---:|---:|---:|---:|---:|
| Skill / bootstrap | 8 | 8 | 0 | 0 | 0 | 0 |
| Runtime | 65 | 65 | 0 | 0 | 0 | 0 |
| 合计 | 73 | 73 | 0 | 0 | 0 | 0 |

## 原测试与新增测试

- 原有测试槽位：56，全部通过。
- 新增测试方法：17，全部通过。
  - `test_credentials.py`：7。
  - `test_fonts.py`：9。
  - `test_typography.py` 新增中文测量：1。

字体合同相关的原测试已按路线 B 更新，而不是删除或 skip：

- 原“固定 SmileySans 文件 fallback”断言改为“所有来源缺失时必须 fail-closed”；
- 长标题仍在 V4 的 608px 安全区验证；
- 语义换行使用确定性测试字体对应的边界宽度；
- 字号权衡新增 `font_size < max` 与下限断言，未弱化为仅“不抛异常”。

## 覆盖新增

### Doctor / 凭据

- Windows、Linux 不执行 macOS `security`；
- macOS `security` 存在/不存在、成功/失败；
- 环境变量优先；
- Provider 缺凭据时明确错误；
- planning Doctor 正式子进程成功。

### 字体

- 显式环境/Profile 路径；
- 路径不存在和无效字体文件；
- Windows 系统候选存在/不存在；
- 合法 Runtime fallback；
- 所有来源缺失时明确修复指引；
- 可移植搜索目录；
- 中文测量、长标题、语义换行和字号权衡。

## 额外校验

`git diff --check` 退出码 0。未发现 unexpected skip、真实视频生成、外部 API 调用
或测试生成资产残留。

## 结论

基线测试已从非绿恢复为 73/73 全绿。该结果只证明现有单元/合同测试范围；它不补足
Phase 1 已识别的 FFmpeg 端到端、V4 编排和 Post-QC 测试缺口。

