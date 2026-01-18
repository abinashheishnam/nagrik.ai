import re

def summarize(title: str, description: str, category: str, priority: str, address: str = "") -> str:
    desc = re.sub(r"\s+", " ", (description or "").strip())
    short = desc
    if len(short) > 180:
        short = short[:177].rstrip() + "..."

    loc = f" Location: {address}." if address else ""
    return f"{category} issue reported: {title}. {short}{loc} Priority assessed as {priority}."
