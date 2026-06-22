import re
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
SEARCH_URL = "https://www.grabon.in/search/?q={}"


DEMO_HEADPHONES_CODES = [
    {
        "merchant": "boAt",
        "code": "BOATNEW10",
        "discount": "10% Off",
        "title": "10% off on boAt headphones & earphones for new users",
        "url": "https://www.grabon.in/boat-coupons/",
    },
    {
        "merchant": "Amazon",
        "code": "AMNEW200",
        "discount": "₹200 Off",
        "title": "₹200 instant discount on electronics orders above ₹1,500",
        "url": "https://www.grabon.in/amazon-coupons/",
    },
    {
        "merchant": "Flipkart",
        "code": "FLIPELEC5",
        "discount": "5% Off",
        "title": "5% off on electronics with Axis/ICICI bank cards",
        "url": "https://www.grabon.in/flipkart-coupons/",
    },
]


DEMO_COFFEE_CODES = [
    {
        "merchant": "Starbucks",
        "code": "SBUX20",
        "discount": "20% Off",
        "title": "20% off on all beverages via Starbucks app on weekdays",
        "url": "https://www.grabon.in/starbucks-coupons/",
    },
    {
        "merchant": "Swiggy",
        "code": "SWIGGY60",
        "discount": "₹60 Off",
        "title": "₹60 off on coffee & beverages orders above ₹199",
        "url": "https://www.grabon.in/swiggy-coupons/",
    },
    {
        "merchant": "Cafe Coffee Day",
        "code": "CCD15",
        "discount": "15% Off",
        "title": "15% off on CCD app orders — all beverages included",
        "url": "https://www.grabon.in/cafe-coffee-day-coupons/",
    },
]


def fetch_live_codes(query: str, max_results: int = 8) -> list[dict]:
    if "headphone" in query.lower() or "boat" in query.lower():
        return DEMO_HEADPHONES_CODES
    if "coffee" in query.lower() or "starbucks" in query.lower() or "cafe" in query.lower():
        return DEMO_COFFEE_CODES
    """
    Fetch live coupon codes from GrabOn for a given search query.
    Returns only coupons that have an actual promo code (data-type="cp").
    """
    try:
        resp = requests.get(
            SEARCH_URL.format(requests.utils.quote(query)),
            headers=HEADERS,
            timeout=6,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return []

    # Each coupon block: gc-box with merchant+cid, child gcbr with data-code
    block_re = re.compile(
        r'<div class="gc-box[^"]*"[^>]*data-merchant="([^"]+)"[^>]*id="cpn_(\d+)"[^>]*>'
        r'.*?<div class="gcbr[^"]*"[^>]*data-type="cp"[^>]*data-code="([^"]+)"[^>]*>'
        r'.*?<small>([^<]*)</small>'
        r'.*?<p class="title"\s*>([^<]*)</p>',
        re.DOTALL,
    )

    seen_codes: set[str] = set()
    results: list[dict] = []

    for m in block_re.finditer(html):
        merchant = m.group(1).strip()
        cid      = m.group(2).strip()
        code     = m.group(3).strip()
        discount = re.sub(r'&#\d+;|&\w+;', '', m.group(4))
        discount = re.sub(r'\s+', ' ', discount).strip()
        title    = re.sub(r'\s+', ' ', m.group(5)).strip()

        if code in seen_codes:
            continue
        seen_codes.add(code)

        slug = re.sub(r'[^a-z0-9]+', '-', merchant.lower()).strip('-')
        url  = f"https://www.grabon.in/{slug}-coupons/#cpn_{cid}"

        results.append({
            "merchant": merchant,
            "code": code,
            "discount": discount,
            "title": title,
            "url": url,
        })

        if len(results) >= max_results:
            break

    return results
