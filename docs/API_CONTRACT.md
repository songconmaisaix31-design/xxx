# External Data API Contract

状态：Implementation contract
来源依据：`API_INTERFACE_CATALOG.md`（2026-08-22 核验快照）
适用范围：黑客松 MVP 的只读标签同步

## 1. 统一边界

路由不得直接访问外部服务。每个适配器返回规范化 `ExternalTag`：

```python
ExternalTag(
    tag_id="lang_learning",
    category="学习",
    name="在学语种",
    value={"items": ["英语", "日语"]},
    source="duolingo",
    data_mode="live",
    verified=True,
)
```

约束：

- `tag_id` 来自项目词表；匹配算法和活动标签只依赖该标识。
- `data_mode` 仅允许 `self_reported | fixture | live | derived`。
- `verified=true` 只允许当前 Live 同步成功的直接第三方标签；Derived 始终保持未认证，避免把推导结果包装成上游事实。
- `visibility` 在 MVP 中固定为 `self_only`；未解锁前不得发送给匹配对象。
- 只保存规范化标签、连接状态、模式和同步时间；不保存原始响应、cookie 或 token。

## 2. 支持矩阵

| 数据源 | 模式 | 状态 | MVP 行为 |
| --- | --- | --- | --- |
| Duolingo public profile | Live | Supported, read-only | 用户主动输入公开用户名后同步；无需凭据 |
| Duolingo | Fixture | Supported | 确定性样例；明确标记 Fixture |
| Keep | Fixture | Supported | 确定性样例；明确标记 Fixture |
| Keep login / stats | Live | Not available | 不调用、不展示为已接通 |
| LeetCode CN/COM | Live | Deferred | 仅传输探针有证据，字段映射未冻结 |
| GitHub REST | Live | Deferred to V2 | 接口可用，但不属于 PRD P0 数据源 |
| Steam / WeRead / NetEase | Live | Not available | 需要凭据、服务未配置或路由无效 |

## 3. Duolingo Live

### Request

```http
GET https://www.duolingo.com/2017-06-30/users?username={username}
Accept: application/json
User-Agent: RealTags-Hackathon/1.0
```

输入与网络规则：

- `username` 去除首尾空格后须为 2–64 个由字母、数字、点、下划线或连字符组成的字符。
- URL 参数必须通过标准编码器构造，不拼接用户输入。
- 仅允许固定的 `https://www.duolingo.com` 主机和固定路径。
- 连接/读取总超时 5 秒；最多读取 256 KiB；拒绝非 JSON、非对象根、非列表 `users`。
- 不重试，避免现场请求风暴；用户可显式再次同步。

### Response mapping

仅使用存在且通过类型检查的字段：

| Live 字段 | 规范化标签 | 缺失策略 |
| --- | --- | --- |
| `users[0].courses[*].title` / `learningLanguage` | `lang_learning` | 无可识别语种则省略 |
| `users[0].streak` | `lang_streak`, `learning_consistency` | 非负整数，否则省略 |
| `users[0].totalXp` | `learning_total_xp` | 非负整数，否则省略 |
| `users[0].courses[*].xp` | `learning_course_xp` | 仅保留规范化语种与非负 XP |
| course 数量 | `learning_course_count` | 至少一个合法课程才生成 |

不从缺失字段猜测活跃时段、等级、联赛或总学习天数。同步至少产生一个标签才算成功。

### Stable errors

| code | 含义 |
| --- | --- |
| `invalid_identifier` | 用户名格式不合法 |
| `source_unavailable` | DNS、TLS、超时或非 2xx |
| `response_too_large` | 响应超过 256 KiB |
| `invalid_response` | JSON 或字段结构不符合契约 |
| `profile_not_found` | `users` 为空 |
| `no_supported_tags` | 用户存在但没有可安全映射字段 |

错误信息不得包含完整上游响应、堆栈、cookie 或请求头。

## 4. Fixture contract

- Fixture 由 `source + user_id` 产生确定性结果，便于测试和演示复现。
- Duolingo 与 Keep Fixture 合计不少于 20 个行为标签；另可生成复合标签。
- Fixture 的 `verified` 永远为 `false`，`data_mode="fixture"`。
- 连接文案使用“演示样例/Fixture”，不得使用“已认证/真实同步”。
- Fixture 不执行任何网络请求，不持久化模拟 access token。

## 5. 同步事务

1. 校验 source、mode 和用户输入。
2. 在数据库事务外完成外部只读请求与规范化。
3. 标签列表全部校验成功后，在一个事务中替换同一 source 的旧标签并更新连接元数据。
4. 任一步失败时保留上一次成功数据，不写入部分结果。
5. Live 切换为 Fixture（或反向切换）时，UI 必须显示最新模式。

## 6. 测试边界

- 单元测试不得访问真实网络，使用本地 stub 注入 opener/transport。
- 可选 Live smoke 只请求公开测试用户名，不保存或打印响应正文。
- 测试必须覆盖 URL 编码、超时、非 2xx、超限、坏 JSON、空用户、字段缺失、事务回滚及 Fixture/Live 标识。
