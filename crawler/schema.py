"""数据模型 —— 所有适配器产出、管线消费的统一结构。

一个 Item 描述一件硬件。适配器各自填它能拿到的部分（图片 / 参数 / 售卖渠道 / 评价），
管线负责跨源「交叉查重 + 查漏补缺 + 打分归类」，保证不同数据源口径一致、可比较、可溯源。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any


@dataclass
class Source:
    """数据来源记录 —— 每件商品可来自多个源，便于溯源与去重合并。"""
    name: str                 # 来源名，如 "京东" / "Wikimedia" / "Fujifilm 官网" / "示例数据"
    url: str = ""             # 原始页面链接
    fetched_at: str = ""      # ISO 时间戳，抓取时刻


@dataclass
class Review:
    """单条用户评价。helpful 用于「点赞数」排序取 Top10。"""
    rating: float | None      # 评分（1-5），可空
    text: str                 # 评价正文
    title: str = ""
    author: str = ""
    date: str = ""
    helpful: int = 0          # 有用/点赞数，用于排名
    source: str = ""          # 来自哪个售卖网站


@dataclass
class Seller:
    """一个售卖渠道（含官网）。"""
    name: str                 # 京东 / 天猫 / Amazon / Fujifilm 官网
    url: str                  # 商品页或搜索页 URL
    is_official: bool = False
    price_value: float | None = None
    currency: str = "CNY"
    rating: float | None = None        # 该站综合评分
    review_count: int | None = None    # 该站评价总数
    reviews_pos: list[Review] = field(default_factory=list)  # 好评 Top
    reviews_neg: list[Review] = field(default_factory=list)  # 差评 Top


@dataclass
class Item:
    """一件硬件商品。

    raw signals（适配器填，用于打分）:
      - release_date: 上市日期 -> 「最新」
      - sales_rank:   电商销量排名（1 最好）-> 「最畅销」
      - hot_index:    热度指数 0-100 -> 「最火」
    detail（详情页用）:
      - images / image_credits: 多视图实拍图 + 版权署名
      - specs / spec_sources:   交叉去重后的参数 + 每个字段的来源（体现「跨站交叉对比」）
      - sellers:                各售卖渠道 URL、价格、好评/差评 Top
      - official_url:           官网链接
    scores（pipeline 填，0-1）: latest_score / hot_score / sales_score
    """
    id: str                                  # 稳定唯一键，跨源去重用（brand-model 小写连字符）
    category: str
    name: str
    brand: str = ""
    image: str = ""                          # 主图（= images[0]，向后兼容列表/卡片）
    images: list[str] = field(default_factory=list)          # 多视图实拍图
    image_credits: list[dict] = field(default_factory=list)  # [{title,descurl,license,artist}]
    url: str = ""                            # 主要详情/购买链接
    official_url: str = ""
    summary: str = ""
    price_value: float | None = None
    currency: str = "CNY"
    tags: list[str] = field(default_factory=list)

    # 参数：specs 是最终展示值；spec_sources 记录每个字段被哪些源证实（交叉查重）
    specs: dict[str, Any] = field(default_factory=dict)
    spec_sources: dict[str, list[str]] = field(default_factory=dict)

    sellers: list[Seller] = field(default_factory=list)

    # ---- raw signals ----
    release_date: str = ""
    sales_rank: int | None = None
    hot_index: float | None = None

    # ---- computed scores ----
    latest_score: float = 0.0
    hot_score: float = 0.0
    sales_score: float = 0.0

    # ---- 多平台真实指标（amazon/jd/taobao 适配器填）----
    asin: str = ""                                       # Amazon ASIN
    platforms: dict[str, Any] = field(default_factory=dict)  # {"amazon":{rating,reviews,price,bsr}, "jd":..., "taobao":...}
    rating: float | None = None                          # 综合评分（展示用）
    reviews: int | None = None                           # 综合评价数（展示用）
    bsr: int | None = None                               # 最佳畅销榜排名（展示用，越小越畅销）
    pop_note: str = ""                                   # 热度/畅销「数据支撑」展示文案（真实评价数/销量或定性依据，带来源）
    data_as_of: str = ""                                 # 平台数据截至日期

    # ---- 历史留存（pipeline 维护）----
    first_seen: str = ""      # 首次进入榜单的日期 YYYY-MM-DD
    last_seen: str = ""       # 最近一次被数据源抓到的日期
    active: bool = True        # 本次更新是否仍在榜（False = 历史机型，仍展示）

    sources: list[Source] = field(default_factory=list)

    # ---- helpers ----
    def add_spec(self, field_name: str, value: Any, source: str) -> None:
        """登记一个参数并记录来源。已有则把来源并入（交叉查重）；
        值不一致时保留首个出现的值，但把新来源也记下。"""
        if value in (None, "", []):
            return
        if field_name not in self.specs:
            self.specs[field_name] = value
        srcs = self.spec_sources.setdefault(field_name, [])
        if source and source not in srcs:
            srcs.append(source)

    def price_display(self) -> str:
        if self.price_value is None:
            return ""
        symbol = {"CNY": "¥", "USD": "$", "EUR": "€", "JPY": "¥"}.get(self.currency, "")
        v = int(self.price_value) if float(self.price_value).is_integer() else self.price_value
        return f"{symbol}{v}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["price_display"] = self.price_display()
        return d


def days_since(iso_date: str) -> int | None:
    """距今天数。兼容残缺日期：YYYY-MM-DD / YYYY-MM（按当月1日）/ YYYY（按当年1月1日）。"""
    if not iso_date:
        return None
    s = iso_date.strip()
    for fmt, ln in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            d = datetime.strptime(s[:ln], fmt).date()
            return (date.today() - d).days
        except ValueError:
            continue
    return None
