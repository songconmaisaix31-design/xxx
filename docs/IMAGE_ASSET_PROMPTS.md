# V2 图像资产生成记录

本文件完整保留两项 V2 基础资产的 ImageGen 提示词，并登记后来加入的三张会话工具图。基础资产没有使用 CLI、API key 或外部下载；三张会话图的精确历史提示词未随文件提交，因此这里只记录事实元数据，不反向编造提示词。

## 纸张点阵纹理

- 项目路径：`app/static/img/paper-dot-grid.png`
- 内置生成原件：`C:\Users\HUAYUE\.codex\generated_images\01a0287d-4e35-7ec1-bf52-9ba0b5a9446f\exec-2ae87ce0-c6cd-4477-9dd3-fb61e28b704a.png`
- 用途：页面低对比背景纹理
- 最终提示词：

> Create a seamless square background texture for a polished Chinese neo-brutalist web interface. Warm ivory uncoated paper, extremely subtle evenly spaced micro-dot grid, almost invisible natural paper grain, flat even lighting, low contrast, clean and quiet. No text, no letters, no numbers, no logo, no icon, no object, no illustration, no border, no frame, no gradient, no vignette, no shadow, no watermark. The tile must repeat cleanly without visible seams and must never compete with interface content.

## 品牌标记与 favicon

- 项目路径：`app/static/img/brand-mark.png`
- 内置生成原件：`C:\Users\HUAYUE\.codex\generated_images\01a0287d-4e35-7ec1-bf52-9ba0b5a9446f\exec-82f553e6-d799-475e-8819-366d1010884d.png`
- 用途：页头品牌识别、浏览器标签图标
- 最终提示词：

> Create a single polished square brand icon asset for a Chinese privacy-first social matching product called Real Tags / 真实标签, matching the provided neo-brutalist design direction. Composition: warm ivory background, one bold black rounded-square outer frame, inside an abstract original symbol suggesting two anonymous signals finding resonance and a small verified dot. Use only flat solid colors: black #12110E, electric purple #5B48FF, acid green #51D000, sunflower yellow #FFE45C, with at most a tiny coral #FF5F41 accent. Very thick consistent black strokes, compact geometric construction, optically centered, high contrast, crisp at 24px favicon size, generous safe margin. No text, no letters, no numbers, no emoji, no gradients, no shadows outside the icon, no mockup, no device frame, no extra objects, no transparency halo. Output one centered icon on a square 1:1 canvas.

## 会话任务工具图

| 项目路径 | 用途 | 当前规格 |
| --- | --- | --- |
| `app/static/img/chat-tool-dice.webp` | 摇骰子话题工具 | 720×720 WebP，装饰图 |
| `app/static/img/chat-tool-task.webp` | 随机任务卡工具 | 720×720 WebP，装饰图 |
| `app/static/img/chat-tool-unlock.webp` | 匹配点解锁工具 | 720×720 WebP，装饰图 |

三张图片在 `conversation.html` 中使用空 `alt`，因为同一按钮已经提供完整可见名称与说明；同时声明固定宽高、`loading="lazy"` 和 `decoding="async"`。如需重生成，应先补写新的可复现提示词、模型与日期，再替换资产。
