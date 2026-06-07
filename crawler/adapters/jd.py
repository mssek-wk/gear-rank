"""京东适配器（enricher）—— 用登录态 Playwright 抓真实价格/评价数/好评率，并入综合榜。

激活步骤：
  1) pip install --user playwright && python3 -m playwright install chromium
  2) python3 scripts/login_cn.py jd        # 扫码登录一次，保存会话
  3) 在 JD_SKU 里登记 机型id -> 京东商品 URL（或留空走搜索兜底）
  4) 跑 crawler：jd 适配器会带登录态打开商品页，解析后写入 it.platforms["jd"]

写入字段：{"price","reviews","good_rate","currency":"CNY"}，
管线会把它和 Amazon 等平台归一化后取平均 → 综合最火/最畅销。

注意：京东页面结构会变，下方选择器是「最佳努力」版，首次跑通后按实际 DOM 微调即可；
登录 cookie 会过期，重跑 login_cn.py 即可。抓不到一律跳过，不影响其他平台。
"""

from __future__ import annotations

import re
from pathlib import Path

import json

from schema import Item, Source
from .base import Adapter

SESSION = Path(__file__).resolve().parent.parent / ".cn_session" / "jd.json"
SNAPSHOT = Path(__file__).resolve().parent.parent.parent / "data" / "platform_snapshot.json"
JD_SKU: dict[str, str] = {
    # "汉印-z6": "https://item.jd.com/<sku>.html",
}


def _num(s: str):
    m = re.search(r"([\d.]+)\s*万", s or "")
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m else None


class JdAdapter(Adapter):
    name = "京东"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        # 1) 先载入快照里已核验的真实京东数据（由真实 Chrome 实时浏览抓取，绕过京东频控）
        snap_n = self._load_snapshot(items)
        if snap_n:
            print(f"  · 京东: {snap_n} 款用真实数据（Chrome 实时浏览抓取，截至快照日期）")

        # 2) 可选：有登录会话时再用 Playwright 尝试实时刷新（京东频控基本会拦，最佳努力，失败保留快照）
        if not SESSION.exists():
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return

        ok = 0
        with sync_playwright() as p:
            # 用「完整 chromium + --headless=new」无窗口运行，免去单独的 headless-shell 依赖
            browser = p.chromium.launch(headless=False, args=["--headless=new"])
            ctx = browser.new_context(storage_state=str(SESSION))
            page = ctx.new_page()
            for it in items:
                url = JD_SKU.get(it.id) or self._search(page, it)
                if not url:
                    continue
                try:
                    data = self._scrape(page, url)
                    if data:
                        it.platforms["jd"] = data
                        it.sources.append(Source(name="京东", url=url))
                        ok += 1
                except Exception as e:
                    print(f"  ! 京东抓取失败 {it.id}: {str(e)[:50]}")
            browser.close()
        print(f"  · 京东: {ok}/{len(items)} 款拿到真实数据（登录态）")

    def _load_snapshot(self, items: list[Item]) -> int:
        if not SNAPSHOT.exists():
            return 0
        try:
            si = (json.loads(SNAPSHOT.read_text(encoding="utf-8")) or {}).get("items", {})
        except Exception:
            return 0
        n = 0
        for it in items:
            jd = (si.get(it.id) or {}).get("jd")
            if jd:
                it.platforms["jd"] = jd
                if not it.data_as_of:
                    it.data_as_of = jd.get("as_of", "")
                n += 1
        return n

    def _search(self, page, it: Item) -> str | None:
        """无 SKU 时，用搜索取第一个商品链接（兜底，可能不精确）。"""
        try:
            page.goto(f"https://search.jd.com/Search?keyword={it.brand}+{it.name}", timeout=20000)
            page.wait_for_selector("a[href*='item.jd.com']", timeout=8000)
            href = page.eval_on_selector("a[href*='item.jd.com']", "a => a.href")
            return href
        except Exception:
            return None

    def _scrape(self, page, url: str) -> dict | None:
        page.goto(url, timeout=25000)
        page.wait_for_timeout(2500)
        html = page.content()
        price = re.search(r'¥?\s*([\d]+\.?\d*)', page.inner_text(".p-price, .price, .summary-price") if page.query_selector(".p-price, .price, .summary-price") else "")
        # 评价数 / 好评率（京东商品页"商品评价"区）
        reviews = None
        for sel in ["#comment-count .count", ".comment-count .count", "#comeval .count"]:
            el = page.query_selector(sel)
            if el:
                reviews = _num(el.inner_text())
                break
        gr = re.search(r'好评[率]?\D*?([\d.]+)%', html)
        return {"currency": "CNY",
                "price": float(price.group(1)) if price else None,
                "reviews": reviews,
                "good_rate": float(gr.group(1)) if gr else None}
