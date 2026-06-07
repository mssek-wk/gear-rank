"""电商榜单 + 真实评价适配器 —— 「最畅销」与好评/差评数据源（骨架）。

目标：从京东 / 淘宝 / Amazon 抓销量排名、价格、以及各站好评/差评 Top10，
填充 sales_rank 与 Seller.reviews_pos/neg。

⚠️ 现状：默认返回空，等你接入真实抓取逻辑（不报错，管线先用示例数据跑通）。

【2026-06 实测结论 —— 评价为什么还是示例】
直接 HTTP 打 JD 评价公开接口
  https://club.jd.com/comment/productPageComments.action?productId=<SKU>&...
已被风控拦截：返回的不是 JSON 而是「系统繁忙」反爬响应。淘宝/天猫评价更需登录态。
=> 真实评价不可能靠裸 HTTP 直抓，必须走下列任一可靠路径：
  A. 官方/联盟开放 API（京东宙斯、淘宝开放平台等，需申请 appkey）——最稳、最合规；
  B. Playwright 带「登录 Cookie」的真实浏览器抓取：
        playwright install chromium
        ctx = browser.new_context(storage_state="jd_login.json")  # 预先登录导出的会话
        page.goto(评价页); 滚动加载; 解析 DOM；
  C. 人工/半自动导出评价 CSV，再喂给本适配器。
拿到评价后构造 schema.Review（含 text / rating / helpful / source），
塞进对应 Seller.reviews_pos / reviews_neg，管线会自动取 helpful 最高的 Top10。

【销量榜接入】见下方 _fetch_jd_rank。解析出的商品映射成 schema.Item 时，
**务必复用与示例数据一致的 id 规则**（brand-model 小写连字符），以便跨源按 id 合并。
合规：尊重 robots.txt 与各平台条款；控制频率；仅抓公开页。
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
