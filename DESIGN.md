# DESIGN.md

> 像美术馆白墙上的一张产品标签 —— 让硬件本身成为主角，榜单是安静而精确的排布。

## 1. Visual Theme & Atmosphere

**Style**: 极简产品橱窗（Minimal Pure / Product Showcase）
**Keywords**: 干净、留白、精确、安静、高级、产品为主角、克制
**Tone**: 冷静中性、画廊感、值得信赖 — NOT 花哨、堆砌、廉价、促销感
**Feel**: 像高端相机品牌官网的展示页，又像一本排版克制的器材年鉴；产品图浮在大量白底之上，文字像标签一样精确。

**Interaction Tier**: L2 流畅交互
**Dependencies**: CSS + 原生 JS（IntersectionObserver / rAF）。不引入 GSAP / Lenis —— 极简调性下用最轻的实现达成 reveal、视差、聚光灯、磁吸。

## 2. Color Palette & Roles

```css
:root {
  /* Backgrounds */
  --bg: #FAFAFA;                 /* 页面背景，近白冷调 */
  --surface: #FFFFFF;            /* 卡片 / 容器 */
  --surface-alt: #F4F4F3;        /* 交替 section / 次级面 */
  --surface-hover: #F0F0EE;      /* 悬停态表面 */

  /* Borders */
  --border: #E8E8E8;             /* 默认边框 */
  --border-hover: #D2D2D2;       /* 悬停边框 */
  --border-strong: #1A1A1A;      /* 强调实线（按钮、分隔） */

  /* Text */
  --text: #1A1A1A;               /* 标题、重要文字 */
  --text-secondary: #5E5E5E;     /* 正文、描述 */
  --text-tertiary: #9A9A9A;      /* 标签、辅助信息 */

  /* Accent (克制：仅交互元素与极小色点) */
  --accent: #0066FF;             /* 链接、活跃态、CTA */
  --accent-hover: #0052CC;

  /* Rank accents（仅用于小徽章 / eyebrow 色点，禁止大面积填充） */
  --rank-latest: #1FA37A;        /* 最新 = 清新绿 */
  --rank-hot:    #E5533C;        /* 最火 = 暖珊瑚 */
  --rank-sales:  #2B6CFF;        /* 最畅销 = 蓝 */

  /* RGB variants for rgba() */
  --bg-rgb: 250,250,250;
  --surface-rgb: 255,255,255;
  --accent-rgb: 0,102,255;
  --text-rgb: 26,26,26;
  --rank-latest-rgb: 31,163,122;
  --rank-hot-rgb: 229,83,60;
  --rank-sales-rgb: 43,108,255;

  /* Semantic */
  --success: #1FA37A;
  --error:   #E5533C;
  --warning: #E0A100;
}
```

**Color Rules:**
- 所有颜色通过 CSS 变量引用，**禁止硬编码 hex**。
- 大面积只用中性色（bg / surface / text）；彩色仅出现在「小徽章、eyebrow 色点、链接、焦点环」，单个屏幕彩色占比 < 5%。
- 三个榜单（最新/最火/最畅销）只用对应 rank 色做**小色点和细描边**区分，不做大色块，保持画廊克制。

## 3. Typography Rules

**Font Stack:**
```css
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&family=DM+Mono:wght@400;500&display=swap');
```

| Role | Font | Size | Weight | Line Height | Letter Spacing |
|------|------|------|--------|-------------|----------------|
| Hero H1 | Instrument Serif → Noto Serif SC | clamp(2.8rem, 6vw, 4.5rem) | 400/600 | 1.08 | -0.01em |
| Section H2 | Instrument Serif → Noto Serif SC | clamp(1.6rem, 3vw, 2.2rem) | 400/600 | 1.15 | 0 |
| H3 / 卡片标题 | Inter → Noto Sans SC | 1.0625rem | 600 | 1.3 | 0 |
| Body | Inter → Noto Sans SC | 1rem (≥15px) | 400 | 1.7 | 0.01em |
| Label / eyebrow | Inter | 0.72rem | 600 | 1.4 | 0.16em (uppercase) |
| 数字 / 价格 / 排名 | DM Mono | 按场景 | 500 | 1 | 0 (tabular) |

**Typography Rules:**
- 大字号对比建立层次（Hero 衬线 vs 正文无衬线），不靠装饰。
- 中文正文行高 ≥ 1.7、字距 0.02em、正文 ≥ 15px；中英混排时英文字族在前、中文字族 fallback。
- 价格、排名、统计数字一律用 DM Mono + `font-variant-numeric: tabular-nums`，保证对齐与可信感。
- **NEVER use**: Comic Sans、系统默认无 fallback 的纯英文字体（中文会回退到丑陋系统字）、任何手写 / 装饰花体。

**Text Decoration:**
- Hero H1：**无渐变、无投影**（极简克制风格，决策表判定为 “--”）。靠字号与衬线建立冲击。
- Section H2：无渐变、无投影。
- eyebrow 小标签：`letter-spacing: 0.16em` + 前置 rank 色点，不加 text-shadow。
- 正文 p：任何装饰一律禁止。

## 4. Component Stylings

### Buttons
```css
.btn {
  font: 600 0.9rem/1 'Inter', 'Noto Sans SC', sans-serif;
  padding: 0.75rem 1.4rem;
  border-radius: 8px;
  border: 1px solid var(--border-strong);
  background: var(--text);
  color: #fff;
  cursor: pointer;
  transition: transform .25s cubic-bezier(.2,.7,.2,1), background .2s, box-shadow .25s;
  will-change: transform;
}
.btn:hover  { background: #000; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(var(--text-rgb),.16); }
.btn:active { transform: translateY(0); box-shadow: none; }
.btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }

.btn--ghost { background: transparent; color: var(--text); }
.btn--ghost:hover { background: var(--surface-hover); }
```

### Cards (产品卡 / SpotlightCard)
```css
.card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 1.1rem;
  overflow: hidden;
  transition: transform .35s cubic-bezier(.2,.7,.2,1), border-color .25s, box-shadow .35s;
}
/* 鼠标跟随聚光灯（SpotlightCard，--mx/--my 由 JS rAF 写入） */
.card::before {
  content:''; position:absolute; inset:0; pointer-events:none; opacity:0;
  background: radial-gradient(220px circle at var(--mx,50%) var(--my,50%),
              rgba(var(--accent-rgb),.07), transparent 60%);
  transition: opacity .3s;
}
.card:hover { transform: translateY(-4px); border-color: var(--border-hover); box-shadow: 0 14px 36px rgba(var(--text-rgb),.08); }
.card:hover::before { opacity: 1; }
.card:focus-within { border-color: var(--accent); }
```

### Navigation
```css
.nav {
  position: sticky; top: 0; z-index: 50;
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem clamp(1rem, 4vw, 3rem);
  background: rgba(var(--bg-rgb), .72);
  border-bottom: 1px solid transparent;
  transition: background .3s, border-color .3s, backdrop-filter .3s;
}
.nav.is-scrolled {
  background: rgba(var(--bg-rgb), .85);
  backdrop-filter: blur(12px);          /* ≤14px，符合性能红线 */
  border-bottom: 1px solid var(--border);
}
```

### Category Tabs / Pills（品类切换 —— 扩展性入口）
```css
.pill {
  font: 600 0.85rem/1 'Inter','Noto Sans SC',sans-serif;
  padding: .5rem 1rem; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface);
  color: var(--text-secondary); cursor: pointer;
  transition: color .2s, border-color .2s, background .2s, transform .2s;
}
.pill:hover { border-color: var(--border-hover); color: var(--text); }
.pill[aria-selected="true"] { background: var(--text); color:#fff; border-color: var(--text); }
.pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

### Links
```css
.link { color: var(--accent); text-decoration: none; position: relative; }
.link::after {
  content:''; position:absolute; left:0; bottom:-2px; width:100%; height:1px;
  background: var(--accent); transform: scaleX(0); transform-origin: left;
  transition: transform .3s cubic-bezier(.2,.7,.2,1);
}
.link:hover::after { transform: scaleX(1); }
.link:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

### Tags / Badges
```css
.badge {
  display:inline-flex; align-items:center; gap:.35rem;
  font: 600 .68rem/1 'Inter','Noto Sans SC',sans-serif;
  letter-spacing:.04em; padding:.3rem .55rem; border-radius:999px;
  border:1px solid var(--border); color: var(--text-secondary); background: var(--surface);
}
.badge .dot { width:6px; height:6px; border-radius:50%; }
.badge--latest .dot { background: var(--rank-latest); }
.badge--hot    .dot { background: var(--rank-hot); }
.badge--sales  .dot { background: var(--rank-sales); }

/* 排名序号 */
.rank-no { font: 500 .8rem/1 'DM Mono',monospace; color: var(--text-tertiary); font-variant-numeric: tabular-nums; }
.rank-no--top { color: var(--text); font-weight:600; }
```

## 5. Layout Principles

**Container:**
- Max width: 1200px，居中
- Padding: clamp(1rem, 4vw, 3rem)
- Narrow variant（说明文字）: 720px

**Spacing Scale:** 4 / 8 / 12 / 16 / 24 / 40 / 64 / 96（px）
- Section padding: 80–96px（移动端 56px）
- Component gap: 16–24px
- Card internal padding: 16–20px

**Grid:**
```css
.grid { display:grid; gap:20px; }
.grid--cards { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
/* Bento：首屏榜单不等大，打破等大 grid 的呆板（首页爆点 #3） */
.bento { display:grid; gap:16px; grid-template-columns: repeat(4, 1fr); grid-auto-rows: 1fr; }
.bento .feature { grid-column: span 2; grid-row: span 2; }
```

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat | `box-shadow: none` | 默认表面、section 背景 |
| Subtle | `0 1px 2px rgba(var(--text-rgb),.04)` | 静态卡片（可选） |
| Elevated | `0 14px 36px rgba(var(--text-rgb),.08)` | 卡片 hover |
| Floating | `0 8px 24px rgba(var(--text-rgb),.16)` | 主按钮 hover |

阴影一律低饱和、冷调、近黑透明；禁止彩色阴影（违反极简克制）。

## 7. Animation & Interaction

**Motion Philosophy**: 克制优雅，只用 `opacity` + `transform`；动效服务于「让产品浮现」而非炫技。
**Tier**: L2

### Dependencies
```html
<!-- 无外部动效库；全部原生 CSS + IntersectionObserver + rAF -->
```

### Base Setup（滚动 reveal + 导航态 + 聚光灯，原生实现）
```js
// 1) Scroll reveal（ScrollFloat / ScrollReveal 思路的轻量原生版）
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}, { threshold: .14 });
document.querySelectorAll('[data-reveal]').forEach((el,i) => {
  el.style.setProperty('--d', (i % 8) * 60 + 'ms');   // stagger
  io.observe(el);
});

// 2) Nav scrolled state
const nav = document.querySelector('.nav');
addEventListener('scroll', () => nav.classList.toggle('is-scrolled', scrollY > 12), { passive:true });

// 3) SpotlightCard：rAF 节流写入 --mx/--my（仅 hover 设备）
if (matchMedia('(hover: hover)').matches) {
  let raf = 0;
  document.addEventListener('pointermove', (ev) => {
    const card = ev.target.closest('.card'); if (!card) return;
    if (raf) return; raf = requestAnimationFrame(() => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (ev.clientX - r.left) + 'px');
      card.style.setProperty('--my', (ev.clientY - r.top)  + 'px');
      raf = 0;
    });
  }, { passive:true });
}
```

### Entrance Animation
```css
[data-reveal]{ opacity:0; transform: translateY(20px); }
[data-reveal].in{
  opacity:1; transform:none;
  transition: opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1);
  transition-delay: var(--d, 0ms);
}
/* Hero H1 词级 stagger（SplitText 思路）：每个 .word 由 JS 拆分 */
.hero h1 .word{ display:inline-block; opacity:0; transform: translateY(28px);
  animation: wordIn .8s cubic-bezier(.2,.7,.2,1) forwards; animation-delay: calc(var(--i) * 70ms); }
@keyframes wordIn{ to{ opacity:1; transform:none; } }
```

### Scroll Behavior
- `html{ scroll-behavior:smooth }`（原生平滑，不用 Lenis）
- Hero 背景 DotGrid 极轻视差：`transform: translateY(scrollY * .15)`，rAF 节流。
- Section H2 进入视口浮入（ScrollFloat）。

### Hover & Focus States
- 所有可交互元素（按钮 / pill / 卡片 / 链接）均有 hover + `:focus-visible` 焦点环（见 §4）。
- 卡片 hover：lift + 聚光灯；产品图 hover 轻微 `scale(1.04)`。
- CTA 磁吸（Magnet）：hover 设备下按钮向鼠标偏移 ≤ 6px，rAF 节流。

### Special Effects（签名动效，覆盖 L2 强制 6 类）
1. **Text · Hero H1** — SplitText 词级 stagger 入场。
2. **Text · Section H2** — ScrollFloat 滚动浮入。
3. **Text · Body/Label** — eyebrow ScrollReveal + 统计数字 CountUp（IntersectionObserver 触发）。
4. **Animation · 元素级** — CTA Magnet 磁吸 + 卡片 hover lift。
5. **Component · 交互构件** — SpotlightCard 聚光灯产品卡 + 品牌 logo InfiniteScroll 横滚带 + 品类 Pill 切换。
6. **Background · 氛围层** — DotGrid 点阵背景（Hero，CSS radial-gradient，零 WebGL）。

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  [data-reveal]{ opacity:1 !important; transform:none !important; }
  .hero h1 .word{ opacity:1 !important; transform:none !important; }
  html{ scroll-behavior:auto; }
}
```

## 8. Do's and Don'ts

### Do
- 让产品图和留白主导版面，文字像标签一样精确克制。
- 三个榜单用「小色点 + 细描边 + 序号」区分，颜色克制。
- 价格 / 排名 / 统计数字统一用 DM Mono tabular-nums，对齐可信。
- 品类用数据驱动的 Pill 渲染 —— 加品类只改 `categories.json`，前端零改动。
- 所有彩色集中在徽章、链接、焦点环；中性色承载 95% 画面。
- 每个可交互元素都有 hover + 键盘焦点态。

### Don't
- ❌ 硬编码任何 hex 颜色（一律走 CSS 变量）。
- ❌ 给 Hero / Section 标题加渐变或投影（破坏极简克制）。
- ❌ 用大色块填充榜单分区或卡片背景。
- ❌ 用 Emoji 当功能图标（非 Playful 调性，统一用内联 SVG / 极简线性图标）。
- ❌ 产品图缺失时用纯色块占位（用统一占位图 / 来源 URL）。
- ❌ 引入 GSAP / Lenis / WebGL —— 极简 L2 用原生即可，避免性能与体积负担。
- ❌ 在移动滚动区大面积叠 `backdrop-filter`（仅导航条用，blur ≤14px）。
- ❌ 给正文段落加任何文字装饰。
- ❌ 把品类写死在 HTML 里（必须从数据渲染，保留扩展性）。

## 9. Responsive Behavior

**Breakpoints:**
| Name | Width | Key Changes |
|------|-------|-------------|
| Desktop | > 1024px | Bento 4 列、榜单三栏并排、完整导航 |
| Tablet | 640–1024px | Bento 2 列、榜单单列堆叠、导航保留 |
| Mobile | < 640px | 单列、Pill 横向滚动、统计 2×2、section padding 56px |

**Touch Targets:** 最小 44×44px（pill、按钮、卡片点击区）。
**Collapsing Strategy:** 导航在移动端收为 Logo + 「数据更新时间」+ 汉堡/锚点；Bento 退化为单列卡片流；横滚 logo 带保留但加 `-webkit-overflow-scrolling`。

```css
@media (max-width: 1024px){
  .bento{ grid-template-columns: repeat(2,1fr); }
  .bento .feature{ grid-column: span 2; grid-row: span 1; }
  .boards{ grid-template-columns: 1fr; }
}
@media (max-width: 640px){
  .bento{ grid-template-columns: 1fr; }
  .grid--cards{ grid-template-columns: repeat(auto-fill, minmax(150px,1fr)); }
  .stats{ grid-template-columns: repeat(2,1fr); }
  section{ padding-block: 56px; }
  .pills{ overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; }
}
/* 移动端关闭聚光灯 / 磁吸（无 hover），保留 reveal */
@media (hover: none){
  .card::before{ display:none; }
}
```

---

**致谢**：动效思路（SplitText / ScrollFloat / ScrollReveal / SpotlightCard / Magnet / InfiniteScroll / DotGrid）derived from [vue-bits / react-bits](https://github.com/DavidHDev/vue-bits) by DavidHDev (MIT)，本项目以原生 CSS/JS 重写。
