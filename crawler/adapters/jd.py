"""京东适配器（enricher）—— 真实「销量/评价」，接入后并入综合榜（待激活）。

目标：给每款机型补 it.platforms["jd"] = {"price","reviews","good_rate","sales_rank",...}，
管线会自动把它和 Amazon 等平台做归一化后取平均，得出「综合最火 / 综合最畅销」。

⚠️ 实测：京东评价/销量接口（club.jd.com/comment/...）裸 HTTP 直接返回「系统繁忙」反爬响应，
搜索页与商品页也有风控。所以 JD 数据**不能靠裸 HTTP 直抓**，必须走下列之一再激活：
  A. 京东联盟/宙斯开放平台 API（申请 appkey，最稳最合规）；
  B. Playwright 带登录 Cookie 的真实浏览器：
        ctx = browser.new_context(storage_state="jd_login.json")  # 预先登录导出
        page.goto(商品页/评价页); 滚动加载; 解析；
  C. 人工/半自动导出 CSV 再喂进来。
拿到后写入 it.platforms["jd"]，并把 it.sources 追加一条京东来源即可，前端会显示"京东"参与综合。
"""

from __future__ import annotations

from schema import Item
from .base import Adapter

# 每款机型对应的京东商品/SKU（接入时填）：id -> sku 或 商品页 URL
JD_SKU: dict[str, str] = {}


class JdAdapter(Adapter):
    name = "京东"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        if not JD_SKU:
            print("  · 京东: 未配置 SKU/接入方式，跳过（待接入；见 jd.py 顶部）")
            return
        for it in items:
            sku = JD_SKU.get(it.id)
            if not sku:
                continue
            try:
                data = self._fetch(sku)          # TODO: 实现 A/B/C 任一
                if data:
                    it.platforms["jd"] = data
            except Exception as e:
                print(f"  ! 京东抓取失败 {it.id}: {e}")

    def _fetch(self, sku: str) -> dict | None:
        """返回 {'price':.., 'reviews':.., 'good_rate':.., 'sales_rank':..}。"""
        raise NotImplementedError("京东真实数据接入见本文件顶部 A/B/C 方案")
