"""适配器基类。

两类角色（一个适配器可只实现其一）：
  - producer：实现 fetch(category_id) -> list[Item]，从某数据源「产出」候选商品。
  - enricher：实现 enrich(category_id, items)，给已合并的商品「补充」字段（图片/参数/评价…）。

管线流程：先跑所有 producer 的 fetch() 收集并按 id 合并，再依次跑所有 enricher 的
enrich() 在合并结果上原地补全。这样接入新数据源时改动面最小，也天然支持「跨源交叉补全」。

约定：网络失败 / 反爬 / 未实现一律「打印告警 + 跳过」，不要抛异常，
以免单个源拖垮整次更新。
"""

from __future__ import annotations

from schema import Item


class Adapter:
    name: str = "base"

    def fetch(self, category_id: str) -> list[Item]:
        """producer：产出候选商品列表（默认不产出）。"""
        return []

    def enrich(self, category_id: str, items: list[Item]) -> None:
        """enricher：在已合并的 items 上原地补充字段（默认什么都不做）。"""
        return None
