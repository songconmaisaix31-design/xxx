# Harness Engineering：完整流程验证

## 目标

`tests/test_e2e_harness.py` 是项目的端到端验证 harness。它不使用真实浏览器、外部 API 或生产数据库；每个测试都创建一份临时 SQLite 数据库，并通过 Flask `test_client()` 发起真实 HTTP GET/POST 请求。因此它能验证路由、服务端渲染、登录态、表单解析、302 跳转、权限校验和数据库状态，而不是只测单个 Python 函数。

## 执行命令

```powershell
python -m unittest discover -s tests -p "test_e2e_harness.py" -v
```

完整回归（核心单元检查 + harness）使用：

```powershell
python -m unittest discover -s tests -v
node --test tests/match_flow.test.mjs
python -m compileall -q app tests
flask --app run.py process-events
```

测试成功时不写入 `instance/realtags.sqlite3`，也不依赖之前运行过的页面数据。

## 覆盖流程

| Harness 场景 | 从哪里开始 | 验证到哪里 | 关键断言 |
| --- | --- | --- | --- |
| 注册、授权、标签 | 访客首页 → 注册 | Duolingo / Keep mock 授权 → 我的标签 | 正确 302、10+ 来源标签、全部 `self_only` |
| 匿名匹配与聊天 | Demo 用户登录 → 首页双入口 → 待匹配 → 三阶段计算 → 单个结果 | 双向文字、骰子/任务卡、L0→L4、举报/拉黑 | searching HTML 无候选资料；结果由服务端确认；L0 不泄露；拉黑阻止新会话 |
| 真实账户匹配与对话 | `DEMO_MODE=False` → 两个全新注册账户 | 有效 attempt → 唯一 direct 会话 → 双向持久化消息 | 不播种演示账户；双方候选池互相可见；伪造 attempt 失败；双方列表/详情看到同一会话；非成员举报失败；拉黑后消息不落库 |
| C 端饭局 | 创建饭局 → 平台待审 | 管理员通过 → 匿名申请审核 → 成团 → 群聊破冰 | 待审活动不向他人暴露；管理员真实登录并留审计记录；发起人审核页无申请者身份；群聊只显示匿名成员 |
| B 端饭局 | 商家预置活动 → 报名 | 截止结算 → 成团群聊 → 发券 → 核销 | 状态 `recruiting → formed`；券 `issued → redeemed` |
| 失败分支 | 人数不足的活动 | 截止结算 | 状态 `recruiting → cancelled` |

专项检查另外覆盖：管理员 session 与普通用户隔离、活动审核拒绝原因、举报重复处理保护、旧数据库迁移、系统卡片 kind 白名单、归档群聊只读，以及定位拒绝/非法坐标/半径/距离排序/无位置降级。默认 TagPulse 全量命令会运行这些检查，不需要外部地图或定位服务。

匹配流程另有两层竞态验证：HTTP 测试确认 `attempt_id`、取消、换一位和旧页面失效；`tests/match_flow.test.mjs` 用 Node 内置测试确认完整时序、减弱动画、取消后回调失效与新 generation 独占完成。两层均不引入浏览器框架或第三方依赖。

## 受控时间设计

活动状态应由定时任务驱动，测试不能真实等待数小时。Harness 在完成 HTTP 报名后，以明确的、晚于 `signup_deadline` 的测试时间调用既有的 `refresh_event_statuses(now=...)`。这不是对业务逻辑的绕过：生产定时任务 `flask --app run.py process-events` 调用的正是同一个函数。它把“等待两个小时”的不可控条件变成可重复且毫秒级的验证。

## 失败定位

- **HTTP 200/302 失败**：检查对应的 `app/routes/` 路由或 Jinja 模板变量。
- **匿名泄露断言失败**：优先检查 `app/services/chat.py:get_conversation` 和 `app/services/events.py:get_event`，不要在模板层简单隐藏字段。
- **匹配状态竞争失败**：检查 `app/routes/matches.py` 中 session `match_flow` 的 `phase`、`attempt_id` 与候选重新校验；不要让 JS 决定结果。
- **成团/取消失败**：检查 `app/services/events.py:refresh_event_statuses` 与报名状态是否为 `approved`。
- **平台审核失败**：检查 `app/services/moderation.py` 的状态转换、管理员 session 与 `admin_audit_logs`；不要直接把待审活动改成公开状态。
- **附近排序失败**：检查 POI 白名单坐标、`parse_nearby_query` 和 `haversine_km`；精确用户坐标不应持久化。
- **券失败**：检查商家活动 `merchant_benefit`、`event_coupons` 和 `_form_group`。
- **临时 DB 清理失败（Windows）**：确认新连接通过 Flask app context 创建；`close_db` 必须在初始化前注册。

## 新功能接入规则

新增 P0 流程时，先判断是否能把它插进以上真实 HTTP 场景；能插入就扩展 harness，而不是只加服务函数的单元测试。每一个会影响隐私、成团、支付/权益或权限的分支，至少要有一个可重复的终态断言，并且测试不能依赖真实时间、网络或已有数据库。
