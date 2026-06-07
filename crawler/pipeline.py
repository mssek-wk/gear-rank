"""管线：合并 -> 打分 -> 归类 -> 落盘。

数据流：
  adapters[].fetch() -> 原始 Item 列表
    -> merge_by_id   (跨源按 id 去重合并)
    -> score         (三类信号各自 min-max 归一化到 0-1，口径统一)
    -> build_boards  (按分数取 Top N 生成 最新/最火/最畅销 三榜)
    -> write         (本地 JSON 落盘 + 生成前端 data.js)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from schema import Item, days_since

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
BOARD_SIZE = 8  # 每个榜单展示前 N 名


# ---------- 合并 ----------

def merge_by_id(items: list[Item]) -> list[Item]:
    """同一 id 的多源数据合并：后到的非空字段补全先到的，sources 累加。"""
    merged: dict[str, Item] = {}
    for it in items:
        if it.id not in merged:
            merged[it.id] = it
            continue
        base = merged[it.id]
        for f in ("image", "url", "official_url", "summary", "price_value",
                  "release_date", "sales_rank", "hot_index"):
            if not getattr(base, f) and getattr(it, f):
                setattr(base, f, getattr(it, f))
        base.tags = list(dict.fromkeys(base.tags + it.tags))
        if not base.images and it.images:
            base.images, base.image_credits = it.images, it.image_credits
        base.specs = {**it.specs, **base.specs}
        # 合并每个参数字段的来源（交叉查重）
        for fld, srcs in it.spec_sources.items():
            base.spec_sources.setdefault(fld, [])
            for s in srcs:
                if s not in base.spec_sources[fld]:
                    base.spec_sources[fld].append(s)
        if not base.sellers and it.sellers:
            base.sellers = it.sellers
        base.sources.extend(it.sources)
    return list(merged.values())


# ---------- 打分 ----------

def _normalize(values: dict[str, float]) -> dict[str, float]:
    """min-max 归一化到 [0,1]；全相等时统一给 0.5；缺值给 0。"""
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {k: 0.0 for k in values}
    lo, hi = min(present.values()), max(present.values())
    out = {}
    for k, v in values.items():
        if v is None:
            out[k] = 0.0
        elif hi == lo:
            out[k] = 0.5
        else:
            out[k] = round((v - lo) / (hi - lo), 4)
    return out


def score(items: list[Item]) -> None:
    """就地写入 latest_score / hot_score / sales_score。"""
    # 最新：发布越近越高 -> 用 -距今天数 作为信号
    latest_sig = {it.id: (-d if (d := days_since(it.release_date)) is not None else None)
                  for it in items}
    # 最畅销：销量排名越小越高 -> 用 -rank 作为信号
    sales_sig = {it.id: (-it.sales_rank if it.sales_rank is not None else None)
                 for it in items}
    # 最火：热度指数直接用
    hot_sig = {it.id: it.hot_index for it in items}

    latest_n = _normalize(latest_sig)
    sales_n = _normalize(sales_sig)
    hot_n = _normalize(hot_sig)
    for it in items:
        it.latest_score = latest_n[it.id]
        it.sales_score = sales_n[it.id]
        it.hot_score = hot_n[it.id]


# ---------- 归类 ----------

def build_boards(items: list[Item]) -> dict[str, list[str]]:
    """返回三榜的有序 id 列表。"""
    def top(key, tie):
        ranked = sorted(items, key=lambda it: (getattr(it, key), tie(it)), reverse=True)
        return [it.id for it in ranked[:BOARD_SIZE]]

    return {
        "latest": top("latest_score", lambda it: it.hot_score),
        "hottest": top("hot_score", lambda it: it.sales_score),
        "bestselling": top("sales_score", lambda it: it.hot_score),
    }


# ---------- 资源保鲜 ----------

def carry_over_images(category_id: str, items: list[Item]) -> int:
    """用上次落盘的图片补全本次没拿到图的商品（抵御 Wikimedia 偶发 429）。
    返回沿用旧图的件数。"""
    prev_file = DATA_DIR / category_id / "items.json"
    if not prev_file.exists():
        return 0
    try:
        prev = {p["id"]: p for p in json.loads(prev_file.read_text(encoding="utf-8"))}
    except Exception:
        return 0
    n = 0
    for it in items:
        if not it.images and prev.get(it.id, {}).get("images"):
            old = prev[it.id]
            it.images = old["images"]
            it.image = it.image or old.get("image", "")
            it.image_credits = old.get("image_credits", [])
            n += 1
    return n


# ---------- 本地自托管图片覆盖 ----------

def apply_image_overrides(items: list[Item]) -> int:
    """把 data/image_overrides.json 里登记的本地产品图覆盖到对应商品。
    用于 Commons 没收录的机型（从厂商/电商取真实多视角图，自托管在 web/images/）。"""
    f = DATA_DIR / "image_overrides.json"
    if not f.exists():
        return 0
    try:
        ov = (json.loads(f.read_text(encoding="utf-8")) or {}).get("overrides", {})
    except Exception:
        return 0
    n = 0
    by_id = {it.id: it for it in items}
    for iid, spec in ov.items():
        it = by_id.get(iid)
        imgs = (spec or {}).get("images") or []
        if not it or not imgs:
            continue
        it.images = imgs
        it.image = imgs[0]
        cr = (spec or {}).get("credit") or {}
        it.image_credits = [{"title": cr.get("source", "厂商产品图"),
                             "license": cr.get("note", ""), "artist": "", "descurl": ""}]
        n += 1
    if n:
        print(f"  · 本地图片覆盖：{n} 件机型使用自托管真实产品图")
    return n


# ---------- 历史留存（累积式，绝不删除老机型）----------

def merge_history(category_id: str, items: list[Item], run_date: str) -> list[dict]:
    """把本次抓到的商品与历史 items.json 做并集，实现「全部机型」累积保留：

    - 本次抓到的：active=True，刷新 last_seen；first_seen 沿用历史首见日期（没有则今天）。
    - 历史里有、本次没抓到的：保留整条，标 active=False（= 历史/已下架，仍在「全部机型」展示）。
    返回合并后的 dict 列表（fresh 在前、历史在后）。
    """
    prev_file = DATA_DIR / category_id / "items.json"
    prev: dict[str, dict] = {}
    if prev_file.exists():
        try:
            prev = {p["id"]: p for p in json.loads(prev_file.read_text(encoding="utf-8"))}
        except Exception:
            prev = {}

    out: list[dict] = []
    fresh_ids = set()
    for it in items:
        fresh_ids.add(it.id)
        it.active = True
        it.last_seen = run_date
        it.first_seen = (prev.get(it.id) or {}).get("first_seen") or run_date
        out.append(it.to_dict())

    carried = 0
    for pid, pd in prev.items():
        if pid in fresh_ids:
            continue
        pd = dict(pd)
        pd["active"] = False           # 历史机型：保留展示，但不在本次榜单
        out.append(pd)
        carried += 1
    if carried:
        print(f"  · 历史留存：{carried} 件本次未上榜的老机型仍保留在「全部机型」")
    return out


# ---------- 落盘 ----------

def write_category(category_id: str, items_dicts: list[dict], boards: dict) -> dict:
    """写入已合并好的 dict 列表（含历史机型）+ 三榜。"""
    out_dir = DATA_DIR / category_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "items.json").write_text(
        json.dumps(items_dicts, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "boards.json").write_text(
        json.dumps(boards, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"items": items_dicts, "boards": boards}


def write_meta(meta: dict) -> None:
    (DATA_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def write_web_bundle(payload: dict) -> None:
    """生成前端可直接 <script> 加载的 data.js，使 index.html 双击即可离线查看
    （避免 file:// 下 fetch 本地 JSON 的跨域限制）。"""
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    js = "window.__GEAR_DATA__ = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    (WEB_DIR / "data.js").write_text(js, encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
