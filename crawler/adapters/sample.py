"""示例/基础数据适配器（producer）—— 离线、零依赖，开箱即用。

产出每件商品的：原始信号（发布/销量/热度）、**多源参数（带来源，体现交叉对比/查漏补缺）**、
**各售卖渠道真实搜索/官网链接**、以及**代表性好评/差评**（标注为示例，待真实抓取替换）。

真实图片由 Wikimedia 适配器实时补充；真实评价由 ecommerce 适配器接入后替换。
参数里每个字段都登记了来源，前端详情页会展示「该参数由哪些来源交叉确认」。
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from schema import Item, Source, Seller, Review
from .base import Adapter

_NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _seller_search_urls(name: str, brand: str) -> list[tuple[str, str, bool]]:
    """构造各电商「搜索该型号」的真实可点链接 (站名, url, is_official)。"""
    q = urllib.parse.quote(f"{brand} {name}")
    return [
        ("京东", f"https://search.jd.com/Search?keyword={q}", False),
        ("天猫", f"https://list.tmall.com/search_product.htm?q={q}", False),
        ("Amazon", f"https://www.amazon.com/s?k={q}", False),
    ]

_OFFICIAL = {
    "Fujifilm": "https://instax.com/",
    "Polaroid": "https://www.polaroid.com/",
    "Kodak": "https://www.kodak.com/",
}


def _reviews(seller: str, pros: list[str], cons: list[str]) -> tuple[list[Review], list[Review]]:
    """把 pros/cons 短语合成「代表性」评价对象（标注来源为示例）。
    helpful 递减以演示 Top 排序；真实抓取接入后整体替换。"""
    src = f"{seller}（示例）"
    pos = [Review(rating=5.0, text=t, author="用户***", helpful=h, source=src)
           for t, h in zip(pros, range(len(pros) * 30 + 10, 0, -30))]
    neg = [Review(rating=2.0, text=t, author="用户***", helpful=h, source=src)
           for t, h in zip(cons, range(len(cons) * 25 + 8, 0, -25))]
    return pos, neg


# 每件商品：完整字段。specs 为 (字段, 值, [来源]) 列表，体现多源交叉确认。
_CAMERAS = [
    {
        "id": "fujifilm-instax-mini-12", "name": "Instax Mini 12", "brand": "Fujifilm",
        "price": 499, "release": "2023-03-15", "rank": 1, "hot": 88,
        "tags": ["入门", "自动曝光", "高人气"],
        "summary": "最好上手的拍立得，自动曝光、近拍模式，新手闭眼买。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网", "京东参数"]),
            ("相纸", "instax mini", ["Fujifilm 官网", "DPReview"]),
            ("画幅", "62×46 mm", ["Fujifilm 官网"]),
            ("镜头", "60mm f/12.7", ["DPReview"]),
            ("曝光", "自动（含近拍模式）", ["Fujifilm 官网", "京东参数"]),
            ("自拍镜", "有", ["Fujifilm 官网"]),
            ("电源", "2 节 AA 电池", ["京东参数"]),
            ("重量", "306g", ["Fujifilm 官网", "DPReview"]),
        ],
        "pros": ["拧一下镜头就能开机，操作太简单了", "自动曝光很准，废片率低", "颜色多，外形可爱", "出片快，聚会很受欢迎"],
        "cons": ["相纸偏贵，长期成本高", "没有手动控制，可玩性一般"],
    },
    {
        "id": "fujifilm-instax-mini-99", "name": "Instax Mini 99", "brand": "Fujifilm",
        "price": 899, "release": "2024-03-20", "rank": 5, "hot": 92,
        "tags": ["进阶", "手动控光", "新品"],
        "summary": "可玩性最高的 mini 机型，多色温滤镜 + 手动亮度，出片有氛围。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网", "京东参数"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("镜头", "60mm f/12.7", ["DPReview"]),
            ("曝光", "手动 + 自动", ["Fujifilm 官网", "DPReview"]),
            ("色彩特效", "6 种色温/暗角滤镜", ["Fujifilm 官网"]),
            ("闪光灯", "可关闭", ["京东参数"]),
            ("电源", "可充电锂电池", ["Fujifilm 官网"]),
            ("重量", "约 320g", ["Fujifilm 官网"]),
        ],
        "pros": ["氛围感拉满，色温滤镜很出片", "终于能手动控光了", "做工和质感比 Mini 12 高级"],
        "cons": ["价格偏高", "上手需要一点学习成本", "机身偏重"],
    },
    {
        "id": "fujifilm-instax-wide-400", "name": "Instax Wide 400", "brand": "Fujifilm",
        "price": 899, "release": "2024-06-25", "rank": 8, "hot": 85,
        "tags": ["宽幅", "新品", "聚会"],
        "summary": "时隔多年的宽幅新机，画面是 mini 的两倍，适合合影与风景。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网"]),
            ("相纸", "instax WIDE", ["Fujifilm 官网", "京东参数"]),
            ("画幅", "99×62 mm", ["Fujifilm 官网"]),
            ("曝光", "自动", ["Fujifilm 官网"]),
            ("自拍/合影", "支持自拍延时", ["Fujifilm 官网"]),
            ("重量", "约 612g", ["DPReview"]),
        ],
        "pros": ["宽幅出片大气，合影神器", "自动曝光省心"],
        "cons": ["机身大且重，不便携", "相纸更贵"],
    },
    {
        "id": "fujifilm-instax-mini-evo", "name": "Instax Mini Evo", "brand": "Fujifilm",
        "price": 1099, "release": "2022-01-20", "rank": 3, "hot": 90,
        "tags": ["混合", "可选打印", "复古"],
        "summary": "数码+拍立得混合机，100 种滤镜组合，先看后印不浪费相纸。",
        "specs": [
            ("类型", "混合式（数码+打印）", ["Fujifilm 官网", "DPReview"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("传感器", "1/5 英寸 CMOS", ["DPReview"]),
            ("特效", "10 镜头 × 10 胶片 = 100 种", ["Fujifilm 官网", "京东参数"]),
            ("存储", "内置 + microSD", ["京东参数"]),
            ("打印", "可选打印，先看后印", ["Fujifilm 官网"]),
            ("重量", "285g", ["Fujifilm 官网", "DPReview"]),
        ],
        "pros": ["先看后印太省相纸了", "复古造型颜值高", "滤镜组合多，玩法丰富", "可以连手机当打印机"],
        "cons": ["打印分辨率一般", "充电口还是 micro-USB"],
    },
    {
        "id": "fujifilm-instax-square-sq40", "name": "Instax Square SQ40", "brand": "Fujifilm",
        "price": 799, "release": "2023-09-10", "rank": 6, "hot": 70,
        "tags": ["方画幅", "复古"],
        "summary": "复古皮革质感方画幅机，构图更经典，ins 风首选。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网"]),
            ("相纸", "instax SQUARE", ["Fujifilm 官网", "京东参数"]),
            ("画幅", "62×62 mm 方形", ["Fujifilm 官网"]),
            ("曝光", "自动", ["Fujifilm 官网"]),
            ("重量", "457g", ["DPReview"]),
        ],
        "pros": ["方画幅构图好看", "复古外观有质感"],
        "cons": ["体积偏大", "功能比较基础"],
    },
    {
        "id": "fujifilm-instax-pal", "name": "Instax Pal", "brand": "Fujifilm",
        "price": 499, "release": "2023-10-15", "rank": 4, "hot": 78,
        "tags": ["数码", "迷你", "可遥控"],
        "summary": "乒乓球大小的数码小相机，拍完连手机选片再打印。",
        "specs": [
            ("类型", "数码（需配打印机）", ["Fujifilm 官网", "DPReview"]),
            ("传感器", "1/5 英寸 CMOS", ["DPReview"]),
            ("存储", "内置约 50 张 + microSD", ["京东参数"]),
            ("连接", "蓝牙连 App", ["Fujifilm 官网"]),
            ("重量", "约 41g", ["Fujifilm 官网"]),
        ],
        "pros": ["超小巧，可以挂着拍", "可远程遥控拍合影", "配 App 选片再打印"],
        "cons": ["本身不能直接出片", "需要另配打印机"],
    },
    {
        "id": "fujifilm-instax-mini-liplay", "name": "Instax Mini LiPlay", "brand": "Fujifilm",
        "price": 849, "release": "2019-07-01", "rank": 2, "hot": 65,
        "tags": ["混合", "录音", "常青"],
        "summary": "能把声音做成二维码印在照片上的混合机，长青畅销款。",
        "specs": [
            ("类型", "混合式（数码+打印）", ["Fujifilm 官网"]),
            ("相纸", "instax mini", ["Fujifilm 官网", "京东参数"]),
            ("特色", "录音转二维码印在照片上", ["Fujifilm 官网", "DPReview"]),
            ("存储", "内置 + microSD", ["京东参数"]),
            ("重量", "255g", ["DPReview"]),
        ],
        "pros": ["声音二维码很有创意", "轻便好携带", "可当打印机用"],
        "cons": ["屏幕较小", "上市时间久了，接口偏旧"],
    },
    {
        "id": "polaroid-now-plus-gen3", "name": "Polaroid Now+ Gen 3", "brand": "Polaroid",
        "price": 1099, "release": "2024-09-05", "rank": 9, "hot": 80,
        "tags": ["经典宝丽来", "App 控制", "新品"],
        "summary": "经典白边宝丽来，配 App 解锁多重曝光等创意镜头滤镜。",
        "specs": [
            ("类型", "模拟即时成像", ["Polaroid 官网"]),
            ("相纸", "i-Type / 600", ["Polaroid 官网", "京东参数"]),
            ("对焦", "双镜头自动", ["Polaroid 官网"]),
            ("App", "支持，解锁多重曝光等", ["Polaroid 官网", "DPReview"]),
            ("滤镜", "附 5 枚镜头滤镜", ["Polaroid 官网"]),
            ("重量", "约 457g", ["DPReview"]),
        ],
        "pros": ["经典白边氛围感无敌", "App 玩法丰富", "送的滤镜很好玩"],
        "cons": ["相纸最贵", "成片色彩随机性大"],
    },
    {
        "id": "polaroid-now-gen2", "name": "Polaroid Now Gen 2", "brand": "Polaroid",
        "price": 899, "release": "2023-08-15", "rank": 7, "hot": 68,
        "tags": ["经典宝丽来", "自动对焦"],
        "summary": "宝丽来标志性方形白边，双镜头自动对焦，氛围感拉满。",
        "specs": [
            ("类型", "模拟即时成像", ["Polaroid 官网"]),
            ("相纸", "i-Type / 600", ["Polaroid 官网", "京东参数"]),
            ("对焦", "双镜头自动", ["Polaroid 官网", "DPReview"]),
            ("重量", "约 434g", ["DPReview"]),
        ],
        "pros": ["白边方画幅很经典", "自动对焦实用"],
        "cons": ["相纸贵", "暗光成片一般"],
    },
    {
        "id": "polaroid-i-2", "name": "Polaroid I-2", "brand": "Polaroid",
        "price": 4499, "release": "2023-09-07", "rank": 12, "hot": 75,
        "tags": ["旗舰", "手动", "发烧友"],
        "summary": "宝丽来旗舰，连续自动对焦 + 全手动光圈快门，拍立得里的天花板。",
        "specs": [
            ("类型", "模拟即时成像（旗舰）", ["Polaroid 官网", "DPReview"]),
            ("相纸", "i-Type / 600", ["Polaroid 官网"]),
            ("对焦", "LiDAR 连续自动对焦", ["Polaroid 官网", "DPReview"]),
            ("控制", "全手动光圈/快门 + 取景器", ["Polaroid 官网"]),
            ("重量", "约 656g", ["DPReview"]),
        ],
        "pros": ["画质是拍立得里最好的", "全手动可玩性极高", "内置取景器专业"],
        "cons": ["非常贵", "偏重，门槛高"],
    },
    {
        "id": "polaroid-go-gen2", "name": "Polaroid Go Gen 2", "brand": "Polaroid",
        "price": 629, "release": "2023-01-10", "rank": 10, "hot": 60,
        "tags": ["迷你", "便携"],
        "summary": "全世界最小的模拟拍立得，口袋机，出片是迷你白边方块。",
        "specs": [
            ("类型", "模拟即时成像", ["Polaroid 官网"]),
            ("相纸", "Polaroid Go", ["Polaroid 官网", "京东参数"]),
            ("画幅", "迷你方形白边", ["Polaroid 官网"]),
            ("重量", "约 242g", ["DPReview"]),
        ],
        "pros": ["真的很小，随身带", "迷你白边很可爱"],
        "cons": ["专用相纸选择少", "成片偏小"],
    },
    {
        "id": "kodak-smile-plus", "name": "Kodak Smile+", "brand": "Kodak",
        "price": 699, "release": "2022-05-20", "rank": 11, "hot": 55,
        "tags": ["数码", "贴纸相纸", "AR"],
        "summary": "用 ZINK 免墨贴纸相纸，配 App 玩 AR 滤镜，年轻人玩具。",
        "specs": [
            ("类型", "数码即时打印", ["Kodak 官网"]),
            ("打印", "ZINK 免墨贴纸相纸", ["Kodak 官网", "京东参数"]),
            ("特色", "App AR 滤镜", ["Kodak 官网"]),
            ("重量", "约 180g", ["京东参数"]),
        ],
        "pros": ["免墨贴纸很方便", "AR 滤镜小朋友喜欢"],
        "cons": ["打印质量一般", "塑料感强"],
    },
]


class SampleAdapter(Adapter):
    name = "示例数据"
    _DATASETS = {"instant-camera": _CAMERAS}

    def fetch(self, category_id: str) -> list[Item]:
        rows = self._DATASETS.get(category_id)
        if not rows:
            print(f"  · sample: 品类 '{category_id}' 暂无示例数据集，返回空")
            return []
        out: list[Item] = []
        for c in rows:
            it = Item(
                id=c["id"], category=category_id, name=c["name"], brand=c["brand"],
                summary=c["summary"], price_value=float(c["price"]), currency="CNY",
                tags=list(c["tags"]), release_date=c["release"],
                sales_rank=c["rank"], hot_index=float(c["hot"]),
                official_url=_OFFICIAL.get(c["brand"], ""),
                sources=[Source(name=self.name, fetched_at=_NOW)],
            )
            for fld, val, srcs in c["specs"]:
                for s in srcs:
                    it.add_spec(fld, val, s)
            it.add_spec("上市时间", c["release"], "示例数据")
            for sname, url, off in _seller_search_urls(c["name"], c["brand"]):
                pos, neg = _reviews(sname, c["pros"], c["cons"])
                it.sellers.append(Seller(
                    name=sname, url=url, is_official=off, currency="CNY",
                    price_value=float(c["price"]),
                    rating=round(4.6 - 0.03 * c["rank"], 1),
                    review_count=max(50, 4000 - c["rank"] * 280),
                    reviews_pos=pos, reviews_neg=neg))
            if it.official_url:
                it.sellers.append(Seller(name=f"{c['brand']} 官网", url=it.official_url, is_official=True))
            out.append(it)
        print(f"  · sample: 品类 '{category_id}' 提供 {len(out)} 条（含参数/渠道/示例评价）")
        return out
