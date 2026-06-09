# SaverAI — AI in Action FY27 Q2 Competition Notes

## Competition Details

- **Theme:** From Insight to Impact
- **Submission deadline:** June 26, 2026 (end of day)
- **Judging period:** June 29 – July 10
- **Winners announced:** July 14 at Town Hall
- **Submission format:** 5-minute max demo/concept video (solo or team of up to 3)
- **Submit via:** https://forms.office.com/r/J3eLPfD8a3
- **Slack:** #ai-in-action

### Judges (FY27 Q2)
- Arun Rajamanickam (VP, Engineering)
- Kean Fichera (Director, AI Operations)
- Matthew Blackert (Manager, Security Operations Center)
- Veronica Giannopoulos (Principal Product Designer + FY27 Q1 AIA Winner)
- Vinay Jain (Data Scientist + FY27 Q1 AIA Winner)

### Prizes
| Place | Prize |
|---|---|
| 1st | Passport44 Global Work Exchange ($2,000 stipend) OR Meta Smart Glasses |
| 2nd | Apple iPad 11" 128GB (~$350) OR $300 Apple Gift Card |
| 3rd | AirPods 4 OR p44 Swag OR $150 Amazon Gift Card |

---

## The Idea: SaverAI

**Tagline:** "Tell me what you're buying. I'll tell you which card to use and which voucher to apply."

**Category:** AI @ Home

### Problem
- Vouchers from apps like Amazon, GPay, Swiggy etc. are scattered, forgotten, and expire unused
- People with multiple credit cards don't know which one gives the best benefit for each purchase
- No single tool solves both problems together — especially for the Indian market

### Solution
A web app (mobile-responsive) where you:
1. Upload screenshots of vouchers → AI extracts platform, discount, expiry, promo code
2. Upload credit card benefits page → AI extracts reward rates per category
3. Before any purchase, type what you're buying + amount → app shows:
   - **Best card to swipe** (with estimated savings)
   - **Matching vouchers** you already have (that apply to that purchase)

### The Demo Moment (for the video)
> "I want to buy Sony headphones for ₹15,000 on Amazon"
> → Best card: HDFC Regalia — 5% cashback = ₹750 saved
> → Voucher: Amazon 10% off expiring in 2 days = ₹1,500 saved
> → Total savings surfaced in one search: ₹2,250

---

## Competition Fit Analysis

### Past AI @ Home Winners
| Quarter | Place | Project | Domain |
|---|---|---|---|
| Q1 2026 | 🥇 | Lumina AI Expense Manager | Personal finance / budgeting |
| Q1 2026 | 🥈 | PromptArena | Gamified AI literacy |
| Q1 2026 | 🥉 | CallGuard AI | Unknown |
| Q4 2025 | 🥇 | ShopWhiz – AI That Runs Your Store | Small retail |
| Q4 2025 | 🥈 | Becoming: A Productive Agentic Tool | Knowledge / learning |
| Q4 2025 | 🥉 | Sakhi AI | Women's wellness |
| Q3 2025 | 🥇 | Atelier.AI – Style Made Simple | Personal styling |
| Q3 2025 | 🥈 | Together Spend AI | Household spending |
| Q3 2025 | 🥉 | Google AI Studio: Your Personal Genius | Productivity |
| Q2 2025 | 🥇 | Smart Home AI Companion | Home automation |
| Q2 2025 | 🥈 | Everyday AI Helper | Personal productivity |

**Key observations:**
- Finance/savings tools have won before (Lumina, Together Spend AI) — judges like this domain
- No one has done voucher management specifically
- Most past entries appear to be web apps — a mobile-responsive app stands out
- Pattern of winners: practical, personal, universally relatable, easy to demo

### Competitive Landscape (External Apps)

**Voucher/Coupon Apps**
| App | What it does | Our advantage |
|---|---|---|
| **Vouchet: Your Voucher Vault** (Snorlytics) | Camera scan + on-device OCR extracts expiry/discount/store, expiry alerts, location notifications, barcode display | Only 100+ downloads (barely launched); on-device OCR fails on stylised UIs (GPay, Swiggy); no credit card advisor; no semantic search; Singapore-focused |
| **Gutscheinify** | Photo → AI extracts voucher, expiry reminders, loyalty cards | 🇩🇪 Germany only, no credit card advisor, no semantic search, no Indian apps |
| Gift Card Balance Checker | QR/barcode scan, expiry reminders | No AI, no screenshot parsing, no semantic search |
| CouponScan | Scans physical coupons | No AI extraction |
| Vouchery | Enterprise voucher mgmt | Not a personal app |

**Closest competitor: Vouchet.** It overlaps most on the voucher scanning angle. Key differentiators against it:
- We use cloud AI (Gemini) vs on-device OCR — handles messy/stylised screenshots from GPay, Swiggy, Zomato etc. that OCR struggles with
- Credit card advisor is entirely absent in Vouchet
- Combined card + voucher smart search is unique to SaverAI
- India-first vs Singapore-first

**Credit Card Advisor Apps**
| App | What it does | Our advantage |
|---|---|---|
| CardPointers | Best card per purchase, AR feature, free | US cards only |
| MaxRewards | Auto-activates bonus categories | US cards only |
| AwardWallet | Merchant lookup for best card | US cards only |

**Key differentiators:**
1. **Indian market focus** — Indian credit cards (HDFC, Axis, SBI, Kotak) + Indian voucher apps (GPay, Swiggy, Zomato, Amazon IN, Myntra)
2. **Cloud AI vs on-device OCR** — Gemini handles stylised/complex screenshots (GPay, Swiggy) that basic OCR fails on
3. **Combined** voucher + card advisor in one search — no existing app does both
4. **Semantic search** — "I want to buy groceries" finds relevant vouchers, not just keyword match

**One-line pitch:** *"Vouchet does voucher scanning with basic OCR. CardPointers does card advice but only for the US. SaverAI uses cloud AI to handle any screenshot — and is the only app that combines both into one search, built for India."*

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| AI (Vision + Text) | Gemini 2.0 Flash via Google Vertex AI | Free via p44's GCP (`hackathon-2025-450908`), handles images + text |
| Backend / Frontend | Streamlit (Python) | Matches user's Python background, fastest to build |
| Database + Storage | Supabase (free tier) | Stores voucher/card data + screenshot images |
| Auth (GCP) | gcloud ADC (already configured) | No API key needed, uses p44 SSO |
| Deployment | Local (for demo video) / Streamlit Cloud | No server needed for competition |

### GCP Details
- **Project:** `hackathon-2025-450908`
- **Region:** `us-central1`
- **Model:** `gemini-2.0-flash-001`
- **Auth:** `gcloud auth application-default login` (already done)

---

## Project Structure

```
voucher-vault/
├── app.py              # Streamlit UI — 5 tabs
├── gemini_client.py    # Shared Gemini/Vertex AI initialisation
├── parser.py           # Voucher screenshot → structured JSON (Gemini Vision)
├── card_parser.py      # Card benefits screenshot → structured JSON (Gemini Vision)
├── card_advisor.py     # Best card recommendation for a purchase (Gemini)
├── search.py           # Semantic voucher search (Gemini)
├── database.py         # Supabase CRUD for vouchers + cards
├── supabase_schema.sql # Run once in Supabase SQL editor
├── requirements.txt
└── .env                # SUPABASE_URL + SUPABASE_KEY only (no AI key needed)
```

### App Tabs
1. **🎯 Smart Advisor** — main feature: type purchase → get best card + matching vouchers
2. **➕ Add Voucher** — upload screenshot → AI extracts + saves
3. **💳 Add Card** — upload benefits screenshot → AI extracts + saves
4. **🎟️ My Vouchers** — list all vouchers, mark used, delete
5. **💳 My Cards** — list all cards, delete

---

## Remaining Setup Steps

- [ ] Create Supabase project at https://supabase.com
- [ ] Run `supabase_schema.sql` in Supabase SQL editor
- [ ] Create two storage buckets: `voucher-screenshots` and `card-screenshots` (both Public)
- [ ] Add Supabase URL + key to `.env`
- [ ] Run: `venv/bin/streamlit run app.py`
- [ ] Test with real voucher screenshot
- [ ] Test with real credit card benefits screenshot
- [ ] Record 5-minute demo video
- [ ] Submit via https://forms.office.com/r/J3eLPfD8a3

---

## Demo Video Flow (Suggested)

1. **(0:00–0:30)** Hook — "I just got a voucher on Amazon. I have 4 credit cards. I have no idea which to use or even remember the voucher exists."
2. **(0:30–1:30)** Upload a voucher screenshot → show AI extracting details instantly
3. **(1:30–2:30)** Upload a credit card benefits screenshot → show AI extracting reward structure
4. **(2:30–4:00)** Smart Advisor demo — type "Sony headphones ₹15,000 on Amazon" → show card ranking + voucher surfaced together
5. **(4:00–4:30)** Show expiry alert on a nearly-expired voucher
6. **(4:30–5:00)** Close with impact — "Zero manual entry. Any card. Any voucher app. India-first."
