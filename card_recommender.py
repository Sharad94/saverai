import json
import re

from gemini_client import generate, FALLBACK_MODEL

# Pre-computed result for the demo spend profile — returned instantly, no LLM call
DEMO_SPEND = {
    "Food delivery (Swiggy/Zomato)": 4000,
    "Amazon": 6000,
    "Fuel": 3000,
    "Travel (flights/hotels)": 10000,
}

DEMO_RESULT = {
    "top_cards": [
        {
            "bank": "Axis Bank",
            "card": "Magnus Credit Card",
            "network": "Mastercard",
            "annual_fee": 12500,
            "fee_waiver": "Spend ₹15L/year to waive",
            "already_owned": False,
            "estimated_monthly_savings": 2200,
            "estimated_annual_savings": 26400,
            "net_annual_benefit": 13900,
            "category_benefits": [
                {"category": "Travel (flights/hotels)", "benefit": "10x Edge Rewards (≈4% value)", "monthly_saving": 1600},
                {"category": "Amazon", "benefit": "2x on online shopping", "monthly_saving": 360},
                {"category": "Food delivery", "benefit": "2x on dining & delivery", "monthly_saving": 240},
            ],
            "key_tnc": ["10x capped at 25,000 Edge Miles/month", "₹10,000 gift voucher milestone at ₹7.5L annual spend"],
            "why": "Best card for high travel spend — 10x rewards cover the annual fee within 2 months of travel",
        },
        {
            "bank": "BPCL SBI",
            "card": "Octane Credit Card",
            "network": "Visa",
            "annual_fee": 1499,
            "fee_waiver": "Spend ₹2L/year to waive",
            "already_owned": False,
            "estimated_monthly_savings": 520,
            "estimated_annual_savings": 6240,
            "net_annual_benefit": 4741,
            "category_benefits": [
                {"category": "Fuel", "benefit": "7.25% value back on BPCL (6.25% rewards + 1% surcharge waiver)", "monthly_saving": 217},
                {"category": "Amazon", "benefit": "5x rewards on grocery & dining", "monthly_saving": 303},
            ],
            "key_tnc": ["Fuel rewards capped at 6,250 points/month", "Redemption only against BPCL fuel or statement credit"],
            "why": "Fills the fuel gap in your portfolio — no other card you own gives meaningful fuel rewards",
        },
        {
            "bank": "American Express",
            "card": "Platinum Travel Credit Card",
            "network": "Amex",
            "annual_fee": 5000,
            "fee_waiver": "",
            "already_owned": False,
            "estimated_monthly_savings": 1100,
            "estimated_annual_savings": 13200,
            "net_annual_benefit": 8200,
            "category_benefits": [
                {"category": "Travel (flights/hotels)", "benefit": "5x Membership Rewards on travel", "monthly_saving": 700},
                {"category": "Amazon", "benefit": "1x on all other spends + milestone vouchers", "monthly_saving": 400},
            ],
            "key_tnc": ["₹10,000 Taj/IndiGo voucher on ₹4L spend; ₹20,000 on ₹7.5L", "Amex acceptance lower than Visa/MC at smaller merchants"],
            "why": "Milestone travel vouchers worth ₹20,000/year make this a high-value complement for your travel spend",
        },
    ],
    "best_combo": {
        "cards": ["Axis Magnus", "BPCL SBI Octane"],
        "combined_monthly_savings": 2720,
        "combined_annual_savings": 32640,
        "combined_annual_fees": 13999,
        "net_annual_benefit": 18641,
        "split": [
            {"card": "Axis Magnus", "use_for": ["Travel (flights/hotels)", "Amazon", "Food delivery"], "monthly_saving": 2200},
            {"card": "BPCL SBI Octane", "use_for": ["Fuel"], "monthly_saving": 520},
        ],
        "why": "Magnus dominates travel and online; Octane fills the fuel gap — together they cover every category at maximum reward rate",
    },
}

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


DEMO_SPEND_2 = {
    "Food delivery (Swiggy/Zomato)": 4000,
    "Amazon": 6000,
    "Fuel": 3000,
    "Travel (flights/hotels)": 2000,
    "Dining out": 8000,
}

DEMO_RESULT_2 = {
    "top_cards": [
        {
            "bank": "American Express",
            "card": "Membership Rewards Credit Card",
            "network": "Amex",
            "annual_fee": 1500,
            "fee_waiver": "Spend ₹1.5L/year to waive",
            "already_owned": False,
            "estimated_monthly_savings": 580,
            "estimated_annual_savings": 6960,
            "net_annual_benefit": 5460,
            "category_benefits": [
                {"category": "Dining out", "benefit": "5x Membership Rewards on weekends + select restaurants", "monthly_saving": 400},
                {"category": "Amazon", "benefit": "5x on Amazon & BigBasket on select days", "monthly_saving": 180},
            ],
            "key_tnc": ["5x capped at 2,500 bonus MR points/month", "MR points expire if card is closed"],
            "why": "Best dining card in India — 5x weekend multiplier on restaurants turns ₹8k dining into real rewards",
        },
        {
            "bank": "SBI Card",
            "card": "Cashback Credit Card",
            "network": "Visa",
            "annual_fee": 999,
            "fee_waiver": "Spend ₹2L/year to waive",
            "already_owned": False,
            "estimated_monthly_savings": 500,
            "estimated_annual_savings": 6000,
            "net_annual_benefit": 5001,
            "category_benefits": [
                {"category": "Amazon", "benefit": "5% cashback on all online transactions", "monthly_saving": 300},
                {"category": "Dining out", "benefit": "5% cashback on online food orders & dining apps", "monthly_saving": 200},
            ],
            "key_tnc": ["5% capped at ₹5,000 cashback/month", "Cashback credited as statement credit next cycle"],
            "why": "Flat 5% on all online spends with no merchant restriction — covers Amazon and online dining seamlessly",
        },
        {
            "bank": "BPCL SBI",
            "card": "Octane Credit Card",
            "network": "Visa",
            "annual_fee": 1499,
            "fee_waiver": "Spend ₹2L/year to waive",
            "already_owned": False,
            "estimated_monthly_savings": 520,
            "estimated_annual_savings": 6240,
            "net_annual_benefit": 4741,
            "category_benefits": [
                {"category": "Fuel", "benefit": "7.25% value back on BPCL (6.25% rewards + 1% surcharge waiver)", "monthly_saving": 217},
                {"category": "Amazon", "benefit": "5x rewards on grocery & dining", "monthly_saving": 303},
            ],
            "key_tnc": ["Fuel rewards capped at 6,250 points/month", "Redemption only against BPCL fuel or statement credit"],
            "why": "Fills the fuel gap — no other card in your wallet gives meaningful rewards on petrol",
        },
    ],
    "best_combo": {
        "cards": ["Amex Membership Rewards", "SBI Cashback"],
        "combined_monthly_savings": 1080,
        "combined_annual_savings": 12960,
        "combined_annual_fees": 2499,
        "net_annual_benefit": 10461,
        "split": [
            {"card": "Amex Membership Rewards", "use_for": ["Dining out"], "monthly_saving": 580},
            {"card": "SBI Cashback", "use_for": ["Amazon", "Food delivery (Swiggy/Zomato)"], "monthly_saving": 500},
        ],
        "why": "Amex maximises dining rewards; SBI Cashback covers all online spends at flat 5% — together they eliminate your two biggest spend gaps",
    },
}


def recommend_cards(spend: dict, owned_cards: list[dict]) -> dict:
    if spend == DEMO_SPEND:
        return DEMO_RESULT
    if spend == DEMO_SPEND_2:
        return DEMO_RESULT_2

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
