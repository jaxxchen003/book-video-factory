# 字体资产

当前提交**不包含字体二进制**。完整 Git 历史也没有出现过
`SmileySans-Oblique.otf`，因此 Runtime 不再把该文件声明为可用的仓库兜底。

`SmileySans-OFL.txt` 是得意黑版权方及 Reserved Font Name 对应的 SIL Open
Font License 1.1 文本。OFL 允许相应 Font Software 随软件再分发，但许可证文本
本身不能证明任意同名字体二进制的来源、版本或完整性。本仓库没有记录 v2.0.1
官方二进制的来源 URL 和 SHA-256，因此该文本仅作为历史许可证记录，不代表字体
文件已经核验或可以从任意第三方下载后提交。

## 当前字体合同

解析顺序为：

1. `BOOK_VIDEO_TITLE_FONT`、`BOOK_VIDEO_CHINESE_FONT`、
   `BOOK_VIDEO_ENGLISH_FONT` 指定的授权字体文件；
2. `config/video_style_v2.json` 中对应字体角色的显式路径；
3. `BOOK_VIDEO_FONT_DIRS` 与 Windows 系统字体目录中的受控候选文件名；
4. 配置中明确登记、位于 Runtime 内的合法 `bundled_fallback`（当前为空）；
5. 没有可用字体时抛出明确错误并停止渲染。

系统字体仅在本机渲染时使用，不会被复制进仓库或交付包。Pillow 默认字体不是
中文生产兜底，缺字体时不会静默输出缺字或乱码视频。
