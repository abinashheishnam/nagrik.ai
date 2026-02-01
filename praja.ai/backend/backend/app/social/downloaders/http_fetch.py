from __future__ import annotations

import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

def fetch_html(url: str, timeout: int = 20) -> tuple[str, dict]:
    meta = {"url": url, "timeout": timeout}
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        r = client.get(url)
        meta["final_url"] = str(r.url)
        meta["status_code"] = r.status_code
        meta["content_type"] = r.headers.get("content-type", "")
        r.raise_for_status()
        return r.text, meta
