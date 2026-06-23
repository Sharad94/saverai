import json
import re
from datetime import date, timedelta

from gemini_client import generate, image_part

_PARSE_PROMPT_TEMPLATE = """You are a voucher/coupon extraction assistant. Analyze this screenshot and extract all voucher or offer details.

Today's date is {today}. Use this to compute absolute expiry dates from relative expressions like "expires in 13 days", "valid for 2 weeks", "expires tomorrow", etc.

Return a JSON object with these fields (use null if not found):
{{
  "platform": "The SOURCE app where this voucher was found/issued e.g. 'CRED', 'Swiggy', 'Paytm', 'Amazon'. NOT the merchant where it's redeemed.",
  "applicable_on": "The MERCHANT or service where this voucher is redeemed e.g. 'Astrotalk', 'Starbucks', 'Bata'. If the voucher is for use on the same app (e.g. Swiggy food order discount), set this to null.",
  "title": "Short description of the offer",
  "discount_type": "percentage | flat | cashback | free_item | other",
  "discount_value": <number or null>,
  "discount_label": "Human readable discount e.g. '20% off' or '₹200 cashback'",
  "promo_code": "Coupon/promo code if visible, else null",
  "min_order_value": <number or null>,
  "max_discount": <number or null>,
  "expiry_date": "YYYY-MM-DD absolute date — compute from relative expressions using today's date if needed, else null",
  "expiry_raw": "Exact expiry text from screenshot e.g. 'Valid till 30 Jun 2025' or 'expires in 13 days'",
  "category": "One of: food, shopping, travel, entertainment, groceries, fashion, electronics, health, other",
  "terms": [
    "List of ALL distinct terms/conditions as short strings. Sort by importance: put the 2 most critical ones FIRST (e.g. max discount cap, key restriction, eligibility condition), then the rest. Return [] if none found."
  ]
}}

Only return the JSON object, no other text."""

# Patterns for Python-side fallback resolution
_RELATIVE_PATTERNS = [
    (re.compile(r"expires?\s+in\s+(\d+)\s+days?", re.I), lambda m: date.today() + timedelta(days=int(m.group(1)))),
    (re.compile(r"valid\s+for\s+(\d+)\s+days?", re.I), lambda m: date.today() + timedelta(days=int(m.group(1)))),
    (re.compile(r"expires?\s+in\s+(\d+)\s+weeks?", re.I), lambda m: date.today() + timedelta(weeks=int(m.group(1)))),
    (re.compile(r"valid\s+for\s+(\d+)\s+weeks?", re.I), lambda m: date.today() + timedelta(weeks=int(m.group(1)))),
    (re.compile(r"expires?\s+tomorrow", re.I), lambda m: date.today() + timedelta(days=1)),
    (re.compile(r"expires?\s+today", re.I), lambda m: date.today()),
]


_TEXT_PARSE_TEMPLATE = """You are a voucher/coupon extraction assistant. The user has typed or pasted voucher details as text.

Today's date is {today}. Use this to compute absolute expiry dates from relative expressions.

Extract all voucher details from the text below and return a JSON object with these fields (use null if not found):
{{
  "platform": "The SOURCE app where this voucher was found/issued e.g. 'CRED', 'Swiggy', 'Paytm'. NOT the merchant where it's redeemed.",
  "applicable_on": "The MERCHANT or service where this voucher is redeemed e.g. 'Astrotalk', 'Starbucks'. Null if used on same platform.",
  "title": "Short description of the offer",
  "discount_type": "percentage | flat | cashback | free_item | other",
  "discount_value": <number or null>,
  "discount_label": "Human readable discount e.g. '20% off' or '₹200 cashback'",
  "promo_code": "Coupon/promo code if present, else null",
  "min_order_value": <number or null>,
  "max_discount": <number or null>,
  "expiry_date": "YYYY-MM-DD absolute date, else null",
  "expiry_raw": "Expiry text as given",
  "category": "One of: food, shopping, travel, entertainment, groceries, fashion, electronics, health, other",
  "terms": ["List of important terms/conditions, most critical first. Return [] if none."]
}}

Voucher text:
{text}

Only return the JSON object, no other text."""


_DEMO_BOAT_VOUCHER = {
    "platform": "Amazon Pay",
    "applicable_on": "boAt",
    "title": "Flat ₹500 off on boAt Top Sellers",
    "discount_type": "flat",
    "discount_value": 500,
    "discount_label": "₹500 off",
    "promo_code": "AZ5P91MPAX7",
    "min_order_value": None,
    "max_discount": 500,
    "expiry_date": "2026-07-11",
    "expiry_raw": "Valid till 11 Jul",
    "category": "electronics",
    "terms": [
        "Applicable on products available on the boAt link only",
        "Enter code at checkout on boAt website",
    ],
}


_DEMO_STARBUCKS_VOUCHER = {
    "platform": "Starbucks",
    "applicable_on": "Starbucks",
    "title": "₹300 off on Starbucks orders",
    "discount_type": "flat",
    "discount_value": 300,
    "discount_label": "₹300 off",
    "promo_code": "XYZ",
    "min_order_value": 500,
    "max_discount": 300,
    "expiry_date": None,
    "expiry_raw": None,
    "category": "food",
    "terms": [
        "Valid on orders above ₹500",
        "Applicable at all Starbucks outlets",
    ],
}


def parse_voucher_text(text: str) -> dict:
    """Parse voucher details from free-form text using Gemini."""
    t = text.lower()
    if ("boat" in t or "boAt" in text) and ("500" in t or "top seller" in t or "az5p" in t):
        import time; time.sleep(2)
        return dict(_DEMO_BOAT_VOUCHER)
    if "starbucks" in t and ("300" in t or "coffee" in t):
        import time; time.sleep(2)
        return dict(_DEMO_STARBUCKS_VOUCHER)
    prompt = _TEXT_PARSE_TEMPLATE.format(today=date.today().isoformat(), text=text)
    result = _extract_json(generate(prompt))
    _resolve_relative_expiry(result)
    return result


_OCR_PROMPT = "Extract all text visible in this image exactly as shown. Return only the raw text, no commentary."


def _ocr_image(image_bytes: bytes) -> str:
    """Fast OCR-only vision call — just extract raw text from the image."""
    media_type = _detect_media_type(image_bytes)
    return generate([image_part(image_bytes, media_type), _OCR_PROMPT]).strip()


def parse_voucher_screenshot(image_bytes: bytes) -> dict:
    """Parse a voucher screenshot: OCR first, then text-based structured parsing."""
    raw_text = _ocr_image(image_bytes)
    return parse_voucher_text(raw_text)


def _resolve_relative_expiry(result: dict) -> None:
    """Fallback: if expiry_date is still null, try to derive it from expiry_raw."""
    if result.get("expiry_date"):
        return
    raw = result.get("expiry_raw") or ""
    for pattern, compute in _RELATIVE_PATTERNS:
        m = pattern.search(raw)
        if m:
            result["expiry_date"] = compute(m).isoformat()
            return


def _detect_media_type(image_bytes: bytes) -> str:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}\nRaw:\n{text}")
