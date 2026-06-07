"""测评 / 媒体适配器 —— 「最新」与「最火」数据源（骨架）。

目标：从相机媒体与种草社区抓取新品发布与热度信号，填充 release_date 与 hot_index：
  - 最新：新品发布日期（厂商发布会 / 媒体上新）
  - 最火：评测数、搜索/社媒讨论度，归一化成 0-100 的 hot_index

⚠️ 现状：默认返回空，等你接入真实抓取逻辑（不报错，便于管线先用示例数据跑通）。

候选数据源（按可抓性 / 合规性自行取舍）：
  - DPReview / 数码媒体的「新品」「评测」列表 -> release_date、评测热度
  - 什么值得买：拍立得相关「好价 / 文章」热度 -> hot_index
  - 小红书 / B站 关键词热度：多为登录墙 + 反爬，建议走开放数据或人工补充

实现位置：_fetch_media_feed。解析后映射成 schema.Item，
id 规则与示例数据保持一致（brand-model 小写连字符）以便跨源按 id 合并。
"""

from __future__ import annotations

from schema import Item
from .base import Adapter

CATEGORY_FEED_URLS = {
    "instant-camera": [
        # "https://www.dpreview.com/products/cameras/...",
    ],
}


class MediaAdapter(Adapter):
    name = "media"

    def fetch(self, category_id: str) -> list[Item]:
        urls = CATEGORY_FEED_URLS.get(category_id, [])
        if not urls:
            print(f"  · media: 品类 '{category_id}' 未配置媒体源 URL，跳过（待接入）")
            return []
        items: list[Item] = []
        for url in urls:
            try:
                items.extend(self._fetch_media_feed(category_id, url))
            except Exception as e:
                print(f"  ! media: 抓取失败 {url} -> {e}")
        return items

    def _fetch_media_feed(self, category_id: str, url: str) -> list[Item]:
        """TODO: 实现真实抓取。返回带 release_date / hot_index 的 Item 列表。"""
        raise NotImplementedError("媒体源抓取尚未实现 —— 见本文件顶部接入指南")
