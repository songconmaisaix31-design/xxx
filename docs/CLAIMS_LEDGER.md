# Claims Ledger

本文件是路演、README 和评审问答的真实性边界。`Implemented` 表示仓库中存在并由测试或运行时检查覆盖；`Live evidence` 是当前时间点的外部请求证据，不代表 SLA；`Fixture` 只证明产品工作流；`Not implemented` 不得包装成已完成能力。

## Implemented

| Claim | Evidence | Boundary |
| --- | --- | --- |
| 注册、8 类自填信号和双向匹配偏好 | `tests/test_core.py`, `tests/test_prd_acceptance.py` | 不包含实名/KYC |
| 33 个预置信号，来源与模式可见 | `app/services/adapters.py`, profile runtime QA | 其中 22 个行为信号为 Fixture，3 个为 Derived |
| 服务端硬过滤、相似度和展示分 | `app/services/matching.py`, matching tests | 不宣称机器学习或线上效果指标 |
| 单结果匿名匹配与最小披露 | route/template tests and desktop runtime QA | 不传候选完整资料或原始权重 |
| L0–L4、协作任务、共同活跃日与双向发言门槛 | `app/services/chat.py`, chat tests | Demo 快捷推进单独标记，不能当作自然互动证据 |
| 公开场所饭局、审核、成团/取消、群聊和归档 | event workflow tests | 地点和商家均为 Fixture |
| 一桌一码、时间/门店约束和 Demo 核销 | event/coupon tests | 未接真实 POS、支付或商家后台 |
| CSRF、生产密钥门槛、外部请求边界和无原始响应落库 | security/adapter tests | 仍是黑客松 Demo，不等同于完成生产安全审计 |
| PRD 视觉 token、硬投影、触控和 reduced-motion | CSS contract tests and desktop runtime QA | 本次自动化环境未完成移动端运行时截图 |

## Live evidence

| Capability | Evidence | Caveat |
| --- | --- | --- |
| Duolingo public profile | 2026-08-23 使用公开用户名 `duo` 完成只读 smoke，规范化为 6 个 Live 标签；adapter 单测覆盖成功、失败与边界 | 公开端点不是项目控制的稳定授权 API，随时可能变更、限流或不可用；CI 不依赖该端点 |

## Fixture-only capabilities

| Capability | What is demonstrated | What is not claimed |
| --- | --- | --- |
| Keep | 11 个确定性运动标签和匹配参与 | Keep 登录、授权或真实运动记录 |
| Venue / POI | 公开场所白名单、距离计算和创建约束 | 实时地图、库存或餐厅真实性认证 |
| SMS verification | 发起饭局前的验证门槛和明确 Demo 验证 | 短信发送、运营商交付或真实手机号所有权 |
| Merchant benefits | 商家标识、成团发券、一桌一码 | 已签约商户或真实营销预算 |
| POS redemption | 时间、门店、状态校验和显式 Demo 核销 | 真实收银系统、支付或财务结算 |

## Not implemented

- Keep production API, OAuth or credential storage.
- Production SMS, maps/POI, merchant identity, POS, payment or notification integrations.
- WebSocket/SSE real-time chat, push notifications and offline delivery.
- Production deployment, observability, abuse/rate-limit operations, backups or disaster recovery.
- KYC, legal/compliance approval, security penetration test or external privacy audit.
- Official user growth, retention, matching quality, conversion, latency or revenue metrics.

## Allowed wording

- “Duolingo 支持公开资料 Live 同步；Keep 当前使用 Fixture。”
- “Demo 跑通了从行为标签到匿名匹配、关系解锁和公开饭局的完整工作流。”
- “餐厅、短信、商家和 POS 是明确标记的 Fixture，后续可替换为生产 adapter。”

## Disallowed wording

- “已接入 Keep / 商家 / POS / 短信生产系统。”
- “所有标签都是真实认证数据。”
- “已验证真实餐厅”或“已有签约商户”。
- “已上线”“生产可用”“通过安全审计”或任何无证据的商业/用户指标。
