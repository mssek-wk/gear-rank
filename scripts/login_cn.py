#!/usr/bin/env python3
"""一次性登录京东 / 淘宝，保存登录会话（cookie），供爬虫复用。

用法（在你自己的电脑上跑，会弹出浏览器窗口）：
    python3 scripts/login_cn.py            # 同时登录京东 + 淘宝
    python3 scripts/login_cn.py jd         # 只登录京东
    python3 scripts/login_cn.py taobao     # 只登录淘宝

流程：脚本打开浏览器 → 你用手机 App 扫码登录 → 回终端按回车 →
会话保存到 crawler/.cn_session/<站点>.json（已在 .gitignore，等同账号凭证，别外传）。
之后 jd / taobao 适配器会带着这个会话去抓真实价格/销量/评价；cookie 过期了重跑本脚本即可。

依赖：pip install --user playwright && python3 -m playwright install chromium
"""

from __future__ import annotations

import sys
from pathlib import Path

SESSION_DIR = Path(__file__).resolve().parent.parent / "crawler" / ".cn_session"
SITES = {
    "jd": "https://www.jd.com/",
    "taobao": "https://www.taobao.com/",
}


def login(site: str, url: str) -> None:
    from playwright.sync_api import sync_playwright
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    out = SESSION_DIR / f"{site}.json"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(url)
        print(f"\n>>> 已打开 {site}（{url}）")
        print(">>> 请在弹出的浏览器里用手机 App 扫码 / 账号登录。")
        input(">>> 登录完成后，回到这里按【回车】保存会话…")
        ctx.storage_state(path=str(out))
        browser.close()
    print(f"✓ {site} 会话已保存到 {out}")


def main() -> int:
    targets = sys.argv[1:] or ["jd", "taobao"]
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("未安装 playwright。先运行：")
        print("  python3 -m pip install --user playwright")
        print("  python3 -m playwright install chromium")
        return 1
    for site in targets:
        if site not in SITES:
            print(f"未知站点：{site}（可选 jd / taobao）")
            continue
        login(site, SITES[site])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
