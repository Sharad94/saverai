import json
import re

from gemini_client import generate, FALLBACK_MODEL

RECOMMEND_PROMPT = """Indian credit card advisor. Recommend cards to GET based on monthly spend.

Spend profile:
{spend_profile}

Already owns: {owned_cards}

Return ONLY valid JSON, no markdown:
{{"top_cards":[{{"bank":"","card":"","network":"","annual_fee":0,"fee_waiver":"","already_owned":false,"estimated_monthly_savings":0,"estimated_annual_savings":0,"net_annual_benefit":0,"category_benefits":[{{"category":"","benefit":"","monthly_saving":0}}],"key_tnc":[],"why":""}}],"best_combo":{{"cards":[],"combined_monthly_savings":0,"combined_annual_savings":0,"combined_annual_fees":0,"net_annual_benefit":0,"split":[{{"card":"","use_for":[],"monthly_saving":0}}],"why":""}}}}

Rules:
- top_cards: exactly 3 best Indian cards for this spend (2024-2025), prioritise high net_annual_benefit
- best_combo: best 2-card combination, assign each spend category to the card that maximises reward
- already_owned: true if card is in the owned list
- All rupee values as integers
- key_tnc: max 2 items, most important caps/restrictions only"""


def recommend_cards(spend: dict, owned_cards: list[dict]) -> dict:
    spend_profile = "\n".join(
        f"- {cat}: ₹{amt:,.0f}/month" for cat, amt in spend.items() if amt > 0
    )
    owned = ", ".join(
        f"{c.get('bank_name')} {c.get('card_name')}" for c in owned_cards
    ) or "None"

    prompt = RECOMMEND_PROMPT.format(spend_profile=spend_profile, owned_cards=owned)
    raw = generate(prompt, model=FALLBACK_MODEL).strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    try:
        return json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError) as e:
        import sys
        print(f"[card_recommender] JSON parse failed: {e}\nRaw response:\n{raw[:500]}", file=sys.stderr)
        return {"top_cards": [], "best_combo": None, "_error": str(e)}
