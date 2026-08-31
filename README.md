# 同频：真实标签

用行为标签先找到同频的人，在匿名互动中逐步决定是否交换更多身份信息。

`PORTFOLIO / MAINTENANCE` · 纯爱战神黑客松全场第二 · Flask / Jinja2 / SQLite

> 当前仓库是可本地运行、可自动验证的黑客松原型，不是生产社交服务。第三方数据连接使用确定性 Mock；页面里的“已认证”是原型内部的来源元数据，不代表平台完成了真实账号核验。

## 产品主线

同频把传统社交产品中过早暴露的照片、职业等身份信息放到关系建立之后：

1. 将行为信号标准化为带来源、可见性和验证状态的标签。
2. 在服务端按偏好、标签和安全条件生成单个匿名匹配结果。
3. 建立双方共享的匿名会话，以消息、任务和活跃天数推进 L0–L4 解锁。
4. 只有关系逐步建立后，才呈现更多资料或提供离开产品的能力标志。

这套实现关注的是“真实行为标签 → 匿名匹配 → 渐进身份解锁”的可演示机制，不宣称已经解决真实平台授权、身份真实性、线上安全治理或规模化运营。

## 当前真正实现了什么

| 能力 | 当前代码行为 | 证据边界 |
| --- | --- | --- |
| 行为标签 | 统一标签结构，保存来源、验证布尔值和 `self_only` 可见性 | Duolingo / Keep 数据由本地确定性 Fixture 生成 |
| 匿名匹配 | 双向偏好与拉黑过滤、服务端计算、单结果、`attempt_id` 状态保护 | 展示分用于原型体验，不是第三方平台或科学测评结论 |
| 渐进解锁 | L0–L4 服务端裁剪，依据消息、互动热度、活跃日与任务推进 | 头像、联系方式等部分阶段仍是能力标志或占位语义 |
| 双向会话 | SQLite 中唯一 direct 会话、双方消息持久化、举报与拉黑限制 | 服务端渲染；对方需要打开或刷新页面，无实时推送 |
| 兴趣饭局 | 本地活动创建、审核、报名、状态推进、匿名群聊和演示权益 | 白名单 POI 与演示权益；无真实地图、商家、支付或到店核验 |
| 管理后台 | 独立管理员登录、活动/举报审核、受限账户目录与审计记录 | 缺少生产 RBAC、MFA、限流和完整处罚/申诉闭环 |

## 第三方集成真相表

| 来源 | 仓库当前状态 | 可以怎样描述 |
| --- | --- | --- |
| Duolingo | `MockDataSourceAdapter`，固定授权码触发确定性学习标签 | 可演示的数据适配器与标签规范，不是真实接入 |
| Keep | `MockDataSourceAdapter`，固定授权码触发确定性运动标签 | 可演示的数据适配器与标签规范，不是真实接入 |
| GitHub | 当前运行树没有 GitHub 适配器 | 仅有过调研/其他本地实验，不属于本版本能力 |
| Steam | 当前运行树没有 Steam 适配器 | 仅有过调研/其他本地实验，不属于本版本能力 |
| 其他平台 | 当前运行树没有可用连接 | 不应写成已授权、已同步或已上线 |

本次整理没有从其他工作树导入 connector probe、凭据文件、私有报告或未推送实验提交。

## 快速开始

需要 Python 3.10+。应用依赖只有 `requirements.txt` 中声明的 Flask；完整测试还需要支持内置 test runner 的 Node.js。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

打开 `http://127.0.0.1:5000`。默认 `DEMO_MODE=1`，会创建本地演示数据；不要在演示库中录入真实个人数据。`run.py` 使用 Flask 开发服务器，仅适合本地验证。

### 演示入口

| 类型 | 本地演示值 |
| --- | --- |
| 普通用户 | `demo@realtags.local` / `demo-password` |
| 管理员 | `admin@realtags.local` / `admin-password` |
| Mock 数据源授权码 | `demo-authorized` |

以上均为仓库内的公开 Fixture，不是线上凭据。

## 验证

完整既有门禁：

```powershell
.\harness.cmd --no-color
```

也可以分别运行：

```powershell
python -m unittest discover -s tests -v
node --test tests/match_flow.test.mjs
python -m compileall -q app tests
```

Python 测试使用临时 SQLite 和 Flask `test_client()`，不访问外部 provider，也不需要任何凭据。当前验证结果与已知限制见 [STATUS.md](STATUS.md)。

## 目录

```text
app/                    Flask 应用、模板、静态资源与领域服务
tests/                  Python HTTP/领域回归与 Node 动效测试
tools/harness_cli.py    现有验证控制台
prototypes/             早期可点击原型与路演 deck，不参与运行时
docs/product/           产品需求输入
docs/brand/             品牌规范与资产生成记录
docs/design/            设计 QA 与前端交接
docs/history/           历史指南与只读审计记录
```

关键文档：

- [项目状态与集成矩阵](STATUS.md)
- [产品 PRD](docs/product/PRD.md)（需求输入，不代表全部完成）
- [品牌规范](docs/brand/BRAND_SPEC.md)
- [前端交接](docs/design/FRONTEND_HANDOFF.md)
- [设计 QA](docs/design/DESIGN_QA.md)
- [Harness 说明](docs/HARNESS_ENGINEERING.md)
- [生产缺口](docs/PRODUCTION_GAPS_AND_ROADMAP.md)
- [历史原型](prototypes/)

## 团队与贡献

项目由四人随机组队，产品方向来自团队共同构思。用户带入“真实标签”和“个人数据接口”的方向，并承担了主体前端、后端、整合、部署、演示视频，以及部分路演工作；其他成员共同参与了创意、讨论和比赛交付。

AI 工具参与了发散、实现辅助和文档整理。AI 产出、团队构思、个人执行与最终可验证代码是不同层次的贡献，不能互相替代，也不应把 Mock 或研究材料包装成真实集成。

## 维护状态

- 当前定位是作品集展示与有限维护，不进行无验证的功能扩张。
- 仓库暂不改名；`tongpin-real-tags` 只是独立 QA 通过后的目标名称。
- 本次不创建新的比赛 Tag 或 Release。开始快照由 `pre-cleanup-2026-08-31` 保留，比赛版本仍需独立 QA 确认。
- 生产公开上线仍为 NO-GO；详见 [STATUS.md](STATUS.md) 与 [生产缺口](docs/PRODUCTION_GAPS_AND_ROADMAP.md)。

## License

[MIT](LICENSE)
