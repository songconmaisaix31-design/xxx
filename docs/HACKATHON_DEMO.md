# Hackathon Demo Script

## Demo objective

在 4 分钟内证明一条完整且可信的用户链路：行为数据不是装饰性资料，而是匿名匹配、关系解锁和安全线下见面的输入；有接口的能力使用 Live，没有稳定接口的能力使用明确标记的 Fixture。

## Preflight

```powershell
uv sync --locked --python 3.12
uv run python run.py
```

打开 `http://127.0.0.1:5000`。演示前确认首页出现“进入预置演示账号”，并保留 `Duolingo Fixture` 作为断网降级路径。

## Four-minute route

### 0:00–0:30 — Problem and promise

讲述：传统社交产品先展示身份，再让用户判断是否同频；真实标签反过来，先用最小行为信号验证同频，再由双方互动决定披露多少身份。

点击“进入预置演示账号”。

### 0:30–1:15 — Data provenance, not profile decoration

在“我的标签”展示 33 个信号及四种明确来源：

- 11 Duolingo Fixture
- 11 Keep Fixture
- 3 Derived
- 8 Self

打开“管理数据连接”。强调 Keep 当前没有稳定接口，所以不伪装 Live；Duolingo 可输入公开用户名执行一次 HTTPS Live 同步。网络或上游异常时，直接切回 Fixture，不让演示链路依赖外部可用性。

### 1:15–2:10 — Anonymous matching

进入“匿名匹配”，点击“开始匿名匹配”。讲述服务端先执行双向年龄和性别偏好硬过滤，再比较集合、数值、等级与活跃时段；客户端拿不到原始分、权重或候选列表。

结果页只展示平滑后的分数、隐藏共同点数量和匿名操作。指出右侧“此刻不会显示什么”：照片、姓名、年龄、城市、职业和标签详情仍被封存。

### 2:10–3:10 — Relationship progression

点击“开启匿名会话”。展示：

- 文本、骰子和任务卡都写入同一条服务端消息流。
- 正常 L1 需要双方发言、共同活跃日且累计至少 10 点热度。
- L2/L3 分别需要 3/7 个共同活跃日；全部匹配点解锁后才进入 L4。
- “演示：推进时间至 L3”和“演示：解锁一个匹配点”是独立、显式标记的 Demo 快捷动作，不冒充自然互动。

### 3:10–3:45 — Safe offline table

打开“饭局广场”。展示公开场所、3–10 人、匿名成员、性别构成、匹配排序和商家权益。强调位置只在用户主动点击后用于本次请求，不保存精确坐标。

说明当前餐厅、短信验证、商家和 POS 都是 Fixture：它们证明审核、成团、发券、一桌一码、时段/门店限制和核销工作流，而不是生产合作关系。

### 3:45–4:00 — Close with trust

收束：这个 Demo 的差异不是“多做了几个社交页面”，而是把数据来源、最小披露、双向关系进度和线下安全做成一条可验证的产品协议。

## Failure recovery

| Failure | Demo response |
| --- | --- |
| Duolingo Live unavailable | 展示明确错误后点击“改用 Fixture 演示数据”；不重试到超时 |
| Browser location denied | 保留城市筛选与全部饭局列表，说明这是预期降级 |
| External network unavailable | 全程使用预置 Fixture，核心链路不受影响 |
| Demo state already advanced | 重新点击首页 Demo 登录会回到同一预置账号；关键测试使用临时数据库保证可重复 |

## Evidence commands

```powershell
uv lock --check
uv run python -m unittest discover -s tests -v
node --test tests/match_flow.test.mjs
uv run python -m compileall -q app tests tools
.\harness.cmd
```
