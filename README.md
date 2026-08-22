# 真实标签 Flask MVP

基于 PRD 实现的 Flask + Jinja2 多页面服务端渲染应用。没有 React/Vue、前端路由、Hash 路由或单一入口 HTML；每个页面由独立 Flask 路由渲染。

## Hackathon release candidate (INT-001)

Judges should use the integrated evidence from
`songconmaisaix31-design/trk-integration-int-001`, not the isolated worker
screenshots or QA-stage assembly notes:

- [Final claims ledger](docs/qa/hackathon/integration/FINAL_CLAIMS.md)
- [Final gate receipt](docs/qa/hackathon/integration/FINAL_GATE_RECEIPT.md)
- [Final visual evidence](docs/qa/hackathon/integration/FINAL_VISUAL_EVIDENCE.md)
- [Fresh integrated screenshots](docs/qa/hackathon/integration/screenshots/)

The candidate keeps four evidence classes separate: **Public Live** means a
bounded credential-free public response passed the frozen mapper and does not
prove account ownership; **Fixture** means deterministic synthetic demo data;
**Unavailable** means the source is intentionally disabled for P0; and
**Roadmap** means it is not implemented. The public demo below is deployment
evidence only; it is not evidence of an official third-party API, production
readiness, real merchant integration, users, revenue, or match-quality results.

## Public hackathon demo

- Demo: <https://realtags.davidwang.space>
- Evidence: [public demo deployment receipt](docs/qa/hackathon/integration/PUBLIC_DEMO_DEPLOYMENT_RECEIPT.md)
- Fast path: click **进入预置演示账号**, then open **我的标签**, **连接数据源**,
  **匿名匹配**, **对话**, and **饭局**.

This deployment uses synthetic demo data and function-local SQLite storage. It
can reset between instances or deployments and is not a persistent production
service. The existing blog, `/tags/`, and `tags.davidwang.space` are hosted
separately and were not changed.

## 运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

打开 `http://127.0.0.1:5000`。本地默认启用 `DEMO_MODE=1`，可点击“进入预置演示账号”，或使用 `demo@realtags.local` / `demo-password`；审核后台位于 `/admin/login`，演示管理员为 `admin@realtags.local` / `admin-password`。真实注册账户与演示账户使用完全隔离的候选池，不会匹配到无人回复的演示账号。

部署真实环境时显式关闭演示数据并更换密钥：

```powershell
$env:DEMO_MODE="0"
$env:FLASK_SECRET_KEY="请替换为生产随机密钥"
```

真实模式不会创建默认管理员。首次部署请在同一环境中交互式执行 `flask --app run.py create-admin`，密码输入会隐藏且要求二次确认。

正式部署应使用独立的新生产数据库；`DEMO_MODE=0` 不会删除旧库里已经存在的演示饭局。历史真实/演示跨池会话会自动转为只读，但旧演示活动数据若不应保留，请不要复用开发演示数据库。

`python run.py` 仅用于本机开发，且现在默认关闭调试器。公网部署必须使用平台提供的生产级 WSGI 服务器与 HTTPS 反向代理，禁止暴露 Flask 开发服务器或调试器。

## 已实现的 MVP 后端

- SQLite 持久化：用户、第三方连接、带来源与可见度的标签、活动、成员、会话、消息、权益、举报和拉黑。
- `DataSourceAdapter` 抽象及 Duolingo / Keep mock 适配器：模拟 OAuth 授权、标准化标签返回和稳定错误码。
- 服务端匹配：首页进入准备页，经过三阶段计算过场后只返回一个匿名结果；真实/演示候选池隔离，开启会话必须携带当前匹配令牌；支持取消、换一位、旧尝试失效与无 JavaScript 降级。硬性过滤、权重、相似度和展示分均留在服务端。
- 匿名一对一聊天：同一用户对只建立一条持久化会话，双方登录后均可查看并互发消息；L0–L4 渐进解锁、按任务类型区分的服务端系统卡、带专属视觉图的任务工具台、可滚动固定消息区、原生举报/拉黑弹窗与无 JavaScript 回退。拉黑后双方只读，非成员不能查看、发言或举报该会话。
- 3–10 人饭局：真实餐厅 POI 白名单、按需浏览器定位、附近半径与距离排序、匿名报名审核、成团/取消状态机、临时群聊、商家权益与手动核销；精确位置不写账户、session 或数据库。
- 独立管理员账户与审核台：只读查看/搜索注册账户；用户饭局先进入 `pending_review`，审核通过后才公开；举报可处理/驳回，所有决定记录管理员、时间、备注与审计日志。

## 定时任务

开发环境每个请求都会检查截止时间，保证演示可用。生产环境还必须按固定周期执行：

```powershell
flask --app run.py process-events
```

将该命令配置为至少每 5 分钟运行一次，才能在没有访问流量时也自动成团、取消、结束和归档活动。

## 验证

炫酷的终端验证控制台：

```powershell
.\harness.cmd
```

它会依次完成运行时预检、语法检查、核心 SSR 测试和完整 HTTP workflow harness。可用 `.\harness.cmd flow --verbose` 只查看完整产品链路；直接执行 `python tools/harness_cli.py` 也完全等价。

直接运行测试：

```powershell
python -m unittest discover -s tests -v
```

完整流程 harness（临时数据库、真实 HTTP 表单链路）可单独执行：

```powershell
python -m unittest discover -s tests -p "test_e2e_harness.py" -v
```

详见 [前端交接文档](docs/FRONTEND_HANDOFF.md)、[Harness Engineering 验证说明](docs/HARNESS_ENGINEERING.md) 和 [TagPulse CLI 说明](docs/HARNESS_CLI.md)。
