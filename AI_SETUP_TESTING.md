# §10 AI setup and frontend testing — eason

这份说明对应 `eason` 分支。Analysis 和 Sprint review 都使用 `gpt-6-luna`，通过后端调用 OpenAI；浏览器不会接收 API key。

## 1. API key 怎么填

打开项目**根目录**的 `.env`，找到这一行，把等号后面换成自己的 key，然后 Ctrl+S：

```dotenv
OPENAI_API_KEY=在这里填写自己的实际key
```

不要填写示例文字，不要把 key 发到聊天、截图或 Git。文件已被 `.gitignore` 忽略。Docker Compose 使用根目录 `.env`；直接从 `backend/` 启动 Python 时才使用 `backend/.env`。

当前模型配置如下，不需要再填两个独立的 OpenAI key：

```dotenv
ANALYSIS_LLM_BASE_URL=https://api.openai.com/v1
ANALYSIS_LLM_MODEL=gpt-6-luna
ANALYSIS_LLM_REASONING_EFFORT=medium
ANALYSIS_LLM_MAX_OUTPUT_TOKENS=4096
REVIEW_LLM_BASE_URL=https://api.openai.com/v1
REVIEW_LLM_MODEL=gpt-6-luna
REVIEW_LLM_REASONING_EFFORT=high
REVIEW_LLM_MAX_OUTPUT_TOKENS=6000
```

改完 `.env` 后，在项目根目录执行以下命令，使运行中的后端重新读取设置：

```powershell
docker compose --env-file .env -p dinnerbell-eason -f docker-compose.yaml -f compose.github-local.yaml up -d --no-deps backend
```

如需从代码重新构建完整本地环境：

```powershell
docker compose --env-file .env -p dinnerbell-eason -f docker-compose.yaml -f compose.github-local.yaml up -d --build
```

`ANALYSIS_LLM_API_KEY` / `REVIEW_LLM_API_KEY` 可选，非空时优先于共享 key。改用自定义代理时必须配置对应的专用 key；共享 `OPENAI_API_KEY` 只会发给官方 `https://api.openai.com`。

## 2. 两个测试网址

| 页面 | 用途 | API 费用 |
|---|---|---|
| [真实接入：localhost:8082](http://localhost:8082/) | 使用你的 OpenAI key，`DinnerBell Demo` 项目 | 点击运行会产生实际 API 用量 |
| [界面演示：127.0.0.1:8083](http://127.0.0.1:8083/) | `AI sprint demo (MOCK)` 项目，预设 GitHub 和 AI 结果 | 无 OpenAI / GitHub 请求 |

两个环境都运行在本机 Docker，数据库互相独立。登录均为 `taylor` / `devpassword`。8083 必须用 `127.0.0.1`，避免与 localhost 的登录 cookie 混用。原来的 8081 环境不受影响。

启动 mock 环境使用下面的命令；它会显式清空 API 凭据，测试文件只读挂载，不进入生产镜像：

```powershell
docker compose --env-file .env.example -p dinnerbell-eason-ui-demo -f docker-compose.yaml -f compose.github-ui-demo.yaml up -d --no-build
```

## 3. 只用前端验收

选择项目 → **Board** → 顶部 **Selected sprint** 选 sprint → 向下滚动到 **AI for …**。

| 功能 | 点击 / 输入 | 应看到什么 |
|---|---|---|
| 生成进度报告 | **Analysis → Run analysis** | 运行状态变为 complete，显示 `gpt-6-luna` 和八段报告：Summary、Progress、Velocity、Estimated Completion、Accomplished、Remaining Work、Blockers and Risks、Suggested Next Steps |
| 补充背景 | Additional context 填团队中断、风险等，再运行 | 新建一份分析，旧记录仍在左侧历史列表 |
| 编辑最终报告 | **Edit and save as final** → 修改 → **Save final** | 显示 Final、保存人及时间；刷新页面后仍保留 |
| 重新生成 | 保存 Final 后再次 **Run analysis** | 自动显示新的 AI draft；点击旧历史仍能看到保存的 Final |
| 查看输入 | 展开 **Data sent to the AI** | 查看当次输入快照；数值来自后端计算 |
| 失败重试（mock） | Additional context 填 `simulate timeout` 再运行 | 显示失败原因及 **Retry**；点击 Retry 会创建新的成功分析，失败记录保留 |
| 切换 sprint | 顶部改选 `Next demo sprint`（mock） | AI 面板标题和历史切换，旧 sprint 的错误 / 报告不会串过去 |
| 查看代码评估（mock） | **Sprint review → Run sprint review** | 进度完成后有四行：Recipe search → Matches；Grocery list → Partial；Pantry tracking → No evidence；No linked code → No link |
| 查看证据 | 点击 Review 的故事行 | 展开说明、验收标准、文件路径 / 行号证据和是否有测试；链接固定到检查时的 commit |
| 未关联的工作 | 看 Review 表格下方 **Merged work not linked to a story** | 展示没有关联故事的已合并 PR；mock 链接与评估内容是演示数据 |
| Review 历史 | 再次运行后用 **Past reviews** 下拉框 | 可以查看过去结果；运行中禁止重复发起同一 sprint 的 Review |
| 建议性质 | 对照 Review 前后的 Board | AI 只给建议，不会修改故事状态、分数或负责人 |

关闭 sprint 会在已配置 Analysis 时自动生成一份分析。用新建的测试 sprint 验证：Planning → New sprint → 回 Board 选中 → Close；历史项显示 **On close**。关闭会冻结该 sprint 的统计，只在可丢弃测试 sprint 上操作。

## 4. 真实 GitHub Review 的额外配置

OpenAI key 足够运行 Analysis。真实 Review 还需要：

1. 根目录 `.env` 中的 `GITHUB_TOKEN`：对目标仓库具有 Contents、Pull requests、Metadata 的只读权限；私有组织可能需要管理员批准。
2. 前端 **Settings → GitHub repository** 填目标仓库 URL。
3. 在故事详情 **GitHub branch** 填实际 branch 名，或粘贴同仓库完整 `/tree/...` URL。项目可以不设仓库、只保存 branch；真正开始代码评估前需要设仓库。
4. 用本页命令重新加载 backend，然后从前端运行 Review。

没有 token 时会提示 `GitHub token not configured`。没有 branch 的故事得到 No link；无法读取或证据不足时会给 Can't tell / No evidence，不能当成代码已通过。

输出 token 上限包含 reasoning，是**每次请求**的限制；Review 会进行多次工具往返，现有限制为每次 Review 最多 30 个故事、每个故事最多 15 次工具调用。它不是总费用封顶。每次点击 Run 都可能产生新用量。

## 5. Coolify 上线

当前 `.github/workflows/ci.yml` 已定义：代码 push / merge 到 `main` → 后端测试及前端构建成功 → 用 webhook 触发生产 Coolify 部署。`staging` 同理部署测试环境；仅 Markdown / ignore 文件修改会被 workflow 忽略。

是否真的自动上线，还取决于 GitHub Secrets `COOLIFY_DEPLOY_WEBHOOK_PROD`、`COOLIFY_API_TOKEN` 是否有效，以及 Coolify 应用是否绑定正确仓库和 `main`。本次只验证了仓库中的配置，没有验证线上 Secrets 或 Coolify 后台。

首次部署本改动，需要在 Coolify 后端运行环境设置 `OPENAI_API_KEY`、以上两组模型配置和 `GITHUB_TOKEN`；本地 `.env` 不会随 merge 上传。线上不要使用两个本地 Compose override，也不要设置 `SEED_DEMO_DATA=true`。后续走团队既有 staging → main PR 流程，检查 GitHub Actions 和 Coolify 的部署结果；本次没有提交、push、merge 或触发线上部署。

## 6. 改动位置和验证边界

- `backend/app/config.py`：共享 key、模型、reasoning 和输出上限设置。
- `backend/app/services/llm.py`：Chat Completions / Responses SDK、工具往返、输出状态检查和脱敏错误提示。
- `backend/app/services/analysis.py`、`sprint_review.py`：后台任务保存可读的错误；`routers/analyses.py` 在配置检查前验证成员权限。
- `frontend/src/features/ai/`：切换 sprint 清理状态、新报告自动选中、Final 历史标记同步、显示 Review 模型。
- `.env.example`、`backend/.env.example`、`docker-compose.yaml`：可部署配置；密钥本身不进 Git。
- `backend/tests/test_llm.py`：用真实 OpenAI SDK + HTTP mock 检查请求、工具往返、结构化输出、错误和 key 优先级。
- `backend/tests/ai_ui_preview.py`、`compose.github-ui-demo.yaml`：独立无费用的前端验收环境。

2026-10-23 本地验证：后端 158 tests passed，`alembic check` 无模型差异，前端生产构建成功。真实 `gpt-6-luna` 文本请求成功，Responses 只读工具调用及结构化输出往返成功；8082 从前端生成的八段报告在 Docker 重启后仍可查看。8083 已操作验证保存 Final、历史保留、新草稿选中、超时 Retry、切换 sprint、四类 Review 结果及 commit 文件证据；两页 console 无 error。尚未配置真实 `GITHUB_TOKEN`，因此真实 GitHub Review 全链路待验证。mock 结果不代表模型对真实仓库的质量评估。
