# WRITING.md · 每次更新怎么写（自助流程，不用每次问）

> 目标：浏览到真实数据后，Claude 按本文件固定格式直接写入、重算、即更新榜单。
> 原则：**只写真实可验证的数据；缺图/缺评直接留空**——前端自动走空状态 + 来源链接，不阻塞写入、不编造、不占位。

## 0. 数据采集方式（账号安全）
- **不用任何登录态爬虫**（账号异常风险）。见 `项目记忆/` 与 `交接说明.md`。
- 淘宝搜索页（`uland.taobao.com`）：Claude-in-Chrome 插件 `get_page_text` 可读。
- 京东全域 + 淘宝详情页：插件封禁 → 用 computer-use 系统截图读（浏览器在 Redmi 显示器，`switch_display` 后 `screenshot`；截图不落盘）。
- 一次一页、跟随用户人工浏览，绝不批量自动翻页。

## 1. 四个品类（自动归类，别问用户）
| 品类 id | 名称 | 收什么 |
|---|---|---|
| `instant-camera` | 拍立得 | 即拍即得（银盐/ZINK/热升华/混合）+ 便携照片打印机 |
| `action-camera` | 运动相机 | DJI / Insta360 / GoPro / AKASO / SJCAM 等 |
| `film-camera` | 胶片相机 | 胶片机、一次性/可复用、Lomography 等 |
| `retro-digital-camera` | 模拟胶卷数码相机 | 复古数码 / CCD / 双反造型数码（拍照存卡，非即时成像） |

判型要点：**会出片/打印 → 拍立得**；**存卡复古数码/CCD → 模拟胶卷数码**；运动相机/胶片机各归各。型号要精确匹配（套餐不同＝不同条目，别混）。

## 2. 给「已有机型」补平台价/销量（最常见）
改 `data/platform_snapshot.json` → `items["<机型id>"]`：
```jsonc
"items": {
  "fujifilm-instax-mini-12": {
    "taobao": { "currency":"CNY", "price":675.89, "sales":6000, "good_rate":98.9,
                "as_of":"2026-06-25", "source":"淘宝商品页(手动·截屏 2026-06-25)" },
    "jd":     { "currency":"CNY", "price":668, "as_of":"2026-06-25",
                "source":"京东(手动·截屏读页 2026-06-25)" }
    // amazon 字段（asin/rating/reviews/price/bsr）保留不动
  }
}
```
- `price` 取该机型**销量最高的在售链接**价；`sales` 填数字下限（"6000+"→6000，"已售1万+"→10000）；`good_rate` 有则填。
- 平台键：`taobao` / `jd` / `amazon`。前端 `marketHTML` 自动按平台分行标价。

## 3. 加「新机型」
拍立得在 `crawler/adapters/sample.py` 的 `_CAMERAS`；其余三品类在 `data/expansion_products.json[品类]`，结构：
```jsonc
{
  "id":"chuzhao-m1", "name":"初照 M1 双反复古相机", "brand":"初照",
  "release":"2026", "tags":["复古CCD","双反造型","学生入门"],
  "summary":"一句话定位（真实可验证，不夸大）。",
  "specs":[ ["类型","双反造型复古CCD数码相机",["来源标注"]], ["使用场景","学生/日常",["来源"]] ],
  "pros":[], "cons":[], "official_url":"",       // 白牌无官网就留空
  "hot":70.0, "sales":80.0,                        // 排序信号（参照同类相对高低，非真实销量）
  "note":"来源 + 价/销量/好评率 + 截至日期"
}
```
然后把价格/销量写进 `platform_snapshot.json`（见 §2）。新机型 id 用 `品牌-型号` kebab。
> 三个扩展品类已挂 `jd`/`taobao` 适配器（`categories.json`），写进快照即生效。

## 4. 图片
- 有真实图：下载到 `web/images/<机型id>/1.jpg 2.jpg …`，在 `data/image_overrides.json` 的 `overrides["<id>"]` 登记 `{ "images":[...], "credit":{ "source":"...","note":"..." } }`。
- **没有图：什么都不用做**——前端自动显示「产品图待补 · 查看来源 →」空状态卡（链接到官网/电商）。先试官网/百度百科/Wikimedia，实在没有就留空给链接。**绝不放纯色块/占位图。**

## 5. 评价
- **只写真实评价**（结构见 schema 的 `Seller.reviews_pos/neg`）。
- 没有真实评价：**什么都不写**——前端自动显示「暂无已核验的真实评价 · 去京东/淘宝看 →」。**绝不合成示例评价。**

## 6. 写完重算（必做）
```bash
cd ~/Desktop/photo\ web/gear-rank
python3 crawler/run.py            # 重算三榜 + 生成 web/data.js
```
- 校验：`git status` 无登录凭证；`grep 示例 web/data.js` 应只剩 0（无假评价）。
- 全部数据都在本文件夹 → 直接 `git add/commit/push` 上 GitHub Pages。

## 7. 红线
- 数据真实可验证；图真实多视角（给 ID 设计师参考）；反对编造/占位。
- 不启用登录态爬虫；提交前确认无 cookie/session 文件。
