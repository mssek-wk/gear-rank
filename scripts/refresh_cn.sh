#!/bin/bash
# 刷新京东/淘宝/抖音/小红书 真实数据 → 并入综合榜（助手式，需有人在 + 已登录）。
#
# 它做两件事：
#   1) 跑「四平台综合爬虫」（headed 真实浏览器，绕过风控；用其 storage_state.json 登录态）
#   2) import_cn.py 把产出 CSV 并入 gear-rank 的 platform_snapshot.json
# 之后再跑 crawler/run.py，淘宝/京东真实销量评价就并入综合最火/最畅销。
#
# 注意：爬虫是 headed + 交互式 + 风控敏感，无法放进无人值守的每日 cron。
# 所以 CN 数据是「偶尔有会话时刷新」，Amazon 才是真·每天自动。登录失效就重跑 login_export.py。

set -e
REPO="$HOME/Desktop/gear-rank"
SPIDER_DIR="$REPO/四平台综合爬虫"
KEYWORD="${1:-拍立得}"

echo "▶ 1/3 跑四平台爬虫（关键词：$KEYWORD）…"
cd "$SPIDER_DIR"
printf '1\n1\n%s\n' "$KEYWORD" | /usr/bin/python3 full_spider.py

echo "▶ 2/3 导入 CSV 到快照…"
cd "$REPO"
/usr/bin/python3 crawler/import_cn.py "$SPIDER_DIR/采集数据/全平台汇总_${KEYWORD}.csv"

echo "▶ 3/3 重算综合榜…"
/usr/bin/python3 crawler/run.py | grep -E '淘宝|京东|Amazon|全部机型'
echo "✅ CN 数据已刷新并入综合榜。记得 git add/commit/push 让公网站点更新。"
