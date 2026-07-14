# Book Video Factory v2 合同层

这一层把现有 V4/V5 渲染器包装成可审计执行引擎，不重写已经稳定的媒体合成代码。

## 对象边界

- `release_profile`：平台、画布、脚本、场景、标题安全区和编码规格。
- `stage_manifest`：一次阶段运行的输入、输出、hash、检查、工具与 release ID。
- `approval_event`：人工审批决定以及审批时对应的文件 hash。
- `claim / source_document / content_unit`：由后续 `content-system-backed` 模式接入；不复制上游内容系统的主题、关系和去重实现。
- `release_manifest`：后续 freeze-release 阶段生成的不可覆盖交付清单。

## 真源规则

1. 原始来源与人工批准文件不得被生成脚本覆盖。
2. `project.json.status` 只是旧脚本兼容缓存。
3. 发布状态必须由当前文件、manifest 和 approval event 重新计算。
4. 审批事件绑定文件 hash；审批对象改变后旧审批自动失效。
5. manifest 与 release 使用新文件写入，不允许覆盖。

## 首个 release profile

`config/release_profiles/book-v4-bilingual-3x4.json` 冻结当前已经验证的 V4 能力：

- `720×960 / 30fps`
- 15 行双语脚本
- 12 张按 SHA-256 去重的 PNG 场景
- H.264 + AAC
- 标题左右各 56px 安全边距、最多两行、34–70px 动态字号

这不是把所有平台都硬编码成 V4，而是先把已经验证的行为命名为一个可选择、可版本化的 profile。
