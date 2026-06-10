#!/usr/bin/env python3
"""京东联盟官方 API 取数 —— 拉真实「评价数 / 30天销量 / 价格」，写入快照供榜单使用。

为什么用它：京东/淘宝/小红书的免登录公开接口已被反爬封死（club.jd.com 返回「系统繁忙」、
搜索 302 跳风控页）。唯一干净、可持续、不靠爬虫的国内真实数据通道就是京东联盟官方
开放接口 jd.union.open.goods.query —— 返回 comments(评价数)、inOrderCount30Days(30天销量)、
priceInfo.lowestPrice(到手价)。它需要「开发者 appKey + appSecret」（不是联盟后台的「授权Key」）。

凭证来源（二选一，都不入库）：
  1) 环境变量 JD_UNION_APP_KEY / JD_UNION_APP_SECRET
  2) 文件 crawler/.jd_union.json  ->  {"app_key": "...", "app_secret": "..."}

用法：
  python3 crawler/jd_union_fetch.py                 # 拉全部扩展品类产品
  python3 crawler/jd_union_fetch.py --category action-camera
产物：
  data/jd_union_snapshot.json  ->  {产品id: {"jd": {reviews, sales, price, sku, sku_name, as_of}}}
  sample 适配器会自动读取并以真实数据覆盖该产品的热度/畅销信号与「数据支撑」文案。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CRED_FILE = BASE / "crawler" / ".jd_union.json"
EXPANSION = DATA / "expansion_products.json"
SNAPSHOT = DATA / "jd_union_snapshot.json"
API = "https://api.jd.com/routerjson"


def load_cred() -> tuple[str, str]:
    ak = os.environ.get("JD_UNION_APP_KEY", "")
    sec = os.environ.get("JD_UNION_APP_SECRET", "")
    if ak and sec:
        return ak.strip(), sec.strip()
    if CRED_FILE.exists():
        c = json.loads(CRED_FILE.read_text(encoding="utf-8"))
        return c.get("app_key", "").strip(), c.get("app_secret", "").strip()
    raise SystemExit(
        "❌ 缺少京东联盟凭证。请设环境变量 JD_UNION_APP_KEY/JD_UNION_APP_SECRET，"
        f"或创建 {CRED_FILE}（{{\"app_key\":\"...\",\"app_secret\":\"...\"}}）。"
    )


def _sign(params: dict, secret: str) -> str:
    base = secret + "".join(f"{k}{params[k]}" for k in sorted(params)) + secret
    return hashlib.md5(base.encode("utf-8")).hexdigest().upper()


def goods_query(app_key: str, secret: str, keyword: str) -> list[dict]:
    """调用 jd.union.open.goods.query，返回 data 列表（最多5条，按30天销量降序）。"""
    biz = {"goodsReqDTO": {"keyword": keyword, "pageIndex": 1, "pageSize": 5,
                           "sortName": "inOrderCount30Days", "sort": "desc"}}
    params = {
        "method": "jd.union.open.goods.query",
        "app_key": app_key,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "1.0",
        "sign_method": "md5",
        "360buy_param_json": json.dumps(biz, ensure_ascii=False),
    }
    params["sign"] = _sign(params, secret)
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(API, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read().decode("utf-8", "replace"))
    if "error_response" in resp:
        raise RuntimeError(resp["error_response"].get("zh_desc", resp["error_response"]))
    # 注意 JD 官方拼写为 ...responce
    node = resp.get("jd_union_open_goods_query_responce") or resp.get("jd_union_open_goods_query_response") or {}
    qr = node.get("queryResult")
    if not qr:
        return []
    parsed = json.loads(qr)
    return parsed.get("data") or []


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^0-9a-zA-Z]+", s.lower()) if len(t) >= 2}


def best_match(name: str, results: list[dict]) -> dict | None:
    """从搜索结果里挑与产品名最匹配的一条（命中型号 token 数最多）。"""
    qt = _tokens(name)
    best, best_score = None, -1
    for it in results:
        sku_name = it.get("skuName", "")
        score = len(qt & _tokens(sku_name))
        if score > best_score:
            best, best_score = it, score
    return best if best_score >= 1 else (results[0] if results else None)


def extract(it: dict) -> dict:
    price = ((it.get("priceInfo") or {}).get("lowestPrice")
             or (it.get("priceInfo") or {}).get("price"))
    return {
        "reviews": it.get("comments"),
        "sales": it.get("inOrderCount30Days") or it.get("inOrderCount30DaysSku"),
        "good_rate": it.get("goodCommentsShare"),
        "price": float(price) if price not in (None, "") else None,
        "sku": str(it.get("skuId", "")),
        "sku_name": it.get("skuName", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", help="只拉指定扩展品类")
    ap.add_argument("--sleep", type=float, default=1.0, help="每次请求间隔秒（默认1，避免频控）")
    args = ap.parse_args()

    app_key, secret = load_cred()
    datasets = json.loads(EXPANSION.read_text(encoding="utf-8"))
    snap = {}
    if SNAPSHOT.exists():
        try:
            snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except Exception:
            snap = {}

    today = date.today().isoformat()
    ok = miss = err = 0
    for cat, items in datasets.items():
        if args.category and cat != args.category:
            continue
        print(f"\n▶ {cat}（{len(items)} 款）")
        for c in items:
            kw = c["name"]
            try:
                results = goods_query(app_key, secret, kw)
            except Exception as e:
                print(f"  ! {kw}: {str(e)[:60]}")
                err += 1
                time.sleep(args.sleep)
                continue
            m = best_match(kw, results)
            if not m:
                print(f"  · {kw}: 无结果")
                miss += 1
                time.sleep(args.sleep)
                continue
            info = extract(m)
            snap[c["id"]] = {"jd": {**info, "as_of": today, "source": "京东联盟 jd.union.open.goods.query"}}
            print(f"  ✓ {kw}: 评价{info['reviews']} 销量{info['sales']} ¥{info['price']} ← {info['sku_name'][:30]}")
            ok += 1
            time.sleep(args.sleep)

    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 写入 {SNAPSHOT}：成功 {ok} · 无结果 {miss} · 出错 {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
