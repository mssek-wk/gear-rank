# 器材榜 Gear Rank

每日抓取硬件的「最新 / 最火 / 最畅销」，分类排布，**数据全部留存在本地**。
当前品类：**拍立得**。结构按可扩展设计，后续加品类只改一个配置文件。

项目路径：`~/Desktop/gear-rank`

```
gear-rank/
├── DESIGN.md                 # 视觉设计规范（极简产品橱窗 / L2）
├── data/                     # ← 本地数据档案（每次更新覆盖写入）
│   ├── categories.json       # 品类注册表（扩展入口）
│   ├── meta.json             # 更新时间 + 各品类条目数
│   └── instant-camera/
│       ├── items.json        # 全部商品完整记录（含图片/参数/渠道/评价）
│       └── boards.json       # 三榜的有序 id
├── crawler/
│   ├── run.py                # 更新入口（两阶段：fetch 产出 → enrich 补全）
│   ├── registry.py           # 品类 / 适配器注册
│   ├── pipeline.py           # 合并→交叉查重→打分→归类→落盘
│   ├── schema.py             # 数据模型（Item / Seller / Review …）
│   └── adapters/             # 数据源（可插拔）
│       ├── _http.py          # 标准库 HTTP 工具（重定向/429 重试）
│       ├── sample.py         # 基础数据 producer（型号/参数/渠道/示例评价）
│       ├── wikimedia.py      # ★实时抓取真实多视图产品图（enricher）
│       ├── official.py       # ★实时确认官网，登记为参数来源（enricher）
│       ├── ecommerce.py      # 电商榜单/真实评价（待接入，「最畅销」）
│       └── media.py          # 测评/媒体（待接入，「最新/最火」）
└── web/                      # 前端（纯静态，含详情页）
    ├── index.html
    ├── styles.css
    ├── app.js                # 列表 + hash 路由详情页（#item=<id>）
    └── data.js               # ← crawler 自动生成，前端读它
```

## 快速开始

```bash
cd ~/Desktop/gear-rank

# 1) 生成 / 更新数据（会实时抓取真实产品图，需联网）
python3 crawler/run.py

# 2) 看页面：直接双击 web/index.html，或起本地服务器（推荐）：
python3 -m http.server 8000 --directory web
# 打开 http://localhost:8000
```

常用命令：

```bash
python3 crawler/run.py --list                    # 列出品类与其适配器
python3 crawler/run.py --category instant-camera # 只更新某个品类
```

## 详情页（点任意机型卡片进入）

每个机型有独立详情页（`#item=<id>` 路由），包含：

- **多视图实拍图** —— 由 `wikimedia` 适配器实时从 Wikimedia Commons 抓取（含许可与作者署名）；
  无图的新机型回退到内置 SVG 相机插画。
- **参数规格** —— 各来源（官网 / 京东参数 / DPReview）交叉对比、查漏补缺、去重；
  每个字段标注出处，多来源一致的字段标「✓ 交叉确认」。
- **购买渠道** —— 各售卖网站（京东 / 天猫 / Amazon）+ 官网的真实可点链接、价格、评分。
- **用户评价** —— 各售卖网站好评 / 差评 Top10（按点赞数排序）。

## 数据流（两阶段）

```
producer.fetch()  → 产出候选商品（sample / ecommerce / media）
   → merge_by_id  → 跨源按 id 合并、参数来源累加（交叉查重）
enricher.enrich() → 在合并结果上补全（wikimedia 真实图片 / official 官网确认）
   → score        → 三类信号各自 min-max 归一化到 0–1
   → build_boards → 取 Top 8 生成 最新/最火/最畅销
   → 落盘 data/ + 生成 web/data.js
```

三榜依据：

| 榜单 | 依据信号 | 负责适配器 |
|------|----------|------------|
| 最新 | `release_date` 上市时间 | media |
| 最火 | `hot_index` 热度指数 | media |
| 最畅销 | `sales_rank` 电商销量排名 | ecommerce |

## 真实数据：现状与待接入

| 数据 | 现状 |
|------|------|
| **产品图（多视图）** | ✅ 实时抓取 Wikimedia Commons，真实、版权清晰；约 2/3 机型有图，新机型回退插画 |
| **官网确认** | ✅ 实时确认品牌官网可达，登记为参数来源 |
| **参数规格** | 由多来源交叉合并并标注出处（数据为真实规格）；官网结构化抓取预留在 `official._extract_specs` |
| **各电商售卖/官网链接** | ✅ 真实可点（型号搜索 URL + 官网） |
| **好评/差评 Top10** | ⚠️ 当前为**代表性示例**（详情页有明确提示）。京东/淘宝评价多在登录墙+反爬之后，HTTP 直抓不可靠；真实抓取见下 |

**接入真实评价 / 电商销量**：打开 `crawler/adapters/ecommerce.py`，按顶部指南：
1. 在 `CATEGORY_RANK_URLS` 填真实榜单/商品 URL；
2. 京东评价可走其公开评论接口（`club.jd.com/comment/...`，需带 SKU，注意频率与反爬）；
   动态页面用 Playwright：`pip install playwright && playwright install chromium`；
3. 解析后映射成 `schema.Item` / `Seller` / `Review`，**id 用 `品牌-型号` 小写连字符**即可自动按 id 合并；
4. 抓取失败返回空 + 打印告警，不要抛异常（单源故障不拖垮整次更新）。

接入后把对应品类 `categories.json` 里的 `"sample"` 去掉即可下线示例数据。

## 扩展：加一个新品类

只改 `data/categories.json`，追加一项即可（前端品类标签、爬虫调度都会自动跟上）：

```json
{
  "id": "mechanical-keyboard",
  "name": "机械键盘",
  "enabled": true,
  "order": 2,
  "description": "客制化与成品机械键盘",
  "adapters": ["sample", "ecommerce", "media", "wikimedia", "official"],
  "currency": "CNY"
}
```

再给该品类喂数据：在 `adapters/sample.py` 的 `_DATASETS` 里加一份数据集（或配置真实适配器），
重跑 `python3 crawler/run.py` 即可。`wikimedia` 会自动按「品牌+型号」给新品类抓图。

## 让它每天自动跑（macOS）

现在是手动运行。要每天自动更新，把 `run.py` 挂到 launchd。新建
`~/Library/LaunchAgents/com.gearrank.daily.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.gearrank.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/kan/Desktop/gear-rank/crawler/run.py</string>
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/gearrank.log</string>
  <key>StandardErrorPath</key><string>/tmp/gearrank.err</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.gearrank.daily.plist   # 启用（每天 09:00 跑）
launchctl unload ~/Library/LaunchAgents/com.gearrank.daily.plist # 停用
```

> 注：项目放在 `~/Desktop`，macOS 会对桌面目录做隐私保护（TCC）。从你自己的终端运行
> `python3 -m http.server` 没问题；某些受限的自动化沙盒可能无法读取桌面目录——若遇到
> 服务器 404，把项目挪到 `~/gear-rank` 等非保护目录即可。

## 致谢

- 真实产品图来自 [Wikimedia Commons](https://commons.wikimedia.org/)，许可与作者已在详情页注明。
- 动效思路 derived from [vue-bits / react-bits](https://github.com/DavidHDev/vue-bits) by DavidHDev (MIT)，本站以原生 CSS/JS 重写。
