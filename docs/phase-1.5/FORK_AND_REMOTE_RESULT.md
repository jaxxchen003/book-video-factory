# Fork 与远程结果

## 当前状态

- 本地仓库：`E:\AI\BookVideoFactory`
- 基线 SHA：`7ec72370cce1d2fa899e0e0f9b2c0d8131d4660b`
- 代码实现 HEAD：`04e652978f76c4af2d85391c37703a13445f9ede`
- 当前分支：`fix/windows-baseline-readiness`
- Fork：`mit-mary/book-video-factory`
- origin：`git@github.com:mit-mary/book-video-factory.git`
- upstream：`git@github.com:jaxxchen003/book-video-factory.git`
- 浅克隆：否
- 工作分支是否独立于 main：是

## 执行记录

用户终端通过 GitHub CLI 创建了 `mit-mary/book-video-factory`，当时
`gh api user --jq .login` 返回 `mit-mary`。第一次 Fork 命令还在主仓库下创建了
一个嵌套克隆；后续主仓库状态不再包含该目录，因此它没有进入本轮修改或提交范围。

主仓库完成了：

```text
git fetch --unshallow upstream
git switch -c fix/windows-baseline-readiness
```

历史补全成功，`git rev-parse --is-shallow-repository` 返回 `false`。分支创建前，
原有 Phase 0/1 报告先通过 stash 临时移出，分支创建后再恢复；因此修复没有直接
发生在 `main` 上。

## 远程判定

远程协议实际为 SSH，而不是指令中“优先”的 HTTPS。关键安全关系已经满足：

```text
origin   → 用户个人 Fork
upstream → 原作者仓库
```

SSH 协议本身不降低 Fork 隔离性。本轮已通过实际 push 验证 Fork 可写：

```text
7ec7237..04e6529  fix/windows-baseline-readiness -> fix/windows-baseline-readiness
```

## 认证状态说明

- 已确认事实：用户终端成功创建 Fork 并查询到登录用户 `mit-mary`。
- 已确认事实：Codex 隔离进程随后带代理运行 `gh auth status`/`gh api` 得到 HTTP 401。
- 合理推测：两个进程看到的临时环境凭据或凭据存储上下文不同。
- 暂无法验证：Codex 进程为何不能复用用户终端当时的 GitHub CLI 认证。

该差异没有影响公开仓库 fetch，也没有影响 SSH push。CLI 认证差异的根因仍暂时无法
验证，但它不再阻塞 Phase 1.5。

## Git 警告

Git 仍提示无权读取用户级 ignore 文件：

```text
C:\Users\SSS\.config\git\ignore
```

本轮 `git status`、分支、历史和测试未因此失败。

## 结论

Fork、远程隔离、完整历史和独立分支均已就绪。两个代码提交已经推送到个人 Fork：

- `5b4782fca28ff2b3e153275626bb2f9e846e8d87`：Windows Doctor/凭据修复；
- `04e652978f76c4af2d85391c37703a13445f9ede`：确定性字体合同。

Codex 执行审批器不能写 `.git` 的限制由用户终端完成提交规避；实际 Git 提交和远端
SSH push 均成功。
