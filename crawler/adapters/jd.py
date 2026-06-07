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

from schema import Item, Source
from .base import Adapter

SESSION = Path(__file__).resolve().parent.parent / ".cn_session" / "jd.json"
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
        if not SESSION.exists():
            print("  · 京东: 未发现登录会话，跳过（先跑 scripts/login_cn.py jd）")
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  · 京东: 未装 playwright，跳过（pip install --user playwright）")
            return

        ok = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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
