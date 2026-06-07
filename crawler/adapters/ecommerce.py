"""电商榜单适配器 —— 「最畅销」数据源（骨架）。

目标：从京东 / 淘宝 / Amazon 的品类销量榜抓取排名与价格，填充 sales_rank。

⚠️ 现状：默认返回空，等你接入真实抓取逻辑。之所以做成「不报错的空实现」，
是为了让整条管线在数据源未就绪时也能跑通（示例数据先顶上）。

接入指南（在下方 _fetch_jd_rank 里实现）：
  1. 主流电商有反爬，优先走官方/联盟 API；无 API 再考虑 requests + 解析。
  2. 动态渲染页面（销量榜常是 JS 渲染）用 Playwright：
        playwright install chromium
        page.goto(榜单URL); page.wait_for_selector(...)
  3. 解析出 (商品名, 品牌, 价格, 排名, 链接, 图片) 后，映射成 schema.Item，
     **务必复用与示例数据一致的 id 规则**（brand-model 小写连字符），
     这样同一台相机的电商数据能和媒体数据按 id 自动合并。
  4. 合规：尊重 robots.txt 与各平台条款；控制频率；仅抓公开榜单页。
"""

from __future__ import annotations

from schema import Item
from .base import Adapter

# 各品类对应的电商榜单页（示意；接入时替换为真实 URL，可按平台拆成多个）
CATEGORY_RANK_URLS = {
    "instant-camera": [
        # "https://list.jd.com/list.html?cat=...&sort=sort_totalsales15_desc",
    ],
}


class EcommerceAdapter(Adapter):
    name = "ecommerce"

    def fetch(self, category_id: str) -> list[Item]:
        urls = CATEGORY_RANK_URLS.get(category_id, [])
        if not urls:
            print(f"  · ecommerce: 品类 '{category_id}' 未配置榜单 URL，跳过（待接入）")
            return []
        items: list[Item] = []
        for url in urls:
            try:
                items.extend(self._fetch_jd_rank(category_id, url))
            except Exception as e:  # 单源失败不拖垮整次更新
                print(f"  ! ecommerce: 抓取失败 {url} -> {e}")
        return items

    def _fetch_jd_rank(self, category_id: str, url: str) -> list[Item]:
        """TODO: 实现真实抓取。返回带 sales_rank / price_value / image / url 的 Item 列表。"""
        raise NotImplementedError("电商榜单抓取尚未实现 —— 见本文件顶部接入指南")
