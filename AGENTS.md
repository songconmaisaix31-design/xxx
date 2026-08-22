# AGENTS.md

## 项目目标

本项目是“真实标签”黑客松 MVP：以用户授权的真实行为数据生成可解释标签，在匿名匹配、渐进式聊天和 3–10 人约饭场景中建立可信连接。产品事实来源是根目录 `产品需求文档_PRD.md`。

## 工作范围与事实来源

- 产品与 P0 验收：`产品需求文档_PRD.md`、`docs/PRD_ACCEPTANCE_MATRIX.md`。
- 技术方案：`docs/HACKATHON_IMPLEMENTATION_SPEC.md`。
- 外部数据边界：`docs/API_CONTRACT.md`。
- UI 视觉事实来源：PRD 第 5 章；其他品牌或交接文档不得与其冲突。
- 当前交付分支：`competition/prd-hackathon`。不得提交或推送到 `main`。

## 架构与实现约定

- 保持 Flask + Jinja2 服务端渲染和 SQLite 架构；优先复用现有 service、route 和 template 模式。
- 用函数和小模块表达业务逻辑；除非现有架构明确需要，不增加 class、框架或依赖。
- 所有外部输入在边界验证；权限、活动状态、拉黑关系和数据可见度必须在服务端强制执行。
- 数据源必须通过统一适配器返回规范化标签。`Fixture` 与 `Live` 必须在模型、UI、测试和文档中清晰区分。
- 不保存外部接口原始响应，只保存实现匹配所需的最小规范化字段。
- 中文用户界面和产品文档使用中文；代码、变量、注释和 commit message 使用英文。

## 安全约束

- 永远不要读取、输出或提交 `.env`、凭据、token、cookie、私钥或账号密码文件。
- 不硬编码生产 secret。演示账号和演示数据只能在显式 `DEMO_MODE` 下存在，并必须标记为演示。
- 只接入无需凭据且已经验证的公开只读接口，或明确标记为 `Fixture` 的模拟数据。
- 外部 HTTP 请求必须使用 HTTPS、超时、响应大小限制、输入白名单与稳定错误码；不得记录原始个人数据。
- 所有修改状态的表单必须有 CSRF 防护；生产模式不得运行 Flask debugger。

## 验证命令

```powershell
python -m unittest discover -s tests -v
node --test tests/match_flow.test.mjs
python -m compileall -q app tests tools run.py
python tools/harness_cli.py
git diff --check
```

涉及外部数据源时，测试默认使用本地 stub；Live smoke 仅限无需凭据、只读且可安全重复的请求。涉及 UI 时检查 390×844 与桌面关键页面，并保存可复核证据。

## 完成标准

- PRD P0 验收矩阵无未解释缺口；安全和真实性阻断项全部关闭。
- 核心用户链路、失败分支和权限边界有自动化测试。
- README、演示脚本、声明清单与实际运行能力一致，不把 Fixture、规划或截图写成 Live/生产证据。
- 最终提交只存在于 `competition/prd-hackathon`，工作区干净，完整验证通过。
