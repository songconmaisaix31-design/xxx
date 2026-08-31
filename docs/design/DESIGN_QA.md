# Design QA：匿名匹配流程扩展

## 比较目标

- 流程参考：`prototypes/prototype2.0.html`。按用户澄清，仅参考首页双入口、待匹配、三阶段计算、单个结果、换一位和进入会话的状态顺序，不将其作为视觉还原目标。
- 视觉真值：`docs/brand/BRAND_SPEC.md` 与 `app/static/qa/mobile-home.png`，即现有“可信关系实验板”视觉系统。
- 实现证据：
  - `docs/qa/match-flow-ready-mobile-390.png`
  - `docs/qa/match-flow-searching-mobile-390.png`
  - `docs/qa/match-flow-result-mobile-390.png`
  - `docs/qa/match-flow-ready-desktop-1100.png`
- 同屏比较证据：`docs/qa/match-flow-comparison.png`

## 视口与归一化

- 手机 CSS 视口：`390 × 844`，`deviceScaleFactor` 由 Codex in-app Browser 管理。
- 手机源基线与三张实现截图均由浏览器捕获为 `375 × 812` 像素；同屏板直接使用等尺寸像素，不做不同密度间的视觉判断。
- 额外响应式检查：`320 × 720`、`360 × 820`、`430 × 820`、`760 × 900`、`1100 × 900`。
- 桌面实现截图：`docs/qa/match-flow-ready-desktop-1100.png`。
- 主题与登录态：浅色、演示账号已登录。

## 全视图比较

`docs/qa/match-flow-comparison.png` 将既有手机首页视觉基线和新的 idle / searching / result 三个状态放在同一画布中。新流程延续暖象牙纸面、粗黑边界、硬阴影、中文重型标题、黄色事实层、紫色品牌层和绿色进行/完成状态；没有把 `prototypes/prototype2.0.html` 的圆角柔和视觉搬入现有产品。

## 聚焦比较

- 待匹配：`match-flow-ready-mobile-390.png`。重点检查标题换行、状态胶囊、真实品牌资产、主按钮和移动底栏。
- 匹配中：`match-flow-searching-mobile-390.png`。重点检查进度条、三阶段文字状态、`aria-busy`、可滚动密度与底部操作间距。
- 单个结果：`match-flow-result-mobile-390.png`。重点检查分数层级、问号共同点、开启会话和换一位动作。
- 桌面准备页：`match-flow-ready-desktop-1100.png`。重点检查双栏比例、规则面板、页头导航与首屏层级。

## 必查表面

- 字体与排版：沿用 `--neo-font-display` / `--neo-font-body`；标题与正文权重、行高和换行与既有页面一致。320px 下没有截断。
- 间距与布局：手机单列、桌面双栏；320/360/390/430/760/1100 均无横向溢出。390px 匹配中滚动到底后，操作区与固定底栏仍有 `231px` 可用间距。
- 颜色与令牌：全部来自既有黄色、紫色、绿色、珊瑚色与纸面令牌；新增 CSS 中无渐变和游离色彩角色。
- 图像质量：只复用真实 `brand-mark.png`，390px 检查中损坏图片为 `0`；没有 CSS/div 插画、内联 SVG、emoji 或占位头像。
- 文案与内容：流程解释区分硬筛、标签相似度和匿名结果；未向用户公开权重，未暗示前端在计算匹配。
- 图标：新流程没有引入新的图标家族；品牌标记继续使用现有位图资产。
- 状态与交互：已测试开始、自动完成、跳过等待、取消、换一位和开启匿名会话；取消后回 idle，换一位生成新尝试，旧令牌不能完成新任务。
- 可访问性：三步骤有文字状态，进度条有 `role="progressbar"`，状态文字有 `role="status" aria-live="polite"`；控件键盘可达，390px 可见触控目标无小于 44px 项；减弱动画路径由纯控制器测试验证。

## Findings

没有可执行的 P0、P1 或 P2 视觉 / 交互差异。

## Open Questions

无。参考 HTML 的视觉语言已按用户要求明确排除，仅保留流程结构。

## 比较历史

- Pass 1：同屏比较没有发现 P0/P1/P2；无需视觉返工。
- 行为补强不属于视觉返工：实现额外增加取消、旧尝试失效、重复开始幂等、无 JavaScript 完成和减弱动画快速完成，修复了参考原型中的真实流程缺口。

## 浏览器验证

- 主流程：`首页 → /matches → /matches/searching → /matches/<candidate_id> → /conversations/<id>` 已完成。
- 分支：`result → retry → searching → cancel → idle` 已完成。
- 控制台 warning / error：`0`。
- 320/360/390/430/760/1100 关键页面横向溢出：`0`。
- 手机关键页面损坏图片：`0`。

## Implementation Checklist

- [x] 流程由 Flask 路由和签名 session 状态机拥有。
- [x] searching HTML 不包含候选 ID、匿名代号、展示分、原始分或结果 JSON。
- [x] JS 只负责时序和提交普通 POST 表单。
- [x] 无 JavaScript、减弱动画、取消和换一位均可完成。
- [x] 全部 P0/P1/P2 已清零。

final result: passed
