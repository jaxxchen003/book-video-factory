# Phase 0 测试结果

- 记录时间：2026-07-31T17:21:45+08:00
- 基线提交：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 代码修改：测试前无生产逻辑修改

## 执行命令

```powershell
python -m unittest discover -s skills/book-video-factory/tests -v
python -m unittest discover -s skills/book-video-factory/runtime/book_video_factory/tests -v
```

## 汇总

| 测试组 | 执行数 | 通过（按结果记录推导） | Failure | Error | 跳过 | 退出码 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill / bootstrap | 8 | 7 | 1 | 0 | 0 | 1 |
| Runtime | 48 | 41 | 0 | 7 | 0 | 1 |
| 合计 | 56 | 48 | 1 | 7 | 0 | 1 |

按 Phase 0 汇总口径：测试总数 56，通过数 48，失败/错误数 8，跳过数 0。

注意：Runtime 的 7 个 Error 中，4 个来自同一个 `test_long_titles_fit_inside_v4_safe_area` 方法的 4 个 subtest。若按测试方法而不是 unittest 结果记录计数，则共有 51 个方法通过、5 个方法未通过。报告主表保留 unittest 的原生 Failure/Error 计数，避免掩盖 subtest 错误。

## 未通过项目

### 1. Windows Doctor 可运行性

- 测试：`test_bundled_doctor_planning_profile_is_runnable`
- 类型：Failure
- 直接原因：Doctor 退出码为 1。
- 根因：`credential_available()` 无条件调用 `os.uname()`；Windows Python 没有该 API，抛出 `AttributeError`。
- 分类：项目跨平台兼容问题，不是缺少依赖。

### 2. 字体兜底文件缺失

- 测试：`test_missing_system_fonts_fall_back_to_bundled_ofl_font`
- 类型：Error
- 直接原因：找不到 `resources/fonts/SmileySans-Oblique.otf`。
- 分类：仓库/打包内容缺失。

### 3. 长标题安全区

- 测试：`test_long_titles_fit_inside_v4_safe_area`
- 类型：4 个 subtest Error
- 直接原因：Pillow 无法打开缺失的 `SmileySans-Oblique.otf`，抛出 `OSError: cannot open resource`。
- 受影响标题：
  - `允许一切发生：过不紧绷松弛的人生`
  - `自卑与超越（完整全译本）`
  - `当你开始爱自己，全世界都会来爱你`
  - `原生家庭：如何修补自己的性格缺陷`
- 分类：仓库字体资产缺失；当前结果不能证明排版算法本身失败。

### 4. 语义换行

- 测试：`test_prefers_semantic_break_before_parenthetical_subtitle`
- 类型：Error
- 直接原因：同一字体文件缺失。
- 分类：仓库字体资产缺失。

### 5. 字号与语义换行权衡

- 测试：`test_semantic_break_can_trade_a_little_font_size`
- 类型：Error
- 直接原因：同一字体文件缺失。
- 分类：仓库字体资产缺失。

## 已确认的字体证据

`resources/fonts/README.md` 明确说明应包含 `SmileySans-Oblique.otf`，测试也直接引用该路径；但 Git 跟踪列表中只有：

- `resources/fonts/README.md`
- `resources/fonts/SmileySans-OFL.txt`

因此这不是本机系统字体路径导致的偶发现象。许可证文本存在，但实际 OTF 文件未随当前提交提供。

## 结论

- 内容桥接、Manifest、Gate、Release、成本、项目初始化等 48 条结果记录通过。
- 测试不是全绿状态。
- 失败已区分为两个上游项目问题：Windows Doctor 兼容性和缺失的字体资产。
- Phase 0 不修改这些问题；应在后续独立修复分支中处理并重新跑全套测试。
