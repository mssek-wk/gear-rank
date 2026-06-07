"""极简 HTTP 工具（仅用标准库，零三方依赖）。

所有适配器统一走这里：带 UA、超时、手动跟随重定向（含 308）、429 退避重试，
失败返回 None 而非抛异常。
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_CTX = ssl.create_default_context()
_UA = "GearRank/0.1 (hardware ranking; research use; contact: local)"
TIMEOUT = 12
_MAX_REDIRECT = 5


def _raw_get(url: str, headers: dict | None = None) -> str:
    """跟随重定向（含 308）取文本；失败抛 HTTPError/URLError。"""
    seen = 0
    while True:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and seen < _MAX_REDIRECT:
                loc = e.headers.get("Location")
                if loc:
                    url = urllib.parse.urljoin(url, loc)
                    seen += 1
                    continue
            raise


def _with_retry(fn, label: str, url: str):
    """对 429 做最多 2 次退避重试。"""
    delay = 1.0
    for attempt in range(3):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = float(e.headers.get("Retry-After") or delay)
                time.sleep(min(wait, 5))
                delay *= 2
                continue
            print(f"    ! {label} 失败 {url[:80]} -> HTTP {e.code}")
            return None
        except Exception as e:
            print(f"    ! {label} 失败 {url[:80]} -> {type(e).__name__}: {str(e)[:50]}")
            return None


def get_json(url: str, params: dict | None = None, headers: dict | None = None) -> Any | None:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    txt = _with_retry(lambda: _raw_get(url, headers), "GET json", url)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def get_text(url: str, headers: dict | None = None) -> str | None:
    return _with_retry(lambda: _raw_get(url, headers), "GET text", url)
