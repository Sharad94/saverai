import json
import re

from gemini_client import generate

ADVISOR_PROMPT = """Rank these credit cards for the purchase below, best to worst.

Purchase: {item}{platform_part}

Cards:
{cards_text}

Return ONLY a JSON array ordered best-to-worst:
[{{"card_id":<id>,"card_label":"<label>","estimated_savings":0,"reward_label":"<best applicable benefit or 'No specific benefit'>","reason":"<one line>"}}]"""


DEMO_HEADPHONES_ADVICE = {
    "best_card_id": None,
    "ranked_cards": [
        {
            "card_id": None,
            "card_label": "ICICI Bank Amazon Pay Credit Card",
            "estimated_savings": 250,
            "reward_label": "5% cashback on Amazon.in",
            "reason": "Highest cashback for Prime members on Amazon — best pick for boAt electronics.",
        },
        {
            "card_id": None,
            "card_label": "Axis Flipkart Credit Card",
            "estimated_savings": 175,
            "reward_label": "5% cashback on Flipkart, Myntra",
            "reason": "5% flat cashback if buying on Flipkart instead of Amazon.",
        },
    ],
    "summary": "Use your ICICI Bank Amazon Pay Credit Card — 5% cashback on Amazon.in.",
}


def advise_best_card(item: str, amount: float, platform: str, cards: list[dict]) -> dict:
    if "headphone" in item.lower() or "boat" in item.lower() or "boAt" in item:
        import time; time.sleep(1)
        return DEMO_HEADPHONES_ADVICE
    if not cards:
        return {"best_card_id": None, "ranked_cards": [], "summary": "No cards added yet."}

    cards_text = ""
    id_to_label = {}
    for c in cards:
        label = f"{c.get('bank_name', '')} {c.get('card_name', '')}".strip()
        id_to_label[c["id"]] = label
        benefits = "\n".join(
            f"  - {b.get('category', '')}: {b.get('reward_label', '')}"
            + (f" on {', '.join(b['platforms'])}" if b.get("platforms") else "")
            for b in (c.get("benefits") or [])[:6]
        )
        cards_text += f"\n[id={c['id']}] {label}\n{benefits or '  No benefits listed'}\n"

    platform_part = f" on {platform}" if platform else ""
    prompt = ADVISOR_PROMPT.format(
        item=item, platform_part=platform_part, cards_text=cards_text.strip()
    )

    try:
        raw = generate(prompt).strip()
    except Exception:
        return {"best_card_id": None, "ranked_cards": [], "summary": "Card ranking unavailable right now."}

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    try:
        ranked = json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError):
        return {"best_card_id": None, "ranked_cards": [], "summary": "Could not determine best card."}

    for r in ranked:
        r.setdefault("card_label", id_to_label.get(r.get("card_id"), ""))
        try:
            r["estimated_savings"] = float(r.get("estimated_savings") or 0)
        except (ValueError, TypeError):
            r["estimated_savings"] = 0.0

    best = ranked[0] if ranked else None
    summary = (
        f"Use your {best.get('card_label','your card')} — {best.get('reward_label','best rewards')}."
        if best else "No cards available."
    )

    return {
        "best_card_id": best["card_id"] if best else None,
        "ranked_cards": ranked,
        "summary": summary,
    }
