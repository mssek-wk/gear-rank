"""淘宝/天猫适配器（enricher）—— 真实「销量/评价」，接入后并入综合榜（待激活）。

目标：给每款机型补 it.platforms["taobao"] = {"price","reviews","sales","sales_rank",...}，
管线会把它与 Amazon/京东 归一化平均，得出「综合最火 / 综合最畅销」。

⚠️ 淘宝/天猫的销量与评价基本都在**登录态 + 强风控**之后，裸 HTTP 不可得。激活方式：
  A. 淘宝开放平台 / 淘宝客 API（需 appkey 与备案，最合规）；
  B. Playwright 带登录 Cookie 抓商品页（storage_state 预登录）；
  C. 人工导出。
拿到后写入 it.platforms["taobao"]，并追加 it.sources 一条来源。
"""

from __future__ import annotations

from schema import Item
from .base import Adapter

TAOBAO_ITEM: dict[str, str] = {}   # id -> 商品 itemId 或 URL（接入时填）


class TaobaoAdapter(Adapter):
    name = "淘宝"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        if not TAOBAO_ITEM:
            print("  · 淘宝: 未配置商品/接入方式，跳过（待接入；见 taobao.py 顶部）")
            return
        for it in items:
            iid = TAOBAO_ITEM.get(it.id)
            if not iid:
                continue
            try:
                data = self._fetch(iid)
                if data:
                    it.platforms["taobao"] = data
            except Exception as e:
                print(f"  ! 淘宝抓取失败 {it.id}: {e}")

    def _fetch(self, item_id: str) -> dict | None:
        raise NotImplementedError("淘宝真实数据接入见本文件顶部 A/B/C 方案")
