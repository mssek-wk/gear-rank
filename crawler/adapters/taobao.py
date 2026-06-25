"""淘宝/天猫适配器（enricher）—— 用登录态 Playwright 抓真实价格/销量/评价，并入综合榜。

激活步骤同京东：
  1) playwright 安装；2) python3 scripts/login_cn.py taobao（扫码登录）；
  3) 在 TAOBAO_ITEM 里登记 机型id -> 商品 URL（或留空走搜索兜底）；4) 跑 crawler。

写入 it.platforms["taobao"] = {"price","sales","reviews","currency":"CNY"}。
淘宝风控更严，登录态下也可能需要人机验证；抓不到一律跳过，不影响其他平台。
选择器为最佳努力版，按实际 DOM 微调。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from schema import Item, Source
from .base import Adapter

SESSION = Path(__file__).resolve().parent.parent / ".cn_session" / "taobao.json"
SNAPSHOT = Path(__file__).resolve().parent.parent.parent / "data" / "platform_snapshot.json"
TAOBAO_ITEM: dict[str, str] = {
    # "汉印-z6": "https://item.taobao.com/item.htm?id=<id>",
}


def _num(s: str):
    m = re.search(r"([\d.]+)\s*万", s or "")
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m else None


class TaobaoAdapter(Adapter):
    name = "淘宝"

    def _load_snapshot(self, items: list[Item]) -> int:
        if not SNAPSHOT.exists():
            return 0
        try:
            si = (json.loads(SNAPSHOT.read_text(encoding="utf-8")) or {}).get("items", {})
        except Exception:
            return 0
        n = 0
        for it in items:
            blk = si.get(it.id) or {}
            tb = blk.get("taobao")
            if tb:
                it.platforms["taobao"] = tb
                _as_of = tb.get("as_of", "")
                if _as_of and _as_of > (it.data_as_of or ""):
                    it.data_as_of = _as_of  # 取各平台最新日期，避免被先跑的平台占住
                n += 1
            # 顺带载入社媒讨论热度 + 广告嫌疑标记（供前端展示/交叉验证）
            if blk.get("buzz"):
                it.platforms["buzz"] = blk["buzz"]
        return n

    def enrich(self, category_id: str, items: list[Item]) -> None:
        # 1) 载入快照里的真实淘宝数据（手动浏览/截屏整理写入 platform_snapshot.json，见 WRITING.md）
        snap_n = self._load_snapshot(items)
        if snap_n:
            print(f"  · 淘宝: {snap_n} 款用真实数据（手动整理，截至快照日期）")

        # 2) 可选：有登录会话再用 Playwright 实时刷新（最佳努力，失败保留快照）
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
                url = TAOBAO_ITEM.get(it.id)
                if not url:
                    continue
                try:
                    page.goto(url, timeout=25000)
                    page.wait_for_timeout(2500)
                    txt = page.inner_text("body")
                    price = re.search(r'¥\s*([\d]+\.?\d*)', txt)
                    sales = re.search(r'(\d[\d.,]*\s*万?)\s*(?:人付款|人收货|月销|已售)', txt)
                    reviews = re.search(r'累计评价\D*?([\d,]+)', txt) or re.search(r'(\d[\d.,]*\s*万?)\s*条评价', txt)
                    it.platforms["taobao"] = {
                        "currency": "CNY",
                        "price": float(price.group(1)) if price else None,
                        "sales": _num(sales.group(1)) if sales else None,
                        "reviews": _num(reviews.group(1)) if reviews else None,
                    }
                    it.sources.append(Source(name="淘宝", url=url))
                    ok += 1
                except Exception as e:
                    print(f"  ! 淘宝抓取失败 {it.id}: {str(e)[:50]}")
            browser.close()
        print(f"  · 淘宝: {ok}/{len(items)} 款拿到真实数据（登录态）")
