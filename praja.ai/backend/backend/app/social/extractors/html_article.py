from __future__ import annotations

from bs4 import BeautifulSoup

def extract_article(html: str) -> tuple[str, dict]:
    soup = BeautifulSoup(html, "html.parser")

    # remove junk
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    title = (soup.title.string.strip() if soup.title and soup.title.string else "")

    # Prefer article-like containers
    candidates: list[str] = []
    for sel in ["article", "main", "div#content", "div.post", "div.entry-content", "div.article-body"]:
        for node in soup.select(sel):
            txt = node.get_text("\n", strip=True)
            if txt and len(txt) > 200:
                candidates.append(txt)

    if candidates:
        text = max(candidates, key=len)
    else:
        text = soup.get_text("\n", strip=True)

    # normalize
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    meta = {"title": title, "text_len": len(cleaned)}
    return cleaned, meta
