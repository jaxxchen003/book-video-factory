# 字体合同审查

## 1. 当前提交原先承诺什么

修改前，`config/video_style_v2.json` 和资源 README 共同表达的是：

```text
macOS Songti / Times New Roman 系统字体优先
→ 仓库内 SmileySans-Oblique.otf 兜底
```

字体加载实现也会在任意配置字体缺失时退回 `fonts.title`。因此项目原先承诺的是
“系统字体优先 + 仓库兜底”，不是纯用户自备字体合同。

该承诺与仓库事实矛盾：`SmileySans-Oblique.otf` 不存在，导致系统字体不可用时
直接失败。

## 2. OFL 文本是否覆盖缺失 OTF

`SmileySans-OFL.txt` 包含：

- Copyright 2022–2024 atelierAnchor；
- Reserved Font Name `Smiley` 与 `得意黑`；
- SIL Open Font License 1.1；
- 对相应 Font Software 使用、嵌入和再分发的许可条件。

这能证明版权方对其明确发布并标记的 Font Software 使用 OFL，但不能单独证明某个
外部取得的同名 OTF 就是该官方版本。OFL 自身把 Font Software 定义为由版权方发布
并明确标记的文件集合。

结论：许可证文本与“得意黑”项目相关，但不足以对一个当前不存在、没有来源记录的
具体 `SmileySans-Oblique.otf` 做版本和来源认证。

## 3. 是否有足够再分发证据

完整历史查询结果：

- 字体目录在提交 `e0af254026704460d21401bcc1b6b0027b750034` 中加入；
- 该提交只加入 README 与 `SmileySans-OFL.txt`；
- `git log --all --follow -- SmileySans-Oblique.otf` 无记录；
- `git rev-list --objects --all` 中没有 OTF/TTF 字体对象。

仓库也未记录官方 OTF 下载 URL、版本元数据或 SHA-256。因此目前没有满足指令路线 A
全部条件的证据，不能从第三方补入二进制。

## 4. 原测试验证了什么

原 Renderer 测试明确比较返回路径是否等于
`resources/fonts/SmileySans-Oblique.otf`；Typography 测试也直接打开该路径。

因此原测试主要验证“特定文件名存在”，并没有覆盖：

- 用户显式字体；
- 路径存在但不是有效字体；
- 系统候选；
- 合法仓库 fallback；
- 所有来源缺失时的明确失败；
- Windows 路径和非本机可重复测试夹具。

## 5. 最符合原意与可重复构建的修改

采用路线 B：显式字体配置合同。

理由：

1. 不虚构缺失二进制的来源和版本。
2. 保留用户/Profile 显式选择字体的能力。
3. 可使用操作系统已安装、但不随仓库再分发的受控候选。
4. 未来若获得官方来源、许可匹配和 SHA，可在同一合同中登记合法 bundled fallback。
5. 所有来源不可用时明确 fail-closed，不输出缺字视频。

## 审查结论

- 路线 A：当前证据不足，不采用。
- 路线 B：满足当前事实和可重复验证要求，采用。
- 路线 C：本轮没有必要引入另一字体二进制，不采用。

