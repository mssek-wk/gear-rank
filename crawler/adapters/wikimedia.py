"""Wikimedia Commons 图片适配器 —— 实时抓取真实多视图产品图（enricher）。

Commons 是免费、稳定、可热链、版权清晰的图库，是合规获取「真实设备图」的首选。
做法：对每件商品用「品牌+型号」在 Commons 文件命名空间搜索，按标题与型号的匹配度
打分过滤（避免搜到无关图，如新机型搜不到时返回的地铁站照片），取 Top N 作为多视图，
并保留每张图的版权署名（Commons 要求署名）。

这是一个 enricher：只给已存在的 Item 补 images / image_credits，不新增商品。
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from schema import Item, Source
from .base import Adapter
from . import _http

API = "https://commons.wikimedia.org/w/api.php"
MAX_IMAGES = 5
_GENERIC = {"camera", "instant", "film", "the", "of", "and", "a", "with", "for"}


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^0-9a-z]+", s.lower()) if t]


def _distinctive(name_tokens: list[str]) -> set[str]:
    """型号里最有区分度的 token（数字 / 非通用词），用于强匹配判定。"""
    return {t for t in name_tokens if t and (t.isdigit() or t not in _GENERIC)}


def _score_title(title: str, brand: str, name: str) -> int:
    """文件标题与商品的匹配分；分越高越可能是该商品的真实图。"""
    tl = title.lower()
    qt = _tokens(f"{brand} {name}")
    return sum(1 for t in set(qt) if t and t in tl)


class WikimediaAdapter(Adapter):
    name = "Wikimedia"

    def enrich(self, category_id: str, items: list[Item]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ok = 0
        for i, it in enumerate(items):
            if i:
                time.sleep(0.4)  # 对 Commons 友好，降低 429 概率
            imgs, credits = self._images_for(it)
            if not imgs:
                continue
            it.images = imgs
            if not it.image:
                it.image = imgs[0]
            it.image_credits = credits
            it.sources.append(Source(name=self.name,
                                     url=f"https://commons.wikimedia.org/?search={it.brand}+{it.name}",
                                     fetched_at=now))
            ok += 1
        print(f"  · Wikimedia: {ok}/{len(items)} 件拿到真实图片")

    def _images_for(self, it: Item) -> tuple[list[str], list[dict]]:
        query = f"{it.brand} {it.name}".strip()
        data = _http.get_json(API, {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 12,
            "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 800,
        })
        if not data:
            return [], []
        pages = list(((data.get("query") or {}).get("pages") or {}).values())

        # 必须命中型号里的区分性 token（如 "evo" / "wide"），否则判为无关
        distinct = _distinctive(_tokens(it.name))
        # 型号里的数字（如 12 / 41 / 400）必须精确匹配，且标题里不能出现「别的型号数字」，
        # 否则会把 Mini 8 / Mini 25 误当成 Mini 41。无数字型号(如 Evo Cinema) 跳过此判。
        model_nums = set(re.findall(r"\d+", it.name))
        scored = []
        for p in pages:
            title = p.get("title", "")
            ii = (p.get("imageinfo") or [{}])[0]
            url = ii.get("thumburl") or ii.get("url")
            if not url:
                continue
            if not title.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            tl = title.lower()
            title_nums = set(re.findall(r"\d+", tl))
            if model_nums:
                # 型号数字必须全部出现，且标题不得带其它机型数字（排除 Link 2 等附属数字）
                if not model_nums <= title_nums:
                    continue
                if title_nums - model_nums - {"1", "2", "3", "4", "5"}:  # 容忍视图序号 1-5
                    continue
            hit_distinct = any(t in tl for t in distinct) if distinct else True
            sc = _score_title(title, it.brand, it.name)
            # 门槛：命中区分 token，且总匹配分 >=2（品牌/系列+型号）
            if hit_distinct and sc >= 2:
                meta = ii.get("extmetadata") or {}
                scored.append((sc, url, {
                    "title": title.replace("File:", ""),
                    "descurl": ii.get("descriptionurl", ""),
                    "license": (meta.get("LicenseShortName") or {}).get("value", ""),
                    "artist": re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:80],
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        imgs = [u for _, u, _ in scored[:MAX_IMAGES]]
        credits = [c for _, _, c in scored[:MAX_IMAGES]]
        return imgs, credits
