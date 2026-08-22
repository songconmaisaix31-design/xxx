# MEMORY.md

## 项目状态

- 2026-08-23：从远端 `main@648caa40ccd880f331b050bb27cfe80c361b0328` 创建隔离工作区和 `competition/prd-hackathon` 分支。
- 原始目录 `C:\Users\DW\orca\xxx` 保持只读；它包含另一套 API 核验材料和未跟踪文件，不用于本次实现。
- 当前目标是在不伪造能力的前提下完成 PRD P0，形成可稳定演示、可解释、可复核的黑客松候选版本。

## 长期决策

- 产品事实来源是 `产品需求文档_PRD.md`；PRD 第 5 章是视觉事实来源。
- 保留 Flask + Jinja2 + SQLite 的朴素架构，修复根因，不为黑客松重写前端或引入不必要框架。
- 外部接口依据 `C:\Users\DW\orca\xxx\API_INTERFACE_CATALOG.md` 的 2026-08-22 核验结果筛选，但该文件不复制进项目，也不读取其同目录下任何凭据。
- Duolingo public profile 与 GitHub REST 可作为无需凭据的 Live 候选；Keep 登录/统计、Steam、WeRead、GitHub GraphQL 均不得宣称已接通。
- Fixture、Live、待验证能力必须在 UI、数据、测试和提交材料中分开；Fixture 不等于已验证真实数据。
- 不保存第三方原始响应或 secret，只持久化最小规范化标签与来源证明。

## 验证与发布

- 最终必须运行 Python tests、Node tests、compileall、完整 harness 和 `git diff --check`。
- 只提交和推送 `competition/prd-hackathon`；不得修改或推送 `main`。
- README、演示证据和 claims 必须区分实现事实、Fixture 证据、Live 证据、待验证项与路线图。

## 2026-08-23 黑客松实现结果

- Duolingo 使用无需凭据的公开 Profile endpoint 作为可选 Live 数据源；固定 HTTPS、用户名白名单、5 秒超时和 256 KiB 响应上限，并且只保存规范化标签。Keep、场地、短信验证、商家和 POS 继续使用明确标记的 Fixture/Demo 流程。
- Demo 提供 22 条确定性的 Fixture 行为标签、8 条自填标签和 3 条透明派生标签。派生标签始终保持未认证，不能冒充第三方证据。
- 已补齐双向年龄/性别过滤、标签相似度、手机号门槛、同桌性别策略、活动成团/归档/核销约束，以及需要双方完成协作任务的渐进解锁。
- PRD 最终会议决议优先于早期阶段表：`self_only` 行为标签在 L0–L4 均不得返回给匹配对象；L3 只展示本人填写的兴趣。
- 已加入 Session 绑定 CSRF、生产密钥 fail-closed、生产环境 Demo 路由禁用和敏感字段最小化。当前仍是黑客松 Demo，不代表生产身份核验、支付、商家或合规能力已完成。
- PRD 第 5 章视觉 token 已落入独立契约层；桌面 Edge 对首页、标签、连接、匹配、会话和活动主流程做过真实浏览器检查。移动端真实截图因浏览器自动化运行时不可用未完成，验收矩阵将该项保持为 `PARTIAL`。
- 最终本地门禁：48/48 Python tests、4/4 Node tests、compileall、`uv lock --check`、`uv sync --locked` 和扩展后的 Harness 6/6 均通过。
- 实现期间远端 `main` 推进到 `89e80a9eb3b21cd22441be218302f429c8d78471`（文档提交）；发布分支已 rebase 吸收，并把基于旧代码的生产缺口文档改为当前分支的事实与路线图。
