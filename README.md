# 真实标签 Flask MVP

基于 PRD 实现的 Flask + Jinja2 多页面服务端渲染应用。没有 React/Vue、前端路由、Hash 路由或单一入口 HTML；每个页面由独立 Flask 路由渲染。

## 运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

打开 `http://127.0.0.1:5000`，点击“进入预置演示账号”；或用 `demo@realtags.local` / `demo-password` 登录。审核后台位于 `/admin/login`，演示管理员为 `admin@realtags.local` / `admin-password`。

## 已实现的 MVP 后端

- SQLite 持久化：用户、第三方连接、带来源与可见度的标签、活动、成员、会话、消息、权益、举报和拉黑。
- `DataSourceAdapter` 抽象及 Duolingo / Keep mock 适配器：模拟 OAuth 授权、标准化标签返回和稳定错误码。
- 服务端匹配：首页进入准备页，经过三阶段计算过场后只返回一个匿名结果；支持取消、换一位、旧尝试失效与无 JavaScript 降级。硬性过滤、权重、相似度和展示分均留在服务端。
- 匿名一对一聊天：L0–L4 渐进解锁、按任务类型区分的服务端系统卡、带专属视觉图的任务工具台、可滚动固定消息区、原生举报/拉黑弹窗与无 JavaScript 回退。
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
