#!/usr/bin/env python3
"""把「四平台综合爬虫」产出的 CSV 真实数据并入 gear-rank 的 platform_snapshot.json。

来源：~/Desktop/gear-rank/四平台综合爬虫/采集数据/全平台汇总_<关键词>.csv（淘宝/京东/抖音/小红书）。
做的事：
  - 解析 淘宝/京东 的「价格 + 付款数(真实销量)」→ 写入 snapshot items[id].taobao / .jd
  - 统计 抖音/小红书 出现该机型的笔记/视频条数 → buzz（讨论热度）
  - 交叉验证：若「讨论热度高但实销低」→ 标 ad_suspect=True（疑似广告刷量）
  - 保守匹配：只认高置信关键词命中的行；未命中的行打印出来供人工确认，绝不瞎归类。

用法：python3 crawler/import_cn.py [CSV路径]
之后跑 crawler/run.py，京东适配器/管线会把这些真实 CN 数据并入综合榜。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "data" / "platform_snapshot.json"
DEFAULT_CSV = REPO / "四平台综合爬虫" / "采集数据" / "全平台汇总_拍立得.csv"

# 机型匹配：id -> 若干「关键词组」，任一组内关键词全部命中即算匹配（小写、去空格）。保守，命中才认。
MATCH = {
    "chuzhao-x1": [["初照", "x1"]],
    "chuzhao-d1-pro": [["初照", "d1"], ["初照", "644"]],   # 644 是 D1Pro 在京东/淘宝的价位标识
    "hprt-z6-pro": [["汉印", "z6"]],
    "fujifilm-instax-mini-99": [["mini99"]],
    "fujifilm-instax-mini-12": [["mini12"]],
    "fujifilm-instax-mini-evo": [["minievo"], ["mini", "evo"]],
    "fujifilm-instax-wide-400": [["wide400"], ["wide", "400"]],
    "fujifilm-instax-square-sq40": [["sq40"]],
    "fujifilm-instax-pal": [["instaxpal"]],
    "fujifilm-instax-mini-41": [["mini41"]],
    "fujifilm-instax-mini-13": [["mini13"]],
    "polaroid-now-gen2": [["polaroid", "now"], ["宝丽来", "now"]],
    "polaroid-go-gen2": [["polaroid", "go"], ["宝丽来", "go"]],
    "polaroid-flip": [["polaroid", "flip"]],
    "polaroid-i-2": [["polaroidi-2"], ["宝丽来i-2"]],
    "leica-sofort-2": [["sofort"]],
}


def parse_sales(s: str):
    """'4000+人付款' -> 4000；'4万+人付款' -> 40000；'已售1.2万' -> 12000。"""
    if not s:
        return None
    s = s.replace(",", "")
    m = re.search(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"([\d.]+)", s)
    return int(float(m.group(1))) if m else None


def parse_price(s: str):
    m = re.search(r"([\d.]+)", str(s or ""))
    return float(m.group(1)) if m else None


def match_id(title: str) -> str | None:
    t = title.lower().replace(" ", "")
    for iid, groups in MATCH.items():
        for grp in groups:
            if all(tok.lower().replace(" ", "") in t for tok in grp):
                return iid
    return None


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"❌ 找不到 CSV：{csv_path}")
        return 1
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    today = date.today().isoformat()

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {"items": {}}
    items = snap.setdefault("items", {})

    # 聚合
    agg: dict[str, dict] = {}
    unmatched = []
    buzz: dict[str, dict] = {}
    for r in rows:
        plat = r.get("平台", "")
        title = r.get("标题", "")
        iid = match_id(title)
        if not iid:
            unmatched.append((plat, title[:36], r.get("价格", ""), r.get("销量/热度", "")))
            continue
        if plat in ("淘宝", "天猫"):
            sales = parse_sales(r.get("销量/热度", ""))
            price = parse_price(r.get("价格", ""))
            cur = agg.setdefault(iid, {}).setdefault("taobao", {"sales": 0, "price": None})
            if sales:
                cur["sales"] = max(cur["sales"], sales)         # 取该机型最高销量链接
            if price and (cur["price"] is None or price < cur["price"]):
                cur["price"] = price                            # 取最低价
        elif plat == "京东":
            sales = parse_sales(r.get("销量/热度", ""))
            price = parse_price(r.get("价格", ""))
            cur = agg.setdefault(iid, {}).setdefault("jd", {})
            if sales:
                cur["reviews"] = max(cur.get("reviews", 0), sales)
            if price:
                cur["price"] = price
        elif plat in ("抖音", "小红书"):
            b = buzz.setdefault(iid, {"douyin": 0, "xhs": 0})
            b["douyin" if plat == "抖音" else "xhs"] += 1

    # 写入快照 + 交叉验证
    n = 0
    for iid, plats in agg.items():
        node = items.setdefault(iid, {})
        if "taobao" in plats and (plats["taobao"]["sales"] or plats["taobao"]["price"]):
            node["taobao"] = {"currency": "CNY", "price": plats["taobao"]["price"],
                              "sales": plats["taobao"]["sales"] or None,
                              "as_of": today, "source": "淘宝(四平台爬虫)"}
            n += 1
        if "jd" in plats and plats["jd"]:
            jd = node.get("jd", {})
            jd.update({k: v for k, v in plats["jd"].items() if v})
            jd.setdefault("currency", "CNY"); jd["as_of"] = today
            node["jd"] = jd
            n += 1
    # buzz + 广告嫌疑
    for iid, b in buzz.items():
        node = items.setdefault(iid, {})
        sales = (node.get("taobao") or {}).get("sales") or 0
        mentions = b["douyin"] + b["xhs"]
        node["buzz"] = {"douyin": b["douyin"], "xhs": b["xhs"], "as_of": today,
                        # 讨论多但实销很低 -> 疑似广告/种草刷量，热度打个问号
                        "ad_suspect": bool(mentions >= 3 and sales and sales < 500)}

    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 并入快照：{n} 条平台数据；buzz {len(buzz)} 个机型")
    for iid, plats in agg.items():
        tb = plats.get("taobao", {})
        print(f"  {iid:28} 淘宝¥{tb.get('price')} 销量{tb.get('sales')} 京东{plats.get('jd')}")
    if unmatched:
        print(f"\n未匹配（候选新品/需人工确认）{len(unmatched)} 条：")
        for p, t, pr, s in unmatched[:20]:
            print(f"  [{p}] {t}  ¥{pr}  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
