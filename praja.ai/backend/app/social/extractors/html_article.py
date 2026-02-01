from __future__ import annotations

from bs4 import BeautifulSoup

def extract_title_and_text(html: str) -> dict:
    """
    Simple HTML -> {title, text, text_len}.
    Stable MVP extractor: removes scripts/styles, prefers <article>.
    """
    soup = BeautifulSoup(html, "lxml")

    # remove noise
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)

    # Prefer <article> if present
    article = soup.find("article")
    root = article if article else (soup.body if soup.body else soup)

    text = root.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    return {
        "title": title,
        "text": cleaned,
        "text_len": len(cleaned),
    }
