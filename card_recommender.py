import json
import re

from gemini_client import generate

RECOMMEND_PROMPT = """You are an expert Indian credit card advisor. A user wants to know which credit card(s) to GET based on their monthly spending.

Monthly spend profile:
{spend_profile}

Cards they already own:
{owned_cards}

Analyse this spend profile and recommend:
1. The TOP 3 individual cards to get (Indian market, 2024-2025)
2. The BEST 2-card combo that maximises savings across all categories

For each card consider: cashback/rewards rate per category, annual fee, welcome benefits, and whether the annual fee is justified by the savings.

Return ONLY this JSON:
{{
  "top_cards": [
    {{
      "bank": "e.g. HDFC Bank",
      "card": "e.g. Millennia Credit Card",
      "network": "Visa/Mastercard/Amex/Rupay",
      "annual_fee": 1000,
      "fee_waiver": "Spend ₹1L/year to waive",
      "already_owned": false,
      "estimated_monthly_savings": 850,
      "estimated_annual_savings": 10200,
      "net_annual_benefit": 9200,
      "category_benefits": [
        {{"category": "Food delivery", "benefit": "5% cashback on Swiggy & Zomato", "monthly_saving": 250}},
        {{"category": "Amazon", "benefit": "5% cashback", "monthly_saving": 300}}
      ],
      "key_tnc": ["Cashback capped at ₹1000/month", "Min transaction ₹2000"],
      "why": "One line reason this card suits their spend profile"
    }}
  ],
  "best_combo": {{
    "cards": ["HDFC Millennia", "Axis Flipkart"],
    "combined_monthly_savings": 1400,
    "combined_annual_savings": 16800,
    "combined_annual_fees": 2000,
    "net_annual_benefit": 14800,
    "split": [
      {{"card": "HDFC Millennia", "use_for": ["Amazon", "Food delivery"], "monthly_saving": 800}},
      {{"card": "Axis Flipkart", "use_for": ["Flipkart", "Myntra"], "monthly_saving": 600}}
    ],
    "why": "One line reason this combo maximises their savings"
  }}
}}"""


def recommend_cards(spend: dict, owned_cards: list[dict]) -> dict:
    spend_profile = "\n".join(
        f"- {cat}: ₹{amt:,.0f}/month" for cat, amt in spend.items() if amt > 0
    )
    owned = ", ".join(
        f"{c.get('bank_name')} {c.get('card_name')}" for c in owned_cards
    ) or "None"

    prompt = RECOMMEND_PROMPT.format(spend_profile=spend_profile, owned_cards=owned)
    raw = generate(prompt).strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    try:
        return json.loads(raw.strip())
    except (json.JSONDecodeError, ValueError):
        return {"top_cards": [], "best_combo": None}
