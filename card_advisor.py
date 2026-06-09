import json
import re

from gemini_client import generate

ADVISOR_PROMPT = """Rank these credit cards for the purchase below, best to worst.

Purchase: {item}{platform_part}

Cards:
{cards_text}

Return ONLY a JSON array ordered best-to-worst:
[{{"card_id":<id>,"card_label":"<label>","estimated_savings":0,"reward_label":"<best applicable benefit or 'No specific benefit'>","reason":"<one line>"}}]"""


def advise_best_card(item: str, amount: float, platform: str, cards: list[dict]) -> dict:
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

    raw = generate(prompt).strip()
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
