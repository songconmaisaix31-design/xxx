# 真实标签 MVP：前端交接文档

> 当前事实来源依次为 `docs/API_CONTRACT.md`、`产品需求文档_PRD.md` 第 5 章和当前服务端实现。Fixture、Live、Derived 与 Self 必须在数据和 UI 中保持可区分。

## 1. 交接结论

本项目是传统多页面 Web 应用。前端接入应继续使用 Flask + Jinja2：后端通过路由取数后渲染完整 HTML，写操作使用普通 HTML `<form method="post">`，成功或失败后以 `flash` 消息和 302 跳转反馈。不要改造成 SPA，不要加入 React/Vue、前端路由、Hash 路由，也不要把页面收敛进一个 `index.html`。

当前交付已经完成一套可直接使用的响应式视觉系统与全部页面的语义化结构。后续前端工作应在现有设计令牌和组件类之上扩展，不应改变表单 `name`、HTTP 方法、路由或后端传入变量。所有用户文本都按 Jinja 默认转义输出，禁止把文本内容用 `|safe` 直接插入 DOM。

### PRD 视觉收口说明

当前界面使用 PRD 第 5 章定义的玩具箱式新粗野主义，完整规范见根目录 `brand-spec.md`。项目仍是传统 Flask 多页面应用：视觉层使用分层 CSS 和无依赖渐进增强脚本，所有核心跳转继续由普通链接完成，所有写操作继续由服务端表单完成。

| 层 | 文件 | 责任 |
| --- | --- | --- |
| 兼容基线 | `app/static/css/app.css` | 原有布局与分层样式失效时的回退 |
| 视觉基础 | `app/static/css/brutalist-foundation.css` | 令牌、字体、页面外壳、控件、基础动效 |
| 页面组件 | `app/static/css/brutalist-components.css` | 首页、资料、匹配、聊天、饭局和表单组件 |
| 手机编排 | `app/static/css/brutalist-mobile.css` | 320–1100px 重排、触控、安全区、底部导航 |
| 匹配流程 | `app/static/css/match-flow.css` | 首页任务入口、匹配准备/计算/结果状态与移动端编排 |
| 首页 / 资料收口 | `app/static/css/trust-profile.css` | 信任协议排版、来源分组、紧凑标签账本 |
| 会话任务台 | `app/static/css/chat-mission-deck.css` | 对话工作区、系统任务卡、工具抽屉、举报/拉黑弹窗 |
| 附近饭局 | `app/static/css/nearby-events.css` | 定位说明、距离筛选与附近状态 |
| 管理后台 | `app/static/css/admin-console.css` | 独立审核队列、举报队列与审计日志 |
| PRD 收口 | `app/static/css/prd-contract.css` | 最后加载，统一当前 token、字体、描边、硬投影、触控与强调色比例 |
| 动效增强 | `app/static/js/motion.js` | 进入、按压、选择、计数、提交和页面离开反馈 |
| 匹配时序 | `app/static/js/match-flow.js` | 只控制三阶段动画和普通 POST 提交，不计算结果 |
| 会话增强 | `app/static/js/chat-mission-deck.js` | details 状态、字数、原生 dialog；不改变业务状态 |
| 按需定位 | `app/static/js/nearby-events.js` | 仅在用户点击后请求 geolocation 并提交 GET 筛选 |

`motion.js` 不是应用运行时：禁用 JavaScript 后，导航、表单、筛选、聊天与全部后端流程仍可使用。它不得接管路由、修改业务字段、推导权限或在客户端制造服务端状态。

## 2. 项目位置与运行方式

| 内容 | 位置 / 命令 |
| --- | --- |
| Flask 工厂 | `app/__init__.py` |
| 页面路由 | `app/routes/` |
| Jinja 页面 | `app/templates/` |
| 样式入口 | `base.html` 加载分层页面 CSS，并把 `prd-contract.css` 放在最后 |
| 业务服务 | `app/services/` |
| 启动 | `python run.py` |
| 演示账号 | `demo@realtags.local` / `demo-password`，或首页一键进入 |

模板共同继承 `base.html`。它已经提供主导航、登录态 `current_user`、静态 CSS 引用和 flash 消息区域。新增页面必须继承它，而不是复制页面外壳。

## 3. 页面与路由总表

| 页面 | 方法 / 路由 | 模板 | 后端提供的数据 | 主要跳转或提交 |
| --- | --- | --- | --- | --- |
| 首页 | `GET /` | `home.html` | `user`、`stats` | 演示登录、注册、匿名匹配、兴趣饭局 |
| 登录 | `GET/POST /login` | `login.html` | 无 | 成功后 `/profile` |
| 注册 | `GET/POST /register` | `register.html` | 各枚举选项 | 成功后 `/profile/connections` |
| 我的标签 | `GET /profile` | `profile.html` | `user`、`tags`、`connections` | 数据连接 |
| 数据连接 | `GET /profile/connections` | `connections.html` | `user`、`connections` | `POST /profile/connections/<source>/authorize` |
| 匹配准备 | `GET /matches` | `matches.html` | `candidate_count` | `POST /matches/search/start` |
| 匹配计算 | `GET /matches/searching` | `match_searching.html` | `attempt_id` | 完成或取消 POST |
| 开始 / 完成 / 取消 / 换一位 | `POST /matches/search/start|complete|cancel|retry` | 无 | 签名 session `match_flow` | 全部使用 302 PRG |
| 匹配详情 | `GET /matches/<candidate_id>` | `match_detail.html` | `match`（受限）、`attempt_id`（可选） | 开启会话或换一位 |
| 会话列表 | `GET /conversations` | `conversations.html` | `conversations` | 会话详情 |
| 一对一 / 群聊 | `GET /conversations/<id>` | `conversation.html` | `conversation`、`demo_mode` | 发消息、工具箱、举报、拉黑 |
| 饭局广场 | `GET /events` | `events.html` | `events`、`tags`、`filters`、`nearby` | 城市/附近筛选、详情、发起 |
| 发起饭局 | `GET/POST /events/new` | `event_form.html` | `pois`、`tags`、`default_start` | 发布后详情 |
| 饭局详情 | `GET /events/<id>` | `event_detail.html` | `event`、`applicants`、`coupon`、`demo_mode` | 报名、审核、取消、群聊、核销、举报 |
| 管理员登录 | `GET/POST /admin/login` | `admin_login.html` | 无 | 成功后 `/admin/` |
| 审核控制台 | `GET /admin/` | `admin_dashboard.html` | `admin`、`pending_events`、`pending_reports`、`registered_users`、`account_query`、`audit_logs` | 搜索账户、打开活动/举报审核 |
| 活动审核 | `GET /admin/events/<id>`、`POST .../review` | `admin_event_review.html` | `admin`、`event` | `approve` / `reject` |
| 举报审核 | `GET /admin/reports/<id>`、`POST .../review` | `admin_report_review.html` | `admin`、`report` | `resolved` / `dismissed` |

除首页、登录和注册外，所有页面需要会话登录。未登录访问时后端跳转到 `/login` 并显示 flash 提示。

## 4. 全局模板契约

`base.html` 总会收到：

```jinja
current_user  # dict 或 None
```

`current_user` 的字段包括 `id`、`anonymous_alias`、`city`、`purposes`、`interests`、`mbti`、`zodiac`、`schedule`、`phone_verified`。它是**本人资料**；除了需要它的个人页，不能把这个对象错误地当作其他用户资料传递或展示。

所有 POST 表单必须保留原始 action、method 和隐藏字段 `_csrf_token`。应用默认在 session 中生成并验证 token；缺失、错误或跨 session token 返回 400。新增 POST 页面必须使用 `{{ csrf_token() }}`，不能关闭全局防护。

## 5. 页面数据契约与可视性边界

### 5.1 我的标签与数据连接

`profile.html` 的 `tags` 是当前用户自己的完整标签。每条为：

```text
tag_id, category, name, value, source, data_mode, verified, visibility, updated_at
```

来源标记请保留：`duolingo`、`keep`、`derived`、`self`。`data_mode` 为 `live`、`fixture`、`derived` 或 `self_reported`；只有成功的 Live 外部请求可令 `verified=true`，Derived 始终未认证。所有行为标签的 `visibility` 均为 `self_only`。在“我的标签”页展示来源与模式徽标是产品真实性设计的一部分。

`connections` 是按数据源索引的对象，例如 `connections.get('duolingo')`。Duolingo Live 表单提交 `mode=live` 与公开 `identifier`；Fixture 表单提交 `mode=fixture`。Keep 只接受 Fixture。失败时 flash 返回稳定错误码；页面不得请求、保存或渲染第三方密码、access token 或原始响应。

### 5.2 匿名匹配

候选集合只存在于服务端。`GET /matches` 仅接收 `candidate_count` 用于决定是否可开始；`GET /matches/searching` 只接收当前 `attempt_id`，不得渲染候选 ID、匿名代号、分数、标签或结果 JSON。

服务端完成匹配后，`match_detail.html` 当前实际使用的字段只有：

```text
candidate.id, display_score, common_point_count
```

`match` 服务对象目前仍携带完整 `candidate` 与 `raw_score`，只是模板没有渲染。这是过宽模板上下文的 P0 缺口，后端应改成显式安全投影。修复前允许在最终结果展示的仍只有 `display_score`、氛围文案和 `?` 占位卡；禁止展示或从对象中补取匿名代号、邮箱、密码哈希、照片、年龄、性别、学历、职业、城市、兴趣详情、第三方标签、`raw_score`、权重或逐项相似度。

`raw_score` 仅用于服务端排序，绝不渲染；`display_score` 是将原始分线性映射至 60–98 的体验分。页面文案不能暗示用户可以调节匹配权重。

匹配流程状态机：

```text
idle → searching → result → chat
          │           └→ retry → searching
          └→ cancel → idle
```

- `POST /matches/search/start` 由后端选择候选并创建 `attempt_id`；重复点击保持同一次 searching，不重复创建任务。
- 真实账户只进入真实候选池，演示账户只进入演示候选池；`DEMO_MODE=0` 时不播种演示数据，也不展示或接受演示登录。
- searching 页约在 `260 / 1000 / 1740 / 2500ms` 展示硬筛、相似度、排序和完成，但 JS 不读取候选或分数。
- `complete`、`cancel`、`retry` 都必须提交当前隐藏字段 `attempt_id`。旧页面令牌失效，不能覆盖新的匹配。
- “开启匿名会话”同样必须提交当前 result 的 `attempt_id`；直接拼 candidate URL、复用旧结果或跨真实/演示池建会均会被后端拒绝。同一用户对无论从哪一方发起都复用同一条 direct 会话。
- 禁用 JavaScript 时，用户仍可用“跳过等待，直接查看结果”提交 `complete`。
- `prefers-reduced-motion` 下不创建延迟时间线，步骤直接完成并提交服务端结果。

### 5.3 一对一聊天

`conversation.type == 'direct'` 时：

```text
conversation.progress = {
  level, label, next_requirement, heat, unlocked_points, total_point_count
}
conversation.counterpart = {
  anonymous_alias, level,
  # L1 起：city, age_range
  # L2 起：interest_category, avatar_mode
  # L3 起：interests, tags, avatar_mode
  # L4 起：contact_exchange_available
}
```

前端必须完全按后端是否给出字段决定展示；不能根据阶段值自行推测、补全或缓存对方资料。L0 只能显示匿名代号、匹配度/问号和关系进度。L1 解锁城市与年龄段，L2 解锁兴趣类别与模糊头像。当前 L3 返回完整标签，但它与 `visibility=self_only` 冲突，不能视为已批准的产品契约；后端完成可见性修复后，前端只显示安全投影。L4 目前只显示“可自愿交换联系方式”，没有实际交换表单或双方同意流程。

`conversation.messages` 内每条包含 `sender_id`、`message_type`（`text` / `system_card`）、`content`、`metadata`、`created_at`。系统卡片不能设计成单方私信；它必须在双方/全群聊天流中统一呈现。消息文字最大 500 字。

系统卡片只识别服务端白名单 `metadata.kind`：`match_started`、`dice`、`task_card`、`match_point`、`group_unlock_task`、`demo_progress`。每一类在 `conversation.html` 中有独立语义结构和视觉角色；未知值必须回退为普通 `notice`，禁止把元数据拼成 class、HTML 或脚本。连续普通消息会按同一发送者分组，但服务端消息顺序和内容不被 JavaScript改写。

`.mission-messages` 是固定视口高度的独立滚动日志，新增消息只能增加其内部滚动高度，不能继续拉长整页或挤压关系进度与任务区。它保留 `role="log"`、键盘焦点与可见滚动条；页面重新渲染后，渐进增强脚本只负责把该容器定位到最新消息。

双方消息持久化在同一会话，任一方重新打开或刷新服务端页面都能看到完整顺序。当前仍是 SSR 异步会话，不包含 WebSocket/SSE 实时推送。拉黑后 `conversation.is_blocked` 为真，模板必须隐藏发送器和任务工具，仅保留只读历史与举报入口；服务端会同时拒绝绕过界面的消息或工具 POST。

### 5.4 饭局群聊

`conversation.type == 'event_group'` 时不要读取 `counterpart`。应展示 `conversation.members`，但每个成员只有：

```text
alias, interest_tags  # 仅 1–2 个兴趣标签
```

群聊内禁止出现真实姓名、年龄、照片、联系方式或完整个人标签。`conversation.is_archived=true` 时前端必须隐藏发送控件，仅保留历史查看；但当前正常进入 `ended` 后的活动不再被定时查询，七天自动归档存在已知缺陷，不能仅依赖当前调度实现数据保留策略。

### 5.5 饭局广场与详情

每个 `event` 具有 `host_type`（`user` / `merchant`）、`is_merchant`、`status`、`status_label`、时间地点、`approved_count`、`max_size`、`gender_counts`、`required_tag_labels`、`display_score`、`merchant_benefit`。

浏览阶段只展示饭局元信息、人数、性别构成、商家标识、权益和“与你的匹配度”。不展示成员列表。`event.viewer_membership` 存在时只可展示当前用户的报名状态与共同标签数量。审核列表 `applicants` 当前提供 `match_score`、`common_tag_count`、`joined_at` 和提交审核使用的内部 `user_id`；视觉上仅称为“申请 #1”等。稳定 `user_id` 仍可能被发起人跨活动关联，后端后续必须改为每次报名独立的 opaque Application ID。

附近模式当前使用 `GET /events?lat=<纬度>&lng=<经度>&accuracy=<米>&radius=<公里>&sort=distance`。经纬度必须成对出现，范围分别为 `[-90, 90]` 与 `[-180, 180]`；`accuracy` 为浏览器可选回传的定位精度，半径为 `0–50km`，推荐 UI 选项为 `1/3/5/10/20/50`。定位成功页会服务端渲染“你的位置”、四位小数坐标、浏览器精度和最近白名单 POI 参照点。浏览器只有在用户点击“使用当前位置”后才可调用 Geolocation；禁止自动请求权限，禁止把精确坐标写入 localStorage、sessionStorage、账户或数据库。服务端只用白名单 POI 坐标计算 Haversine 直线估算距离。拒绝权限、浏览器不支持或参数非法时，页面必须保留城市筛选和全部活动降级路径。坐标仍会进入地址栏、浏览器历史、Referer 与访问日志，这是 P1 隐私缺口，不得将“不落库”描述为“无痕”。

用户发起活动的初始状态为 `pending_review`。广场、附近列表和非发起人的详情页都不会暴露待审或驳回活动；发起人可查看自己的待审详情。管理员通过后状态变为 `recruiting`，拒绝后为 `rejected`。

## 6. 表单字段与后端校验

### 6.1 注册：`POST /register`

| name | 必填 | 后端校验 / 选项 |
| --- | --- | --- |
| `email` | 是 | 合法邮箱，唯一 |
| `password` | 是 | 至少 8 字符 |
| `anonymous_alias` | 是 | 2–20 字符 |
| `birth_year` | 是 | 18–100 岁 |
| `gender` | 是 | `male` / `female` / `undisclosed` |
| `match_gender` | 是 | `male` / `female` / `any` |
| `match_age_min` / `match_age_max` | 否 | 默认 18–100；必须满足 `18 ≤ min ≤ max ≤ 100` |
| `city` | 是 | 由模板 `cities` 提供 |
| `purposes` | 是，多选 | 至少 1 个，由 `purposes` 提供 |
| `interests` | 否，多选 | 由 `interests` 提供 |
| `mbti` / `zodiac` / `schedule` | 否 | 均使用后端下发枚举 |

### 6.2 连接数据源：`POST /profile/connections/<source>/authorize`

`source` 仅接受 `duolingo` 和 `keep`。Duolingo 接受 `mode=live&identifier=<public_username>` 或 `mode=fixture`；Keep 只接受 `mode=fixture`。成功后以事务方式替换该来源的规范化标签并刷新 Derived 标签；失败显示 Adapter 错误码和可读消息。不要在浏览器或数据库保存 access token、密码或原始响应。

### 6.3 聊天：`POST /conversations/<id>/messages`

字段 `content` 为 1–500 个字符。工具按钮分别提交到：

| 功能 | action |
| --- | --- |
| 摇骰子出话题 | `/conversations/<id>/tools/dice` |
| 抽任务卡 | `/conversations/<id>/tools/task_card` |
| 匹配点解锁任务 | `/conversations/<id>/tools/unlock` |
| 举报 | `/conversations/<id>/report`，字段 `reason`（1–200） |
| 拉黑 | `/conversations/<id>/block`，仅一对一会话 |

所有工具结果由后端生成并作为 `system_card` 消息返回，前端不掷骰子、不随机抽题、不在客户端决定解锁内容。`DEMO_MODE` 打开时才显示推进阶段的演示按钮；当前服务端只检查全局模式、没有校验账户本身必须是 Demo，因此这不是生产权限边界，真实模式必须关闭且后端需要补充账户类型校验。任务入口使用 `app/static/img/chat-tool-{dice,task,unlock}.webp` 三张装饰图；图片 `alt=""`，因为同一按钮内已有完整可见名称与说明。手机端工具区为横向吸附卡组，不应退化成三个被挤窄的栏。

增强环境下，举报入口初始 `aria-expanded="false"` 且保持白色；原生 `dialog` 成功打开后脚本才设为 `true`，对应黄色打开态，关闭、Esc 或打开失败时必须恢复 `false`。无 `HTMLDialogElement` 时保留服务端表单回退。

### 6.4 发起饭局：`POST /events/new`

| name | 必填 | 规则 |
| --- | --- | --- |
| `title` | 是 | 2–60 字符 |
| `poi_id` | 是 | 必须为后端下发的公开场所 Fixture 白名单项 |
| `start_at` | 是 | 未来时间，分钟仅 00 或 30 |
| `signup_deadline` | 否 | 留空默认开始前 2 小时；必须在现在与开始时间之间 |
| `min_size` / `max_size` | 是 | `3 ≤ min_size ≤ max_size ≤ 10` |
| `budget_level` | 是 | `under_50` / `50-100` / `100-200` / `200_plus` |
| `pay_type` | 是 | `AA` / `host_pays` / `separate` |
| `required_tags` | 是，多选 | 1–5 项，必须来自后端 `tags` |
| `gender_policy` | 否 | `any` / `balanced` / `same_gender` |
| `signup_mode` | 是 | `first_come` / `review` |
| `description` | 否 | 最多 200 字 |

不要提供自定义地址输入框。地点白名单是线下安全的 P0 规则。

### 6.5 饭局后续操作

- 报名：`POST /events/<id>/signup`。低匹配度只提示，不可置为不可提交。
- 审核：`POST /events/<id>/review/<applicant_id>/approve|reject`。按钮只对用户发起且审核制的饭局主人展示。
- 取消：`POST /events/<id>/cancel`。仅用户发起人、草稿/报名中状态可见。
- 核销：`POST /events/<id>/redeem`，提交 `redeem_code`。权益只在成团后出现，状态为 `issued` 时可核销。
- 举报：`POST /events/<id>/report`，提交 `reason`，1–200 字。

### 6.6 管理员审核

- 管理员使用与普通用户完全分离的 `admin_id` session；普通登录态不能访问 `/admin/`。
- `DEMO_MODE=0` 不创建默认管理员；部署人员必须通过 `flask --app run.py create-admin` 交互式创建真实管理员。不要把管理员初始密码写进模板、仓库或启动日志。
- 注册账户目录为只读白名单视图，可用 `GET /admin/?q=<邮箱|匿名代号|城市>` 搜索；只允许返回邮箱、真实/演示账户类型、匿名代号、城市、手机验证、注册时间及已连接数据源数量，禁止查询或渲染 `password_hash`、`access_token`。
- 活动决定提交到 `POST /admin/events/<id>/review`：字段 `decision=approve|reject`；拒绝时 `rejection_reason` 必填且最多 500 字。
- 举报决定提交到 `POST /admin/reports/<id>/review`：字段 `decision=resolved|dismissed`，可带 `note`（最多 500 字）。
- 所有决定使用 PRG 跳转，后端防止重复处理和非法状态转换；前端不能乐观修改队列或伪造完成状态。
- 管理模板是独立安全工作台，但复用项目的暖纸面、粗黑边、黄/紫/绿/珊瑚令牌；不要把管理员导航混入普通用户主导航。

## 7. 状态机与前端状态

```text
pending_review ──approve──→ recruiting → formed → ongoing → ended
       └────────reject────→ rejected       └────→ cancelled
```

| 后端 `status` | 显示中文 | 可进行的前端动作 |
| --- | --- | --- |
| `draft` | 草稿 | 当前 MVP 不在广场展示 |
| `pending_review` | 待平台审核 | 仅发起人和管理员可见；不能报名 |
| `rejected` | 审核未通过 | 仅发起人和管理员可见；展示拒绝结果，不公开 |
| `recruiting` | 报名中 | 报名；用户发起人可取消 / 审核 |
| `formed` | 已成团 | 已通过成员可进匿名群聊；若商家局显示权益 |
| `ongoing` | 进行中 | 仅保留活动信息、群聊和权益状态 |
| `ended` | 已结束 | 不再报名；群聊当前仍可查看，正常七天归档有已知缺陷 |
| `cancelled` | 已取消 | 不再报名；商家权益失效 |

后端在每次请求时检查到期活动，生产还必须每 5 分钟执行 `flask --app run.py process-events`。前端不应自行根据浏览器时间切换状态，而是重新请求服务端渲染页面。

## 8. 已实现的视觉系统与组件契约

### 8.1 设计方向

视觉语言为“可信关系实验板”：暖白纸面、2.5px 黑边、零模糊硬阴影，以及受限使用的黄色、紫色、绿色和橙色。暖白与白卡约 60%，黑色约 25%，黄色约 10%，其余强调色合计约 5%；强调色不能作为大面积页面背景。

核心令牌位于 `app/static/css/brutalist-foundation.css`，`prd-contract.css` 最后收口：

| 令牌 | 当前值 | 用途 |
| --- | --- | --- |
| `--bg` | `#FFFCF0` | 全局暖白底 |
| `--surface` | `#FFFFFF` | 卡片、表单和列表表面 |
| `--text` | `#17150F` | 主文字、边界和硬阴影 |
| `--dim` | `#6B675A` | 次级正文和元信息 |
| `--surface2` | `#FFE95C` | 选中、高亮、chip |
| `--primary` | `#5B4DFF` | 主行动、焦点和关键数字 |
| `--accent` | `#58CC02` | 已连接、成功和进度 |
| `--hot` | `#FF5A36` | 优惠、未读和警告 |

字体只使用本机字体栈，不加载外部字体；H1/H2/H3 分别为 23/18/16px，正文 13.5px。组件统一使用 2.5px 黑边；主投影为 `6px 7px 0`，卡片投影为 `4px 5px 0`，hover 为 `3px 4px 0`，active 为零投影。禁止装饰性渐变和模糊阴影。

### 8.2 全局页面外壳

- `base.html` 提供 skip link、粘性导航、服务端当前页状态、flash 状态区、`main#main-content` 与统一页脚。
- 主内容宽度由 `--page-width: 1180px` 控制；普通页面使用 `.page-shell`，首页在同一模板中略微放宽到 1280px。
- 当前导航通过 `request.endpoint` / `request.blueprint` 在服务端输出 `.is-active` 与 `aria-current="page"`，不要在浏览器中重算。
- `.button` 是主行动；`.secondary` 是次行动；`.text-link` 是低权重跳转；`.danger` / `.danger-outline` 只用于举报、拒绝、拉黑和取消。
- 所有交互控件都有 `hover / active / focus-visible / disabled` 状态；移动端主触控目标至少 44px。

### 8.3 页面级结构

| 页面 | 核心结构类 | 设计意图 |
| --- | --- | --- |
| 首页 | `.home-hero`、`.home-launchpad`、`.home-path-grid`、`.principle-list` | 先给匿名匹配 / 兴趣饭局两个任务入口，再解释隐私原则 |
| 登录 | `.auth-layout`、`.auth-story`、`.auth-form-panel` | 将隐私承诺与账号表单分区 |
| 注册 / 发起饭局 | `.structured-form`、`.form-section`、`.choice-tile` | 单个 SSR 表单，通过视觉分段形成步骤感 |
| 我的标签 | `.profile-hero`、`.tag-grid`、`.tag-data` | 本人私密资料与来源认证标签；映射/列表值不再显示原始 JSON |
| 数据连接 | `.source-grid`、`.source-card`、`.source-meta` | 状态、用途、最近同步、下一动作四层信息 |
| 匿名匹配 | `.match-ready`、`.match-search-board`、`.match-calculation-steps`、`.match-result` | 准备、计算、单个结果三个独立 SSR 页面状态 |
| 会话列表 | `.inbox-list`、`.inbox-row` | 名称 > 阶段 > 最后一条消息 > 进入动作 |
| 会话详情 | `.mission-header`、`.relation-deck`、`.mission-log`、`.mission-drawer` | 借鉴任务台排版，但完整沿用项目令牌；不同系统任务拥有不同票据结构 |
| 饭局广场 | `.nearby-panel`、`.filter-bar`、`.event-list`、`.event-row` | 请求期定位说明、附近状态和编辑式活动条目 |
| 饭局详情 | `.event-detail-hero`、`.detail-grid`、`.group-entry`、`.coupon-panel` | 决策区、活动事实、安全边界、成团/权益状态 |
| 管理后台 | `.admin-shell`、`.admin-queue-card`、`.admin-account-table`、`.admin-audit` | 活动、举报、只读账户与审计使用不同任务表面，保持项目视觉一致 |

系统卡片的 class 判定必须优先于发送者判定：`message_type == 'system_card'` 时始终使用 `.system-event` 及其 `system-*` 变体，不能因为触发工具的人是本人就画成 `.chat-message` 私信气泡。

### 8.4 响应式与无障碍

- UI 采用手机优先编排，完整断点为 `360 / 430 / 560 / 760 / 900 / 1100px`；小屏规则写在文件根级，宽屏通过 `min-width` 逐步恢复多栏结构。
- `320–429px`：全部功能单列；登录态页头只保留品牌与退出，四个核心任务使用固定底部导航；表单控件为 16px，触控目标至少 44px。
- `430px`：大手机恢复部分双列事实和“输入 + 行动”结构，但不会把密集桌面卡片压进窄列。
- `560px`：标签与匹配卡可进入两列，会话成员和活动元信息开始横向组合。
- `760px`：平板恢复部分双栏工作区；登录态仍使用底部任务导航。当前 `.mission-workspace` 仍为单列，聊天工具箱不会在此断点进入侧栏。
- `900px`：切换为桌面页头导航并隐藏底部导航，聊天、匹配结果和饭局详情恢复完整多栏结构。
- `1100px`：启用完整编辑式桌面网格、最大硬阴影与宽筛选条。
- 页面最小宽度为 320px；所有内容列使用 `min-width: 0` 与可换行策略，禁止制造横向滚动。
- 底部导航和页脚包含 `env(safe-area-inset-*)`；页面底部预留导航高度，不能遮住表单、危险操作或页脚。
- `prefers-reduced-motion` 会关闭平滑滚动与过渡；`forced-colors` 保留按钮、状态和当前导航边界。
- flash 错误使用 `role="alert"`，成功/提示使用 `role="status"`；聊天消息流使用有名称的 `role="log"`，消息显示“我 / 对方 / 系统任务”而非只靠颜色区分。
- 举报原因有真实 `<label>`；弹窗入口同步 `aria-controls` / `aria-haspopup="dialog"` / `aria-expanded`；重复审核按钮有包含申请序号的 `aria-label`；待解锁问号对读屏器隐藏，只保留父级完整描述。

### 8.5 动效与渐进增强

- `motion.js` 只增加视觉反馈，不保存业务状态，也不接管路由或表单。
- `match-flow.js` 是匹配计算页的薄时序层；纯控制器由 Node 内置测试覆盖，最终状态仍由 Flask 决定。
- 页面进入：主区域立即揭示，其余卡片由 `IntersectionObserver` 在接近视口时错峰进入。
- 组件角色：卡片轻弹、列表轻移、左右消息分向进入、系统卡片纵向进入；每个角色使用统一时长和不同方向。
- 数字角色：匹配分在首次进入视口时计数至后端值，完成后恢复原始服务端文本。
- 选择角色：input、choice tile、details 和提交表单分别获得 active、selected、open、submitting 状态。
- 普通内部链接离页前只有 140ms 轻反馈，随后仍调用浏览器原生 `location.assign()`；外链、下载、修饰键和页内锚点不被拦截。
- 关闭 JavaScript 后，所有元素默认可见，所有链接和表单仍然完成同一服务端流程。

### 8.6 图像资产

- `paper-dot-grid.png` 是低对比真实纹理，只服务于纸面质感。
- `brand-mark.png` 同时用于页头和 favicon；替换时必须保持 1:1、高对比与小尺寸清晰度。
- 不要用 emoji、字符、内联 SVG、CSS/div 绘画替代可见品牌或插画资产。
- 完整生成方式与提示词见 `docs/IMAGE_ASSET_PROMPTS.md`。

### 8.7 后续扩展规则

- 使用普通 `<a href="{{ url_for(...) }}">` 做跳转，用常规 POST 表单做动作；页面刷新是正常反馈。
- 只使用服务端给出的 `status_label`、`merchant_benefit.label`、来源、认证状态和可见字段；不要把服务端状态复制进客户端逻辑。
- 不要将卡片整体包进链接，因为详情内存在多个独立 POST 动作，会产生无效嵌套或误触。
- 不要把 `current_user`、完整 candidate、`sender_id`、`applicant.user_id`、`raw_score` 或算法权重序列化进 DOM、`data-*` 或前端 JSON。
- `redeem_code` 只在服务端返回 `coupon` 后显示；工具结果、随机题卡、关系解锁和活动状态全部由服务端决定。
- 新页面优先复用以上结构类；确实出现新语义时再增加组件，不要复制一套近似样式。

## 9. 后端已明确处理与暂未覆盖的边界

已处理：输入长度/枚举/人数/Fixture POI 白名单校验、活动时段冲突、重复报名、匿名审核、标签来源、真实/演示候选隔离、匹配 attempt 校验、direct 会话去重、成员权限、拉黑后只读与举报记录、请求期附近定位、管理员活动/举报审核与审计日志、群聊归档、商家 Fixture 权益的成团后发放和 Demo 核销。

MVP 限制：Keep、短信、POI、商家与 POS 均为 Fixture；不含 WebSocket/SSE 实时推送、地图瓦片/路线导航、真实支付、媒体/语音、商家自助后台、通知推送、出席信誉分或活动后评价。正式发布前还需增加限流、细粒度管理员角色、真实手机号验证、生产调度/观测和隐私合规授权页。

## 10. 前端验收清单

当前交付已通过以下项目；后续改动应把本清单作为回归门槛：

- [x] 每个页面有独立 Flask 路由和 Jinja 模板，没有客户端路由。
- [x] 匹配页和 L0 聊天页不出现对方年龄、性别、城市、照片、标签、权重或原始分。
- [x] 匹配准备、计算和单个结果为独立 SSR 状态；匹配中 HTML 不预埋候选身份或分数。
- [x] 匹配取消、换一位、旧令牌失效、无 JavaScript提交和减弱动画均有确定降级路径。
- [x] 两个新注册的非演示账户可互相匹配、进入同一条持久化会话并双向发消息；演示账号不会进入真实候选池。
- [x] 自己的标签显示来源与认证标识；第三方标签不会被错误复用到对方资料。
- [x] 所有工具、报名、审核、核销、举报和拉黑都通过既定 POST 表单提交。
- [x] 饭局地点只从 `pois` 选择，人数控件限制 3–10，目标标签限制 1–5。
- [x] 定位只在点击后申请，坐标只进入本次 GET；拒绝权限和非法参数均回退到城市/全部活动。
- [x] 用户饭局待审时不公开；管理员通过后才可报名，拒绝与举报处理均留下审计记录。
- [x] 商家饭局带明确标识，成团前不展示券码，成团群成员仍只显示匿名代号与 1–2 个兴趣标签。
- [x] 各种失败显示后端 flash，不在前端吞掉失败或伪造成功状态。
- [x] 移动端下导航、筛选表单、消息发送区和活动卡保持可操作，键盘焦点可见。

验证证据：`design-qa.md`、`docs/qa/mobile-montage-pass2.png` 和 `./harness.cmd --no-color`。
