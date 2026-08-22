# 真实标签 — Hackathon Demo

一个以“先验证同频，再交换身份”为核心的 Flask + Jinja2 社交 Demo。产品把第三方行为数据转换成最小化标签，用于匿名匹配、渐进式关系解锁和公开场所饭局；每条外部能力都明确标记为 `Live`、`Fixture`、`Derived` 或 `Self`。

> 当前交付适合本地演示、产品评审和后续开发，不代表已经具备公开生产所需的身份核验、合规、实时通信、支付或规模化运维能力。

## Hosted hackathon demo

访问 [https://tags.davidwang.space](https://tags.davidwang.space)，点击“进入预置演示账号”即可体验完整流程。

这是部署在 Vercel Function 上的黑客松 Demo。SQLite 状态使用临时存储，冷启动或并发实例可能导致操作结果重置；请勿输入敏感信息，也不要把该地址视为生产级持久化服务。部署证据和回滚边界见 [Deployment evidence](docs/DEPLOYMENT_EVIDENCE.md)。

## Quick start

项目使用锁定的 Python 3.12 环境：

```powershell
uv sync --locked --python 3.12
uv run python run.py
```

打开 `http://127.0.0.1:5000`，点击“进入预置演示账号”。也可以登录：

- User: `demo@realtags.local` / `demo-password`
- Admin: `admin@realtags.local` / `admin-password`

`requirements.txt` 仅保留为不使用 uv 时的兼容入口。`python run.py` 只适用于本机演示，默认关闭 debugger。

## Data truth

| Capability | Current mode | What the demo proves |
| --- | --- | --- |
| Duolingo public profile | Live or Fixture | Live 仅接收公开用户名，经固定 HTTPS 端点读取一次并立即规范化；失败会明确报错，不伪装成功 |
| Keep activity | Fixture | 11 个确定性运动标签，清楚标记为演示样例 |
| Derived signals | Derived | 只从规范化标签推导自律程度、活跃时段和目标一致性，并始终保持未认证 |
| User profile | Self | 8 类本人填写信号 |
| Venue / merchant / SMS / coupon POS | Fixture | 跑通安全门槛、审核、成团、发券与核销工作流，不声称已接生产服务 |

预置账号共有 33 个信号：11 个 Duolingo Fixture、11 个 Keep Fixture、3 个 Derived 和 8 个 Self。Live 模式不保存第三方原始响应、密码或 token，只持久化最小规范化标签和来源状态。

## Implemented product loop

- 双向年龄与性别偏好先做硬过滤，再计算集合、数值、等级和活跃时段相似度。
- 一次只返回一个匿名结果；页面不渲染照片、真实姓名、年龄、城市、职业、原始标签、原始分或算法权重。
- 匿名会话支持文字、骰子、任务卡、协作解锁、举报和拉黑；L0–L4 由双向发言、共同活跃日和已解锁点共同推进。
- 3–10 人公开场所饭局支持请求级定位、审核、报名、性别限制、成团/取消、临时群聊、权益和明确标记的 Demo 核销。
- 活动结束 7 天后归档，会话转为只读；生产模式需定时执行 `flask --app run.py process-events`。
- 管理后台提供活动与举报审核，决策写入审计日志。

## Security defaults

- 所有 POST 请求默认校验 session CSRF token。
- `DEMO_MODE=0` 时必须显式提供 `FLASK_SECRET_KEY`，否则应用拒绝启动。
- 外部 Live 请求使用固定 HTTPS 主机、输入白名单、5 秒超时、256 KiB 响应上限和严格类型收窄。
- 精确定位仅用于当前请求筛选，不写入账户、session 或数据库。
- 真实部署必须使用全新数据库、生产级 WSGI 服务与 HTTPS；首次管理员通过 `flask --app run.py create-admin` 交互创建。

## Verification

```powershell
uv lock --check
uv run python -m unittest discover -s tests -v
node --test tests/match_flow.test.mjs
uv run python -m compileall -q app tests tools run.py
uv run python tools/harness_cli.py --no-color run
```

CI 使用同一份 `uv.lock` 和 Python 3.12 运行 Python tests、Node tests 与 compileall。

## Delivery documents

- [Hackathon demo script](docs/HACKATHON_DEMO.md)
- [Claims ledger](docs/CLAIMS_LEDGER.md)
- [Implementation spec](docs/HACKATHON_IMPLEMENTATION_SPEC.md)
- [API contract](docs/API_CONTRACT.md)
- [PRD acceptance matrix](docs/PRD_ACCEPTANCE_MATRIX.md)
- [Frontend handoff](docs/FRONTEND_HANDOFF.md)
- [Deployment specification](docs/DEPLOYMENT_SPEC.md)
- [Deployment evidence](docs/DEPLOYMENT_EVIDENCE.md)
- [Production gaps and roadmap](docs/PRODUCTION_GAPS_AND_ROADMAP.md)
