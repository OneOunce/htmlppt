# AGENTS.md

> 给后续接手这个项目的 AI / 人看的**项目说明书**。
> 重点不是"有哪些功能"，而是**为什么这么写**，以及**哪些地方一改就会坏**。
>
> **本文件按社区通行约定命名为 `AGENTS.md`（复数）** —— 那是 OpenAI Codex、GitHub Copilot、Google Gemini 等主流工具默认读取的标准文件名。单数 `AGENT.md` 是 Sourcegraph AMP 的早期变体，部分工具（如 Devin）仍会读它，但新项目一律用复数。
>
> **这里只写"当下的规则"。** 项目历史上踩过的坑、犯过的错、已解决的问题归档在 **`MEMORY.md`**（记忆与状态），日常流水在 `.workbuddy/memory/YYYY-MM-DD.md`（短期工作日志）。
>
> **开源读者注意**：本项目对外发布后，绝大多数 Agent 的任务是「**为用户生成一套演示分页**」，不是维护放映器。请先看下面的「快速路由」，选对你的角色再决定读多少。

---

## 〇、快速路由：先选你的角色

同一个仓库，三种读者的任务完全不同，**别读多余的章节**：

| 你是谁 | 你的任务 | 你该读什么 | 你不该碰什么 |
| --- | --- | --- | --- |
| **内容生成 Agent**（最常见） | 用户说「帮我做一套关于 X 的演示」 | `README.MD` 第二部分（制作规范）+ `pages/_template.html`（模板）。本文件只需读第一节 | `index.html`、`generate_index.py`、`js/*.js`——一行都不要改 |
| **放映器维护 Agent** | 改翻页、字幕、菜单、构建脚本等本体行为 | 本文件**全文**，先背第七节「不可破坏的不变量」，再按第八节方法验证 | `pages/*.html`（那是用户的内容） |
| **人类用户** | 放映、加页、改字幕 | `README.MD` 第一部分，读完即可停止 | 同上 |

**内容生成 Agent 的最短路径**（详见 `README.MD` 第二部分，这里只给骨架）：

1. 填**页序大纲**与**术语表**——不填大纲不许开写；
2. 复制 `pages/_template.html` → `pages/<序号>-<页名>.html`，只改 `<title>`、`<main>` 文字、`slide-foot`，**STYLE-BLOCK 逐字节保留**；
3. `python generate_index.py` 更新清单 → `python generate_index.py --check` 确认；
4. `python check_style.py` + 禁用项扫描（`<script>` / 外链 URL / 行内 style / 写死页码，grep 应无输出）；
5. **有浏览器权限时**：`python serve.py` 起服务，逐页实际翻看（无滚动条、右键页码的缩略图非全黑、版式一致）。推理不算证据，采样才算。

做完这五步即可交付。只有任务变成「改放映器本体」时，才继续读下面的架构与不变量。

---

## 本项目的 Agent 文件分工

| 类别 | 文件 | 作用 |
| --- | --- | --- |
| 指令与上下文 | **`AGENTS.md`**（本文件） | 项目规则、工作流、架构约束、编码规范 |
| 记忆与状态 | **`MEMORY.md`** | 长期记忆：历史失误、坑位档案、已验证的结论 |
| 记忆与状态 | `.workbuddy/memory/YYYY-MM-DD.md` | 短期工作日志：当天改了什么、验证结果 |
| 指令与上下文 | `README.MD` | 对用户的放映说明 + 分页制作规范 |
| 指令与上下文 | `pages/_template.html` | 样式的唯一真源与可复制骨架 |

**读法**：改代码前先读本文件的「不可破坏的不变量」和「验证方法」；想知道"以前在哪儿栽过跟头"，翻 `MEMORY.md`。

> **单数 `AGENT.md` 已不在根目录。** 它原本只是 16 行兼容指针（给仍读单数文件名的老工具用），现已按用户要求移入 `.ignore/AGENT.MD`，与旧版全文归档 `.ignore/htmlppt/AGENT.MD-20261106170347.md` 放在一起。`AGENTS.md` 仍是唯一的面向 Agent 的权威说明书，别再往根目录恢复单数文件。

---

## 一、项目是什么

一个**零依赖、零框架、零构建的 HTML 放映器**。用浏览器打开就是 PPT：

- 左右方向键 / ↑↓ 翻页，空格逐句翻字幕
- 字幕条可拖动、可三档控制显隐
- 右键出玻璃风格菜单：显示字幕、字幕显示方式、分页跳转（带真实缩略图）
- **演讲者模式**：`presenter.html` 在副屏当控制台——当前页预览、上一页/下一页、全部页跳转、字幕提词、计时器，还能一键把观众屏收成纯幻灯片

### 为什么有这个项目

AI 时代有两个事实：

1. **代码能力提升、代码成本下降**——AI 用 HTML/CSS 能做出比传统 PPT 更精美的版式与动画；
2. **但 AI 直接操纵 PPT 很难**——python-pptx / Office 自动化技术壁垒高、上下文消耗大，AI 很难在较短的上下文中保持稳定的高质量输出。

而用户与 Agent 又确实需要「展示、解说作品」的能力。htmlppt 的解法是把演示**降维**：放映交给一个一次写好、永远不动的放映器；创作只剩一件事——**往 `pages/` 里放一页页纯 HTML**。这正是 AI 最擅长、质量最稳定的工作形态。

设计目标（用户原话，优先级高于一切技术偏好）：
**一个单独的、简约的 HTML 文件，用来放映分页 HTML。**

这句话约束了两个"不能"：
- 本体必须是**单个 `index.html`**，不引入框架、不打包、不生成副本。
- 幻灯片必须能**作为独立 html 文件单独存在**（可以单独打开、单独发人），不能塞进 `index.html` 里维护。

> **`presenter.html` 是这条目标的唯一例外，且是「可选伴随页」。** 演讲者视图必须活在与观众屏**不同的窗口**里，而第二个窗口只能是另一个文档——这是浏览器给的唯一路径，没有"同一份代码渲染到两个窗口"的做法（`document.write` 拼模板也是同一个文件在干活，只是把 HTML 藏进了 JS 字符串）。所以约定是：**放映本体仍是单个 `index.html`，`presenter.html` 不参与放映，删掉它放映器照旧完整可用。**

---

## 二、文件结构

```
htmlppt/
├── index.html              # 放映器本体：界面 + 全部交互逻辑（约 1450 行）
├── presenter.html          # 演讲者控制台（可选伴随页，不参与放映；删掉不影响放映）
├── serve.py                # 本地 HTTP 服务（同源必需，见第四节）
├── serve.bat               # Windows 一键启动 serve.py
├── generate_index.py       # 构建脚本：扫描 pages/ → 整份写 js/*.js（不碰 index.html）
├── generate_index.py.bat   # Windows 一键运行构建
├── check_style.py          # 样式块一致性校验（与 README 第二部分配套）
├── subtitle.txt            # 字幕源文本，一行一句
├── js/                     # 两个数据文件，整份由脚本生成，手改会被覆盖
│   ├── pages.js            #   const SLIDE_PAGES / slideFiles / slideTitles
│   └── subtitle.js         #   const SUBTITLE_TEXT
├── pages/                  # 分页目录，放什么就放映什么
│   ├── _template.html      # ← 样式的唯一真源（下划线开头，扫描时自动忽略）
│   ├── 1-封面.html         # ← 这三行是「序号-页名」的形状示例，
│   ├── 03-目录.html        #    不是固定文件名；叫什么都行，见下方命名规则
│   └── 7-结束页.html
├── AGENTS.md               # ← 本文件：架构与不变量（权威）
├── MEMORY.md               # 历史失误与坑位档案
├── README.MD               # 用户说明 + 分页制作规范
├── docs/                   # 每轮改动说明与验证截图
└── .workbuddy/memory/      # 跨会话工作日志
```

> `pages/` 那三行是**示例形状，不是本仓库的固定文件名**。清单由脚本每次扫描目录得出，没有任何写死的名单；本仓库现有的四页是 `slide-1.html` ~ `slide-4.html`（旧命名，脚本仍兼容，页名回落 `<title>` / `<h1>`），你随时可以按下面的规则改名。

**分页命名规则**（构建脚本按此解析，`pages/` 里放什么就放映什么；下表同样是**示例**，不是仓库里必须存在的文件）：

| 文件名 | 序号 | 页名 |
| --- | --- | --- |
| `3-目录.html` | 3 | 目录 |
| `03-目录.html` | 3 | 目录 |
| `0006-结束.html` | 6 | 结束 |
| `5.html`、`slide-5.html` | 5 | 空 → 回落 `<title>` / `<h1>` |

- 序号是自然数、**位数不限**，只按数值比大小：`1 < 2 < 03 < 0006`。前导零只是文件管理器里的视觉对齐，不参与排序，也不影响显示。
- 排序后**显示序号由数组下标决定**（1、2、3…），所以 `1-`、`03-`、`7-` 这种带空号的目录会自动挤紧成 1、2、3，不跳号。
- 页名取「序号-」之后的文字；缺页名时回落分页文件里的 `<title>`，再回落第一个 `<h1>`，都没有就只显示序号，不显示空标签。
- 分隔符接受半角/全角横线与下划线，两侧允许空格；`_` 或 `.` 开头的文件、`template.html` 默认忽略。
- 无序号文件默认忽略并提示；要收录加 `--append-unnumbered`，会按文件名接在末尾。
- **同号（如 `03-目录.html` 与 `3-摘要.html`）属于歧义**：脚本按文件名定序并警告，`--strict` 直接报错退出。

**数据不再写进 `index.html`**，而是拆成两个整份生成的数据文件，统一放在 `js/` 目录（文件名固定，构建脚本只认这两个名字）：

```js
// js/pages.js（脚本整份生成）
const SLIDE_PAGES = [ { "file": "03-目录.html", "title": "目录" }, … ];
const slideFiles  = SLIDE_PAGES.map(function (p) { return p.file; });
const slideTitles = SLIDE_PAGES.map(function (p) { return p.title; });

// js/subtitle.js（脚本整份生成）
const SUBTITLE_TEXT = "第一句\n第二句";
```

`index.html` 只用两个外链引入，都在 `<body>` 末尾的脚本序列里，各占一行：

```html
<script src="js/subtitle.js"></script>   <!-- 必须在字幕解析脚本之前 -->
<script src="js/pages.js"></script>      <!-- 必须在 loadSlide 所在脚本之前 -->
```

`#subtitle` 元素本身留空，启动时由 `SUBTITLE_TEXT` 填进 `textContent`——**DOM 结构留在 `index.html`**，因为拖拽、悬停显隐、左右按钮都挂在它上面，结构一变逻辑就得跟着改；脚本只负责文本，职责干净。

**关键收益：脚本对 `index.html` 零写入。** 不再需要哨兵标记、不再需要"定位失败"的错误分支，也不存在"改个缩进就找不到块"的问题。`index.html` 你怎么重排、怎么加注释、怎么调顺序，构建结果都一样。

唯一的前提是那两行 `<script src>` 还在——脚本每次会检查，**引用了就正常工作，缺失只提示不拦截**（`index.html` 里也有兜底：`pages.js` 没加载时页面显示一句「缺少 js/pages.js」，而不是一屏 ReferenceError）。

改名、增删分页后跑一次 `python generate_index.py` 即可；`--dry-run` 只看结果不写，`--check` 校验产物是否已最新（不一致退出码 1，可挂 CI），`--strict` 把命名歧义当错误，`--no-subtitle` 只更分页不碰字幕。

**幻灯片格式约定**：`pages/*.html` 是裸片段，浏览器直接打开它也能看（有默认白底），但不带任何样式与脚本。不要往里面加 `<script>`——理由见 `MEMORY.md`「错误 2」。

---

## 三、`index.html` 内部地图

单文件按顺序分成这几段，改哪块先看这张表（行号随改动漂移，**以内容对照为准**）：

| 行号 | 内容 |
| --- | --- |
| 6–437 | `<style>`：设计变量 `:root` + 全部样式（含缩略图三档、悬浮滚动条 `.pages-rail`、字幕上方导航 `.subtitle-navs`、干净输出 `html.is-clean`、轻提示 `#toast`） |
| 438–446 | `<head>` 里的首帧脚本：读 `localStorage['ppt-clean']` 给 `<html>` 挂 `is-clean`（见不变量 15） |
| 448–513 | HTML 骨架：`#slide-container`、`#page-indicator`、`#controls`、`#subtitle-container`（**初始带 `is-hidden`**；内含 `.subtitle-navs` 按钮行 + 空的 `#subtitle`）、`#toast`、`#ctx-menu`（page 组含「显示字幕」「演讲者模式」「全屏显示」；subtitle 组三档；pages 组含列数切换与 `.pages-body` 内的 `#pages-grid`、`#pages-rail`） |
| 515 | `<script src="js/subtitle.js">`：字幕文本常量 |
| 516–571 | 字幕行解析（用 `SUBTITLE_TEXT` 填充 DOM）、`stepSubtitle()`、空格翻句、方向键翻页、`P` 开演讲者窗口（**没有 `F` 全屏键**，见不变量 20） |
| 572–1147 | 字幕三档显隐 + 右键菜单三上下文 + 分页缩略图面板 + 列数切换 + 悬浮滚动条 + **观众屏全屏控制**（`enterFull/exitFull/toggleFull/restoreFull`）+ `openPresenter()` + `toast()`（导出 `window.pptSubtitle`、`window.pptPresenter`） |
| 1148 | `<script src="js/pages.js">`：分页清单常量 |
| 1149–1326 | 缺清单兜底提示 + 幻灯片加载 + `iframe.onload` 注入（含全屏补位）+ `prev/next` + 导出 `window.pptPages` |
| 1327–1383 | 字幕拖拽（Pointer Events + 指针捕获） |
| 1384–1423 | 字幕左右导航按钮（点击不触发拖拽），导出 `window.pptSub` |
| 1424–1462 | 跨窗口同步桥：监听 `storage`，把 `ppt-current` / `ppt-sub-idx` / `ppt-clean` 映射到页面动作 |

两个外链的位置有硬约束：`subtitle.js` 必须在字幕解析脚本**之前**，`pages.js` 必须在 `loadSlide` 所在脚本**之前**——它们是普通 `<script>`，同步执行，顺序错了就是 `undefined`。

跨模块靠**三个**全局对象通信，不要再开新的全局：
- `window.pptSubtitle` → `{ onMove, openMenu, closeMenu, getMode }`
- `window.pptPages` → `{ files, titles, current, go }`
- `window.pptSub` → `{ show(idx, opts), index(), total() }` —— 改字幕句号的**唯一门**（`subtitleIdx` 是脚本级 `let`，别的脚本只能读不能安全地改）
- `window.pptPresenter` → `{ open(), fullscreen(), restore() }` —— `open` 供菜单项与 `P` 键；`fullscreen` 是 `toggleFull`（**只由右键「全屏显示」点击触发**，不再绑键位）；`restore` 只给 iframe 注入用（见第五节全屏）
- 另有三个由外链提供的全局常量：`SUBTITLE_TEXT`、`SLIDE_PAGES`、`slideFiles` / `slideTitles`

### `presenter.html` 内部地图（689 行）

| 行号 | 内容 |
| --- | --- |
| 15–287 | `<style>`：同一套 `:root` 变量 + 控制台布局（顶栏 / 舞台 / 字幕区 / 右列缩略图） |
| 289–341 | HTML：`#bar`（页码、页名、计时器）、`.stage`、`.sub`（当前句 / 下一句 / 全文列表）、`.thumbs`、`#allPages`、`#cleanBtn` |
| 342–343 | `<script src="js/subtitle.js">`、`js/pages.js`（与放映器共用同一份生成数据） |
| 344–686 | 全部逻辑：`fitStage()`、`loadPage()`、`renderSub()`（含 `centerSub()` 居中当前句）、`setClean()`、计时器、键盘、`storage` 监听 |

**它自己不生成任何数据、也不反向写 `js/*.js`。** 所有页与字幕都来自那两个外链文件，所以两边永远同源同步。

**跨窗口同步协议（四个 localStorage 键）**：

| 键 | 谁写 | 含义 |
| --- | --- | --- |
| `ppt-current` | 两边 | 当前页号（放映器 `loadSlide()` 本来就在写） |
| `ppt-sub-idx` | 两边 | 当前字幕句号 |
| `ppt-clean` | 演讲者窗口写，放映器读 | 观众屏是否「干净输出」`'1'`/`'0'` |
| `ppt-subtitle-mode` | 只有放映器 | 字幕三档，**不同步**——它属于观众屏自己的显示偏好 |

通道是 `storage` 事件（不是 `BroadcastChannel`）：它只在**别的窗口**写入时触发，同一窗口自己写不会回声；写同值也不触发事件，所以「收到通知 → 执行 → 再写回同值」这条链天然收敛。

---

## 四、架构核心：iframe 隔离是这个项目所有坑的总根源

幻灯片用 `<iframe>` 加载，且**铺满整个视口**。这带来一条贯穿全项目的铁律：

> **鼠标移动、键盘、右键、点击，只要发生在幻灯片上，事件就只存在于 iframe 文档内部，父页面一个都收不到。**

父页面 `document` 上的 `mousemove` / `keydown` / `contextmenu` / `mousedown` 监听器，在幻灯片区域内**全部形同虚设**。这就是为什么：

- 键盘转发、靠近显隐、字幕悬停、右键菜单、点击关闭菜单，**一律注入到 `iframe.contentWindow.document`**（在 `iframe.onload` 里，用 `try/catch` 包住）；
- 注入能成立的前提是**同源**。

**同源是硬门槛**：
- ✅ `python serve.py` 起本地服务后访问 `http://127.0.0.1:8000/`
- ✅ Firefox 双击打开（Firefox 的 `file://` 同源）
- ❌ Chrome / Edge 双击打开 `index.html`（`file://` 下本地 iframe 被判跨域，读 `contentWindow.document` 直接抛 `SecurityError`，所有注入静默失效，只剩翻页能用）

所以：**"Chrome 双击 + iframe + 键盘能从幻灯片里传出来"三者无法同时成立**，这是浏览器安全模型决定的，不是代码问题。不要再尝试绕过。

因为 iframe 与父页面**同视口、坐标系完全一致**，注入的监听里可以直接拿 `e.clientX/Y` 去和父页面元素的 `getBoundingClientRect()` 做比较——不需要任何坐标换算。

---

## 五、设计语言：一套变量管到底

所有控件必须看起来是同一个东西。统一由 `:root` 的变量驱动，**禁止在组件里写死颜色/圆角/间距**：

```css
--c-glass:          rgba(18,20,26,0.5)    /* 常态玻璃底 */
--c-glass-hover:    rgba(18,20,26,0.82)   /* 悬停/按钮实际底色 */
--c-glass-disabled: rgba(18,20,26,0.28)   /* 禁用态 */
--c-border:         rgba(255,255,255,0.16) /* 1px 描边 */
--c-text:           #eef1f6
--c-accent:         rgba(120,170,255,0.9)  /* 当前项高亮、焦点框 */
--blur:             12px                    /* 毛玻璃模糊半径 */
--radius-card:      12px                    /* 统一圆角，卡片式 */
--btn:              48px
--edge:             24px                    /* 四边统一间距 */
--ease:             .22s cubic-bezier(.2,.7,.3,1)
--font:             系统字体栈
```

四条风格规则：

1. **只有毛玻璃，没有阴影。** 用户明确要求去掉所有 `box-shadow` 和发光；`--shadow` 变量已删除，不要再加回来。
2. **圆角一律 12px 卡片**，不用圆形。按钮、页码、字幕条、菜单全是同款圆角矩形玻璃。
3. **边缘间距一律 `--edge`（24px）**：翻页按钮距左右 24、页码距顶 24、字幕距底 24，实测四者精确相等。要调只改这一处。
4. **悬停反馈靠"背景变亮"，不靠描边变色。** 菜单当前项 = 背景微亮 + 6px accent 圆点，跟其它控件同一套语言。

通用类 `.nav-btn` 被翻页按钮和字幕导航按钮共用，改它等于同时改两处，这是刻意设计。

---

## 六、功能与实现要点

| 功能 | 实现要点 |
| --- | --- |
| 翻页 | `←` `↑` 上一页，`→` `↓` 下一页；到首/末页按钮 `disabled` |
| 空格翻字幕 | 单击 → 300ms 后下一句；阈值内双击 → 上一句（`threshold = 300`，第 475 行） |
| 控件靠近显隐 | 到按钮中心距 < 90px 显示，> 200px 收起（迟滞）；页码按**点→矩形最短距离**，70 / 160 |
| 字幕三档 | `persist-show` / `hover`（默认）/ `persist-hide`，存 `localStorage['ppt-subtitle-mode']` |
| 字幕拖拽 | Pointer Events + `setPointerCapture`；边界 `KEEP = 48px` 至少留可见；中心锚点 `translateX(-50%)` |
| 字幕导航按钮 | 两个 26px 按钮在字幕**正上方居中**（`.subtitle-navs` 绝对定位，`left:50%;bottom:100%;translateX(-50%)`）；不参与容器宽度——见下方「按钮为什么放上方」 |
| 右键菜单（三上下文） | `data-context` = `page`（「显示字幕」「演讲者模式」「全屏显示」）/ `subtitle`（三档，贴字幕上沿弹出）/ `pages`（缩略图网格） |
| 页码跳转面板 | 页码 `pointer-events:none`，右键落在 iframe 里 → 用**坐标矩形命中 + 要求 `.show`** 判断；首次打开才构建缩略图 |
| 缩略图 | 内嵌 `iframe` 指向真实分页 HTML，1280×720 渲染后按 `--thumb-scale` 缩放；三档宽度见下 |
| 缩略图下方标签 | `.page-cap` = 序号徽标 `.page-num`（数组下标，1、2、3…）+ 页名 `.page-name`（取自文件名「序号-页名」，长名省略号截断）；序号与文件名里的编号无关 |
| 列数切换 | 面板右上三个图标按钮 `data-cols="1\|2\|3"`，写 `.pages-grid` 的 `data-cols`；选择存 `localStorage['ppt.pagesCols']`，默认双列 |
| 面板滚动 | 网格 `max-height:min(62vh,420px)`，超出在容器内滚动；**原生滚动条整条隐藏**，改用面板右缘**外侧**的自绘悬浮滑轨 `.pages-rail`（见下） |
| 演讲者模式 | 页面右键菜单「演讲者模式」或按 `P` → `openPresenter()` → `window.open('presenter.html')`；已开则只 `focus()`。位置先按主屏偏移，`getScreenDetails()` 可用时再挪到副屏（Chromium + 用户授权才成立） |
| 观众屏全屏 | 进/出全屏的唯一入口是**页面右键菜单 →「全屏显示」**（`toggleFull()`；全屏中该项 `class="active"`，再点一次退出并取消高亮）。开控制台后，观众屏的下一次点击也会自动补全屏（`restoreFull()`，iframe 内的点击在注入脚本里转给 `pptPresenter.restore()`）。**没有 `F` 快捷键**——理由见不变量 20。Chromium 下额外用 `navigator.keyboard.lock(['Escape'])` 把 Esc 从「退出全屏」手里抢过来（见下） |
| 弹窗被拦截 | 不弹 `alert`（会阻塞渲染线程），用 `#toast` 轻提示，3.6 秒自淡出——见不变量 17 |
| 干净输出 | `localStorage['ppt-clean']='1'` → `<head>` 里首帧就把 `is-clean` 挂到 `<html>`（不变量 15）；CSS 只压 `opacity`/`pointer-events`，`#controls` 用 `display:none` |

**缩略图的尺寸耦合**：`width` 与 `scale()` 必须同步改，比值恒为 `width / 1280`。三档都已算好并写死在 `.pages-grid[data-cols]` 里（第 243–245 行）：

| 档位 | `--thumb-w` | `--thumb-scale` | 网格总宽 |
| --- | --- | --- | --- |
| 单列 | 302px | .2359375 | 302 |
| 双列（默认） | 148px | .115625 | 302 |
| 三列 | 96px | .075 | 300 |

三档总宽刻意做成一致，切换时面板不跳宽度。**改任何一档的 `--thumb-w`，必须同步改 `--thumb-scale`**，且与 `aspect-ratio:16/9` 严格对应，否则出现半像素缝。

**滚动条是自绘的，别再改回原生。** 面板外是幻灯片（通常白底），原生滚动条只能待在面板内部：占 9px 宽、把网格中心挤偏 4.5px，样式还受引擎限制。现在原生整条隐藏（`scrollbar-width:none` 与 `::-webkit-scrollbar{display:none}` **两边都要写**——Chrome 认了前者就会忽略后者），滚动指示交给 `.pages-body` 里绝对定位的 `.pages-rail`：

- **位置**：`top:0;bottom:6px;right:-16px;width:4px` —— 面板 `padding 6px` + 边框 `1px` 之外再退 5px，实实在在落在面板**外面**；悬停 / 滚动中 / 拖动时胀到 6px 并加深（`.is-active` / `.is-drag`）。
- **比例**：`syncRail()`（第 600 行）按 `clientHeight / scrollHeight` 算滑块长度（下限 26px），按 `scrollTop / (scrollHeight - clientHeight)` 算位置；轨道长度取 `rail.clientHeight`，不要拿 `view` 顶替，否则滑块会偏短。
- **显隐**：只有真溢出才给 `.pages-body` 加 `has-scroll`（`opacity:1` + `pointer-events:auto`）；不溢出就整条收起并穿透点击。
- **三条交互**：pointerdown 落在滑块上直接拖；落在空白轨先跳到指针处再继续拖（都走 `setPointerCapture`）；滑轨不是滚动容器，指针停在上面时的 `wheel` 要手动转给 `.pages-grid`。
- **配色不能用半透明白**。滑轨在面板外、背后就是白底幻灯片，白色滑块等于隐形。用中性灰 `rgba(110,122,140,.45)` + `0 0 0 1px rgba(255,255,255,.22)` 描边：白底上是灰条，深底上靠描边勾轮廓。
- **定位要留白**：`positionMenu()`（第 777 行）里 pages 上下文用 `padRight = pad + 16`，否则面板贴到窗口右缘时滑轨会被裁掉一半。

**字幕按钮为什么放上方。** 原先两个按钮夹在字幕条左右（flex 行内），而字幕宽度随句子长短变化，按钮就被推着左右跑——切一句就得重新找按钮。现在 `.subtitle-navs` 绝对定位到 `bottom:100%` + 水平居中，容器宽度只由字幕决定，两个按钮相对视口中轴恒定不动（实测字幕宽 50.8px → 625px，按钮 x 坐标一字不差）。两个细节不能丢：

- **`padding-bottom:8px` 是 hover 的「桥」**。它让按钮行一直贴住字幕上沿，鼠标从字幕往上移不会掉出容器；一旦掉出，`#subtitle-container:hover` 就失效，按钮随即淡出并把 `pointer-events` 收回 `none`，那就再也点不到了。
- **拖拽守卫要从 `.subtitle-nav` 扩到 `.subtitle-navs`**，否则点在按钮行的空白缝里会开始拖字幕；上边界同时收成 `Math.max(-(elH-KEEP), NAV_H-4)`，保证按钮行不会整排被拖到屏幕外。

**历史坑（只在你把原生滚动条加回来时才相关）**：Chrome 只要出现 `scrollbar-width` / `scrollbar-color`，就会**整组忽略** `::-webkit-scrollbar` 定制，结果是系统细滚动条加两端小箭头。

**为什么「全屏」和「开控制台」不能在同一按键里完成。** 五条都是实测出来的硬约束（真实窗口 + CDP 真按键，Chrome 125），不要试图"优化"它：

1. `requestFullscreen()` 与 `window.open()` 都要**瞬时用户激活**，而一次请求就把这份激活用掉了；
2. 先要全屏、再开窗 → `window.open()` 被判成无手势，**直接拦截**（toast 报"浏览器拦截了弹出窗口"）；
3. 先开窗、再要全屏 → 请求落在**失去焦点**的文档上，被拒（`TypeError`）；
4. **先全屏、再延时开窗也不行**：全屏后 400ms / 1500ms 再 `window.open` 一率被拦（`window.open` 返回 `null`），加 `--disable-popup-blocking` 也一样——`requestFullscreen` 已经把这轮瞬时激活消耗掉了；
5. 即便全屏后隔一次真实点击再开窗，**打开新窗口会让当前窗口退出全屏**（Chromium 行为，`document.fullscreenElement` 变回 `null`）。

所以流程被固定成：**先开窗（消耗这次按键）→ 观众屏的下一次点击补全屏**。`restoreFull()` 守 `pointerdown` + `keydown`（放过 `Esc`），一旦 `wantFull` 且当前不全屏就补；`wantFull` 落盘 `localStorage['ppt-fs']`，刷新后仍然记得。两个细节：

- **iframe 里的点击必须转一手。** 幻灯片铺满视口，观众的第一下几乎必然落在 iframe 内，父页面的 `pointerdown` 收不到。注入脚本里 `parent.pptPresenter.restore()` 要在**同一个真实事件**里同步调用——不能用转发出去的新 `KeyboardEvent`，合成事件不带用户激活。
- **跨窗口请求全屏无解。** 在 `presenter.html` 里调 `opener.document.documentElement.requestFullscreen()` 会 `TypeError`，别试。

**为什么不给全屏配快捷键（`F` 已移除）。** 同上一条的根因：用户按 `F` 时焦点通常已经在幻灯片 iframe 里，父页面拿到的是注入脚本转发的**合成** `KeyboardEvent`，瞬时激活早已丢失 → 要么没反应、要么被浏览器拒（用户的原话是"`F` 一般会失效"）。改成**右键菜单「全屏显示」**后，每次都是父文档上的真实点击，稳定可进；退出也走同一项，选中态直接读 `document.fullscreenElement`（`refreshMenu()` 会在 `fullscreenchange` 里刷新）。

`navigator.keyboard.lock(['Escape'])` 是"持久全屏"的最后一块：它让 Esc 只关右键菜单、不再退出全屏（按住 Esc 约 2 秒仍能强退，浏览器保留的后门）。Firefox / Safari 没有这个 API，退出全屏只能走右键菜单（或在浏览器 UI 里退出）。

---

## 七、不可破坏的不变量

改代码前逐条对照，破了任何一条都会复现已修好的 bug：

1. **不给幻灯片文件注入任何脚本。** 生产幻灯片是独立的、别人的东西，改不动也不该改。
2. **隐藏态的控件保持 `pointer-events:none`。** 否则会挡住幻灯片里的文字选区。只有 `.show` 显示态才恢复可点击。
3. **绝不用 `iframe` 的 `mouseleave` 去隐藏控件。** 按钮显示后会盖在 iframe 上，鼠标落到按钮上 → iframe `mouseleave` → 隐藏 → 鼠标穿透回 iframe → 又显示 → 死循环 = 一直闪烁。隐藏只交给迟滞距离判定。
4. **绝不在 CSS 类里改字幕的 `transform`。** 拖拽是用**内联 `style.transform = 'translateX(-50%)'`** 做中心锚点的，类样式会覆盖内联值，拖一次就失效。隐藏态只改 `opacity` + `pointer-events:none`。
5. **信号判定必须有迟滞。** 单一半径会让鼠标在边界抖动时反复切换 → 闪烁。`EXIT` 必须大于 `ENTER`。
6. **不要用 `e.detail` 做事件去重。** `KeyboardEvent.detail` 是只读属性，赋值被静默忽略、值恒为 0。跨 document 派发本来也只触发一次，无需过滤。
7. **不要在父页面 `document` 上监听幻灯片区域内的事件。** 收不到。注入到 `iframe.contentWindow.document`。
8. **父页面收不到 iframe 里的点击。** 所有"点击别处关闭菜单"必须在 iframe 里另挂一个 `mousedown`。
9. **`js/pages.js` 与 `js/subtitle.js` 是整份生成的文件，手改必被覆盖。** 要改内容就改数据源（`pages/` 文件名、`subtitle.txt`）再跑构建。`generate_index.py` 不写 `index.html`，所以对 `index.html` 的任何手动改动都是安全的——唯一别动的是那两行 `<script src>`。
10. **不要给 `index.html` 引入外部依赖**（CDN、框架、图片资源）。单文件、纯本地、离线可用是项目底线。
11. **列数按钮不能放进 `.page-item` 里，`menu` 的 click 委托必须先判 `.pages-cols button`。** 否则点一下排列方式就直接跳页、还把面板关了。列数按钮点击后**不关面板**，但必须调 `positionMenu()` 重排——宽度变了不重排就会错位。
12. **悬浮滚动条必须留在面板外面，且不能用半透明白。** `.pages-rail` 靠 `right:-16px` 探出面板；挪进 `.pages-grid` 里就又退回"占 9px 宽度、把网格挤偏"的内嵌滚动条，`syncRail()` 的整套比例也一起错。面板外是白底幻灯片，白色滑块等于隐形——只用中性灰 + 描边。
13. **字幕容器的 `is-hidden` 必须写死在 HTML 里。** 默认档 `hover` 与 `persist-hide` 都要求首帧就不显示；如果等脚本 `applyMode()` 再补这个类，从 HTML 解析完成到脚本执行之间会渲染一帧字幕条，刷新时就是「闪一下就没了」。`applyMode()` 只负责运行期的三档切换（`persist-show` 会把它移除）。
14. **不要给 `index.html` 引入外部依赖之外再加"构建期写回 `index.html`"。** 构建脚本对 `index.html` 必须零写入——这是第二节"关键收益"的前提，破了它整份数据分离方案就白做了。
15. **`is-clean` 必须挂在 `<html>` 上、由 `<head>` 里的脚本在解析 `<body>` 之前挂好。** 挂在 `<body>` 上等末尾脚本加，刷新时会先画一帧字幕条/页码（与不变量 13 同一类错误）。这也是唯一允许在 `<head>` 里读 `localStorage` 的地方；别把它推广到字幕三档——三档的"默认态"要能被后续脚本反向覆盖，而干净输出本来就是运行时开关，不存在这个问题。
16. **跨窗口同步只走 `storage` 事件，并且只写「状态键」不写「命令」。** 不要退回 `window.opener` 直连：那样演讲者窗口一刷新就成孤儿、用户手动开第二个标签也控制不了。也不要同时维护 `BroadcastChannel` 第二通道——两条路径对不上时极难排查。
17. **不要用 `alert()` / `confirm()` / `prompt()`。** 它们会阻塞渲染线程直到用户点掉，放映途中弹出来等于把画面卡死；连无头自动化测试都会挂住。要提示就用 `#toast`。
18. **全屏只在观众屏自己的手势里请求，且开窗与全屏永远分两步。** 见第五节末尾那四条实测约束：`requestFullscreen` 与 `window.open` 抢同一份用户激活，而"开新窗口"必然让当前窗口退出全屏。别为了"一步到位"把 `enterFull()` 挪到 `window.open()` 前面，那会让弹窗被浏览器拦掉。
19. **演讲者窗口里当前句必须**在列表中线**并被特殊标记，不能只改底色。** 用户要的是"抬眼一瞬定位"：`centerSub()` 把当前行滚到列表垂直中间（`offsetFromCenter` 实测 ±0.3px），`.sub-list li.on` 给左侧 3px 主色竖条 + 淡蓝渐变底 + 内描边 + 加粗。别再退回 `scrollIntoView({block:'nearest'})`——它只在出界时动，视线仍要自己找。
20. **不要给全屏再绑键盘快捷键（`F` 已因此移除）。** 幻灯片 iframe 铺满视口，按键几乎都落在 iframe 里，父页面收到的是转发出来的合成 `KeyboardEvent`，瞬时激活早丢了 → `requestFullscreen` 必被拒（用户反馈的「`F` 一般失灵」就是这个）。全屏唯一入口是**右键菜单「全屏显示」**：真实点击必带激活，菜单项选中态直接读 `document.fullscreenElement`。

---

## 八、验证方法（改完必须这么验）

不要靠"看起来对"。这套项目已经证明推理会翻车。

**启动**：`python serve.py -p <port> --no-browser`

**驱动真实事件**：Edge 无头 + DevTools 协议

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --headless=new --disable-gpu --remote-debugging-port=9333 \
  --user-data-dir=/tmp/edge-test --no-first-run about:blank
```

用 Node 22 内置 WebSocket 连 CDP，`Input.dispatchMouseEvent` / `Input.dispatchKeyEvent` 派发真实输入。

**关键采样手法**：
- 判定闪烁：在固定点位稳定悬停 1 秒、每 50ms 采样 `.show` 是否存在，**统计切换次数，必须为 0**。
- 判定跟手：一步跳到远点（跳过 iframe），比对元素中心与目标点是否一致。
- 判定命中：用 `elementFromPoint` 查该坐标下的真实元素栈，别猜。
- **Node 侧读不到 `innerWidth`**，视口尺寸要从页面 `Runtime.evaluate` 取。

**构建层验证（几秒钟，先跑这个）**：
- `python generate_index.py --check`：产物是否与 `pages/`、`subtitle.txt` 同步，**退出码 1 = 过期**。
- `node --check js/pages.js`、`node --check js/subtitle.js`：确认生成物语法没坏。
- `index.html` 的内联脚本建议逐块抽到临时文件跑 `node --check`（按 `<script>` 正则切块），HTML 本身不报错不代表 JS 能跑。
- 想证明"构建没碰 `index.html`"，比对构建前后的 `mtime` 即可，比读代码可靠。

**收尾**：临时脚本放 `%TEMP%`，用完即删；确认 `grep` 无 `console.log` / `__ppt` 之类诊断残留；`<script>` 与 `</script>` 数量必须相等。

---

## 九、常见修改怎么做

| 想做的事 | 改哪里 |
| --- | --- |
| 调四边间距 | `--edge`（一处生效） |
| 调按钮/页码灵敏度 | 第 929–930 行 `ENTER_RADIUS / EXIT_RADIUS`、`IND_ENTER / IND_EXIT`（`EXIT` 必须 > `ENTER`） |
| 调字幕悬停灵敏度 | 第 522 行 `ENTER = 70, EXIT = 160` |
| 加字幕菜单项 | `#ctx-menu` 里 `data-group="subtitle"` 组内加 `.ctx-item`，逻辑在 `menu` 的 click 委托里 |
| 加页面菜单功能 | `data-group="page"` 组内加，注意 `refreshMenu()` 里的 active 规则要跟着扩 |
| 加幻灯片 | 放进 `pages/`，命名 `序号-页名.html`（`序号` 位数不限），跑 `python generate_index.py` |
| 看当前收进了哪些分页 | `python serve.py --list`（列 `pages/` 下全部 HTML，不再只认 `slide-*`） |
| 改字幕 | 编辑 `subtitle.txt`（一行一句），跑构建 |
| 调缩略图大小 | 改 `.pages-grid[data-cols]` 里的 `--thumb-w`，**同步**改 `--thumb-scale`（比值 = `width/1280`） |
| 改列数档位（比如加四列） | HTML 里加一个 `.pages-cols button[data-cols="4"]` + 一条 `[data-cols="4"]` 的宽度/缩放声明，JS 的 `applyCols()` 白名单同步放开 |
| 调面板滚动条样式 | 改 `.pages-rail` / `.pages-rail-thumb` 的宽度、颜色、圆角、悬停变粗幅度；滑块最小长度在 `syncRail()` 里（现为 26px）。别再往 `.pages-grid` 上加滚动条属性 |
| 让滑轨离面板更远 / 更近 | 只改 `.pages-rail` 的 `right`（现值 `-16px` ＝ padding 6 + 边框 1 + 间距 5）；同时确认 `positionMenu()` 的 `padRight` 还够用 |
| 加一档字幕模式 | `MODES` 数组 + `applyMode()` 分支 + 菜单项，三处都要动 |
| 改演讲者窗口的布局 | `presenter.html` 的 `<style>`：`main` 两列宽度、`.col-main` 两行比例（行高实际由 `fitStage()` 写成 px）、`.sub` 内部结构 |
| 改演讲者窗口的舞台尺寸 | `fitStage()` 里三个上限（撑满列宽 / `colH * 0.66` / 给字幕留 `MIN_SUB`），以及 `MIN_SUB` 本身 |
| 调字幕列表滚动条 | `presenter.html` 里的 `.sub-list::-webkit-scrollbar*`；**别在这里加 `scrollbar-width` 以外的标准属性到 Chrome 会认的地方** |
| 调当前句居中/高亮 | `presenter.html` 的 `centerSub()`（改成贴边/留 1/3 就改这里的 `delta`）+ `.sub-list li.on` 与 `li.on::before`（竖条宽高、渐变、描边） |
| 改全屏行为（自动进 / 菜单项 / 锁 Esc） | `index.html` 的 `enterFull()` / `exitFull()` / `toggleFull()` / `restoreFull()` / `lockEsc()`；入口是 page 组菜单项 `data-action="fullscreen"` 与 `window.pptPresenter.fullscreen`。**不要往 `keydown` 里加全屏键**（见不变量 20） |
| 同步新状态（比如「观众屏静音」「当前计时」） | 三处：写键的地方、`index.html` 末尾同步桥的 `storage` 分支、`presenter.html` 的 `storage` 分支 |

---

## 十、已知限制（不要试图修，是设计取舍）

1. **Chrome/Edge 双击 `index.html` 不能用键盘和右键菜单。** 必须经 `serve.py` 或 Firefox。这是同源限制，无法绕过。
2. **幻灯片里的输入框不转发键盘。** `INPUT` / `TEXTAREA` / `contenteditable` 内保留原生输入，这是刻意行为。
3. **缩略图首次打开面板时才构建**，会看到短暂空白；换来的是进页面时不加载全部分页。
4. **页码 `pointer-events:none` 是必须的**——它若可交互，会挡住靠近判定并在显示后自己压住鼠标，重演闪烁死循环。
5. **字幕隐藏后按空格翻句没有任何视觉反馈**，这是用户明确要求的（翻句与显隐完全解耦）。
6. **演讲者窗口能否自动上副屏，取决于浏览器。** `getScreenDetails()` 只有 Chromium 有，且要用户授权；Firefox 与部分 Linux 环境下拿不到，只能弹出后由用户手动拖到扩展屏。**不要**为了这个去引第三方库或要求 HTTPS。
7. **`file://` 下演讲者窗口可能与主窗口不同步。** `localStorage` 在部分浏览器的 `file://` 下按文件隔离，两个页面各存各的。要同步就必须走 `serve.py`（本来 Chrome 下也非走不可）。
8. **演讲者窗口里的全部页缩略图会一次性建 N 个 iframe。** 页数很多时打开会顿一下，这是拿"即开即用"换的；不改成按需构建，是因为控制台一打开就要能跳页。
9. **「按一次 P 就同时全屏 + 开控制台」做不到，"先全屏再延时开窗"也一样做不到。** 实测：全屏后延时 400ms / 1500ms 调 `window.open` 一律被拦（返回 `null`，加 `--disable-popup-blocking` 无效），因为 `requestFullscreen` 已经把这一轮瞬时激活消耗掉；而且开新窗口必定让当前窗口退出全屏。现在退一步：P 开窗 + 提示一句，观众屏的**下一次点击**补全屏（`restoreFull()`）。第二次起（控制台已开）按 `P` 就是一键全屏。这不是没做完，是平台限制。
10. **只有 Chromium 能锁 Esc。** `navigator.keyboard.lock(['Escape'])` 让 Esc 不再退出全屏（仍可长按 2 秒强退）；Firefox / Safari 没有这个 API，退出全屏只能走右键菜单或浏览器 UI。全屏状态还受浏览器"窗口切换/系统抢占"影响，掉出来时点一下画面（`restoreFull()`）或右键「全屏显示」即可恢复。

---

## 十一、工作约定

> **以下约定是本仓库作者的个人工作流**（署名、`docs/` 时间戳文档、`.workbuddy` 日志）。**外来 Agent 为开源用户生成分页时不必遵守**——你的交付物只有 `pages/*.html`（和必要时的 `subtitle.txt`），跑通构建与校验即可。只有当你直接在本仓库里协作开发时才需要遵守。

- **署名按会话确认一次。** 每个新会话第一次落款前问一次「该署什么名」，之后本会话内所有文档、代码注释、协作标识都沿用这个署名，不再逐次问；换新会话重新问。未答复前不写署名。既有标识（`Hy3-1`、`Hy4-1`、`DeepSeek-V4.1-Flash-1`）都是用户指定的结果，**不得自行编号或顶替**。详见 `MEMORY.md`「署名沿革」。
- **一篇文章的署名跟着写它的那个会话走**，不随项目里其它会话的改名而变。非本会话产出的文档，落款有分歧时先问用户，不代改。
- 每轮改动在 `docs/` 下留一份说明，命名 `<标题>-YYYYMMDDHHMMSS.md`，标题 2–16 汉字、无空格无特殊字符。
- **`docs/*.md` 文末统一落款**，格式固定（前置空行 + 分隔线）：

  ```
  ---

  > 作者：<署名>
  ```

  其中 `<署名>` 用**本次会话已确认**的署名填入（会话首次落款前问过用户），会话内不再逐篇重问。新文档必带；批量补落款时统一追加，已有则跳过，不要重复。`docs/` 下的 `.png` 预览图不落款（署名写在引用它的文档里）。
- 验证截图也放 `docs/`，同样带时间戳。
- 工作日志追加到 `.workbuddy/memory/YYYY-MM-DD.md`，只记跨会话有价值的东西（约束、坑、决策），不记临时路径与报错。
- **踩过的坑、犯过的错、已验证的结论** → 追加到 `MEMORY.md`，不要塞进本文件。本文件只写"当下的规则"。
- 回复用户时**不复述长文**，直接给结论 + 指向文档；用户读中文。

---

## 十二、人称约定（防止「我」被误读为用户）

- 本文件里的 **「我」＝该节的写作 Agent**，**从不指用户**。
- 指用户时统一写 **「用户」**；指后续接手者是 **「你」**。
- 涉及归属判断（谁改的、谁的失误）时，一律用具体署名写死，不用「我」。
- `MEMORY.md` 里的失误档案保留**各自作者的原署名**，不合并、不改写。
