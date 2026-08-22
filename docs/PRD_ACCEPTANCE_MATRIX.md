# PRD Acceptance Matrix

状态定义：`PASS` 已由当前分支证据验证；`PASS + FIXTURE` 功能链路完整但至少一个外部能力为明确标记的演示数据；`FIXTURE` 只证明演示工作流；`PARTIAL` 仍有未完成验收证据。

## P0

| ID | PRD 必做项 | 可检查的验收标准 | 当前状态 | Evidence / boundary |
| --- | --- | --- | --- | --- |
| P0-01 | 注册与 8 类自填标签 | 年龄/双向年龄偏好与性别偏好硬过滤；城市、目的、兴趣、MBTI、星座、作息可见于本人页；选填可留空 | PASS | registration and matching tests |
| P0-02 | 第三方接入与 20+ 标签 | 统一 adapter；Duolingo + Keep Fixture ≥20；来源/模式/认证/可见度明确；Duolingo Live 可选 | PASS + FIXTURE | 22 Fixture + 3 Derived；Duolingo Live adapter and smoke；Keep Fixture |
| P0-03 | 匹配算法 | 权重启动校验 100%；先硬过滤；集合/数值/时段/分级/MBTI 相似度；原始分排序、60–98 展示 | PASS | matching unit and workflow tests |
| P0-04 | 匿名结果页 | 仅分数、氛围文案、匿名占位和 `?`；不传候选资料/权重 | PASS | route/template tests + desktop runtime QA |
| P0-05 | 匿名聊天 | 文字与系统卡；成员鉴权；拉黑、跨池、归档后只读 | PASS | two-user, permission and archive tests |
| P0-06 | 破冰工具 | 6 面骰子、≥30 分类任务、协作解锁任务；1V1 和群聊共用消息模型 | PASS | chat service/UI tests |
| P0-07 | L0–L4 | 共同活跃日；L1 双向累计≥10；L2=3 天；L3=7 天；全点解锁到 L4；Demo 加速明确标记 | PASS | time-boundary and collaboration tests |
| P0-08 | C 端饭局 | 手机验证门槛、公开 POI、3–10 人、审核/报名/成团/取消/群聊、匹配排序、低分可坚持报名 | PASS + FIXTURE | workflow passes；SMS and POI are Fixture |
| P0-09 | B 端与权益 | 2–3 场商家演示；商家标识；成团发券；一场一码；时间/门店约束；Demo 手动核销 | FIXTURE | lifecycle/coupon tests；no production merchant/POS integration |
| P0-10 | UI 定稿规范 | PRD token、2.5px 黑描边、零模糊硬投影、焦点态、44px 触控、reduced motion、桌面/移动无溢出 | PARTIAL | desktop runtime QA + CSS/static responsive tests pass；mobile runtime screenshot unavailable in current automation session |

## Security and truth gates

| ID | Rule | Acceptance | Status |
| --- | --- | --- | --- |
| S-01 | CSRF | 所有 POST 默认验证 session token；测试覆盖拒绝分支 | PASS |
| S-02 | Secret defaults | 生产缺少 `FLASK_SECRET_KEY` 时拒绝启动；Demo 使用进程随机密钥；debug 默认关闭 | PASS |
| S-03 | External data minimization | 无 token/原始响应落库；HTTPS、超时、响应上限、类型检查 | PASS |
| S-04 | Fixture/Live truth | Fixture 不显示为已认证；Live 失败不静默写成成功 | PASS |
| S-05 | Offline safety | 未验证手机号不能发起；同性别局服务端约束；活动和群聊可举报 | PASS |
| S-06 | Lifecycle | ended 活动在结束 7 天后归档，归档群不能消息或使用工具 | PASS |

## Judge route

1. 进入明确标识的 Demo 账号，查看 Self、Fixture 与 Derived 来源。
2. 可选输入公开 Duolingo 用户名，展示 Live 标签或稳定失败提示。
3. 准备页 → 服务端计算 → 单一匿名结果 → 建立会话。
4. 使用骰子和任务卡；对比正常关系门槛与显式 Demo 加速。
5. 浏览按匹配度排序的饭局，查看公开场所、商家 Fixture、性别构成和低匹配提示。
6. 展示创建安全门槛、匿名审核、成团群聊、权益与显式 Demo 核销。
7. 以 `docs/CLAIMS_LEDGER.md` 收尾，明确 Live、Fixture、已实现与未实现边界。
