from parser import _detect_media_type, _extract_json
from gemini_client import generate, image_part

_BENEFITS_SCHEMA = """{
  "bank_name": "e.g. HDFC, Axis, SBI, ICICI, Kotak, Amex",
  "card_name": "e.g. Regalia, Flipkart, Magnus, SimplyCLICK",
  "card_network": "Visa | Mastercard | Amex | Rupay | null",
  "benefits": [
    {
      "category": "One of: shopping, food, travel, fuel, groceries, entertainment, electronics, fashion, health, utilities, all",
      "platforms": ["specific platforms/merchants, or empty for all"],
      "reward_type": "cashback | points | miles | discount | waiver",
      "reward_rate": "<number — percentage or points per ₹100>",
      "reward_label": "Human readable e.g. '5% cashback' or '10X reward points'",
      "cap_per_month": "<max INR per month or null>",
      "min_transaction": "<min transaction INR or null>",
      "notes": "Any conditions"
    }
  ]
}"""

CARD_PARSE_PROMPT = f"""You are a credit card benefits extraction assistant. Analyze this image and extract all card details and benefits.

Return ONLY a JSON object with this structure:
{_BENEFITS_SCHEMA}

Extract ALL benefits visible. Only return the JSON, no other text."""

CARD_NAME_PROMPT = """You are an expert on Indian credit cards. Generate a complete and accurate structured JSON for the {bank_name} {card_name}.

{description_section}

Return ONLY a JSON object with this structure:
{schema}

Include ALL meaningful benefits: cashback rates, reward points, lounge access, co-brand perks, fuel waiver, milestone rewards, welcome benefits. Be specific with numbers and platforms. Only return the JSON, no other text."""


def parse_card_benefits(image_bytes: bytes) -> dict:
    media_type = _detect_media_type(image_bytes)
    return _extract_json(generate([image_part(image_bytes, media_type), CARD_PARSE_PROMPT]))


def parse_card_from_name(bank_name: str, card_name: str, description: str = "") -> dict:
    """Generate structured card benefits from card name using Gemini knowledge."""
    desc_section = (
        f"The user has provided this additional context about the card:\n{description}\n"
        if description.strip() else ""
    )
    prompt = CARD_NAME_PROMPT.format(
        bank_name=bank_name,
        card_name=card_name,
        description_section=desc_section,
        schema=_BENEFITS_SCHEMA,
    )
    return _extract_json(generate(prompt))
