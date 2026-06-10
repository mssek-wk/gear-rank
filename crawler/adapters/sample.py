"""示例/基础数据适配器（producer）—— 离线、零依赖，开箱即用。

产出每件商品的：原始信号（发布/销量/热度）、**多源参数（带来源，体现交叉对比/查漏补缺）**、
**各售卖渠道真实搜索/官网链接**、以及**代表性好评/差评**（标注为示例，待真实抓取替换）。

真实图片由 Wikimedia 适配器实时补充；真实评价由 ecommerce 适配器接入后替换。
参数里每个字段都登记了来源，前端详情页会展示「该参数由哪些来源交叉确认」。
"""

from __future__ import annotations

import json as _json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path as _Path

from schema import Item, Source, Seller, Review
from .base import Adapter

_NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# 扩展品类数据集（运动相机/胶片相机/模拟胶卷数码相机）—— 由扩展产品表生成，存于 data/expansion_products.json。
# 结构与 _CAMERAS 一致：每条 {id,name,brand,release,tags,summary,specs:[[字段,值,[来源]]],pros,cons,official_url}
def _load_json(name: str) -> dict:
    f = _Path(__file__).resolve().parent.parent.parent / "data" / name
    try:
        return _json.loads(f.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

_EXPANSION = _load_json("expansion_products.json")
# 京东联盟官方 API 真实数据快照（由 crawler/jd_union_fetch.py 生成；缺失则为空，自动回退估算）。
_JD_UNION = _load_json("jd_union_snapshot.json")


def _wan(n) -> str:
    """把数字格式化为「X万+」/「N+」展示。"""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n >= 10000:
        return f"{n // 10000}万+"
    if n >= 1000:
        return f"{n // 1000}千+"
    return f"{n}+" if n > 0 else ""


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
    "Fujifilm X": "https://fujifilm-x.com/",
    "Polaroid": "https://www.polaroid.com/",
    "Kodak": "https://www.kodak.com/",
    "Canon": "https://www.canon.com.cn/",
    "汉印": "https://www.hprt.com/",
    "爱国者": "https://www.aigo.com.cn/",
    "爱墨": "",
    "Insta360": "https://www.insta360.com/",
    "竞墨&奈扣": "",
    "极印": "",
}

# Amazon ASIN（用于 amazon 适配器实时抓 真实评分/评价数/畅销榜排名）。
# 没有 ASIN 的（如刚上市的新机型）= 暂无电商指标，只按官方上市日期进「最新」。
ASIN = {
    "fujifilm-instax-mini-12": "B0BWNYBRNL", "fujifilm-instax-mini-99": "B0CXZQGL2D",
    "fujifilm-instax-wide-400": "B0D6WXV3MF", "fujifilm-instax-square-sq40": "B0C7KFDKCJ",
    "fujifilm-instax-mini-evo": "B09M4DKBQ9", "fujifilm-instax-pal": "B0DGYZFXML",
    "fujifilm-instax-mini-41": "B0F2V7RKXH", "polaroid-now-gen2": "B0BVNMQ2XL",
    "polaroid-go-gen2": "B0CG7P9KTH", "polaroid-i-2": "B0D4RC69HB",
    "polaroid-now-plus-gen3": "B0DTTPR5T3", "polaroid-flip": "B0F993TYR9",
    "kodak-smile-plus": "B0CQMNDL59", "leica-sofort-2": "B0CNDBT3NX",
    "fujifilm-instax-mini-13": "B0GRHR77S3", "fujifilm-instax-mini-liplay-plus": "B0FT92QK3L",
    "canon-zoemini-s2": "B09HMTKRYG",
    "canon-inspic": "B0BBG2R1YK",
}
# 官方 MSRP（USD）作为价格兜底；amazon 适配器会用实时价覆盖。
MSRP_USD = {
    "fujifilm-instax-mini-13": 93.95, "fujifilm-instax-evo-cinema": 409.95,
    "fujifilm-instax-mini-liplay-plus": 234.95, "polaroid-flip": 199.99,
    "fujifilm-instax-mini-41": 99.95, "fujifilm-instax-wide-400": 149.95,
    "fujifilm-instax-mini-99": 199.95, "polaroid-now-plus-gen3": 159.99,
    "fujifilm-instax-square-sq40": 119.95, "fujifilm-instax-pal": 99.95,
    "polaroid-i-2": 599.99, "fujifilm-instax-mini-12": 79.95,
    "polaroid-now-gen2": 99.99, "polaroid-go-gen2": 79.99,
    "fujifilm-instax-mini-evo": 199.95, "fujifilm-instax-mini-liplay": 159.95,
    "kodak-smile-plus": 99.99, "leica-sofort-2": 389.00,
    "insta360-pocket-printer": 599.99, "hprt-z6-pro": 89.00, "canon-zoemini-s2": 149.99,
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
    # ===== 2025–2026 新机型（官方上市日期已核验）=====
    {
        "id": "fujifilm-instax-mini-13", "name": "Instax Mini 13", "brand": "Fujifilm",
        "release": "2026-06-25", "tags": ["入门", "新品", "最新"],
        "summary": "Mini 12 继任者，柔和雕塑造型 + 金属银 logo，2026 最新入门款。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("曝光", "自动", ["Fujifilm 官网"]),
            ("自拍镜", "有 + 近拍模式", ["Fujifilm 官网"]),
            ("上市", "2026 年 6 月", ["Fujifilm 官方新闻稿"]),
        ],
        "pros": ["造型更精致", "延续 Mini 12 的易用"],
        "cons": ["刚上市，渠道与评价还少"],
    },
    {
        "id": "fujifilm-instax-evo-cinema", "name": "Instax Mini Evo Cinema", "brand": "Fujifilm",
        "release": "2026-02-05", "tags": ["混合", "新品", "影像质感"],
        "summary": "Evo 影院版：Gen Dial 一键套用 10 个年代的影像质感，混合式先看后印。",
        "specs": [
            ("类型", "混合式（数码+打印）", ["Fujifilm 官网"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("特效", "Gen Dial · 10 个年代效果", ["Fujifilm 官网"]),
            ("上市", "2026 年 2 月", ["Fujifilm 官方新闻稿"]),
        ],
        "pros": ["年代效果很有创意", "延续 Evo 的高颜值"],
        "cons": ["价格偏高"],
    },
    {
        "id": "fujifilm-instax-mini-liplay-plus", "name": "Instax Mini LiPlay+", "brand": "Fujifilm",
        "release": "2025-10-24", "tags": ["混合", "双摄", "录音"],
        "summary": "LiPlay 换代：双摄（主摄 + 广角自拍），声音二维码升级。",
        "specs": [
            ("类型", "混合式（数码+打印）", ["Fujifilm 官网"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("特色", "双摄（含广角自拍）+ 录音转二维码", ["Fujifilm 官网"]),
            ("上市", "2025 年 10 月", ["Fujifilm 官方新闻稿"]),
        ],
        "pros": ["双摄自拍更方便", "声音二维码有记忆点"],
        "cons": ["相纸成本仍在"],
    },
    {
        "id": "fujifilm-instax-mini-41", "name": "Instax Mini 41", "brand": "Fujifilm",
        "release": "2025-04-25", "tags": ["入门", "自动曝光"],
        "summary": "Mini 11/40 一脉的换代款，经典造型 + 自动闪光控制、视差校正改进。",
        "specs": [
            ("类型", "模拟即时成像", ["Fujifilm 官网"]),
            ("相纸", "instax mini", ["Fujifilm 官网"]),
            ("镜头", "60mm f/12.7", ["Fujifilm 官网"]),
            ("曝光", "自动 + 自动闪光控制", ["Fujifilm 官网"]),
            ("电源", "2 节 AA 电池", ["Fujifilm 官网"]),
            ("上市", "2025 年 4 月", ["Fujifilm 官方新闻稿"]),
        ],
        "pros": ["自动曝光省心", "经典商务造型"],
        "cons": ["功能基础，可玩性一般"],
    },
    {
        "id": "polaroid-flip", "name": "Polaroid Flip", "brand": "Polaroid",
        "release": "2025-04-29", "tags": ["旗舰", "声呐对焦", "新品"],
        "summary": "Polaroid 迄今最先进：声呐自动对焦 + 超焦四镜头系统 + 可变亮度强力闪光。",
        "specs": [
            ("类型", "模拟即时成像", ["Polaroid 官网"]),
            ("相纸", "i-Type / 600", ["Polaroid 官网"]),
            ("对焦", "声呐自动对焦 · 超焦四镜头", ["Polaroid 官网", "DPReview"]),
            ("闪光", "可变亮度强力闪光", ["Polaroid 官网"]),
            ("App", "蓝牙连 App（遥控/多重曝光等）", ["Polaroid 官网"]),
            ("上市", "2025 年 4 月 29 日", ["Polaroid 新闻稿"]),
        ],
        "pros": ["四镜头自动对焦很准", "暗光/强光都稳", "做工质感好"],
        "cons": ["比 Now 系列贵", "机身偏大"],
    },
    # ===== 非银盐：混合 / ZINK 免墨 / 热升华（品类不止富士宝丽来）=====
    {
        "id": "leica-sofort-2", "name": "Leica Sofort 2", "brand": "Leica",
        "release": "2023-11-10", "tags": ["混合", "徕卡", "可选打印"],
        "summary": "徕卡混合式拍立得：数码取景先看后印，用 instax mini 相纸，徕卡调性 + FOTOS App。",
        "specs": [
            ("成像技术", "混合式（数码 + instax mini 打印）", ["Leica 官网", "DPReview"]),
            ("相纸", "instax mini", ["Leica 官网"]),
            ("屏幕", "3.0 英寸 LCD", ["Leica 官网"]),
            ("特效", "10 种镜头效果", ["Leica 官网"]),
            ("App", "Leica FOTOS（可印手机/徕卡相机照片）", ["Leica 官网"]),
            ("上市", "2023 年 11 月", ["Leica 新闻稿"]),
        ],
        "pros": ["徕卡质感与调色", "先看后印不浪费相纸", "能印其它徕卡机的片子"],
        "cons": ["很贵", "本质仍是低像素数码"],
    },
    {
        "id": "insta360-pocket-printer", "name": "Insta360 Ace Pro 2 即拍即打套装", "brand": "Insta360",
        "release": "2025-11-12", "tags": ["ZINK 免墨", "运动相机", "新品"],
        "summary": "Insta360 给 Ace Pro 2 运动相机配的 ZINK 口袋打印模块，拍完蓝牙即出 2×3 英寸免墨照片。",
        "specs": [
            ("成像技术", "ZINK 免墨热敏打印", ["Insta360 官网", "媒体评测"]),
            ("相纸", "ZINK 2×3 英寸免墨相纸", ["Insta360 官网"]),
            ("形态", "Ace Pro 2 运动相机 + 口袋打印机模块", ["Insta360 官网"]),
            ("连接", "蓝牙快拆", ["Insta360 官网"]),
            ("上市", "2025 年 11 月", ["Insta360 / 媒体"]),
        ],
        "pros": ["运动相机也能即拍即打", "ZINK 免墨、出片干燥防蹭"],
        "cons": ["要先有 Ace Pro 2", "套装较贵"],
    },
    {
        "id": "hprt-z6-pro", "name": "汉印 Z6 Pro", "brand": "汉印",
        "release": "", "tags": ["热升华", "国产", "高画质"],
        "summary": "国产热升华拍立得旗舰：1/3 英寸传感器 + 1.8 英寸触屏先看后印，热升华出片色彩细腻。汉印 2025 年拿下国内拍立得销量第一。",
        "specs": [
            ("成像技术", "热升华（染料升华）", ["汉印官网"]),
            ("传感器", "1/3 英寸", ["汉印官网"]),
            ("屏幕", "1.8 英寸触控预览", ["汉印官网"]),
            ("特色", "一体式相纸/色带 + 5 款滤镜 + 蓝牙 App", ["汉印官网"]),
            ("上市", "约 2025（以官方为准）", ["汉印官网"]),
        ],
        "pros": ["热升华画质细腻、色彩还原好", "一体式耗材好换", "国产价格友好"],
        "cons": ["品牌海外认知度低", "耗材生态不如富士"],
    },
    {
        "id": "chuzhao-d1-pro", "name": "初照 D1 Pro", "brand": "初照",
        "release": "", "tags": ["热升华", "国产", "可存储选打印"],
        "summary": "国产热升华拍立得：拍照先存到内存卡、大屏预览再选打印，前后双摄高清。京东拍立得热卖榜常客。",
        "specs": [
            ("成像技术", "热升华即时打印", ["初照京东自营"]),
            ("屏幕", "2.8 英寸预览屏", ["初照京东自营"]),
            ("特色", "可存储后选打印 + 5 种复古滤镜 + 前后双摄 + App", ["初照京东自营"]),
            ("存储", "标配 16G 内存卡", ["初照京东自营"]),
            ("耗材", "一张约 2.5 元", ["初照京东自营"]),
        ],
        "pros": ["先存后选打印不浪费相纸", "复古颜值高", "耗材便宜性价比高"],
        "cons": ["品牌新、海外认知低", "像素属入门"],
    },
    {
        "id": "chuzhao-x1", "name": "初照 X1", "brand": "初照",
        "release": "", "tags": ["喷墨", "国产", "拍打一体"],
        "summary": "初照拍照打印一体拍立得：喷墨即时出彩色照片，也能打印手机照片，磁吸礼盒装、可选花边，墨盒约 80 张。",
        "specs": [
            ("成像技术", "喷墨即时打印", ["初照京东自营"]),
            ("特色", "拍照打印一体 + 打印手机照片 + 花边 + AI 图片", ["初照京东自营"]),
            ("耗材", "一体式喷墨墨盒约打 80 张，赠 100 张相纸", ["初照京东自营"]),
        ],
        "pros": ["颜值高、送礼合适", "能打手机照片", "相纸性价比高"],
        "cons": ["像素入门", "需补耗材"],
    },
    {
        "id": "canon-zoemini-s2", "name": "Canon Zoemini S2", "brand": "Canon",
        "release": "2021-10-15", "tags": ["ZINK 免墨", "2合1", "便携"],
        "summary": "佳能 2 合 1 ZINK 拍立得：自带补光环 + 自拍镜，支持圆形相纸打印，口袋便携。",
        "specs": [
            ("成像技术", "ZINK 免墨热敏打印", ["Canon 官网", "DPReview"]),
            ("相纸", "ZINK 2×3 英寸（支持圆形相纸）", ["Canon 官网"]),
            ("自拍", "自拍镜 + LED 补光环", ["Canon 官网"]),
            ("形态", "相机 + 打印机 2 合 1", ["Canon 官网"]),
            ("上市", "2021 年 10 月", ["Canon 新闻稿"]),
        ],
        "pros": ["自带补光环自拍友好", "圆形相纸有创意", "口袋便携"],
        "cons": ["ZINK 画质一般", "已属旧款"],
    },
    # ===== 照片打印机竞品（来源：汉图设计语雀竞品分析，17款）=====
    {
        "id": "fujifilm-x-e5", "name": "富士X-E5无反数码相机", "brand": "Fujifilm X",
        "official_url": "https://fujifilm-x.com/",
        "release": "2025-08-01", "tags": ["APS-C", "无反", "旁轴风格", "6K视频", "竞品参考"],
        "summary": "富士X系列新一代旁轴风格无反相机，4020万像素APS-C传感器，支持6K 30P视频，搭配可换镜头系统。",
        "specs": [
            ("类型", "APS-C 无反数码相机（可换镜头）", ["富士官方", "京东参数"]),
            ("传感器", "APS-C CMOS，4020万有效像素", ["富士官方", "京东参数"]),
            ("液晶屏", "3英寸，104万像素", ["富士官方", "京东参数"]),
            ("视频", "6K 30P", ["富士官方"]),
            ("电池", "锂离子电池 NP-W126S", ["京东商品页"]),
        ],
        "pros": ["4020万高分辨率，细节丰富", "6K视频能力强悍", "经典旁轴造型颜值高", "可换镜头系统可扩展"],
        "cons": ["售价偏高（京东¥11490）", "需额外配镜头", "机身比紧凑机大"],
    },
    {
        "id": "jingmo-naike-printer", "name": "竞墨&奈扣照片打印机", "brand": "竞墨&奈扣",
        "release": "2024-01-01", "tags": ["喷墨", "便携", "蓝牙"],
        "summary": "竞墨与奈扣联名喷墨照片打印机，蓝牙连接，600dpi分辨率，一体式墨盒约80张，45×60mm相纸，约¥529。",
        "specs": [
            ("打印方式", "喷墨打印", ["京东参数"]),
            ("接口类型", "蓝牙", ["京东参数"]),
            ("打印分辨率", "600dpi", ["京东参数"]),
            ("打印尺寸", "45×60mm", ["京东参数"]),
            ("墨盒容量", "彩色约80张（5%覆盖率≥100张）", ["京东参数"]),
            ("内置电源", "800mAh", ["京东参数"]),
            ("产品重量", "287g（不含配件）", ["京东参数"]),
            ("机身尺寸", "107.5×128.8×40.8mm", ["京东参数"]),
            ("打印速度", "60mm/s", ["京东参数"]),
            ("耗材", "相纸+一体式墨盒（耗材尺寸52×90mm）", ["京东参数"]),
        ],
        "pros": ["600dpi分辨率清晰", "蓝牙连接方便", "价格适中"],
        "cons": ["喷墨耗材成本较高", "不支持网络打印"],
    },
    {
        "id": "hprt-z1", "name": "汉印Z1 拍立得", "brand": "汉印",
        "release": "2024-01-01", "tags": ["ZINK免墨", "国产", "拍立得"],
        "summary": "汉印Z1即拍即打拍立得相机，ZINK免墨打印，2.8英寸预览屏，500万像素，F2.2，蓝牙连手机，约230g轻便。",
        "specs": [
            ("成像技术", "ZINK 免墨热敏打印", ["汉印官网"]),
            ("打印分辨率", "300dpi", ["汉印官网"]),
            ("屏幕", "2.8英寸预览屏", ["汉印官网"]),
            ("传感器", "500万像素", ["汉印官网"]),
            ("镜头", "35mm等效焦距，F2.2", ["汉印官网"]),
            ("对焦", "自动对焦，最近30cm", ["汉印官网"]),
            ("特效", "8档滤镜，内置补光闪光灯", ["汉印官网"]),
            ("连接", "蓝牙（可打印手机照片）", ["汉印官网"]),
            ("电池", "680mAh，Type-C充电", ["汉印官网"]),
            ("产品重量", "约230g（不含配件）", ["汉印官网"]),
            ("机身尺寸", "121×79.5×32.8mm", ["汉印官网"]),
        ],
        "pros": ["ZINK免墨无耗材焦虑", "2.8英寸大屏预览", "蓝牙连手机印照片"],
        "cons": ["500万像素偏低", "ZINK画质不如热升华细腻"],
    },
    {
        "id": "hprt-z2", "name": "汉印Z2 拍立得", "brand": "汉印",
        "release": "2024-06-01", "tags": ["热升华", "国产", "拍立得", "复古"],
        "summary": "汉印Z2复古风格拍立得相机，热升华打印，蓝牙连手机，多种滤镜，适合日常随手拍与礼赠场景。",
        "specs": [
            ("成像技术", "热升华（染料升华）", ["汉印官网"]),
            ("连接", "蓝牙 App（可打印手机照片）", ["汉印官网"]),
            ("风格", "复古拍立得造型", ["汉印官网"]),
        ],
        "pros": ["复古造型吸引眼球", "蓝牙连手机方便", "热升华色彩细腻"],
        "cons": ["固件升级后出现卡死问题", "操作复杂度偏高"],
    },
    {
        "id": "aigo-d9-pro", "name": "爱国者D9 Pro数码相机", "brand": "爱国者",
        "release": "2024-03-01", "tags": ["数码相机", "复古CCD", "4K"],
        "summary": "爱国者复古风格数码相机，6400万像素，4K视频，3英寸屏，固定定焦镜头，CMOS传感器，约¥399。",
        "specs": [
            ("类型", "紧凑型数码相机", ["京东参数"]),
            ("像素", "6400万（有效像素1600-2000万）", ["京东参数"]),
            ("视频", "4K（3840×2160）", ["京东参数"]),
            ("屏幕", "3.0英寸", ["京东参数"]),
            ("传感器", "CMOS", ["京东参数"]),
            ("镜头", "固定焦距（定焦）", ["京东参数"]),
            ("防抖", "电子防抖", ["京东参数"]),
        ],
        "pros": ["6400万像素细节丰富", "4K视频能力", "复古造型受年轻人喜爱", "价格亲民约¥399"],
        "cons": ["固定镜头无法更换", "非即时出片，需配打印机"],
    },
    {
        "id": "aimoer-c40", "name": "爱墨C40手机照片打印机", "brand": "爱墨",
        "release": "2024-01-01", "tags": ["热升华", "6寸打印", "蓝牙", "自动覆膜"],
        "summary": "爱墨C40家用热升华照片打印机，Wi-Fi+蓝牙双连接，打印6英寸（100×150mm），自动覆膜，支持连续进纸，约¥699。",
        "specs": [
            ("打印方式", "热升华", ["京东参数"]),
            ("连接", "Wi-Fi + 蓝牙", ["京东参数"]),
            ("打印尺寸", "6英寸（100×150mm）", ["京东参数"]),
            ("自动覆膜", "支持", ["京东参数"]),
            ("连续进纸", "支持", ["京东参数"]),
        ],
        "pros": ["6英寸打印尺寸大更精美", "自动覆膜防水防刮", "Wi-Fi+蓝牙双连接灵活"],
        "cons": ["机器体积相对较大", "热升华纸带耗材成本较高"],
    },
    {
        "id": "kodak-smile-basic", "name": "Kodak Smile 拍立得", "brand": "Kodak",
        "release": "2022-01-01", "tags": ["ZINK免墨", "2合1", "贴纸相纸"],
        "summary": "柯达Smile 2合1即拍即印相机，ZINK免墨贴纸相纸，1000万像素，LCD取景器，简单易用，注意：无蓝牙功能。",
        "specs": [
            ("打印方式", "ZINK免墨打印（带背胶）", ["京东参数", "官网"]),
            ("拍摄像素", "1000万", ["京东参数"]),
            ("对焦", "固定对焦", ["京东参数"]),
            ("打印尺寸", "2英寸×3英寸", ["京东参数"]),
            ("曝光", "自动曝光", ["京东参数"]),
            ("充电", "Micro USB", ["京东参数"]),
            ("取景器", "LCD取景屏", ["用研报告"]),
            ("蓝牙", "无（不支持连手机打印）", ["用研报告"]),
        ],
        "pros": ["ZINK免墨免换耗材", "带背胶相纸可贴", "操作简单"],
        "cons": ["无蓝牙，不支持连手机打印", "打印画质一般", "Micro USB接口旧", "1000万像素偏低"],
    },
    {
        "id": "hprt-cp6000", "name": "汉印CP6000照片打印机", "brand": "汉印",
        "release": "2024-01-01", "tags": ["热升华", "6英寸", "AR留声", "家用"],
        "summary": "汉印CP6000热升华家用照片打印机，打印6英寸（100×148mm），Wi-Fi连接，15秒AR动态留声，约58秒出片，约¥889。",
        "specs": [
            ("打印方式", "热升华", ["京东参数"]),
            ("打印尺寸", "6英寸（100×148mm）", ["京东参数"]),
            ("打印分辨率", "300DPI", ["京东参数"]),
            ("打印速度", "约58秒/张", ["京东参数"]),
            ("连接方式", "Wi-Fi", ["京东参数"]),
            ("机身重量", "1400g（不含配件）", ["京东参数"]),
            ("机身尺寸", "200×130×79mm", ["京东参数"]),
            ("特色功能", "15秒AR动态留声、证件照、自动覆膜、蓝牙音响", ["京东参数"]),
        ],
        "pros": ["6英寸大幅打印精美", "AR留声功能有记忆点", "证件照功能实用"],
        "cons": ["机身重（1400g）不便携", "打印速度较慢（约58秒）", "售价偏高"],
    },
    {
        "id": "fujifilm-quicksnap", "name": "Fujifilm QuickSnap", "brand": "Fujifilm",
        "release": "2023-01-01", "tags": ["胶卷", "一次性", "复古", "银盐"],
        "summary": "富士QuickSnap一次性135彩卷胶片相机，ISO400，27张，内置闪光灯，无需调焦，冲洗后获得经典胶片质感，约¥168。",
        "specs": [
            ("类型", "一次性胶卷相机", ["富士官网"]),
            ("胶卷", "135彩卷，感光度ISO 400", ["富士官网"]),
            ("张数", "27张", ["富士官网"]),
            ("闪光", "内置闪光灯，有效3m", ["富士官网"]),
            ("对焦", "固定焦距，无需调焦", ["富士官网"]),
            ("机身尺寸", "120.23×65.6mm（不含挂耳）", ["富士官网"]),
        ],
        "pros": ["胶片质感独特无可替代", "操作极简无需设置", "价格实惠约¥168"],
        "cons": ["需送洗等待，无法即时看到照片", "张数有限（27张）用完即弃", "无法预览"],
    },
    {
        "id": "jiyin-dmp100", "name": "极印DMP100照片打印机", "brand": "极印",
        "release": "2023-01-01", "tags": ["热升华", "NFC", "蓝牙", "便携"],
        "summary": "极印DMP100热升华便携照片打印机，NFC+蓝牙双连接，约237g超轻，约60秒出片，86×54mm标准尺寸，约¥499。",
        "specs": [
            ("打印方式", "热升华", ["京东参数"]),
            ("打印分辨率", "291×294dpi", ["京东参数"]),
            ("连接方式", "NFC + 蓝牙", ["京东参数"]),
            ("打印尺寸", "86×54mm", ["京东参数"]),
            ("打印速度", "约60秒/张", ["京东参数"]),
            ("产品重量", "237g（不含纸盒）", ["京东参数"]),
            ("机身尺寸", "133×80×27mm", ["京东参数"]),
            ("电池容量", "650mAh", ["京东参数"]),
        ],
        "pros": ["NFC一碰即连方便", "超轻便携（约237g）", "价格¥499实惠"],
        "cons": ["官网已下线，售后存疑", "打印约60秒较慢"],
    },
    {
        "id": "hprt-cp2100", "name": "汉印CP2100照片打印机", "brand": "汉印",
        "release": "2024-01-01", "tags": ["热升华", "蓝牙", "RFID", "AR照片"],
        "summary": "汉印CP2100热升华便携照片打印机，300DPI，蓝牙连接，RFID读写+AR照片功能，自动全切，约280g，约¥699。",
        "specs": [
            ("打印方式", "热升华", ["京东参数"]),
            ("打印分辨率", "300DPI", ["京东参数"]),
            ("连接方式", "蓝牙", ["京东参数"]),
            ("机身重量", "280g（不含配件）", ["京东参数"]),
            ("机身尺寸", "146×83×34mm", ["京东参数"]),
            ("电池容量", "800mAh，Type-C充电", ["京东参数"]),
            ("特色", "RFID读写 + AR照片 + 自动全切", ["京东参数"]),
        ],
        "pros": ["RFID与AR功能有趣", "300DPI打印清晰", "蓝牙连接简单"],
        "cons": ["打印约94秒偏慢", "打印有细小条纹", "初始电量低"],
    },
    {
        "id": "canon-selphy-qx20", "name": "Canon SELPHY QX20", "brand": "Canon",
        "release": "2022-09-01", "tags": ["热升华", "防尘防水", "Wi-Fi", "贴纸相纸"],
        "summary": "佳能SELPHY QX20热升华便携打印机，含保护膜，约40秒快速出片，防尘防水，Wi-Fi，85×54mm卡片/85×72mm方形，带背胶。",
        "specs": [
            ("打印方式", "染料热升华转印（含保护膜）", ["佳能官网"]),
            ("打印分辨率", "287×287dpi", ["佳能官网"]),
            ("打印速度", "约40秒/张", ["佳能官网"]),
            ("纸张格式", "卡片：85×54mm / 方形：85×72mm", ["佳能官网"]),
            ("纸张容量", "10张", ["佳能官网"]),
            ("防护", "防尘防水滴", ["佳能官网"]),
            ("无线连接", "Wi-Fi（2.4GHz）", ["佳能官网"]),
            ("电池", "约850mAh，约20张/充，约80分钟充满", ["佳能官网"]),
            ("机身重量", "约455g", ["佳能官网"]),
            ("机身尺寸", "约102.2×145.8×32.9mm", ["佳能官网"]),
        ],
        "pros": ["约40秒快速打印", "带保护膜耐久", "防尘防水适合户外", "带背胶相纸可DIY"],
        "cons": ["机身较重约455g", "相纸容量仅10张"],
    },
    {
        "id": "kodak-c210", "name": "Kodak C210拍立得", "brand": "Kodak",
        "release": "2022-06-01", "tags": ["ZINK免墨", "2合1", "蓝牙", "LCD取景"],
        "summary": "柯达C210即拍即印相机，ZINK免墨，内置LCD取景器，蓝牙连手机打印，礼盒含20张相纸+相册+收纳包。",
        "specs": [
            ("打印方式", "ZINK免墨打印", ["京东参数"]),
            ("屏幕", "LCD取景器", ["用研报告"]),
            ("连接", "蓝牙（连接手机打印）", ["用研报告"]),
            ("套装内容", "相机+相纸20张+相册36位+收纳包+照片墙贴", ["京东商品页"]),
            ("特殊说明", "连蓝牙时相机拍照功能暂停，需断开蓝牙才能拍摄", ["用研报告"]),
        ],
        "pros": ["LCD取景器方便构图", "礼盒套装送礼完整", "蓝牙连手机打印"],
        "cons": ["连蓝牙时无法用相机拍照", "APP在国内下载有问题"],
    },
    {
        "id": "kodak-minishot2-era", "name": "Kodak Mini Shot 2 ERA拍立得", "brand": "Kodak",
        "release": "2023-06-01", "tags": ["ZINK免墨", "2合1", "1300万", "自动覆膜", "方形相纸"],
        "summary": "柯达Mini Shot 2 ERA即拍即印，1300万像素，1.77英寸LCD，3×3英寸方形相纸，ZINK免墨+自动覆膜，蓝牙，6滤镜7框架。",
        "specs": [
            ("打印方式", "ZINK免墨 + 一体式自动覆膜", ["京东参数"]),
            ("打印分辨率", "300DPI", ["京东参数"]),
            ("拍摄像素", "1300万", ["京东参数"]),
            ("屏幕", "1.77英寸LCD取景器", ["京东参数"]),
            ("打印尺寸", "3英寸×3英寸（76×76mm 方形）", ["京东参数"]),
            ("连接", "蓝牙连手机，专属APP打印", ["京东参数"]),
            ("滤镜/框架", "6种滤镜 + 7种框架", ["京东参数"]),
            ("覆膜", "一体式自动覆膜，历久不褪色", ["京东参数"]),
        ],
        "pros": ["1300万像素画质好", "自动覆膜照片耐久", "300DPI清晰", "价格实惠"],
        "cons": ["连蓝牙时相机功能受限", "APP在国内使用有问题"],
    },
    {
        "id": "canon-inspic", "name": "佳能INSPIC照片打印机", "brand": "Canon",
        "release": "2022-10-01", "tags": ["ZINK免墨", "手机打印", "蓝牙", "磁吸上盖"],
        "summary": "佳能INSPIC口袋手机照片打印机，ZINK免墨带背胶相纸，蓝牙连接，磁吸上盖可换色，Type-C充电，App支持拼图/模板/标签打印。",
        "specs": [
            ("打印方式", "ZINK免墨热敏打印（带背胶）", ["亚马逊商品页"]),
            ("连接", "蓝牙（App连接）", ["亚马逊商品页"]),
            ("充电", "Type-C USB", ["用研报告"]),
            ("特色", "磁吸上盖可换色、校准卡自动检测", ["用研报告"]),
            ("App功能", "拼图、模板打印、标签打印、贴纸素材", ["用研报告"]),
        ],
        "pros": ["磁吸上盖个性化可换", "App功能丰富（拼图/模板/标签）", "打印质量好"],
        "cons": ["蓝牙匹配时间较长", "无法多选照片批量打印"],
    },
]


class SampleAdapter(Adapter):
    name = "示例数据"
    _DATASETS = {"instant-camera": _CAMERAS, **_EXPANSION}

    def fetch(self, category_id: str) -> list[Item]:
        rows = self._DATASETS.get(category_id)
        if not rows:
            print(f"  · sample: 品类 '{category_id}' 暂无示例数据集，返回空")
            return []
        out: list[Item] = []
        for c in rows:
            it = Item(
                id=c["id"], category=category_id, name=c["name"], brand=c["brand"],
                summary=c["summary"],
                price_value=float(MSRP_USD.get(c["id"], 0)) or None, currency="USD",
                asin=ASIN.get(c["id"], ""),
                tags=list(c["tags"]), release_date=c.get("release", ""),
                official_url=c.get("official_url") or _OFFICIAL.get(c["brand"], ""),
                sources=[Source(name=self.name, fetched_at=_NOW)],
            )
            # 注意：不再使用编造的 rank/hot —— 真实「最火/最畅销」信号由 amazon 适配器实时抓取
            for fld, val, srcs in c["specs"]:
                for s in srcs:
                    it.add_spec(fld, val, s)
            it.add_spec("上市时间", c["release"], "官方")
            # 购买渠道：真实搜索/官网链接（评分/评价数由各平台适配器填真实值）
            for sname, url, off in _seller_search_urls(c["name"], c["brand"]):
                pos, neg = _reviews(sname, c.get("pros", []), c.get("cons", []))
                it.sellers.append(Seller(name=sname, url=url, is_official=off,
                                         reviews_pos=pos, reviews_neg=neg))
            if it.official_url:
                it.sellers.append(Seller(name=f"{c['brand']} 官网", url=it.official_url, is_official=True))
            # 公开市场热度/畅销信号（来自扩展产品表的「评价数/热度」列 + 公开市场认知，
            # 非平台实时抓取）。仅用于「最火/最畅销」榜排序，不计入展示的评分/评价数。
            mh, ms = c.get("hot"), c.get("sales")
            if mh is not None or ms is not None:
                man = {}
                if mh is not None:
                    man["hot"] = mh
                if ms is not None:
                    man["sales"] = ms
                it.platforms["manual"] = man
            # 「数据支撑」展示文案（真实评价数/销量证据或定性依据）
            if c.get("note"):
                it.pop_note = c["note"]
            # 京东联盟真实数据优先：有则覆盖估算信号 + 文案（真实评价数/销量/到手价）
            ju = (_JD_UNION.get(c["id"]) or {}).get("jd") or {}
            if ju.get("reviews") is not None or ju.get("sales") is not None:
                jd = {}
                if ju.get("reviews") is not None:
                    jd["reviews"] = ju["reviews"]
                if ju.get("sales") is not None:
                    jd["sales"] = ju["sales"]
                it.platforms["jd"] = jd
                it.platforms.pop("manual", None)   # 有真实数据就不用估算
                if ju.get("price") is not None:
                    it.price_value = ju["price"]; it.currency = "CNY"
                parts = []
                if ju.get("reviews"):
                    parts.append(f"京东{_wan(ju['reviews'])}评价")
                if ju.get("sales"):
                    parts.append(f"30天售{_wan(ju['sales'])}")
                if ju.get("good_rate"):
                    parts.append(f"好评{ju['good_rate']}%")
                if parts:
                    it.pop_note = " · ".join(parts) + "（京东联盟）"
            out.append(it)
        print(f"  · 目录: 品类 '{category_id}' 提供 {len(out)} 款机型（含官方上市日期/参数/渠道）")
        return out
