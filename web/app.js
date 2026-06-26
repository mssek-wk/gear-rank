/* 器材榜前端 —— 全部从 window.__GEAR_DATA__（由 crawler 生成的 data.js）渲染。
   品类、榜单、卡片都是数据驱动：加品类只需重跑 crawler，无需改这里。 */
(() => {
  'use strict';

  const DATA = window.__GEAR_DATA__;
  const $ = (s, r = document) => r.querySelector(s);
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!DATA || !DATA.meta) {
    document.body.insertAdjacentHTML('beforeend',
      '<p style="padding:3rem;text-align:center;color:#5E5E5E">数据未生成，请先运行 <code>python3 crawler/run.py</code></p>');
    return;
  }

  const meta = DATA.meta;
  const cats = meta.categories.filter(c => c.count > 0);
  let activeCat = cats.length ? cats[0].id : null;

  /* ---------- 内联 SVG 相机线框图标（产品图兜底，currentColor 适配暗色，非纯色块） ---------- */
  const BRAND_TINT = {
    Fujifilm: 'var(--rank-latest)', Polaroid: 'var(--rank-hot)', Kodak: 'var(--warning)', default: 'var(--accent)'
  };
  function cameraSVG(brand) {
    const tint = BRAND_TINT[brand] || BRAND_TINT.default;
    return `<svg class="camsvg" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${brand} 相机">
      <rect x="18" y="34" width="84" height="62" rx="12" stroke="currentColor" stroke-width="3"/>
      <circle cx="60" cy="62" r="20" stroke="currentColor" stroke-width="3"/>
      <circle cx="60" cy="62" r="10" fill="${tint}" opacity=".28"/>
      <circle cx="60" cy="62" r="10" stroke="currentColor" stroke-width="2.5"/>
      <rect x="30" y="42" width="14" height="8" rx="2" fill="${tint}"/>
      <rect x="78" y="40" width="14" height="10" rx="3" stroke="currentColor" stroke-width="2.5"/>
    </svg>`;
  }
  // 该机型最佳「来源链接」：官网 > 京东搜索 > 淘宝搜索 > 任意 seller（供缺图/缺评空状态）
  function bestSourceLink(it) {
    if (it.official_url) return { url: it.official_url, label: '官网' };
    const ss = it.sellers || [];
    const jd = ss.find(s => (s.name || '').includes('京东'));
    const tb = ss.find(s => (s.name || '').includes('淘宝') || (s.name || '').includes('天猫'));
    const any = jd || tb || ss[0];
    return any ? { url: any.url, label: any.name } : null;
  }
  function mediaHTML(item) {
    if (item.image) {
      return `<img src="${item.image}" alt="${item.name}" loading="lazy"
        onerror="this.outerHTML=window.__camSVG(${JSON.stringify(item.brand)})">`;
    }
    return cameraSVG(item.brand);
  }
  window.__camSVG = cameraSVG; // 供 img onerror 兜底调用

  /* ---------- 数据访问 ---------- */
  const bucket = (cid) => DATA.byCategory[cid] || { items: [], boards: {} };
  const itemMap = (cid) => Object.fromEntries(bucket(cid).items.map(i => [i.id, i]));

  /* ---------- 渲染：品类 pills（首屏 + 吸顶双容器，委托点击联动） ---------- */
  function renderPills() {
    const html = cats.map(c =>
      `<button class="pill" role="tab" data-cat="${c.id}" aria-selected="${c.id === activeCat}">${c.name} <span class="pill__count">${c.count}</span></button>`).join('');
    $('#pills').innerHTML = html;
    // 委托：两条品类条任意 pill 点击都切换品类并同步
    document.addEventListener('click', (ev) => {
      const p = ev.target.closest('.pill[data-cat]'); if (!p) return;
      if (p.dataset.cat === activeCat) return;
      activeCat = p.dataset.cat; renderCategory();
    });
  }

  /* ---------- 渲染：本周焦点（当前品类最火第一名） ---------- */
  function renderFocus() {
    const b = bucket(activeCat);
    const map = itemMap(activeCat);
    const topId = (b.boards.hottest || [])[0];
    const it = map[topId];
    const el = $('#focusCard');
    if (!it) { el.innerHTML = ''; return; }
    el.innerHTML = `
      <a class="focus__media card" href="#item=${it.id}" aria-label="${it.name} 详情">${mediaHTML(it)}</a>
      <div class="focus__body">
        <span class="badge badge--hot"><span class="dot"></span>本周最火</span>
        <h3>${it.name}</h3>
        <p>${it.summary || ''}</p>
        <div class="tags" style="margin-bottom:1rem">${(it.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}</div>
        <div class="focus__meta">
          <span class="focus__price">${it.price_display || '—'}</span>
          <span class="row__brand">${it.brand}</span>
          <a class="btn magnet" href="#item=${it.id}">查看详情</a>
        </div>
      </div>`;
  }

  /* ---------- 渲染：三榜（真实数据驱动）---------- */
  // metric(it) 返回该榜单这一行要展示的「真实依据值」
  // pop_note 是「数据支撑」文案（真实评价数/销量证据或定性依据）。按关键词挑出与该榜相关的片段，
  // 拿不到平台数字时作为可见依据回退展示，让最火/最畅销不再空白。
  const clipNote = (s, n = 9) => {
    s = String(s || '').replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();
    return s.length > n ? s.slice(0, n) + '…' : s;
  };
  // 从长片段里抽「数字+单位」信号（如 6万+付款 / 20万+评价 / 98.9%好评）
  const SIG = /[\d.]+\s*[万千亿]?\+?\s*(?:人?付款|条?评价|加购|售出|好评率?\s*[\d.]*%?)|[\d.]+%\s*好评/;
  const pickNote = (note, kind) => {
    if (!note) return '';
    const parts = note.split(/\s*·\s*/).map(s => s.trim()).filter(Boolean);   // 分隔符宽松
    const wants = kind === 'hot' ? ['好评', '评价', '热度', '关注', '缺货', '新品', '口碑', '人气']
                                 : ['已售', '付款', '销量', '畅销', '加购', '万+', '售出'];
    const hit = parts.find(p => wants.some(w => p.includes(w))) || parts[0] || note;
    if (hit.replace(/（[^）]*）/g, '').trim().length <= 13) return clipNote(hit);
    const m = hit.match(SIG);                      // 长片段：优先抽出数字信号
    return m ? clipNote(m[0]) : clipNote(hit);
  };
  const BOARD_DEFS = [
    { key: 'latest', cls: 'latest', title: '最新', sub: '官方上市日期',
      metric: it => (it.release_date || '').slice(0, 7) },
    { key: 'hottest', cls: 'hot', title: '最火', sub: '综合·按评价数/热度',
      metric: it => it.reviews != null ? it.reviews.toLocaleString() + ' 评价' : pickNote(it.pop_note, 'hot') },
    { key: 'bestselling', cls: 'sales', title: '最畅销', sub: '综合·按销量/畅销',
      metric: it => it.bsr != null ? '榜 #' + it.bsr.toLocaleString() : pickNote(it.pop_note, 'sales') },
  ];
  function renderBoards() {
    const b = bucket(activeCat);
    const map = itemMap(activeCat);
    $('#boardsGrid').innerHTML = BOARD_DEFS.map(def => {
      const ids = (b.boards[def.key] || []).slice(0, 6);
      const rows = ids.map((id, i) => {
        const it = map[id]; if (!it) return '';
        return `<a class="row" href="#item=${it.id}">
          <span class="row__no ${i < 3 ? 'row__no--top' : ''}">${String(i + 1).padStart(2, '0')}</span>
          <span class="row__thumb">${mediaHTML(it)}</span>
          <span>
            <span class="row__name">${it.name}</span><br>
            <span class="row__brand">${it.brand}</span>
          </span>
          <span class="row__metric">${def.metric(it)}</span>
        </a>`;
      }).join('');
      return `<div class="board board--${def.cls}" data-reveal>
        <div class="board__head">
          <span class="board__dot"></span>
          <span class="board__title">${def.title}</span>
          <span class="board__sub">${def.sub}</span>
        </div>
        ${rows}
      </div>`;
    }).join('');
  }

  /* ---------- 渲染：全部机型 grid（含排序） ---------- */
  const SORTERS = {
    sales: (a, b) => b.sales_score - a.sales_score,
    hot: (a, b) => b.hot_score - a.hot_score,
    latest: (a, b) => b.latest_score - a.latest_score,
    'price-asc': (a, b) => (a.price_value ?? 1e9) - (b.price_value ?? 1e9),
    'price-desc': (a, b) => (b.price_value ?? -1) - (a.price_value ?? -1),
  };
  function renderAll() {
    const all = bucket(activeCat).items;
    const isActive = (it) => it.active !== false;          // 缺字段视为在榜（向后兼容）
    const activeN = all.filter(isActive).length;
    const histN = all.length - activeN;

    const showHist = $('#histToggle') ? $('#histToggle').checked : true;
    let items = showHist ? [...all] : all.filter(isActive);

    const mode = $('#sortSelect').value;
    const sorter = SORTERS[mode] || SORTERS.sales;
    // 在榜机型永远排在历史机型前面；组内再按所选维度排
    items.sort((a, b) => (isActive(b) - isActive(a)) || sorter(a, b));

    $('#allDesc').textContent =
      `共 ${all.length} 款${catName(activeCat)}（在榜 ${activeN}` +
      (histN ? ` · 历史 ${histN}` : '') + `）—— 全部历史机型永久留存，本地存档。`;

    $('#allGrid').innerHTML = items.map(it => `
      <a class="card ${isActive(it) ? '' : 'card--hist'}" href="#item=${it.id}" data-reveal>
        ${isActive(it) ? '' : '<span class="hist-flag">历史</span>'}
        <div class="card__media">${mediaHTML(it)}</div>
        <span class="card__brand">${it.brand}</span>
        <span class="card__name">${it.name}</span>
        <div class="tags">${(it.tags || []).slice(0, 2).map(t => `<span class="tag">${t}</span>`).join('')}</div>
        ${it.rating != null ? `<div class="card__rate">★ ${it.rating}${it.reviews != null ? ` <span>· ${it.reviews.toLocaleString()} 评价</span>` : ''}</div>` : ''}
        <div class="card__foot">
          <span class="card__price">${it.price_display || '—'}</span>
        </div>
      </a>`).join('');
    observeReveals();
  }
  const catName = (cid) => (cats.find(c => c.id === cid) || {}).name || '';

  /* ---------- 切换品类时重渲染依赖品类的区块 ---------- */
  function renderCategory() {
    document.querySelectorAll('.pill[data-cat]').forEach(p =>
      p.setAttribute('aria-selected', String(p.dataset.cat === activeCat)));
    renderFocus(); renderBoards(); renderAll();
    observeReveals();
  }

  /* ---------- 头部固定区：stats CountUp + 更新时间 ---------- */
  function renderHeader() {
    const totalItems = cats.reduce((s, c) => s + c.count, 0);
    const brands = new Set();
    cats.forEach(c => bucket(c.id).items.forEach(i => brands.add(i.brand)));
    const updated = new Date(meta.updated_at);
    const dstr = `${updated.getFullYear()}-${String(updated.getMonth() + 1).padStart(2, '0')}-${String(updated.getDate()).padStart(2, '0')}`;
    $('#navUpdated').textContent = `更新 ${dstr}`;
    $('#stats').innerHTML = [
      { n: totalItems, l: '在榜机型' },
      { n: cats.length, l: '硬件品类' },
      { n: brands.size, l: '覆盖品牌' },
      { n: 3, l: '榜单维度' },
    ].map(s => `<div class="stat"><div class="stat__num" data-count="${s.n}">0</div><div class="stat__label">${s.l}</div></div>`).join('');

    // 数据来源透明标注
    const prov = $('#provenance');
    if (prov) {
      const srcs = (meta.platform_sources || ['Amazon US']).join(' / ');
      const asof = meta.platform_as_of || dstr;
      // 待接入平台：综合框架里还没有数据的平台才标「待接入」（有数据后自动消失）
      const ALL_PLATS = ['Amazon US', '淘宝', '京东'];
      const pending = ALL_PLATS.filter(p => !(meta.platform_sources || []).includes(p));
      prov.innerHTML = `数据来源：官方上市日期（厂商）＋ <strong>${srcs}</strong> 真实价格/评分/评价数/销量/畅销榜 · 截至 ${asof}`
        + (pending.length ? ` ｜ 综合多平台框架，<span class="prov-pending">${pending.join(' / ')}待接入</span>` : ' ｜ 综合多平台真实价格');
    }
  }

  function countUp() {
    document.querySelectorAll('[data-count]').forEach(el => {
      const target = +el.dataset.count;
      if (reduce) { el.textContent = target; return; }
      const io = new IntersectionObserver((es) => {
        es.forEach(e => {
          if (!e.isIntersecting) return; io.disconnect();
          const dur = 900; const t0 = performance.now();
          const tick = (t) => {
            const p = Math.min(1, (t - t0) / dur);
            el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
            if (p < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        });
      }, { threshold: .6 });
      io.observe(el);
    });
  }

  /* ---------- Hero SplitText（词级 stagger） ---------- */
  function splitHero() {
    const h = $('#heroTitle'); if (!h) return;
    const nodes = [...h.childNodes];
    let i = 0; const out = [];
    for (const n of nodes) {
      if (n.nodeType === 3) {
        for (const ch of n.textContent) {
          out.push(`<span class="word" style="--i:${i++}">${ch === ' ' ? ' ' : esc(ch)}</span>`);
        }
      } else if (n.nodeType === 1) {
        out.push(`<span class="word ${n.className}" style="--i:${i++}">${esc(n.textContent)}</span>`);
      }
    }
    h.innerHTML = out.join('');
  }

  /* ---------- reveal + scroll-float ---------- */
  let revealIO;
  function observeReveals() {
    if (reduce) { document.querySelectorAll('[data-reveal],.scroll-float').forEach(e => e.classList.add('in')); return; }
    revealIO = revealIO || new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); revealIO.unobserve(e.target); } });
    }, { threshold: .14 });
    document.querySelectorAll('[data-reveal]:not(.in)').forEach((el, i) => {
      el.style.setProperty('--d', (i % 8) * 60 + 'ms'); revealIO.observe(el);
    });
    document.querySelectorAll('.scroll-float:not(.in)').forEach(el => revealIO.observe(el));
  }

  /* ---------- nav scrolled + hero 视差 ---------- */
  function scrollFx() {
    const nav = $('#nav'); const grid = $('#dotgrid');
    let raf = 0;
    addEventListener('scroll', () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        nav.classList.toggle('is-scrolled', scrollY > 12);
        if (grid && !reduce) grid.style.transform = `translateY(${scrollY * .15}px)`;
        raf = 0;
      });
    }, { passive: true });
  }

  /* ---------- SpotlightCard + Magnet（仅 hover 设备） ---------- */
  function pointerFx() {
    if (!matchMedia('(hover: hover)').matches || reduce) return;
    let raf = 0, lastCard = null;
    document.addEventListener('pointermove', (ev) => {
      const card = ev.target.closest('.card');
      const mag = ev.target.closest('.magnet');
      if (raf) return;
      raf = requestAnimationFrame(() => {
        if (card) {
          const r = card.getBoundingClientRect();
          const px = (ev.clientX - r.left) / r.width;   // 0..1
          const py = (ev.clientY - r.top) / r.height;
          card.style.setProperty('--mx', (ev.clientX - r.left) + 'px');
          card.style.setProperty('--my', (ev.clientY - r.top) + 'px');
          // TiltedCard：随鼠标位置 3D 倾斜（≤6°）
          card.style.setProperty('--ry', ((px - .5) * 12).toFixed(2) + 'deg');
          card.style.setProperty('--rx', ((.5 - py) * 12).toFixed(2) + 'deg');
          if (lastCard && lastCard !== card) resetTilt(lastCard);
          lastCard = card;
        } else if (lastCard) { resetTilt(lastCard); lastCard = null; }
        if (mag) {
          const r = mag.getBoundingClientRect();
          const dx = (ev.clientX - (r.left + r.width / 2)) / r.width;
          const dy = (ev.clientY - (r.top + r.height / 2)) / r.height;
          mag.style.transform = `translate(${dx * 6}px, ${dy * 6}px)`;
        }
        raf = 0;
      });
    }, { passive: true });
    const resetTilt = (c) => { c.style.setProperty('--rx', '0deg'); c.style.setProperty('--ry', '0deg'); };
    document.querySelectorAll('.magnet').forEach(m =>
      m.addEventListener('pointerleave', () => { m.style.transform = ''; }));
  }

  /* ---------- Hero Aurora 背景（Canvas-2D，离屏暂停；移动/reduced-motion 用静态渐变） ---------- */
  function aurora() {
    const cv = $('#aurora'); if (!cv) return;
    if (reduce || matchMedia('(max-width: 640px)').matches) { cv.classList.add('aurora--static'); return; }
    const ctx = cv.getContext('2d');
    const css = getComputedStyle(document.documentElement);
    const cols = ['--aurora-1', '--aurora-2', '--aurora-3', '--aurora-4']
      .map(v => css.getPropertyValue(v).trim() || '#5B8CFF');
    let W, H, dpr, blobs = [], raf = 0, running = false;
    function resize() {
      dpr = Math.min(devicePixelRatio || 1, 2);
      W = cv.clientWidth; H = cv.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr; ctx.scale(dpr, dpr);
    }
    function init() {
      blobs = cols.map((c, i) => ({
        c, x: Math.random() * 1, y: Math.random() * 1,
        r: 0.34 + Math.random() * 0.18,
        ax: (Math.random() * 2 - 1) * 0.00006, ay: (Math.random() * 2 - 1) * 0.00006,
        ph: Math.random() * 6.28
      }));
    }
    function draw(t) {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      blobs.forEach(b => {
        const x = (b.x + Math.sin(t * b.ax + b.ph) * 0.12) * W;
        const y = (b.y + Math.cos(t * b.ay + b.ph) * 0.12) * H;
        const rad = b.r * Math.min(W, H);
        const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
        g.addColorStop(0, b.c + '66'); g.addColorStop(1, b.c + '00');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, rad, 0, 6.2832); ctx.fill();
      });
      ctx.globalCompositeOperation = 'source-over';
      raf = requestAnimationFrame(draw);
    }
    function start() { if (running) return; running = true; raf = requestAnimationFrame(draw); }
    function stop() { running = false; cancelAnimationFrame(raf); }
    resize(); init(); addEventListener('resize', () => { resize(); }, { passive: true });
    // 离屏暂停：Hero 不可见时停渲染，省电省 FPS
    new IntersectionObserver((es) => es.forEach(e => e.isIntersecting ? start() : stop()),
      { threshold: .01 }).observe(cv);
  }

  /* ---------- 巧思：滚动到底致谢彩蛋 ---------- */
  function easterEgg() {
    let fired = false;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = '📷 你一直看到了底 —— 谢谢，今天的快门交给你了。';
    document.body.appendChild(toast);
    addEventListener('scroll', () => {
      if (fired) return;
      if (scrollY + innerHeight >= document.body.scrollHeight - 4) {
        fired = true; toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 4200);
      }
    }, { passive: true });
  }

  /* ================= 详情页 ================= */
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  function findItem(id) {
    for (const cid of Object.keys(DATA.byCategory)) {
      const it = bucket(cid).items.find(i => i.id === id);
      if (it) return { it, cid };
    }
    return null;
  }

  // 该商品上了哪些榜、第几名
  function boardBadges(it, cid) {
    const b = bucket(cid).boards;
    const defs = [['bestselling', 'sales', '最畅销'], ['hottest', 'hot', '最火'], ['latest', 'latest', '最新']];
    return defs.map(([k, cls, label]) => {
      const idx = (b[k] || []).indexOf(it.id);
      return idx < 0 ? '' :
        `<span class="badge badge--${cls}"><span class="dot"></span>${label} No.${idx + 1}</span>`;
    }).join('');
  }

  function galleryHTML(it) {
    const imgs = it.images || [];
    if (!imgs.length) {
      const src = bestSourceLink(it);
      const link = src ? `<a class="link" href="${esc(src.url)}" target="_blank" rel="noopener">查看 ${esc(src.label)} 实拍 →</a>` : '';
      return `<div class="gallery"><div class="gallery__main"><div class="empty">
        ${cameraSVG(it.brand)}<span>产品图待补 · 真实图整理中</span>${link}
      </div></div></div>`;
    }
    const main = `<img src="${esc(imgs[0])}" alt="${esc(it.name)}"
      onerror="this.outerHTML=window.__camSVG(${JSON.stringify(it.brand)})">`;
    const thumbs = imgs.map((u, i) => `
      <button class="gallery__thumb ${i === 0 ? 'is-active' : ''}" data-img="${esc(u)}" aria-label="视图 ${i + 1}">
        <img src="${esc(u)}" alt="" loading="lazy"></button>`).join('');
    return `<div class="gallery">
      <div class="gallery__main">${main}</div>
      ${imgs.length > 1 ? `<div class="gallery__thumbs">${thumbs}</div>` : ''}
    </div>`;
  }

  function specsHTML(it) {
    const fields = Object.keys(it.specs || {});
    if (!fields.length) return '';
    const rows = fields.map(f => {
      const srcs = (it.spec_sources && it.spec_sources[f]) || [];
      const crossed = srcs.length > 1 ? '<span class="spec__crossed" title="多来源交叉确认">✓ 交叉确认</span>' : '';
      const tags = srcs.map(s => `<span class="spec__src">${esc(s)}</span>`).join('');
      return `<tr>
        <th>${esc(f)}</th>
        <td><span class="spec__val">${esc(it.specs[f])}</span> ${crossed}<div class="spec__srcs">${tags}</div></td>
      </tr>`;
    }).join('');
    return `<div class="dsection">
      <h3 class="dsection__title">参数规格 <span class="dsection__note">跨来源交叉对比 · 查漏补缺 · 标注出处</span></h3>
      <table class="specs">${rows}</table>
    </div>`;
  }

  function sellersHTML(it) {
    const sellers = it.sellers || [];
    if (!sellers.length) return '';
    const rows = sellers.map(s => `
      <a class="seller" href="${esc(s.url)}" target="_blank" rel="noopener">
        <span class="seller__name">${esc(s.name)}${s.is_official ? '<span class="seller__official">官方</span>' : ''}</span>
        <span class="seller__meta">
          ${s.price_value != null ? `<span class="seller__price">¥${s.price_value}</span>` : ''}
          ${s.rating != null ? `<span class="seller__rating">★ ${s.rating}</span>` : ''}
          ${s.review_count != null ? `<span class="seller__rc">${s.review_count} 条评价</span>` : ''}
        </span>
        <span class="seller__go">访问 →</span>
      </a>`).join('');
    return `<div class="dsection">
      <h3 class="dsection__title">购买渠道 <span class="dsection__note">各售卖网站 + 官网</span></h3>
      <div class="sellers">${rows}</div>
    </div>`;
  }

  function reviewListHTML(reviews, kind) {
    const top = [...(reviews || [])].sort((a, b) => (b.helpful || 0) - (a.helpful || 0)).slice(0, 10);
    if (!top.length) return '';
    return top.map(r => `<li class="review review--${kind}">
      <p class="review__text">${esc(r.text)}</p>
      <span class="review__meta">${esc(r.source || '')}${r.helpful ? ` · 👍 ${r.helpful}` : ''}</span>
    </li>`).join('');
  }

  // 用户评价：只展示「真实」评价；无真实评价 → 空状态 + 去电商看评价的链接（杜绝示例/编造）
  function reviewsHTML(it) {
    const withReviews = (it.sellers || []).filter(s => (s.reviews_pos || []).length || (s.reviews_neg || []).length);
    const head = `<h3 class="dsection__title">用户评价 <span class="dsection__note">仅展示真实评价 · 无则给电商链接</span></h3>`;
    if (!withReviews.length) {
      const links = (it.sellers || [])
        .filter(s => /京东|淘宝|天猫/.test(s.name || ''))
        .map(s => `<a class="link" href="${esc(s.url)}" target="_blank" rel="noopener">去 ${esc(s.name)} 看真实评价 →</a>`)
        .join('');
      return `<div class="dsection">${head}
        <div class="empty empty--wide">
          ${reviewIcon()}<span>暂无已核验的真实用户评价</span>
          <div class="empty__links">${links || '<span class="reviews__empty">可在各电商商品页查看买家评价</span>'}</div>
        </div></div>`;
    }
    const blocks = withReviews.map(s => `
      <div class="reviews__site">
        <h4 class="reviews__sitename">${esc(s.name)}</h4>
        <div class="reviews__cols">
          <div><div class="reviews__head reviews__head--pos">好评</div><ul>${reviewListHTML(s.reviews_pos, 'pos') || '<li class="reviews__empty">暂无</li>'}</ul></div>
          <div><div class="reviews__head reviews__head--neg">差评</div><ul>${reviewListHTML(s.reviews_neg, 'neg') || '<li class="reviews__empty">暂无</li>'}</ul></div>
        </div>
      </div>`).join('');
    return `<div class="dsection">${head}${blocks}</div>`;
  }
  function reviewIcon() {
    return `<svg class="camsvg" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="1.6"/>
    </svg>`;
  }

  function creditsHTML(it) {
    const cr = it.image_credits || [];
    if (!cr.length) return '';
    const items = cr.map(c => `<li>${esc(c.title)}${c.license ? ` · ${esc(c.license)}` : ''}${c.artist ? ` · ${esc(c.artist)}` : ''}
      ${c.descurl ? ` · <a class="link" href="${esc(c.descurl)}" target="_blank" rel="noopener">来源</a>` : ''}</li>`).join('');
    return `<div class="dsection dsection--credits">
      <h3 class="dsection__title">图片来源 <span class="dsection__note">Wikimedia Commons，已注明许可与作者</span></h3>
      <ul class="credits">${items}</ul>
    </div>`;
  }

  // 市场数据面板：真实评分/评价/畅销榜 + 参与平台 + 截至日期
  const PLAT_LABEL = { amazon: 'Amazon', jd: '京东', taobao: '淘宝' };
  function marketHTML(it) {
    // 只展示真实购物平台；'manual'/'buzz' 是内部打分/热度构造，不在面板显示
    const plats = Object.keys(it.platforms || {}).filter(p => p !== 'manual' && p !== 'buzz');
    if (!plats.length) {
      return `<div class="market market--new"><span class="market__newdot"></span>${esc((it.release_date || '').slice(0,7))} 新上市 · 暂无电商热度/销量数据（太新）</div>`;
    }
    const cur = p => (p.currency === 'CNY' ? '¥' : '$');
    const shown = [];   // 实际有可展示数据的平台（跳过空的 manual 等）
    const groups = plats.map(p => {
      const d = it.platforms[p] || {}, c = [];
      if (d.price != null) c.push(`<span class="market__chip market__chip--price">${cur(d)}${d.price}</span>`);
      if (d.rating != null) c.push(`<span class="market__chip">★ ${d.rating}</span>`);
      if (d.reviews != null) c.push(`<span class="market__chip">${(+d.reviews).toLocaleString()} 评价</span>`);
      if (d.good_rate != null) c.push(`<span class="market__chip">好评 ${d.good_rate}%</span>`);
      if (d.sales != null) c.push(`<span class="market__chip">月销 ${(+d.sales).toLocaleString()}</span>`);
      if (d.bsr != null) c.push(`<span class="market__chip">Amazon 畅销榜 #${(+d.bsr).toLocaleString()}</span>`);
      if (d.jd_rank != null) c.push(`<span class="market__chip market__chip--hot">京东拍立得榜 #${d.jd_rank}</span>`);
      if (!c.length) return '';   // 该平台没有任何可展示数据 → 不渲染空行
      shown.push(p);
      return `<div class="market__plat"><span class="market__platname">${PLAT_LABEL[p] || p}</span>${c.join('')}</div>`;
    }).join('');
    if (!shown.length) {
      return `<div class="market market--new"><span class="market__newdot"></span>${esc((it.release_date || '').slice(0,7))} 新上市 · 暂无电商热度/销量数据（太新）</div>`;
    }
    const src = shown.map(p => PLAT_LABEL[p] || p).join(' / ');
    return `<div class="market">
      <div class="market__title">真实市场数据</div>
      ${groups}
      <div class="market__src">综合自 ${esc(src)} · 截至 ${esc(it.data_as_of || '—')}</div>
    </div>`;
  }

  function renderDetail(id) {
    const found = findItem(id);
    const el = $('#detail');
    if (!found) { el.innerHTML = '<div class="container"><a class="link" href="#">← 返回</a><p>未找到该商品。</p></div>'; return; }
    const { it, cid } = found;
    document.title = `${it.name} · 器材榜`;
    el.innerHTML = `
      <div class="container">
        <a class="dback link" href="#">← 返回榜单</a>
        <div class="dhero">
          ${galleryHTML(it)}
          <div class="dhero__info">
            <span class="card__brand">${esc(it.brand)}</span>
            <h1 class="dhero__name">${esc(it.name)}</h1>
            <div class="dhero__badges">${boardBadges(it, cid)}</div>
            <p class="dhero__summary">${esc(it.summary)}</p>
            <div class="tags">${(it.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
            ${marketHTML(it)}
            <div class="dhero__buy">
              <span class="focus__price">${it.price_display || '—'}</span>
              ${it.official_url ? `<a class="btn" href="${esc(it.official_url)}" target="_blank" rel="noopener">前往官网</a>` : ''}
            </div>
          </div>
        </div>
        ${specsHTML(it)}
        ${sellersHTML(it)}
        ${reviewsHTML(it)}
        ${creditsHTML(it)}
      </div>`;
    // 多视图切换
    el.querySelectorAll('.gallery__thumb').forEach(btn => btn.addEventListener('click', () => {
      const main = el.querySelector('.gallery__main img');
      if (main) main.src = btn.dataset.img;
      el.querySelectorAll('.gallery__thumb').forEach(b => b.classList.toggle('is-active', b === btn));
    }));
  }

  /* ---------- hash 路由 ---------- */
  function route() {
    const m = location.hash.match(/item=([^&]+)/);
    const detailMode = !!m;
    document.body.classList.toggle('viewing-detail', detailMode);
    $('#detail').hidden = !detailMode;
    if (detailMode) {
      renderDetail(decodeURIComponent(m[1]));
      scrollTo(0, 0);
    } else {
      document.title = '器材榜 — 最新 / 最火 / 最畅销';
    }
  }

  /* ---------- init ---------- */
  $('#sortSelect').addEventListener('change', renderAll);
  if ($('#histToggle')) $('#histToggle').addEventListener('change', renderAll);
  renderHeader();
  renderPills();
  splitHero();
  renderCategory();
  countUp();
  observeReveals();
  scrollFx();
  pointerFx();
  aurora();
  easterEgg();
  addEventListener('hashchange', route);
  route();
})();
