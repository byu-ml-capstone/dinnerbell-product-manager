# §9 GitHub links：前端测试指南

本次功能范围是 §9（GH-1 至 GH-8、GH-R1 至 GH-R4），不含 §10 AI 功能。

## 打开本地版本

- 地址：<http://localhost:8082>
- Demo 用户：`taylor`，密码：`devpassword`
- 本版本使用独立 Docker Compose project `dinnerbell-eason` 和自己的数据库卷
- `8081` 是之前的本地环境，测试本次修改请使用 `8082`

另有纯前端 PR 状态演示：<http://127.0.0.1:8083>。同样使用 `taylor` / `devpassword` 登录，
选择 **GitHub links UI demo (MOCK)** → **Planning** → **Backlog**，打开五个预置 Story，分别查看 open、merged、closed、
branch 存在但无 PR、branch 不存在。全部 GitHub 数据来自 fakes；该页面不能证明真实 GitHub 联调完成。
这个演示使用另一个独立数据库，测试入口只挂载到演示容器，不包含在生产后端镜像里。
请保持正常预览用 `localhost:8082`、mock 用 `127.0.0.1:8083`，避免两套数据库共用登录 cookie。

需要重新启动时，在项目根目录运行：

```powershell
docker compose --env-file .env.example -p dinnerbell-eason -f docker-compose.yaml -f compose.github-local.yaml up -d --build
```

启动 mock 演示（先完成上面的构建）：

```powershell
docker compose --env-file .env.example -p dinnerbell-eason-ui-demo -f docker-compose.yaml -f compose.github-ui-demo.yaml up -d --no-build
```

停止但保留测试数据：

```powershell
docker compose --env-file .env.example -p dinnerbell-eason -f docker-compose.yaml -f compose.github-local.yaml stop
```

## 只用前端测试

建议创建一个测试 Project，或在此独立环境的 DinnerBell Demo 内创建测试 Story。

| 测什么 | 在哪里操作 | 预期结果 |
|---|---|---|
| 保存 repository | Settings → GitHub repository，输入 `https://github.com/byu-ml-capstone/dinnerbell-product-manager.git/` → Save | 输入框保存后显示去掉 `.git/` 的地址；项目顶部出现 repository 链接 |
| 拒绝其他平台 | 同处输入 `https://gitlab.com/x/y` → Save | 显示校验错误，原来的已保存地址保持不变 |
| 清空 repository | 同处清空 → Save | 项目顶部链接消失；Story 仍保留 branch 名称，名称不再可点击 |
| 新建时关联 branch | Board → + Story；标题 `Add Login Page`，Branch 输入 `eason/login-page` → Create story | 详情显示 branch 名称和链接；卡片有 branch 图标 |
| 粘贴完整 branch URL | Story 详情 → Edit → Branch，输入该 Project 仓库下的 `/tree/eason/login-page` URL → Save | 保存为 `eason/login-page`，不保存整段 URL |
| 拒绝跨仓库 URL | 同处输入 `https://github.com/someone/else/tree/main` → Save | 显示 “Branch URL is for a different repository”，不覆盖原值 |
| branch 非法字符 | 同处输入 `bad..name` 或 `has space` → Save | 显示校验错误 |
| 清空 branch | Edit → Branch 清空 → Save | 显示 “No branch linked.”；卡片图标消失 |
| 未设置 repository | 清空 Project 的 repository，再将 branch 设为 `eason/local-work` | 可以保存；显示普通文本；提示先设置 repository 才能查询 PR |
| 未设 repository 时粘贴 URL | 同上但输入完整 GitHub branch URL | 提示先在 Settings 设置 repository，或者只输入 branch 名称 |
| 未分配时的建议 | 新建 `Add Login Page`，Assignee 保持 Unassigned，当前登录 taylor | Suggested 为 `taylor/add-login-page` |
| 分配后的建议 | Edit → Assignee 选 Jordan Dev → Save | Suggested 变成 `jordan/add-login-page` |
| Copy | Story 详情 → Branch → Copy，再粘贴到 Branch 输入框 | 粘贴内容等于建议名称；按钮短暂显示 Copied |
| Use this | 同处点击 Use this | branch 保存为建议名称；关闭重开后仍存在；不会创建真实 Git branch |
| 无有效 slug | 新建标题 `!!!` | 显示手动填写提示，不出现空建议的 Copy/Use this |
| Subtask 独立 branch | 父 Story → Subtasks 输入标题 → Add；点击该 Subtask → Edit → Branch | 可以保存自己的 branch；父 Story 的 branch 不变 |
| Board 与 Planning | 查看有关联 branch 的卡片，悬停 branch 图标 | 提示 branch 名称；卡片不查询实时 PR 状态 |
| 切换 Story | 连续打开 branch 不同的两个 Story | 详情链接与状态对应当前 Story，不沿用前一个 Story 的结果 |
| 修改 repository | Settings 修改 repository → Save → 回到 Story 详情 | branch 链接使用新仓库，PR 状态重新查询；不能沿用旧仓库状态 |
| 长名称与窄窗口 | 保存较长但合法的 branch，缩窄浏览器窗口 | 链接与按钮仍可读、可操作 |

## PR 状态测试的条件

当前本地预览没有配置真实 `GITHUB_TOKEN` 时，有 branch 且有 repository 的详情应显示
**GitHub token not configured**，其余 Story 编辑、Copy、Use this 仍可用。

真实 open/merged/closed 查询需要后端配置能读取该仓库的 read-only GitHub token。
只在前端 Settings 粘贴 repository 不会授权后端访问 GitHub。

配置后，从前端打开对应 Story，核对以下状态：

| 仓库中的实际情况 | 详情预期显示 |
|---|---|
| branch 有 open PR | 可点击的 `PR #编号 · open` |
| PR 已合并，即使 branch 已删除 | 可点击的 `PR #编号 · merged` |
| PR 关闭但未合并 | 可点击的 `PR #编号 · closed` |
| branch 存在但没有 PR | `Branch exists, no PR` |
| branch 不存在且没有 PR | `Branch not found` |

状态缓存 5 分钟；改变 GitHub 上的 PR 后，等待缓存过期，再关闭重开 Story。
每个 Story 只关联一个 branch；有多个开发 branch 时，可以拆成分别关联 branch 的 Subtask。

## 部署到 Coolify

仓库 `.github/workflows/ci.yml` 当前定义：

1. 功能代码通过 PR 合入 GitHub `staging`
2. `test` job 通过后，`deploy-staging` 调用 staging webhook
3. 团队验证 staging 后，通过 PR 合入 GitHub `main`
4. `test` job 通过后，`deploy-prod` 调用生产 webhook
5. Coolify 根据对应分支拉取并构建运行

这要求 GitHub Actions 的 `COOLIFY_API_TOKEN`、`COOLIFY_DEPLOY_WEBHOOK_STAGING`、
`COOLIFY_DEPLOY_WEBHOOK_PROD` 已配置，且 Coolify 应用跟踪正确分支、可访问仓库。
本地 merge 而不 push 不触发部署；只改 Markdown 等被 paths-ignore 排除的文件也不触发这个 workflow。
GitHub 的 deploy job 成功只证明 webhook 调用成功，还应在 Coolify Deployment 日志确认构建完成，
并打开线上页面验证。此次没有修改、触发或核验线上 Coolify 配置。

本次无数据库 schema 修改，无新增 migration；本地预览 override 不用于 Coolify。
原规格中的 Proposed 状态仍保留，完成代码与测试不等于团队已经批准这些提案。

## 实现与验证记录

| GH 编号 | 文件 | 本次处理 |
|---|---|---|
| GH-4、GH-6 | `backend/app/services/github_links.py` | repository 512 字符上限；无 repository 的 branch URL 提示；空 slug 不生成无效建议 |
| GH-5、GH-8 | `backend/app/services/github_status.py`、`backend/app/routers/github.py` | 查询、最新 PR 选择和 5 分钟缓存放入 service；Router 先验证登录和成员资格 |
| GH-5、GH-8 | `backend/app/services/github_client.py` | 明确按创建时间查询最新 PR；网络、HTTP、重定向、非法 JSON 统一报告 GitHub 错误 |
| GH-6、GH-8 | `frontend/src/features/stories/BranchSection.jsx` | repository 链接变化后重查；空 slug 手动输入提示；Use this 防重复提交；说明不会创建真实 branch |
| GH-4、GH-7 | `frontend/src/features/settings/SettingsView.jsx`、`frontend/src/styles/panels.css` | 保存后显示正规化地址；长 branch 和建议名换行 |
| GH-4 至 GH-8 | `backend/tests/test_projects.py`、`backend/tests/test_github_links.py`、`backend/tests/conftest.py` | 边界、清除、Subtask、权限、缓存、PR 状态、固定 API host 和错误回归 |
| 本地验证 | 两个 `compose.github-*.yaml`、`backend/tests/github_ui_preview.py` | 独立数据库的正常预览和测试专用 mock PR 页面，不修改生产 Compose |
| 需求记录 | `SPRINT_PLANNER_SPEC.md` §9 | 修正过时起点和宽泛 Goal；记录 Eason 确认的边界；保留 Proposed 状态 |

2026-10-23 验证：完整后端 **140 passed**；隔离临时 Postgres 上 `alembic check` 无差异；
Docker 中 `npm run build` 成功。临时回归数据库已清理。

实际前端操作覆盖：repository 正规化/拒绝/清空、branch URL/跨仓库/非法名称/清空、
无 repository 的 branch 保存、负责人建议、Copy 后真实粘贴、Use this、空 slug 提示、
Subtask 独立 branch、Planning 图标、两个页面之间 repository 更新后 Refresh、长 branch 换行，
以及 mock open/merged/closed/两种无 PR 状态和 Story 切换。

未完成真实 GitHub token 联调，未核验线上 Coolify secrets/应用配置，未 Commit/Push/PR/Merge/部署。
