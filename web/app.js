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

  /* ---------- 内联 SVG 相机插画（产品图兜底，非纯色块） ---------- */
  const BRAND_TINT = {
    Fujifilm: '#1FA37A', Polaroid: '#E5533C', Kodak: '#E0A100', default: '#1A1A1A'
  };
  function cameraSVG(brand) {
    const tint = BRAND_TINT[brand] || BRAND_TINT.default;
    return `<svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${brand} 拍立得">
      <rect x="18" y="34" width="84" height="62" rx="12" stroke="#1A1A1A" stroke-width="3"/>
      <rect x="18" y="86" width="84" height="10" rx="5" fill="#F4F4F3" stroke="#1A1A1A" stroke-width="3"/>
      <circle cx="60" cy="62" r="20" stroke="#1A1A1A" stroke-width="3"/>
      <circle cx="60" cy="62" r="10" fill="${tint}" opacity=".18"/>
      <circle cx="60" cy="62" r="10" stroke="#1A1A1A" stroke-width="2.5"/>
      <rect x="30" y="42" width="14" height="8" rx="2" fill="${tint}"/>
      <rect x="78" y="40" width="14" height="10" rx="3" stroke="#1A1A1A" stroke-width="2.5"/>
      <rect x="40" y="92" width="40" height="20" rx="3" fill="#FFFFFF" stroke="#1A1A1A" stroke-width="2.5"/>
    </svg>`;
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

  /* ---------- 渲染：品类 pills ---------- */
  function renderPills() {
    const el = $('#pills');
    el.innerHTML = cats.map(c => `
      <button class="pill" role="tab" data-cat="${c.id}"
        aria-selected="${c.id === activeCat}">
        ${c.name} <span class="pill__count">${c.count}</span>
      </button>`).join('');
    el.querySelectorAll('.pill').forEach(p =>
      p.addEventListener('click', () => { activeCat = p.dataset.cat; renderCategory(); }));
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

  /* ---------- 渲染：三榜 ---------- */
  const BOARD_DEFS = [
    { key: 'latest', cls: 'latest', title: '最新', sub: '按上市时间' },
    { key: 'hottest', cls: 'hot', title: '最火', sub: '按讨论热度' },
    { key: 'bestselling', cls: 'sales', title: '最畅销', sub: '按销量排名' },
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
          <span class="row__price">${it.price_display || ''}</span>
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
    const items = [...bucket(activeCat).items];
    const mode = $('#sortSelect').value;
    items.sort(SORTERS[mode] || SORTERS.sales);
    $('#allDesc').textContent = `${items.length} 款${catName(activeCat)}，数据本地留存，每次更新自动重排。`;
    $('#allGrid').innerHTML = items.map(it => `
      <a class="card" href="#item=${it.id}" data-reveal>
        <div class="card__media">${mediaHTML(it)}</div>
        <span class="card__brand">${it.brand}</span>
        <span class="card__name">${it.name}</span>
        <div class="tags">${(it.tags || []).slice(0, 2).map(t => `<span class="tag">${t}</span>`).join('')}</div>
        <div class="card__foot">
          <span class="card__price">${it.price_display || '—'}</span>
        </div>
      </a>`).join('');
    observeReveals();
  }
  const catName = (cid) => (cats.find(c => c.id === cid) || {}).name || '';

  /* ---------- 切换品类时重渲染依赖品类的区块 ---------- */
  function renderCategory() {
    $('#pills').querySelectorAll('.pill').forEach(p =>
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
    const text = h.textContent.trim();
    h.innerHTML = text.split('').map((ch, i) =>
      `<span class="word" style="--i:${i}">${ch === ' ' ? ' ' : ch}</span>`).join('');
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
    let raf = 0;
    document.addEventListener('pointermove', (ev) => {
      const card = ev.target.closest('.card');
      const mag = ev.target.closest('.magnet');
      if (raf) return;
      raf = requestAnimationFrame(() => {
        if (card) {
          const r = card.getBoundingClientRect();
          card.style.setProperty('--mx', (ev.clientX - r.left) + 'px');
          card.style.setProperty('--my', (ev.clientY - r.top) + 'px');
        }
        if (mag) {
          const r = mag.getBoundingClientRect();
          const dx = (ev.clientX - (r.left + r.width / 2)) / r.width;
          const dy = (ev.clientY - (r.top + r.height / 2)) / r.height;
          mag.style.transform = `translate(${dx * 6}px, ${dy * 6}px)`;
        }
        raf = 0;
      });
    }, { passive: true });
    document.querySelectorAll('.magnet').forEach(m =>
      m.addEventListener('pointerleave', () => { m.style.transform = ''; }));
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
    if (!imgs.length) return `<div class="gallery"><div class="gallery__main">${cameraSVG(it.brand)}</div></div>`;
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
    if (!top.length) return `<p class="reviews__empty">暂无${kind === 'pos' ? '好评' : '差评'}</p>`;
    return top.map(r => `<li class="review review--${kind}">
      <p class="review__text">${esc(r.text)}</p>
      <span class="review__meta">${esc(r.source || '')} · 👍 ${r.helpful || 0}</span>
    </li>`).join('');
  }

  function reviewsHTML(it) {
    const withReviews = (it.sellers || []).filter(s => (s.reviews_pos || []).length || (s.reviews_neg || []).length);
    if (!withReviews.length) return '';
    const sample = withReviews.some(s => (s.reviews_pos[0] || s.reviews_neg[0] || {}).source?.includes('示例'));
    const blocks = withReviews.map(s => `
      <div class="reviews__site">
        <h4 class="reviews__sitename">${esc(s.name)}</h4>
        <div class="reviews__cols">
          <div><div class="reviews__head reviews__head--pos">好评 Top</div><ul>${reviewListHTML(s.reviews_pos, 'pos')}</ul></div>
          <div><div class="reviews__head reviews__head--neg">差评 Top</div><ul>${reviewListHTML(s.reviews_neg, 'neg')}</ul></div>
        </div>
      </div>`).join('');
    return `<div class="dsection">
      <h3 class="dsection__title">用户评价 <span class="dsection__note">各售卖网站好评/差评 Top10</span></h3>
      ${sample ? '<p class="reviews__note">⚠ 当前评价为代表性示例，接入电商真实抓取后自动替换（见 README）。</p>' : ''}
      ${blocks}
    </div>`;
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
      document.title = '器材榜 · 拍立得 — 最新 / 最火 / 最畅销';
    }
  }

  /* ---------- init ---------- */
  $('#sortSelect').addEventListener('change', renderAll);
  renderHeader();
  renderPills();
  splitHero();
  renderCategory();
  countUp();
  observeReveals();
  scrollFx();
  pointerFx();
  easterEgg();
  addEventListener('hashchange', route);
  route();
})();
