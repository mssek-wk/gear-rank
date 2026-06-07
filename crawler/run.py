#!/usr/bin/env python3
"""更新入口。

用法：
  python3 crawler/run.py                 # 更新所有启用的品类
  python3 crawler/run.py --category instant-camera
  python3 crawler/run.py --list          # 列出品类与其适配器

产物（全部落在本地）：
  data/<category>/items.json   每件商品完整记录（本地数据档案）
  data/<category>/boards.json  最新/最火/最畅销 三榜的有序 id
  data/meta.json               更新时间 + 各品类条目数
  web/data.js                  前端直接加载的打包数据（双击 index.html 即可看）

定时自动化（后续接）：把本脚本挂到 launchd / cron 即可，详见 README。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 让 "from schema import ..." / "from adapters... " 在任意工作目录下都可用
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline  # noqa: E402
from registry import load_categories, adapters_for  # noqa: E402


def update_category(cat: dict) -> dict:
    cid = cat["id"]
    print(f"\n▶ 更新品类：{cat.get('name', cid)} ({cid})")
    adapters = adapters_for(cat)

    # 阶段 1：producer 产出候选商品
    raw = []
    for ad in adapters:
        try:
            raw.extend(ad.fetch(cid))
        except Exception as e:  # 适配器异常不应中断整次更新
            print(f"  ! 适配器 {ad.name}.fetch 抛错：{e}")

    items = pipeline.merge_by_id(raw)
    if not items:
        print("  · 无数据（所有 producer 都返回空），跳过落盘")
        return {"id": cid, "name": cat.get("name", cid), "count": 0}

    # 阶段 2：enricher 在合并结果上补充字段（真实图片 / 官网确认 / 真实评价…）
    for ad in adapters:
        try:
            ad.enrich(cid, items)
        except Exception as e:
            print(f"  ! 适配器 {ad.name}.enrich 抛错：{e}")

    # 保鲜：本次没抓到图的，沿用上次的真实图，避免偶发 429 让榜单丢图
    kept = pipeline.carry_over_images(cid, items)
    if kept:
        print(f"  · 图片保鲜：{kept} 件沿用上次抓取的真实图")

    pipeline.score(items)
    boards = pipeline.build_boards(items)
    pipeline.write_category(cid, items, boards)
    print(f"  ✓ 合并后 {len(items)} 件，已写入 data/{cid}/")
    return {"id": cid, "name": cat.get("name", cid),
            "name_en": cat.get("name_en", ""), "icon": cat.get("icon", ""),
            "description": cat.get("description", ""), "count": len(items)}


def main() -> int:
    ap = argparse.ArgumentParser(description="硬件榜单数据更新")
    ap.add_argument("--category", help="只更新指定品类 id")
    ap.add_argument("--list", action="store_true", help="列出品类与适配器后退出")
    args = ap.parse_args()

    cats = load_categories(only_enabled=True)

    if args.list:
        for c in cats:
            print(f"- {c['id']}  ({c.get('name','')})  adapters={c.get('adapters')}")
        return 0

    if args.category:
        cats = [c for c in cats if c["id"] == args.category]
        if not cats:
            print(f"未找到启用的品类：{args.category}")
            return 1

    summaries = []
    web_by_category = {}
    for c in cats:
        s = update_category(c)
        summaries.append(s)
        if s["count"]:
            cdir = pipeline.DATA_DIR / c["id"]
            import json
            web_by_category[c["id"]] = {
                "items": json.loads((cdir / "items.json").read_text(encoding="utf-8")),
                "boards": json.loads((cdir / "boards.json").read_text(encoding="utf-8")),
            }

    meta = {
        "updated_at": pipeline.now_iso(),
        "generator": "hardware-rank crawler",
        "board_size": pipeline.BOARD_SIZE,
        "categories": summaries,
    }
    pipeline.write_meta(meta)
    pipeline.write_web_bundle({"meta": meta, "byCategory": web_by_category})

    total = sum(s["count"] for s in summaries)
    print(f"\n✅ 完成：{len(summaries)} 个品类，共 {total} 件。已更新 data/ 与 web/data.js")
    print(f"   更新时间：{meta['updated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
