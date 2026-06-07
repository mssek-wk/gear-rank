"""品类注册表 + 适配器注册表。

扩展点：
  - 新增品类 -> 编辑 data/categories.json（无需改代码）。
  - 新增数据源 -> 在 adapters/ 下新建一个继承 Adapter 的类，并在 ADAPTERS 里登记。
"""

from __future__ import annotations

import json
from pathlib import Path

from adapters.base import Adapter
from adapters.sample import SampleAdapter
from adapters.ecommerce import EcommerceAdapter
from adapters.media import MediaAdapter
from adapters.wikimedia import WikimediaAdapter
from adapters.official import OfficialAdapter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATEGORIES_FILE = DATA_DIR / "categories.json"

# 适配器登记表：key 对应 categories.json 里 adapters 数组中的名字。
# producer（产出商品）：sample / ecommerce / media
# enricher（补充字段）：wikimedia（真实图片）/ official（官网确认）
ADAPTERS: dict[str, type[Adapter]] = {
    "sample": SampleAdapter,
    "ecommerce": EcommerceAdapter,
    "media": MediaAdapter,
    "wikimedia": WikimediaAdapter,
    "official": OfficialAdapter,
}


def load_categories(only_enabled: bool = True) -> list[dict]:
    data = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
    cats = sorted(data.get("categories", []), key=lambda c: c.get("order", 999))
    if only_enabled:
        cats = [c for c in cats if c.get("enabled", True)]
    return cats


def adapters_for(category: dict) -> list[Adapter]:
    """按品类配置实例化其声明的适配器；未知名字给出告警并跳过。"""
    instances: list[Adapter] = []
    for name in category.get("adapters", []):
        cls = ADAPTERS.get(name)
        if cls is None:
            print(f"  ! 未知适配器 '{name}'（在 registry.ADAPTERS 中登记后即可启用），跳过")
            continue
        instances.append(cls())
    return instances
