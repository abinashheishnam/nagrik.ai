from __future__ import annotations

import time
import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

ALT_HEADERS = {
    # Some sites behave better with a simpler accept header
    **BROWSER_HEADERS,
    "Accept": "text/html,*/*;q=0.8",
}

def fetch_html(url: str, timeout: int = 20, retries: int = 2) -> tuple[str, dict]:
    """
    Fetch HTML with browser-ish headers and small retries.
    Returns (html, meta). Raises httpx.HTTPError on hard failure.
    """
    meta = {"url": url, "timeout": timeout, "retries": retries}

    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        headers = BROWSER_HEADERS if attempt == 0 else ALT_HEADERS
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
                r = client.get(url)

                meta["attempt"] = attempt
                meta["final_url"] = str(r.url)
                meta["status_code"] = r.status_code
                meta["content_type"] = r.headers.get("content-type", "")

                # If server is unhappy (5xx), retry once
                if 500 <= r.status_code < 600:
                    last_exc = httpx.HTTPStatusError(
                        f"server_{r.status_code}",
                        request=r.request,
                        response=r,
                    )
                    # small backoff
                    time.sleep(0.7 * (attempt + 1))
                    continue

                # If blocked/unauthorized, still return HTML so caller can detect login walls
                if r.status_code in (401, 403, 429):
                    meta["blocked_status"] = r.status_code
                    return r.text, meta

                r.raise_for_status()
                return r.text, meta

        except Exception as e:
            last_exc = e
            time.sleep(0.5 * (attempt + 1))
            continue

    # exhausted retries
    assert last_exc is not None
    raise last_exc
