# DESIGN.md

> 像一场高端相机的暗房发布会 —— 深色幕布上，产品在流动的极光里被聚光灯逐一点亮，数据精确跳动。

## 1. Visual Theme & Atmosphere

**Style**: 暗色高级发布会感（Dark Editorial / Product Keynote）
**Keywords**: 深邃、高级、冷静、科技感、流光、聚光、精确、产品为主角
**Tone**: 像高端相机品牌的新品发布页 + 排版克制的器材年鉴 —— NOT 花哨、廉价、促销、喧闹
**Feel**: 深色底幕上浮动柔和极光，产品卡是磨砂玻璃，鼠标划过卡片轻微 3D 倾斜并亮起聚光；榜单数字滚动跳到位。冷静但有「卧槽」时刻。

**Interaction Tier**: **L3 沉浸体验**
**Dependencies**: **纯 CSS + 原生 JS，零外部库**（不引 Three.js / OGL / GSAP / Lenis）。极光背景用 Canvas-2D 自实现（离屏 IntersectionObserver 暂停）。
> **有意不用 WebGL**：本站是静态产物，需同时支持 GitHub Pages 与「双击 index.html 离线打开」，且无构建步骤。故用 Canvas-2D 极光 + CSS 3D 倾斜达成 L3 签名时刻，规避 Three.js/OGL 的体积与离线加载问题。性能更可控。

## 2. Color Palette & Roles

```css
:root {
  /* Backgrounds — 深色幕布 */
  --bg: #0A0A0F;                 /* 页面底，近黑冷蓝 */
  --bg-2: #0E0E16;               /* 交替 section */
  --surface: rgba(255,255,255,.045);   /* 玻璃卡面（叠在极光上） */
  --surface-solid: #14141C;      /* 不透明面（详情/表格底） */
  --surface-hover: rgba(255,255,255,.07);

  /* Borders */
  --border: rgba(255,255,255,.10);
  --border-hover: rgba(255,255,255,.20);
  --border-strong: rgba(255,255,255,.85);

  /* Text — 暗底高对比 */
  --text: #F4F5F7;               /* 标题、重要 */
  --text-secondary: #AEB0BA;     /* 正文 */
  --text-tertiary: #6E7080;      /* 标签、辅助 */

  /* Accent */
  --accent: #5B8CFF;             /* 链接、活跃、CTA */
  --accent-hover: #7AA2FF;

  /* Rank accents（榜单 + 流光点缀） */
  --rank-latest: #38E0A6;        /* 最新 = 极光绿 */
  --rank-hot:    #FF6B57;        /* 最火 = 暖珊瑚 */
  --rank-sales:  #5B8CFF;        /* 最畅销 = 蓝 */

  /* 极光/流光渐变停靠色 */
  --aurora-1: #5B8CFF;
  --aurora-2: #38E0A6;
  --aurora-3: #A66BFF;
  --aurora-4: #FF6B57;

  /* RGB variants for rgba() */
  --bg-rgb: 10,10,15;
  --surface-rgb: 255,255,255;
  --text-rgb: 244,245,247;
  --accent-rgb: 91,140,255;
  --rank-latest-rgb: 56,224,166;
  --rank-hot-rgb: 255,107,87;
  --rank-sales-rgb: 91,140,255;

  /* Semantic */
  --success: #38E0A6;
  --error:   #FF6B57;
  --warning: #F2C14E;
}
```

**Color Rules:**
- 所有颜色走 CSS 变量，**禁止硬编码 hex**（极光渐变停靠色也用变量）。
- 大面积是深色底 + 极光氛围；彩色集中在「关键词流光、徽章、链接、聚光、焦点环」。
- 三榜只用对应 rank 色做小色点 / 细描边 / 流光，不做大色块。
- 玻璃卡面用 `rgba(255,255,255,.045)` + `backdrop-filter: blur(12px)`（≤14px 红线）。

## 3. Typography Rules

```css
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&family=DM+Mono:wght@400;500&display=swap');
```

| Role | Font | Size | Weight | Line Height | Letter Spacing |
|------|------|------|--------|-------------|----------------|
| Hero H1 | Instrument Serif → Noto Serif SC | clamp(2.8rem, 6.5vw, 5rem) | 400/600 | 1.06 | -0.01em |
| Section H2 | Instrument Serif → Noto Serif SC | clamp(1.7rem, 3.2vw, 2.4rem) | 400/600 | 1.14 | 0 |
| H3 / 卡片标题 | Inter → Noto Sans SC | 1.0625rem | 600 | 1.3 | 0 |
| Body | Inter → Noto Sans SC | 1rem (≥15px) | 400 | 1.75 | 0.01em |
| Label / eyebrow | Inter | 0.72rem | 600 | 1.4 | 0.16em (uppercase) |
| 数字 / 价格 / 排名 | DM Mono | 按场景 | 500 | 1 | 0 (tabular) |

**Typography Rules:**
- 层次靠字号 + 衬线/无衬线对比；中文正文行高 ≥ 1.7、字距 0.02em、≥15px；中英混排英文字族在前、中文字族 fallback。
- 价格/排名/统计数字一律 DM Mono + `font-variant-numeric: tabular-nums`。
- **NEVER**: Comic Sans、无中文 fallback 的纯英文字体、手写/花体。

**Text Decoration（暗色风格允许关键词流光）:**
- Hero H1：整句不加投影；**仅 1-2 个关键词**用流动渐变（`--aurora-*` 线性渐变 + `background-position` 动画）。
- Section H2：无渐变无投影，靠 ScrollFloat 入场。
- eyebrow：`letter-spacing:.16em` + 前置 rank 色点。
- 正文：禁止任何文字装饰。

## 4. Component Stylings

### Buttons
```css
.btn{
  font:600 .9rem/1 'Inter','Noto Sans SC',sans-serif;
  padding:.78rem 1.5rem; border-radius:10px;
  border:1px solid var(--border-strong); background:var(--text); color:var(--bg);
  cursor:pointer; will-change:transform;
  transition:transform .25s cubic-bezier(.2,.7,.2,1), background .2s, box-shadow .25s, opacity .2s;
}
.btn:hover{ transform:translateY(-2px); box-shadow:0 10px 30px rgba(var(--accent-rgb),.28); }
.btn:active{ transform:translateY(0); box-shadow:none; }
.btn:focus-visible{ outline:2px solid var(--accent); outline-offset:3px; }
.btn:disabled{ opacity:.4; cursor:not-allowed; transform:none; box-shadow:none; }
.btn--ghost{ background:transparent; color:var(--text); border-color:var(--border); }
.btn--ghost:hover{ background:var(--surface-hover); box-shadow:none; }
```

### Cards（玻璃 + SpotlightCard + TiltedCard + GlareHover）
```css
.card{
  position:relative; background:var(--surface); border:1px solid var(--border);
  border-radius:16px; padding:1.1rem; overflow:hidden;
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  transform-style:preserve-3d; transition:transform .35s cubic-bezier(.2,.7,.2,1), border-color .25s, box-shadow .35s;
}
/* SpotlightCard：鼠标跟随聚光（--mx/--my 由 JS rAF 写入） */
.card::before{
  content:''; position:absolute; inset:0; pointer-events:none; opacity:0;
  background:radial-gradient(240px circle at var(--mx,50%) var(--my,50%),
            rgba(var(--accent-rgb),.16), transparent 60%);
  transition:opacity .3s;
}
/* GlareHover：高光斜扫 */
.card::after{
  content:''; position:absolute; inset:0; pointer-events:none; opacity:0;
  background:linear-gradient(115deg, transparent 30%, rgba(var(--surface-rgb),.10) 48%, transparent 60%);
  transform:translateX(-60%); transition:opacity .4s;
}
.card:hover{ border-color:var(--border-hover); box-shadow:0 18px 50px rgba(0,0,0,.5); }
.card:hover::before{ opacity:1; }
.card:hover::after{ opacity:1; animation:glare .8s ease; }
@keyframes glare{ from{transform:translateX(-60%)} to{transform:translateX(60%)} }
.card:focus-within{ border-color:var(--accent); }
/* TiltedCard：JS 写入 --rx/--ry 旋转（仅 hover 设备，rAF 节流） */
.tilt{ transform:perspective(800px) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg)); }
```

### Navigation
```css
.nav{
  position:sticky; top:0; z-index:50; display:flex; align-items:center; justify-content:space-between;
  padding:1rem clamp(1rem,4vw,3rem);
  background:rgba(var(--bg-rgb),.55); border-bottom:1px solid transparent;
  transition:background .3s, border-color .3s, backdrop-filter .3s;
}
.nav.is-scrolled{ background:rgba(var(--bg-rgb),.78); backdrop-filter:blur(12px); border-bottom:1px solid var(--border); }
```

### Pills / Links / Badges
```css
.pill{ font:600 .85rem/1 'Inter','Noto Sans SC',sans-serif; padding:.5rem 1rem; border-radius:999px;
  border:1px solid var(--border); background:var(--surface); color:var(--text-secondary); cursor:pointer;
  transition:color .2s,border-color .2s,background .2s,transform .2s; }
.pill:hover{ border-color:var(--border-hover); color:var(--text); }
.pill[aria-selected="true"]{ background:var(--text); color:var(--bg); border-color:var(--text); }
.pill:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; }

.link{ color:var(--accent); text-decoration:none; position:relative; }
.link::after{ content:''; position:absolute; left:0; bottom:-2px; width:100%; height:1px; background:var(--accent);
  transform:scaleX(0); transform-origin:left; transition:transform .3s cubic-bezier(.2,.7,.2,1); }
.link:hover::after{ transform:scaleX(1); }
.link:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; }

.badge{ display:inline-flex; align-items:center; gap:.35rem; font:600 .68rem/1 'Inter','Noto Sans SC',sans-serif;
  letter-spacing:.04em; padding:.3rem .55rem; border-radius:999px; border:1px solid var(--border);
  color:var(--text-secondary); background:var(--surface); }
.badge .dot{ width:6px; height:6px; border-radius:50%; }
.badge--latest .dot{ background:var(--rank-latest); }
.badge--hot .dot{ background:var(--rank-hot); }
.badge--sales .dot{ background:var(--rank-sales); }
```

### Empty State（缺图 / 缺评 —— 不用纯色块占位）
```css
.empty{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.6rem;
  padding:1.5rem; text-align:center; color:var(--text-tertiary);
  border:1px dashed var(--border); border-radius:14px; background:var(--surface); }
.empty svg{ width:34px; height:34px; opacity:.5; }
.empty .link{ font-size:.85rem; }
```

## 5. Layout Principles

- **Container**: max 1200px 居中；padding `clamp(1rem,4vw,3rem)`；窄变体 720px。
- **Spacing Scale**: 4 / 8 / 12 / 16 / 24 / 40 / 64 / 96。Section padding 80–96px（移动 56px）。
- **Grid / MagicBento**:
```css
.grid--cards{ display:grid; gap:20px; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }
.bento{ display:grid; gap:16px; grid-template-columns:repeat(4,1fr); grid-auto-rows:1fr; }
.bento .feature{ grid-column:span 2; grid-row:span 2; }   /* 焦点机型不等大，打破呆板 */
```

## 6. Depth & Elevation

| Level | Treatment | Use |
|------|-----------|-----|
| Flat | none | section 背景 |
| Glass | `backdrop-filter:blur(12px)` + 1px 白描边 | 玻璃卡默认 |
| Elevated | `0 18px 50px rgba(0,0,0,.5)` | 卡片 hover |
| Floating | `0 10px 30px rgba(var(--accent-rgb),.28)` | 主按钮 hover |

暗色下用「深黑投影 + 白色细描边 + 玻璃模糊」造层次；禁止彩色硬阴影。

## 7. Animation & Interaction

**Philosophy**: 只用 `opacity` / `transform` / `background-position`；动效服务「让产品在暗场里浮现、被点亮」。**Tier: L3**。

### Dependencies
```html
<!-- 零外部库：CSS + 原生 JS（IntersectionObserver / rAF / Canvas-2D） -->
```

### 签名动效（覆盖 L3 强制 6 类，累计 signature moments ≥ 6）
1. **Background·氛围** — Canvas-2D **极光**（Aurora 思路）：3-4 团 `--aurora-*` 径向光斑缓慢漂移 + 轻噪点；`IntersectionObserver` 离屏暂停；移动端/reduced-motion → 静态 CSS 渐变。
2. **Text·Hero H1** — **SplitText** 词级 stagger 入场 + 关键词 **GradientText/ShinyText** 流光（`background-position` 动画）。
3. **Text·Section H2** — **ScrollFloat** 进视口浮入。
4. **Text·Body/Label** — eyebrow **ScrollReveal** + 统计/榜单数字 **CountUp**（IntersectionObserver 触发，rAF 递增）。
5. **Animation·元素** — CTA **Magnet** 磁吸（≤6px，rAF）+ 卡片 **GlareHover** 高光扫过。
6. **Component·构件** — 产品卡 **SpotlightCard** 聚光 + **TiltedCard** 3D 倾斜 + 品类 Pill 切换 + 焦点 **MagicBento**。

### L3 scroll-story（覆盖 ≥3 模式）
- **汇聚/散开转场**：Hero 焦点卡片从散落 translate/scale 汇聚到位（load 一次性）。
- **轻 pin-scrub**：三榜 section 标题随滚动浮现、卡片 stagger reveal（IntersectionObserver，不劫持滚动）。
- **3D 签名时刻**：焦点卡 / 产品卡 CSS 3D 倾斜（TiltedCard）+ 详情页画廊主图微视差。

### Base Setup（原生实现要点）
```js
// reveal：IntersectionObserver 加 .in（stagger 用 --d）
// nav.is-scrolled：scrollY>12 切换
// SpotlightCard + TiltedCard：单个 pointermove 监听 + rAF 节流，写 --mx/--my/--rx/--ry，仅 matchMedia('(hover:hover)')
// CountUp：元素进视口后 rAF 从 0 递增到 data-count
// Magnet：CTA hover 时按鼠标偏移 transform，离开复位
// Aurora：canvas requestAnimationFrame，IntersectionObserver 不可见时 cancelAnimationFrame
```

### Entrance / Scroll / Hover
```css
[data-reveal]{ opacity:0; transform:translateY(22px); }
[data-reveal].in{ opacity:1; transform:none; transition:opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1); transition-delay:var(--d,0ms); }
.hero h1 .word{ display:inline-block; opacity:0; transform:translateY(28px);
  animation:wordIn .8s cubic-bezier(.2,.7,.2,1) forwards; animation-delay:calc(var(--i)*70ms); }
@keyframes wordIn{ to{opacity:1; transform:none} }
.flow{ background:linear-gradient(90deg,var(--aurora-1),var(--aurora-3),var(--aurora-2),var(--aurora-1));
  background-size:300% 100%; -webkit-background-clip:text; background-clip:text; color:transparent; animation:flow 8s linear infinite; }
@keyframes flow{ to{ background-position:300% 0 } }
html{ scroll-behavior:smooth; }
```

### Reduced Motion（完整降级，不可缺）
```css
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{ animation:none !important; transition:none !important; }
  [data-reveal]{ opacity:1 !important; transform:none !important; }
  .hero h1 .word{ opacity:1 !important; transform:none !important; }
  .flow{ animation:none !important; }
  html{ scroll-behavior:auto; }
  /* canvas 极光 JS 端检测此项 → 不启动，改静态渐变 */
}
```

## 8. Do's and Don'ts

### Do
- 深色幕布 + 柔和极光承载氛围，产品玻璃卡是主角，文字像标签精确克制。
- 三榜用「小色点 + 细描边 + 流光」区分，颜色克制。
- 价格/排名/统计统一 DM Mono tabular-nums。
- 品类数据驱动 Pill 渲染（加品类只改 `categories.json`）。
- 缺图/缺评一律走**空状态 + 来源链接**，绝不编造。
- 每个可交互元素都有 hover + 键盘焦点态。
- 重背景离屏暂停、移动端降级、`prefers-reduced-motion` 全降级。

### Don't
- ❌ 硬编码任何 hex（走 CSS 变量）。
- ❌ Hero/Section 整句加投影或满屏渐变（仅 Hero 关键词流光）。
- ❌ 用大色块填充榜单分区或卡片背景。
- ❌ 用 Emoji 当功能图标（统一内联 SVG 线性图标）。
- ❌ **产品图缺失用纯色块占位**（用空状态卡 + 来源链接）。
- ❌ 展示**编造/示例**评价（无真实评价 → 空状态 + 电商链接）。
- ❌ 引入 Three.js / OGL / GSAP / Lenis（纯 CSS+JS，保离线 + Pages）。
- ❌ 移动滚动区大面积叠 `backdrop-filter`（仅导航 + 卡片，blur ≤14px）。
- ❌ 同页超过 1 个重背景 / Canvas 不离屏暂停。
- ❌ 把品类写死在 HTML（必须数据渲染）。

## 9. Responsive Behavior

| Name | Width | Key Changes |
|------|-------|-------------|
| Desktop | > 1024px | Bento 4 列、三榜并排、完整导航、极光 + 3D 倾斜全开 |
| Tablet | 640–1024px | Bento 2 列、三榜堆叠、保留导航、极光降帧 |
| Mobile | < 640px | 单列、Pill 横滚、统计 2×2、section 56px、**极光→静态渐变**、关闭 3D 倾斜/聚光 |

**Touch Targets**: ≥ 44×44px。
```css
@media (max-width:1024px){ .bento{grid-template-columns:repeat(2,1fr)} .bento .feature{grid-column:span 2;grid-row:span 1} .boards{grid-template-columns:1fr} }
@media (max-width:640px){ .bento,.grid--cards{grid-template-columns:1fr} .stats{grid-template-columns:repeat(2,1fr)} section{padding-block:56px} .pills{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch} }
@media (hover:none){ .card::before,.card::after{display:none} .tilt{transform:none} }   /* 无 hover 设备关聚光/3D */
```

---

**致谢**：动效思路（SplitText / ScrollFloat / ScrollReveal / SpotlightCard / TiltedCard / GlareHover / Magnet / MagicBento / CountUp / Aurora）derived from [vue-bits / react-bits](https://github.com/DavidHDev/vue-bits) by DavidHDev (MIT)，本项目以原生 CSS/JS/Canvas 重写，零运行时依赖。
