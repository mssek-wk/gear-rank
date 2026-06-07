"""官网适配器（enricher）—— 实时确认官网可达，并把「官网」登记为参数来源之一。

做法：按品牌去重，对每个品牌官网做一次实时 GET；可达则给该品牌下所有商品追加一条
官网 Source 记录，作为参数「交叉确认」的来源之一（详情页会显示参数被哪些来源证实）。

进一步抓取官网结构化参数（各机型规格页）属于易碎工作（官网多为 JS 渲染），
预留在 _extract_specs 里，接入时按机型补 URL + 解析即可。
"""

from __future__ import annotations

from datetime import datetime, timezone

from schema import Item, Source
from .base import Adapter
from . import _http

OFFICIAL_HOMES = {
    "Fujifilm": "https://instax.com/",
    "Polaroid": "https://www.polaroid.com/",
    "Kodak": "https://www.kodak.com/",
}


class OfficialAdapter(Adapter):
    name = "官网"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        reachable: dict[str, bool] = {}
        for brand, home in OFFICIAL_HOMES.items():
            reachable[brand] = _http.get_text(home) is not None

        ok = 0
        for it in items:
            home = it.official_url or OFFICIAL_HOMES.get(it.brand, "")
            if home and reachable.get(it.brand):
                it.official_url = it.official_url or home
                it.sources.append(Source(name=f"{it.brand} 官网", url=home, fetched_at=now))
                ok += 1
        print(f"  · 官网: {ok}/{len(items)} 件官网可达并已登记为来源 "
              f"({', '.join(b for b, r in reachable.items() if r) or '无'})")

    def _extract_specs(self, item: Item, html: str) -> None:
        """TODO: 解析官网机型规格页，it.add_spec(字段, 值, f'{品牌} 官网')。"""
        pass
