# 字体合同决策

## 选择路线

采用路线 B：显式字体配置合同。没有下载或提交字体二进制。

## 新解析优先级

```text
1. BOOK_VIDEO_TITLE_FONT / BOOK_VIDEO_CHINESE_FONT / BOOK_VIDEO_ENGLISH_FONT
2. video_style_v2.json 中对应角色的显式路径
3. BOOK_VIDEO_FONT_DIRS 与 Windows 系统目录中的受控候选文件名
4. Runtime 内明确配置并经许可核验的 bundled_fallback
5. 无可用字体时抛 FontConfigurationError，拒绝渲染
```

默认配置不再包含 macOS 绝对路径，也不再指向不存在的 SmileySans OTF。

## 系统候选

当前 Windows 候选：

- Title：微软雅黑粗体、微软雅黑；
- Chinese：微软雅黑、宋体；
- English：Arial、Times New Roman。

候选以系统文件名配置，实际系统字体目录从 `WINDIR` 推导；系统字体不会复制进仓库。
非 Windows 平台可通过显式字体变量或 `BOOK_VIDEO_FONT_DIRS` 提供候选目录。

## 文件有效性

解析器不仅检查 `Path.is_file()`，还使用 Pillow 实际打开字体。路径存在但不是有效字体
时会明确失败，不会继续生成视频。

显式环境/Profile 路径无效时立即失败，避免操作者指定错误字体后又被静默替换。

## Bundled fallback

接口仍支持未来合法仓库 fallback，但要求：

- 配置明确；
- 文件位于 Runtime 内；
- Pillow 可打开；
- 来源、许可和 SHA 在加入前另行核验。

当前 `bundled_fallback` 为空。

## 无字体行为

抛出 `FontConfigurationError`，错误信息指出缺失的字体角色和应设置的环境变量。
Pillow 默认字体不会进入生产解析路径，不会静默输出缺字、方框或乱码。

## 测试策略

新增 9 个字体合同测试，覆盖：

- 显式字体有效；
- 显式字体路径不存在；
- 文件存在但 Pillow 无法打开；
- Profile 相对路径；
- Windows 系统候选存在/不存在；
- 合法 bundled fallback；
- 所有来源缺失时 fail-closed；
- 可配置搜索目录。

Typography 测试使用 Pillow 自带的内存测试字体对象。该对象只用于确定性测量测试，
不写入仓库、不进入配置，也不作为中文生产 fallback。长标题安全区、括号副标题语义
换行、字号权衡和中文文本可测量均继续验证。

## 本机验证

当前 Windows 环境的 Title、Chinese 和 English 三种角色均成功解析到受控系统候选，
且可由 Pillow 打开。报告不记录或提交机器专属绝对路径。

