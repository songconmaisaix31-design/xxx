# TagPulse CLI

`tools/harness_cli.py` 是项目的零额外 Python 依赖 Harness Engineering 控制台。编排器本身只使用 Python 标准库，并通过当前解释器启动检查，因此会自动使用已激活虚拟环境中的 Flask。默认和 `core` 管道还会执行 `node --test`，所以完整验证需要 Python 3.10+、项目 Python 依赖以及支持 Node 内置测试运行器的 Node.js；应用运行本身不需要 Node，也没有 npm 依赖。

当前默认全量管道包含 28 项 Python 测试与 4 项 Node 测试：23 项核心/专项检查、5 条完整产品旅程、4 项匹配动效状态检查。

## 常用命令

```powershell
# 全量：运行时、语法、匹配动效、核心、管理员/会话/附近专项、完整 HTTP workflow
.\harness.cmd

# 只跑完整产品流程
.\harness.cmd flow --verbose

# 查看场景覆盖图
.\harness.cmd map

# 只做 Flask / 语法预检
.\harness.cmd doctor

# 显式运行本地活动定时任务（会更新 instance 数据库）
.\harness.cmd scheduler

# 启动开发服务器
.\harness.cmd serve
```

全局 `--no-color` 必须放在子命令之前，例如 `.\harness.cmd --no-color run --suite core --fail-fast`。

跨平台或不希望使用 Windows 启动器时，将 `.\harness.cmd` 替换为 `python tools/harness_cli.py` 即可。

`run --suite core` 只跑核心单元与 SSR 烟雾检查；`run --suite e2e` 只跑完整 HTTP 流程。`--verbose` 展示每一个成功阶段的原始测试输出，`--fail-fast` 在失败时立即停止，`--no-color` 适合 CI 日志或不支持 ANSI 的终端。

## 安全边界

默认的 `run` 和 `flow` 全部使用测试自行创建的临时 SQLite 数据库，绝不会修改 `instance/realtags.sqlite3`。活动定时任务被设计成独立的 `scheduler` 子命令，只有用户明确调用时才会扫描并更新本地持久化活动。

## 管道阶段

```text
Preflight  →  Syntax  →  Match motion  →  Core checks  →  Feature checks  →  E2E harness
```

完成时终端会输出每个阶段的 PASS/FAIL 与耗时，并以 `VERIFIED` 或 `BLOCKED` 作为最终机器可读的进程状态：成功为退出码 `0`，失败为 `1`，用户中断为 `130`。
