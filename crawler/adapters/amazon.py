"""Amazon 适配器（enricher）—— 真实「评分 / 评价数 / 畅销榜排名 / 价格」。

数据存于 data/platform_snapshot.json（每条带 as_of 日期，可核验）。
- 默认：读快照（快、离线可用）。把已核验的真实值喂给管线。
- 设环境变量 GEARRANK_LIVE=1 时：逐个 ASIN 实时重抓 Amazon 商品页并更新快照
  （每日定时任务用，见 scripts/daily_update.sh）。Amazon 偶发限流时回退到快照值，绝不清空。

抓取字段锚定 Amazon 主商品元素，避免匹配到相关/赞助商品：
  评价数 acrCustomerReviewText、评分 acrPopover、价格 priceAmount、畅销榜 #N in Electronics。
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date
from pathlib import Path

from schema import Item
from .base import Adapter
from . import _http

SNAPSHOT = Path(__file__).resolve().parent.parent.parent / "data" / "platform_snapshot.json"
LIVE = os.environ.get("GEARRANK_LIVE") == "1"


def _scrape(asin: str) -> dict | None:
    h = _http.get_text(f"https://www.amazon.com/dp/{asin}")
    if not h:
        return None
    rv = re.search(r'id="acrCustomerReviewText"\s+aria-label="([\d,]+)\s+Reviews?"', h)
    rt = re.search(r'id="acrPopover"[^>]*title="([0-9.]+) out of 5', h)
    pr = re.search(r'"priceAmount":\s*([\d.]+)', h)
    bsr = re.search(r'#([\d,]+)\s+in\s+Electronics', h)
    return {"asin": asin,
            "rating": float(rt.group(1)) if rt else None,
            "reviews": int(rv.group(1).replace(",", "")) if rv else None,
            "price": float(pr.group(1)) if pr else None,
            "bsr": int(bsr.group(1).replace(",", "")) if bsr else None}


class AmazonAdapter(Adapter):
    name = "Amazon"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        snap = {"as_of": "", "items": {}}
        if SNAPSHOT.exists():
            try:
                snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            except Exception:
                pass
        snap_items = snap.get("items", {})

        if LIVE:
            print("  · Amazon: 实时刷新中（GEARRANK_LIVE=1）…")
            for i, it in enumerate(items):
                if not it.asin:
                    continue
                if i:
                    time.sleep(0.8)
                fresh = _scrape(it.asin)
                if fresh and fresh.get("bsr") is not None:      # 抓到有效数据才覆盖
                    snap_items.setdefault(it.id, {})["amazon"] = fresh
            snap = {"as_of": date.today().isoformat(), "source": "Amazon US", "items": snap_items}
            SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

        as_of = snap.get("as_of", "")
        n = 0
        for it in items:
            az = (snap_items.get(it.id) or {}).get("amazon")
            if not az:
                continue
            it.platforms["amazon"] = az
            it.data_as_of = as_of
            if az.get("price") is not None:
                it.price_value, it.currency = az["price"], "USD"
            n += 1
        print(f"  · Amazon: {n}/{len(items)} 款带真实指标（评分/评价/畅销榜），截至 {as_of}"
              + ("" if LIVE else "（用快照，设 GEARRANK_LIVE=1 实时刷新）"))
