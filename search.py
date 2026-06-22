import json
import re

from gemini_client import generate

SEARCH_PROMPT = """You are a voucher search assistant. Return only vouchers that are genuinely relevant to the user's query.

Rules:
- If the query mentions a specific platform or merchant (e.g. "Zomato", "Amazon"), only return vouchers for that exact platform/merchant. Do NOT return vouchers from unrelated platforms even if the category is similar.
- If the query is a category (e.g. "food", "electronics"), return vouchers from any platform in that category.
- Exclude vouchers that are clearly unrelated — different platform AND different category.
- Return [] if nothing is a good match. Do not force matches.

User is looking for: "{query}"

Available vouchers:
{vouchers_json}

Return a JSON array of voucher IDs ordered by relevance (most relevant first).
Example: [3, 7, 1]
Only return the JSON array, nothing else."""


def _keyword_fallback(query: str, vouchers: list[dict]) -> list[dict]:
    words = set(query.lower().split())
    def score(v):
        text = " ".join(filter(None, [
            v.get("title", ""), v.get("platform", ""),
            v.get("category", ""), v.get("applicable_on", ""),
        ])).lower()
        return sum(1 for w in words if w in text)
    scored = [(score(v), v) for v in vouchers]
    matched = [v for s, v in scored if s > 0]
    return matched if matched else []


DEMO_KEYWORD_RULES = {
    "headphone": ["headphone", "boat", "boAt", "electronic", "audio", "earphone", "wireless"],
    "coffee":    ["coffee", "starbucks", "cafe", "ccd", "beverage"],
}


def _demo_match(query: str, vouchers: list[dict]) -> list[dict] | None:
    q = query.lower()
    for trigger, keywords in DEMO_KEYWORD_RULES.items():
        if trigger in q:
            matched = [
                v for v in vouchers
                if any(kw in " ".join(filter(None, [
                    v.get("title", ""), v.get("platform", ""),
                    v.get("category", ""), v.get("applicable_on", ""),
                ])).lower() for kw in keywords)
            ]
            return matched or vouchers
    return None


def search_vouchers(query: str, vouchers: list[dict]) -> list[dict]:
    """
    Semantic search over vouchers using Gemini.
    Returns vouchers sorted by relevance to the query.
    """
    if not vouchers:
        return []

    demo = _demo_match(query, vouchers)
    if demo is not None:
        return demo

    slim = [
        {
            "id": v["id"],
            "platform": v.get("platform"),
            "title": v.get("title"),
            "discount_label": v.get("discount_label"),
            "category": v.get("category"),
            "applicable_on": v.get("applicable_on"),
            "expiry_date": str(v["expiry_date"]) if v.get("expiry_date") else None,
        }
        for v in vouchers
    ]

    try:
        raw = generate(SEARCH_PROMPT.format(query=query, vouchers_json=json.dumps(slim, indent=2))).strip()
    except Exception:
        return vouchers

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    try:
        ranked_ids = json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError):
        return vouchers

    id_to_voucher = {v["id"]: v for v in vouchers}
    return [id_to_voucher[vid] for vid in ranked_ids if vid in id_to_voucher]
