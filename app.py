import base64
import html
import json
import re
from datetime import date

import requests
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from parser import parse_voucher_screenshot, parse_voucher_text
from card_parser import parse_card_benefits, parse_card_from_name
from card_recommender import recommend_cards, DEMO_SPEND, DEMO_SPEND_2
from card_advisor import advise_best_card
from database import (
    save_voucher, get_all_vouchers, mark_used, delete_voucher,
    get_voucher_screenshot, save_card, get_all_cards, delete_card,
    get_card_screenshot,
)
from search import search_vouchers
from grabon import fetch_live_codes

load_dotenv()

st.set_page_config(page_title="SaverAI", page_icon="💰", layout="centered")
THEMES = {
    "🌿 Vault": {
        "bg": "#0a0f0d", "card": "#0f1f1a", "card2": "#122b24",
        "primary": "#059669", "primary_light": "#34d399", "primary_dark": "#047857",
        "accent": "#34d399", "accent_bg": "#052e16",
        "success_bg": "#14532d", "success_fg": "#4ade80", "success_border": "#16a34a44",
        "hero_grad": "linear-gradient(135deg, #0a0f0d 0%, #052e16 50%, #064e3b 100%)",
        "title_grad": "linear-gradient(90deg, #f0f0f0, #34d399)",
    },
    "🌌 Nebula": {
        "bg": "#0f0f13", "card": "#1a1a2e", "card2": "#1e293b",
        "primary": "#7c3aed", "primary_light": "#a78bfa", "primary_dark": "#6d28d9",
        "accent": "#60a5fa", "accent_bg": "#0f3460",
        "success_bg": "#14532d", "success_fg": "#4ade80", "success_border": "#16a34a44",
        "hero_grad": "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        "title_grad": "linear-gradient(90deg, #f0f0f0, #a78bfa)",
    },
    "🧊 Arctic": {
        "bg": "#080f14", "card": "#0c1929", "card2": "#0f2236",
        "primary": "#0891b2", "primary_light": "#22d3ee", "primary_dark": "#0e7490",
        "accent": "#22d3ee", "accent_bg": "#082f49",
        "success_bg": "#14532d", "success_fg": "#4ade80", "success_border": "#16a34a44",
        "hero_grad": "linear-gradient(135deg, #080f14 0%, #082f49 50%, #0c4a6e 100%)",
        "title_grad": "linear-gradient(90deg, #f0f0f0, #22d3ee)",
    },
    "🖤 Carbon": {
        "bg": "#0a0c0f", "card": "#141820", "card2": "#1c2230",
        "primary": "#64748b", "primary_light": "#94a3b8", "primary_dark": "#475569",
        "accent": "#cbd5e1", "accent_bg": "#1e293b",
        "success_bg": "#14532d", "success_fg": "#4ade80", "success_border": "#16a34a44",
        "hero_grad": "linear-gradient(135deg, #0a0c0f 0%, #1e293b 50%, #334155 100%)",
        "title_grad": "linear-gradient(90deg, #f0f0f0, #94a3b8)",
    },
}

_col_theme, _col_badge = st.columns([3, 1.2])
with _col_theme:
    theme_name = st.radio("Theme", list(THEMES.keys()), horizontal=True,
                          label_visibility="collapsed", index=0)
T = THEMES[theme_name]
_col_badge.markdown(f"""
<div style="display:flex;justify-content:flex-end;align-items:center;padding-top:6px">
  <div style="display:flex;align-items:center;gap:8px;
       background:{T['card']};border:1px solid #ffffff15;border-radius:100px;
       padding:4px 12px 4px 4px">
    <div style="width:28px;height:28px;border-radius:50%;flex-shrink:0;
         background:linear-gradient(135deg,{T['primary']},{T['primary_dark']});
         display:flex;align-items:center;justify-content:center;
         font-size:0.68rem;font-weight:800;color:white;
         border:1.5px solid {T['primary_light']}44">SM</div>
    <div>
      <div style="font-size:0.75rem;font-weight:600;color:#f0f0f0;white-space:nowrap;line-height:1.3">Sharad Maheshwari</div>
      <div style="font-size:0.6rem;color:#64748b;line-height:1">Personal Vault</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: {T['bg']}; color: #f0f0f0; }}
[data-testid="stToolbar"], .stDeployButton, #MainMenu,
[data-testid="stMainMenuPopover"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* Theme picker — hide labels, show only the radio dot, shrink the row */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"]) {{
    margin-bottom: -8px;
}}
div[data-testid="stRadio"] > label {{ display: none; }}
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{
    font-size: 0.7rem !important; color: #475569 !important;
}}
div[data-testid="stRadio"] > div {{ gap: 6px !important; }}
div[data-testid="stRadio"] label {{ padding: 2px 8px !important; font-size: 0.72rem !important; }}

.hero {{
    background: {T['hero_grad']};
    border-radius: 14px; padding: 16px 24px; margin-bottom: 16px;
    border: 1px solid #ffffff10;
}}
.hero-inner {{ display: flex; align-items: center; gap: 14px; }}
.hero-stat {{
    background: #ffffff0d; border: 1px solid #ffffff12; border-radius: 20px;
    padding: 3px 12px; font-size: 0.78rem; color: #94a3b8; white-space: nowrap;
}}
.hero-title {{
    font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px;
    background: {T['title_grad']}; -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text;
}}
.hero-sub {{
    color: #64748b; font-size: 0.78rem; margin-top: 2px; letter-spacing: 0.5px;
}}

.stTabs [data-baseweb="tab-list"] {{
    background: {T['card']}; border-radius: 12px; padding: 4px; gap: 2px;
    border: 1px solid #ffffff10;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px; padding: 8px 16px; color: #94a3b8;
    font-weight: 500; font-size: 0.85rem;
}}
.stTabs [aria-selected="true"] {{ background: {T['primary']} !important; color: white !important; }}

.voucher-card {{
    background: {T['card']}; border: 1px solid #ffffff15; border-radius: 14px;
    padding: 18px 20px 12px; margin-bottom: 12px; transition: border-color 0.2s;
}}
.voucher-card:hover {{ border-color: {T['primary']}55; }}
.voucher-card.expiring {{ border-color: #f59e0b55; background: #1a1a0f; }}
.voucher-card.best {{ border-color: {T['primary']}; background: {T['card']}; }}
.card-actions-row {{
    display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;
    padding-top: 8px; border-top: 1px solid #ffffff0d;
}}
.card-action-btn {{
    position: relative; font-size: 0.85rem; color: #64748b; background: transparent;
    border: 1px solid #ffffff15; border-radius: 6px;
    padding: 2px 9px; cursor: pointer; text-decoration: none;
    transition: color 0.15s, border-color 0.15s;
}}
.card-action-btn:hover {{ color: #cbd5e1; border-color: #ffffff30; text-decoration: none; }}
.card-action-btn.danger:hover {{ color: #f87171; border-color: #f8717155; text-decoration: none; }}
.card-action-btn .btn-tip {{
    display: none; position: absolute; bottom: 130%; right: 0;
    background: #1e293b; border: 1px solid #334155; border-radius: 6px;
    padding: 4px 10px; white-space: nowrap; font-size: 0.72rem;
    color: #94a3b8; z-index: 999; pointer-events: none;
}}
.card-action-btn:hover .btn-tip {{ display: block; }}

.platform-badge {{
    display: inline-block; background: {T['primary']}22; color: {T['primary_light']};
    border: 1px solid {T['primary']}44; border-radius: 6px;
    padding: 2px 10px; font-size: 0.78rem; font-weight: 600; margin-bottom: 6px;
}}
.category-badge {{
    display: inline-block; background: {T['accent_bg']}; color: {T['accent']};
    border-radius: 6px; padding: 2px 8px; font-size: 0.72rem; margin-left: 6px;
}}
.discount-label {{ font-size: 1.3rem; font-weight: 700; color: #f0f0f0; }}
.promo-code {{
    display: inline-flex; align-items: center; gap: 8px;
    font-family: monospace; font-size: 1rem; font-weight: 700;
    background: {T['accent_bg']}; color: {T['accent']};
    border: 1px dashed {T['accent']}55; border-radius: 8px;
    padding: 6px 14px; margin: 8px 0; letter-spacing: 1px;
}}
.copy-btn {{
    font-size: 0.75rem; cursor: pointer; opacity: 0.6;
    background: none; border: none; color: {T['accent']}; padding: 0;
    transition: opacity 0.15s;
}}
.copy-btn:hover {{ opacity: 1; }}
.expiry-text {{ color: #64748b; font-size: 0.82rem; margin-top: 6px; }}
.expiry-soon {{ color: #f59e0b; font-size: 0.82rem; margin-top: 6px; }}

.card-chip {{
    background: {T['card2']}; border: 1px solid #ffffff15; border-radius: 14px;
    padding: 18px 20px; margin-bottom: 12px;
}}
.card-name {{ font-size: 1.1rem; font-weight: 700; color: #f0f0f0; }}
.card-network {{ color: #94a3b8; font-size: 0.82rem; }}
.benefit-row {{ color: #94a3b8; font-size: 0.83rem; margin: 3px 0; }}
.benefit-row span {{ color: {T['primary_light']}; font-weight: 600; }}

.savings-pill {{
    background: {T['success_bg']}; color: {T['success_fg']}; border: 1px solid {T['success_border']};
    border-radius: 20px; padding: 4px 12px; font-weight: 700; font-size: 0.9rem; display: inline-block;
}}
.no-savings-pill {{
    background: {T['card2']}; color: #64748b; border: 1px solid #ffffff10;
    border-radius: 20px; padding: 4px 12px; font-size: 0.9rem; display: inline-block;
}}

.stTextInput input, .stNumberInput input {{
    background: {T['card']} !important; border: 1px solid #ffffff15 !important;
    border-radius: 10px !important; color: #f0f0f0 !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: {T['primary']} !important; box-shadow: 0 0 0 2px {T['primary']}22 !important;
}}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button {{
    background: linear-gradient(135deg, {T['primary']}, {T['primary_dark']}) !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 10px !important;
}}
.stButton > button:not([kind="primary"]) {{
    background: {T['card2']} !important; border: 1px solid #ffffff15 !important;
    border-radius: 8px !important; color: #94a3b8 !important; font-size: 0.8rem !important;
}}
.card-actions .stButton > button {{
    padding: 2px 8px !important; font-size: 0.72rem !important;
    border-radius: 6px !important; min-height: 0 !important; height: 28px !important;
}}
.tip-wrap {{ position: relative; display: inline-block; cursor: default; }}
.tip-wrap .tip-box {{
    display: none; position: absolute; bottom: 120%; left: 0;
    background: #1e293b; border: 1px solid #334155; border-radius: 8px;
    padding: 10px 12px; min-width: 260px; max-width: 320px;
    color: #94a3b8; font-size: 0.76rem; line-height: 1.6;
    z-index: 999; box-shadow: 0 4px 20px #00000055;
}}
.tip-wrap:hover .tip-box {{ display: block; }}
[data-testid="stFileUploader"] {{
    background: {T['card']}; border: 2px dashed #ffffff15; border-radius: 12px; padding: 12px;
}}
hr {{ border-color: #ffffff10 !important; }}
</style>
""", unsafe_allow_html=True)


# ── EFFECTS ──────────────────────────────────────────────────────────────────

def _money_rain():
    components.html("""<!DOCTYPE html>
<html><body>
<script>
(function() {
  var pd = window.parent.document;

  // inject keyframe style once
  if (!pd.getElementById('money-rain-style')) {
    var s = pd.createElement('style');
    s.id = 'money-rain-style';
    s.textContent = '@keyframes moneyfall{0%{transform:translateY(-60px) rotate(0deg);opacity:1}85%{opacity:1}100%{transform:translateY(110vh) rotate(400deg);opacity:0}}';
    pd.head.appendChild(s);
  }

  var overlay = pd.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:99999;overflow:hidden';
  pd.body.appendChild(overlay);

  var emojis = ['₹','💵','🪙','💰','💸','🤑'];
  for (var i = 0; i < 80; i++) {
    var el = pd.createElement('span');
    el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
    var dur  = (3.5 + Math.random() * 2.0).toFixed(2);
    var delay = (Math.random() * 1.5).toFixed(2);
    el.style.cssText = 'position:absolute;top:-60px;user-select:none;font-size:' +
      (2.0 + Math.random() * 2.2).toFixed(1) + 'rem;left:' +
      (Math.random() * 97).toFixed(1) + 'vw;animation:moneyfall ' +
      dur + 's ' + delay + 's linear forwards';
    overlay.appendChild(el);
  }

  setTimeout(function(){ overlay.remove(); }, 7000);
})();
</script>
</body></html>""", height=0)


# ── SHARED RENDERERS ─────────────────────────────────────────────────────────

def _category_badge(category: str) -> str:
    return f'<span class="category-badge">{category}</span>' if category else ""


def _render_voucher_card(v: dict, highlight: bool = False, key_prefix: str = "v"):
    expiry = v.get("expiry_date")
    is_expiring_soon = False
    days_left = None
    if expiry:
        days_left = (date.fromisoformat(str(expiry)) - date.today()).days
        is_expiring_soon = 0 <= days_left <= 3

    platform = v.get("platform") or "Unknown"
    merchant = v.get("applicable_on") or ""
    discount = v.get("discount_label") or ""
    category = v.get("category") or ""
    promo = v.get("promo_code")
    if expiry:
        expiry_text = date.fromisoformat(str(expiry)).strftime("Valid till %-d %b %Y")
    else:
        expiry_text = "No expiry"

    terms = v.get("terms") or []
    if isinstance(terms, str):
        try:
            terms = json.loads(terms)
        except Exception:
            terms = [terms] if terms else []
    if len(terms) == 1 and re.search(r'\d+\.\s', terms[0]):
        parts = re.split(r'\s*\d+\.\s+', terms[0])
        terms = [p.strip() for p in parts if p.strip()]
    top_terms = terms[:2]
    extra_terms = terms[2:]

    # colours
    border_color = "#f59e0b" if is_expiring_soon else (T["primary"] if highlight else "#ffffff15")
    bg_color = "#1a1a0f" if is_expiring_soon else T["card"]
    expiry_color = "#f87171" if is_expiring_soon else "#94a3b8"
    accent = T["accent"]
    accent_bg = T["accent_bg"]
    primary = T["primary"]

    vid = v["id"]
    title_text = html.escape(v.get("title") or "")
    platform_esc = html.escape(platform)
    merchant_esc = html.escape(merchant)
    discount_esc = html.escape(discount)
    expiry_esc = html.escape(expiry_text)
    category_esc = html.escape(category)
    promo_safe = (promo or "").replace("\\", "\\\\").replace("'", "\\'")

    top_terms_html = "".join(
        f'<div style="color:#94a3b8;font-size:0.78rem;margin-top:5px">&#8226; {html.escape(t)}</div>'
        for t in top_terms
    )
    extra_tooltip_html = ""
    if extra_terms:
        tip_items = "".join(f"&#8226; {html.escape(t)}<br>" for t in extra_terms)
        n = len(extra_terms)
        extra_tooltip_html = f"""
<div style="margin-top:6px;position:relative;display:inline-block">
  <span class="tip-trigger" style="color:#64748b;font-size:0.75rem;cursor:default">
    +{n} more condition{"s" if n > 1 else ""} &#9432;
  </span>
  <div class="tip-box" style="display:none;position:absolute;bottom:120%;left:0;
    background:#1e293b;border:1px solid #334155;border-radius:8px;
    padding:10px 12px;min-width:260px;max-width:320px;
    color:#94a3b8;font-size:0.76rem;line-height:1.6;z-index:999;
    box-shadow:0 4px 20px #00000055">
    {tip_items}
  </div>
</div>"""

    promo_section = ""
    if promo:
        promo_esc2 = html.escape(promo)
        promo_section = f"""
<div style="margin:10px 0 4px">
  <button class="promo-btn" onclick="
    navigator.clipboard.writeText('{promo_safe}');
    this.querySelector('.copy-icon').textContent='✓';
    setTimeout(()=>this.querySelector('.copy-icon').textContent='⎘',1500)
  ">
    <span class="promo-code-text">{promo_esc2}</span>
    <span class="copy-icon">⎘</span>
  </button>
</div>"""

    # screenshot as base64 for inline embed — fetched early so source_text logic can reuse it
    img_bytes = get_voucher_screenshot(vid)

    # original text section (text-added vouchers)
    source_text = v.get("source_text") or ""
    source_text_section = ""
    if source_text and not img_bytes:
        source_esc = html.escape(source_text)
        source_text_section = f"""
<div style="margin-top:8px">
  <a id="txt-toggle-{vid}" style="color:#64748b;font-size:0.78rem;cursor:pointer;user-select:none"
     onclick="
       var w=document.getElementById('txt-wrap-{vid}');
       var open=w.style.display==='block';
       w.style.display=open?'none':'block';
       this.textContent=open?'▸ Original text':'▾ Hide original text';
     ">▸ Original text</a>
</div>
<div id="txt-wrap-{vid}" style="display:none;margin-top:6px;
  background:#0f172a;border:1px solid #ffffff15;border-radius:8px;
  padding:8px 12px;font-size:0.76rem;color:#94a3b8;line-height:1.6;white-space:pre-wrap">
{source_esc}
</div>"""

    if img_bytes:
        img_b64 = base64.b64encode(img_bytes).decode()
        img_section = f"""
<div style="margin-top:8px">
  <a id="img-toggle-{vid}" style="color:#64748b;font-size:0.78rem;cursor:pointer;user-select:none"
     onclick="
       var w=document.getElementById('img-wrap-{vid}');
       var open=w.style.display==='block';
       w.style.display=open?'none':'block';
       this.textContent=open?'▸ View screenshot':'▾ Hide screenshot';
       resize();
     ">▸ View screenshot</a>
</div>
<div id="img-wrap-{vid}" style="display:none;margin-top:8px">
  <img src="data:image/jpeg;base64,{img_b64}"
       onload="resize()"
       style="width:300px;border-radius:8px;display:block">
</div>"""
    else:
        img_section = ""

    height = 100 + len(top_terms) * 26 + (50 if promo else 0) + (22 if extra_terms else 0) + (22 if img_bytes else 0) + (22 if source_text_section else 0)

    components.html(f"""<!DOCTYPE html>
<html><head><style>
  * {{ box-sizing:border-box; margin:0; padding:0; font-family:'Inter',sans-serif; }}
  body {{ background:transparent; padding:2px 0 8px; }}
  .card {{
    background:{bg_color}; border:1px solid {border_color};
    border-radius:14px; padding:18px 20px 12px;
  }}
  .row {{ display:flex; justify-content:space-between; align-items:flex-start; }}
  .title {{ font-size:1.1rem; font-weight:800; color:#f0f0f0; }}
  .cat-badge {{
    display:inline-block; background:{accent_bg}; color:{accent};
    border-radius:6px; padding:2px 8px; font-size:0.72rem; margin-left:6px;
  }}
  .app-label {{ color:#94a3b8; font-size:0.8rem; margin-left:6px; }}
  .discount {{ font-size:1.25rem; font-weight:700; color:#f0f0f0; text-align:right; }}
  .expiry {{ color:{expiry_color}; font-size:0.75rem; margin-top:2px; text-align:right; }}
  .promo-btn {{
    display:inline-flex; align-items:center; gap:10px; cursor:pointer;
    font-family:monospace; font-size:1rem; font-weight:700; letter-spacing:1px;
    background:{accent_bg}; color:{accent};
    border:1px dashed {accent}55; border-radius:8px; padding:5px 14px;
    transition:background 0.15s;
  }}
  .promo-btn:hover {{ background:{accent_bg}cc; }}
  .copy-icon {{ font-size:1.1rem; opacity:0.75; }}
  .divider {{ border:none; border-top:1px solid #ffffff0d; margin:10px 0 6px; }}
  .actions {{ display:flex; justify-content:flex-end; gap:8px; }}
  .action-btn {{
    position:relative; font-size:0.85rem; color:#64748b;
    background:transparent; border:1px solid #ffffff15; border-radius:6px;
    padding:2px 9px; cursor:pointer; text-decoration:none;
    transition:color 0.15s,border-color 0.15s;
  }}
  .action-btn:hover {{ text-decoration:none; }}
  .used-btn {{ color:#16a34a; border-color:#16a34a44; }}
  .used-btn:hover {{ color:#4ade80; }}
  .del-btn:hover {{ color:#f87171; border-color:#f8717155; }}
  .btn-tip {{
    display:none; position:absolute; bottom:130%; right:0;
    background:#1e293b; border:1px solid #334155; border-radius:6px;
    padding:4px 10px; white-space:nowrap; font-size:0.72rem;
    color:#94a3b8; z-index:999; pointer-events:none;
  }}
  .action-btn:hover .btn-tip {{ display:block; }}
  .tip-trigger {{ cursor:default; }}
  .tip-trigger:hover + .tip-box, .tip-box:hover {{ display:block !important; }}
</style>
<script>
  function resize() {{
    setTimeout(function() {{
      var h = document.documentElement.scrollHeight;
      window.parent.postMessage({{type:"streamlit:setFrameHeight", height:h}}, "*");
    }}, 50);
  }}
  window.addEventListener('load', resize);
</script>
</head><body>
<div class="card">
  <div class="row">
    <div>
      <span class="title">{title_text if title_text else (merchant_esc or platform_esc)}</span>
      <span class="cat-badge">{category_esc}</span>
      {"<span class='app-label'>via " + platform_esc + "</span>" if merchant_esc else ("<span class='app-label'>App: " + platform_esc + "</span>" if title_text else "")}
      {"<span class='app-label' style='color:#a78bfa;font-size:0.9rem;font-weight:600'>🎯 " + merchant_esc + "</span>" if merchant_esc else ""}
    </div>
    <div>
      <div class="discount">{discount_esc}</div>
      <div class="expiry">{'⚠️' if is_expiring_soon else '🗓'} {expiry_esc}</div>
    </div>
  </div>
  {promo_section}
  {top_terms_html}
  {extra_tooltip_html}
  {source_text_section}
  {img_section}
</div>
</body></html>""", height=height, scrolling=True)

    st.markdown('<div style="margin-top:-12px"></div>', unsafe_allow_html=True)
    _, col_used, col_del = st.columns([10, 1, 1])
    if not v.get("is_used"):
        if col_used.button("✔", key=f"{key_prefix}_used_{vid}", help="Mark as used"):
            mark_used(vid)
            if "advisor_results" in st.session_state:
                ar = st.session_state["advisor_results"]
                ar["vouchers"] = [x for x in ar["vouchers"] if x["id"] != vid]
                st.session_state["advisor_used_rain"] = True
            st.rerun()
    if col_del.button("🗑", key=f"{key_prefix}_del_{vid}", help="Delete voucher"):
        delete_voucher(vid)
        if "advisor_results" in st.session_state:
            ar = st.session_state["advisor_results"]
            ar["vouchers"] = [x for x in ar["vouchers"] if x["id"] != vid]
        st.rerun()



def _render_card(c: dict, key_prefix: str = "c"):
    benefits = c.get("benefits") or []
    network = html.escape(f" · {c['card_network']}" if c.get("card_network") else "")
    cid = c["id"]
    accent = T["accent"]
    accent_bg = T["accent_bg"]
    card_bg = T["card"]
    primary = T["primary"]

    def _brow(b: dict) -> str:
        platforms = f' <span style="color:#64748b">({", ".join(b["platforms"])})</span>' if b.get("platforms") else ""
        return (f'<div style="color:#94a3b8;font-size:0.82rem;margin:3px 0">• '
                f'<span style="color:{accent};font-weight:600">{html.escape(b.get("reward_label",""))}</span>'
                f' on {html.escape(b.get("category","all"))}{platforms}</div>')

    visible_rows = "".join(_brow(b) for b in benefits[:4])
    extra_rows   = "".join(_brow(b) for b in benefits[4:])
    extra_count  = len(benefits) - 4

    extra_section = ""
    if extra_rows:
        extra_section = f"""
<div style="margin-top:6px">
  <a id="more-{cid}" style="color:#64748b;font-size:0.78rem;cursor:pointer;user-select:none"
     onclick="
       var w=document.getElementById('extra-{cid}');
       var open=w.style.display==='block';
       w.style.display=open?'none':'block';
       this.textContent=open?'▸ {extra_count} more benefits':'▾ Hide';
       resize();
     ">▸ {extra_count} more benefits</a>
</div>
<div id="extra-{cid}" style="display:none;margin-top:4px;border-top:1px solid #ffffff0d;padding-top:6px">
  {extra_rows}
</div>"""

    height = 90 + min(len(benefits), 4) * 24 + (22 if extra_rows else 0)

    components.html(f"""<!DOCTYPE html><html><head><style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:'Inter',sans-serif; }}
body {{ background:transparent; padding:2px 0 8px; }}
.card {{ background:{card_bg}; border:1px solid #ffffff15; border-radius:14px; padding:16px 20px 12px; }}
</style>
<script>
function resize() {{
  setTimeout(function() {{
    var h = document.documentElement.scrollHeight;
    window.parent.postMessage({{type:"streamlit:setFrameHeight", height:h}}, "*");
  }}, 50);
}}
window.addEventListener('load', resize);
</script>
</head><body>
<div class="card">
  <div style="font-size:1.05rem;font-weight:700;color:#f0f0f0">💳 {html.escape(c['bank_name'])} {html.escape(c['card_name'])}</div>
  <div style="color:#64748b;font-size:0.8rem;margin-bottom:8px">{network}</div>
  {visible_rows or '<div style="color:#475569;font-size:0.82rem">No benefits extracted</div>'}
  {extra_section}
</div>
</body></html>""", height=height, scrolling=True)

    _, col_del = st.columns([5, 1])
    if col_del.button("🗑", key=f"{key_prefix}del_{c['id']}", help="Delete card"):
        delete_card(c["id"])
        st.rerun()



# ── HEADER ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _hero_stats():
    from datetime import date as _date
    try:
        active = get_all_vouchers(view="active")
        cards = get_all_cards()
        expiring = [v for v in active if v.get("expiry_date") and
                    (_date.fromisoformat(str(v["expiry_date"])) - _date.today()).days <= 7]
        return len(active), len(cards), len(expiring)
    except Exception:
        return 0, 0, 0

_v_count, _c_count, _exp_count = _hero_stats()
_stat_style = "background:#ffffff0d;border:1px solid #ffffff12;border-radius:20px;padding:3px 12px;font-size:0.78rem;color:#94a3b8;white-space:nowrap"

st.markdown(f"""
<div class="hero">
  <div class="hero-inner" style="justify-content:space-between">
    <div style="display:flex;align-items:center;gap:16px">
      <div style="position:relative;flex-shrink:0">
        <div style="position:absolute;inset:-10px;background:radial-gradient(circle,{T['primary']}40 0%,transparent 70%);border-radius:50%;pointer-events:none"></div>
        <svg width="62" height="70" viewBox="0 0 52 58" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="shieldGrad" x1="0" y1="0" x2="52" y2="58" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="{T['primary_light']}"/>
              <stop offset="100%" stop-color="{T['primary_dark']}"/>
            </linearGradient>
            <linearGradient id="boltGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#ffffff"/>
              <stop offset="100%" stop-color="{T['accent']}"/>
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>
          <path d="M26 2 L48 10 L48 28 C48 41 36 52 26 56 C16 52 4 41 4 28 L4 10 Z"
                fill="url(#shieldGrad)" opacity="0.15"/>
          <path d="M26 2 L48 10 L48 28 C48 41 36 52 26 56 C16 52 4 41 4 28 L4 10 Z"
                stroke="{T['primary']}" stroke-width="1.5" fill="none"/>
          <path d="M26 7 L43 14 L43 28 C43 39 33 48 26 51 C19 48 9 39 9 28 L9 14 Z"
                fill="url(#shieldGrad)" opacity="0.9"/>
          <path d="M31 11 L18 31 L25 31 L20 47 L36 24 L28 24 Z"
                fill="white" opacity="0.8"/>
          <path d="M26 7 L43 14 L43 22 C38 18 32 12 26 7 Z" fill="white" opacity="0.1"/>
          <text x="26" y="36" text-anchor="middle" font-family="Inter,sans-serif"
                font-size="22" font-weight="900" fill="#052e16" opacity="1"
                filter="url(#glow)">S</text>
        </svg>
      </div>
      <div>
        <div class="hero-title">SaverAI</div>
        <div class="hero-sub">TURN EVERY PAYMENT INTO SAVINGS</div>
      </div>
    </div>
    <div style="text-align:right;display:flex;flex-direction:column;gap:8px;align-items:flex-end">
      <div style="display:flex;gap:8px">
        <div style="{_stat_style}">🎟️ {_v_count} vouchers</div>
        <div style="{_stat_style}">💳 {_c_count} cards</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_smart, tab_add_voucher, tab_vouchers, tab_add_card, tab_cards, tab_get_card = st.tabs([
    "🎯 Smart Advisor",
    "➕ Add Voucher",
    "🎟️ My Vouchers",
    "💳 Add Card",
    "💳 My Cards",
    "💡 Get a Card",
])


def _section_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f'<div style="color:#64748b;font-size:0.78rem;margin-top:2px">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:18px 0 10px">
  <div style="background:{T['accent_bg']};border-radius:8px;padding:6px 10px;
       font-size:1.1rem;line-height:1">{icon}</div>
  <div>
    <div style="font-size:1rem;font-weight:700;color:#f0f0f0">{title}</div>
    {sub}
  </div>
</div>""", unsafe_allow_html=True)


# ── SMART ADVISOR ─────────────────────────────────────────────────────────────

def _render_grabon_html(grabon_codes: list[dict]) -> None:
    rows_html = ""
    for gc in grabon_codes:
        code_js = gc["code"].replace("\\", "\\\\").replace("'", "\\'")
        rows_html += f"""
<a href="{gc['url']}" target="_blank" class="gc-row">
  <div class="gc-info">
    <div class="gc-meta">{html.escape(gc['merchant'])} &nbsp;·&nbsp; {html.escape(gc['discount'])}</div>
    <div class="gc-title">{html.escape(gc['title'])}</div>
  </div>
  <button class="gc-copy" onclick="event.preventDefault();event.stopPropagation();
    navigator.clipboard.writeText('{code_js}');
    this.querySelector('.ci').textContent='✓';
    setTimeout(()=>this.querySelector('.ci').textContent='⎘',1500)">
    {html.escape(gc['code'])}&nbsp;<span class="ci">⎘</span>
  </button>
</a>"""
    components.html(f"""<!DOCTYPE html><html><head><style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:'Inter',sans-serif; }}
body {{ background:transparent; padding:2px 0; }}
.gc-row {{
  display:flex; align-items:center; justify-content:space-between;
  background:{T['card']}; border:1px solid #ffffff15; border-radius:10px;
  padding:10px 14px; margin-bottom:8px; text-decoration:none;
  transition:border-color 0.2s; cursor:pointer;
}}
.gc-row:hover {{ border-color:{T['primary']}88; }}
.gc-info {{ flex:1; min-width:0; }}
.gc-meta {{ font-size:0.78rem; color:#94a3b8; margin-bottom:3px; }}
.gc-title {{ font-size:0.86rem; color:#f0f0f0; }}
.gc-copy {{
  font-family:monospace; font-size:0.92rem; font-weight:700; letter-spacing:1px;
  background:{T['accent_bg']}; color:{T['accent']};
  border:1px dashed {T['accent']}55; border-radius:8px;
  padding:5px 12px; cursor:pointer; white-space:nowrap;
  display:flex; align-items:center; gap:6px; flex-shrink:0; margin-left:12px;
}}
.gc-copy .ci {{ font-size:1.3rem; line-height:1; }}
.gc-copy:hover {{ opacity:0.85; }}
</style></head><body>{rows_html}</body></html>""", height=len(grabon_codes) * 68)


def _render_card_advice(advice: dict) -> None:
    ranked = advice.get("ranked_cards", [])[:2]
    if not ranked:
        st.info("No cards added yet — go to 💳 Add Card tab.")
        return
    st.success(advice.get("summary", ""))
    cards_html = ""
    for i, rec in enumerate(ranked):
        savings = float(rec.get("estimated_savings") or 0)
        reward = rec.get("reward_label", "")
        no_benefit = not reward or "no specific" in reward.lower()
        medal = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉" if i == 2 else "")
        savings_html = f'<span class="savings-pill">₹{savings:,.0f} saved</span>' if savings >= 1 else ""
        opacity = "opacity:0.45;" if no_benefit else ""
        border = "border-color:#7c3aed;" if i == 0 else ""
        reward_row = f'<div style="color:#a78bfa;font-size:0.83rem;margin-top:3px">↳ {html.escape(reward)}</div>' if reward and not no_benefit else ""
        cards_html += f"""<div class="card-chip" style="{border}{opacity}">
<div style="display:flex;justify-content:space-between;align-items:center">
<div class="card-name">{medal} {html.escape(rec.get('card_label',''))}</div>{savings_html}</div>
<div style="color:#94a3b8;font-size:0.83rem;margin-top:6px">{html.escape(rec.get('reason',''))}</div>
{reward_row}</div>"""
    st.markdown(cards_html, unsafe_allow_html=True)


_ONLINE_SOURCES = [
    ("GrabOn",      "https://www.grabon.in"),
    ("CouponDunia", "https://coupondunia.in"),
    ("CashKaro",    "https://cashkaro.com"),
    ("Desidime",    "https://www.desidime.com"),
]

def _render_online_links() -> None:
    _ocols = st.columns(len(_ONLINE_SOURCES))
    for _col, (_name, _url) in zip(_ocols, _ONLINE_SOURCES):
        _col.markdown(
            f'<a href="{_url}" target="_blank" style="display:block;text-align:center;'
            f'background:{T["card"]};border:1px solid #ffffff15;border-radius:10px;'
            f'padding:10px 8px;color:#94a3b8;text-decoration:none;font-size:0.85rem;'
            f'transition:border-color 0.2s" '
            f'onmouseover="this.style.borderColor=\'{T["primary"]}\'" '
            f'onmouseout="this.style.borderColor=\'#ffffff15\'">'
            f'🔍 {_name}</a>',
            unsafe_allow_html=True,
        )


def _render_advisor_vouchers(vouchers: list[dict]) -> None:
    if not vouchers:
        st.info("No matching vouchers in your vault — add some from ➕ Add Voucher.")
        return
    for i, v in enumerate(vouchers):
        _render_voucher_card(v, highlight=(i == 0), key_prefix="adv")


with tab_smart:
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{T['card']} 0%,{T['card2']} 100%);
     border:1px solid #ffffff10;border-radius:16px;padding:22px 24px 18px;margin-bottom:16px">
  <div style="font-size:1.3rem;font-weight:700;color:#f0f0f0;margin-bottom:4px">
    🎯 Smart Advisor
  </div>
  <div style="color:#64748b;font-size:0.88rem">
    Tell us what you're buying — we'll find the best card and vouchers instantly.
  </div>
</div>
""", unsafe_allow_html=True)

    with st.form("advisor_form"):
        item = st.text_input("Item", placeholder="🛒  What are you buying? e.g. Sony headphones, Swiggy dinner", label_visibility="collapsed")
        platform = st.text_input("Platform", placeholder="🏪  Platform or merchant (optional)", label_visibility="collapsed")
        submitted = st.form_submit_button("Find best card & vouchers →", type="primary", use_container_width=True)

    if submitted and item:
        st.session_state.pop("advisor_results", None)
        cards = get_all_cards()
        vouchers = get_all_vouchers(view="active")
        query = f"{item} {platform}".strip()

        ex = ThreadPoolExecutor(max_workers=3)
        f_vouchers = ex.submit(search_vouchers, query, vouchers)
        f_grabon   = ex.submit(fetch_live_codes, platform or item)
        f_advice   = ex.submit(advise_best_card, item, 0, platform, cards)

        _section_header("🎟️", "Your Saved Vouchers", "Matching vouchers from your vault")
        ph_vouchers = st.empty()
        ph_vouchers.info("🔍 Searching your vault…")

        _section_header("⚡", "Live Online Codes", "Real-time codes from GrabOn")
        ph_grabon = st.empty()
        ph_grabon.info("⚡ Fetching live codes from GrabOn…")

        _section_header("🔍", "Search More Online")
        _render_online_links()

        _section_header("💳", "Best Card to Use", "Ranked by savings for this purchase")
        ph_cards = st.empty()
        ph_cards.info("🤖 Analysing your cards…")

        from concurrent.futures import as_completed
        collected: dict = {}
        futures_map = {f_vouchers: "vouchers", f_grabon: "grabon", f_advice: "advice"}
        for future in as_completed(futures_map):
            key = futures_map[future]
            try:
                result = future.result()
            except Exception:
                result = [] if key != "advice" else {}
            collected[key] = result

            if key == "vouchers":
                with ph_vouchers.container():
                    _render_advisor_vouchers(result)
            elif key == "grabon":
                with ph_grabon.container():
                    if not result:
                        st.caption("No promo codes found for this search.")
                    else:
                        st.caption("⚡ Fetched live from GrabOn · Codes may not always work — verify before checkout.")
                        _render_grabon_html(result)
            elif key == "advice":
                with ph_cards.container():
                    _render_card_advice(result)

        st.session_state["advisor_results"] = {
            "vouchers": collected.get("vouchers", []),
            "grabon":   collected.get("grabon", []),
            "advice":   collected.get("advice", {}),
        }
        ex.shutdown(wait=False)

    elif "advisor_results" in st.session_state:
        cached = st.session_state["advisor_results"]

        if st.session_state.pop("advisor_used_rain", False):
            _money_rain()

        _section_header("🎟️", "Your Saved Vouchers", "Matching vouchers from your vault")
        _render_advisor_vouchers(cached["vouchers"])

        _section_header("⚡", "Live Online Codes", "Real-time codes from GrabOn")
        if not cached["grabon"]:
            st.caption("No promo codes found on GrabOn for this search.")
        else:
            st.caption("⚡ Fetched live from GrabOn · Codes may not always work — verify before checkout.")
            _render_grabon_html(cached["grabon"])

        _section_header("🔍", "Search More Online")
        _render_online_links()

        _section_header("💳", "Best Card to Use", "Ranked by savings for this purchase")
        _render_card_advice(cached["advice"])


# ── ADD VOUCHER ───────────────────────────────────────────────────────────────
with tab_add_voucher:
    _saved = st.session_state.pop("voucher_saved", None)
    if _saved:
        st.success("✅ Voucher saved! Add another below.")
        _money_rain()
        _render_voucher_card(_saved, key_prefix="saved")
        st.divider()

    st.markdown(f"""
<div style="background:linear-gradient(135deg,{T['card']} 0%,{T['card2']} 100%);
     border:1px solid #ffffff10;border-radius:16px;padding:22px 24px 18px;margin-bottom:16px">
  <div style="font-size:1.3rem;font-weight:700;color:#f0f0f0;margin-bottom:4px">➕ Add a Voucher</div>
  <div style="color:#64748b;font-size:0.88rem">Upload a screenshot or paste text — AI extracts all the details automatically.</div>
</div>
""", unsafe_allow_html=True)

    _upload_nonce = st.session_state.setdefault("_upload_nonce", 0)

    mode = st.radio("How do you want to add?", ["📷 Screenshot", "✏️ Type / Paste text"],
                    horizontal=True, label_visibility="collapsed")

    if mode == "📷 Screenshot":
        st.caption("Works with any app — just upload the voucher screenshot.")
        uploaded = st.file_uploader("Upload", type=["png", "jpg", "jpeg", "webp"],
                                    label_visibility="collapsed",
                                    key=f"voucher_upload_{_upload_nonce}")
        if uploaded:
            image_bytes = uploaded.read()
            st.image(image_bytes, width=320)
            platform_override = st.text_input(
                "App / Platform (optional)", placeholder="e.g. CRED, Amazon, Swiggy — fill if not visible in screenshot",
                key=f"plat_img_{_upload_nonce}")

            if st.button("Extract & Save Voucher", type="primary", use_container_width=True):
                with st.spinner("🧠 Scanning your voucher..."):
                    try:
                        parsed = parse_voucher_screenshot(image_bytes)
                    except Exception as e:
                        st.error(f"Failed to parse: {e}")
                        st.stop()

                if platform_override.strip():
                    parsed["platform"] = platform_override.strip()

                with st.spinner("Saving..."):
                    try:
                        saved = save_voucher(parsed, image_bytes)
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
                        st.stop()

                st.session_state["voucher_saved"] = saved
                st.session_state["_upload_nonce"] = _upload_nonce + 1
                st.rerun()

    else:
        st.caption("Paste the voucher text — promo code, discount, expiry, platform, any details you have.")
        voucher_text = st.text_area("Voucher details", height=140,
                                    placeholder="e.g. CRED — Starbucks ₹300 off, code 2XN188558R60, valid till 15 Jun, min order ₹500",
                                    label_visibility="collapsed",
                                    key=f"voucher_text_{_upload_nonce}")
        platform_override = st.text_input(
            "App / Platform (optional)", placeholder="e.g. CRED, Swiggy — fill if not in the text above",
            key=f"plat_txt_{_upload_nonce}")

        if st.button("Extract & Save Voucher", type="primary", use_container_width=True,
                     disabled=not voucher_text.strip()):
            with st.spinner("🧠 Reading your voucher..."):
                try:
                    parsed = parse_voucher_text(voucher_text)
                except Exception as e:
                    st.error(f"Failed to parse: {e}")
                    st.stop()

            if platform_override.strip():
                parsed["platform"] = platform_override.strip()

            with st.spinner("Saving..."):
                try:
                    saved = save_voucher(parsed, b"", source_text=voucher_text)
                except Exception as e:
                    st.error(f"Failed to save: {e}")
                    st.stop()

            st.session_state["voucher_saved"] = saved
            st.session_state["_upload_nonce"] = _upload_nonce + 1
            st.rerun()


# ── ADD CARD ──────────────────────────────────────────────────────────────────
with tab_add_card:
    _saved_card = st.session_state.pop("card_saved", None)
    if _saved_card:
        st.success("✅ Card added!")
        _render_card(_saved_card, key_prefix="saved_c")
        st.divider()

    _section_header("💳", "Add a Credit Card", "We'll look up benefits automatically")

    col_bank, col_card = st.columns(2)
    bank_name = col_bank.text_input("Bank name", placeholder="e.g. HDFC, Axis, ICICI, SBI")
    card_name = col_card.text_input("Card name", placeholder="e.g. Regalia, Flipkart, Magnus")
    card_desc = st.text_area(
        "Extra details (optional)",
        height=100,
        placeholder="Paste any reward details you know — specific cashback rates, offers, etc. Leave blank to let AI fill it in.",
        label_visibility="visible",
    )

    if st.button("Add Card", type="primary", use_container_width=True,
                 disabled=not (bank_name.strip() and card_name.strip())):
        with st.spinner(f"🧠 Looking up {bank_name} {card_name} benefits..."):
            try:
                parsed = parse_card_from_name(bank_name.strip(), card_name.strip(), card_desc)
            except Exception as e:
                st.error(f"Failed to fetch card info: {e}")
                st.stop()

        with st.spinner("Saving..."):
            try:
                saved_card = save_card(parsed, b"")
            except Exception as e:
                st.error(f"Failed to save: {e}")
                st.stop()

        st.session_state["card_saved"] = saved_card
        st.rerun()


# ── MY VOUCHERS ───────────────────────────────────────────────────────────────
with tab_vouchers:
    col_view, col_sort = st.columns([3, 2])
    with col_view:
        view = st.radio("Show", ["Active", "Used", "Expired"],
                        horizontal=True, label_visibility="collapsed")
    with col_sort:
        sort_by = st.radio("Sort", ["By expiry", "Newest first"],
                           horizontal=True, label_visibility="collapsed")

    sort_key = "newest" if sort_by == "Newest first" else "expiry"
    vouchers = get_all_vouchers(view=view.lower(), sort=sort_key)

    if not vouchers:
        st.markdown(f"""
<div style="background:{T['card']};border:1px solid #ffffff10;border-radius:14px;
     padding:32px;text-align:center;margin-top:12px">
  <div style="font-size:2rem;margin-bottom:8px">🎟️</div>
  <div style="color:#94a3b8;font-size:0.95rem">No vouchers yet — add one from ➕ Add Voucher.</div>
</div>""", unsafe_allow_html=True)
    else:
        _section_header("🎟️", f"My Vouchers", f"{len(vouchers)} voucher{'s' if len(vouchers) != 1 else ''}")
        for v in vouchers:
            _render_voucher_card(v)


# ── MY CARDS ──────────────────────────────────────────────────────────────────
with tab_cards:
    cards = get_all_cards()
    if not cards:
        st.markdown(f"""
<div style="background:{T['card']};border:1px solid #ffffff10;border-radius:14px;
     padding:32px;text-align:center;margin-top:12px">
  <div style="font-size:2rem;margin-bottom:8px">💳</div>
  <div style="color:#94a3b8;font-size:0.95rem">No cards yet — add one from 💳 Add Card.</div>
</div>""", unsafe_allow_html=True)
    else:
        _section_header("💳", "My Cards", f"{len(cards)} card{'s' if len(cards) != 1 else ''} in your wallet")
        for c in cards:
            _render_card(c)


# ── GET A CARD ────────────────────────────────────────────────────────────────
SPEND_CATEGORIES = [
    "Food delivery (Swiggy/Zomato)",
    "Amazon",
    "Flipkart",
    "Groceries",
    "Fuel",
    "Travel (flights/hotels)",
    "Travel & Flights",
    "Movies & Entertainment",
    "Dining out",
    "Fashion & Clothing",
    "Electronics",
    "Utilities & Bills",
    "Other online shopping",
]

_PROFILE_TRAVEL = [
    {"cat": "Food delivery (Swiggy/Zomato)", "amt": 4000},
    {"cat": "Amazon", "amt": 6000},
    {"cat": "Fuel", "amt": 3000},
    {"cat": "Travel (flights/hotels)", "amt": 10000},
]
_PROFILE_DINING = [
    {"cat": "Food delivery (Swiggy/Zomato)", "amt": 4000},
    {"cat": "Amazon", "amt": 6000},
    {"cat": "Fuel", "amt": 3000},
    {"cat": "Travel (flights/hotels)", "amt": 2000},
    {"cat": "Dining out", "amt": 8000},
]

CATEGORY_ICONS = {
    "Food delivery (Swiggy/Zomato)": "🍔",
    "Amazon": "📦",
    "Flipkart": "🛒",
    "Groceries": "🥦",
    "Fuel": "⛽",
    "Travel (flights/hotels)": "✈️",
    "Travel & Flights": "✈️",
    "Movies & Entertainment": "🎬",
    "Dining out": "🍽️",
    "Fashion & Clothing": "👗",
    "Electronics": "💻",
    "Utilities & Bills": "💡",
    "Other online shopping": "🛍️",
}

with tab_get_card:
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{T['card']} 0%,{T['card2']} 100%);
     border:1px solid #ffffff10;border-radius:16px;padding:22px 24px 18px;margin-bottom:20px">
  <div style="font-size:1.3rem;font-weight:700;color:#f0f0f0;margin-bottom:4px">
    💡 Find Your Perfect Card
  </div>
  <div style="color:#64748b;font-size:0.88rem">
    Enter your monthly spends — we'll tell you exactly which card to get and how much you'll save.
  </div>
</div>
""", unsafe_allow_html=True)

    if "spend_rows" not in st.session_state:
        st.session_state["spend_rows"] = [r.copy() for r in _PROFILE_TRAVEL]

    rows = st.session_state["spend_rows"]

    # Column headers
    h1, h2, h3 = st.columns([4, 2, 0.5])
    h1.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:600;padding-left:4px;margin-bottom:2px">CATEGORY</div>', unsafe_allow_html=True)
    h2.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:600;padding-left:4px;margin-bottom:2px">₹ / MONTH</div>', unsafe_allow_html=True)

    to_delete = None
    for i, row in enumerate(rows):
        c1, c2, c3 = st.columns([4, 2, 0.5])
        icon = CATEGORY_ICONS.get(row["cat"], "💳")
        cat_options = [f"{CATEGORY_ICONS.get(c, '💳')} {c}" for c in SPEND_CATEGORIES]
        raw_cat = row["cat"]
        display_option = f"{CATEGORY_ICONS.get(raw_cat, '💳')} {raw_cat}"
        selected = c1.selectbox("Category", cat_options,
                                index=cat_options.index(display_option) if display_option in cat_options else 0,
                                key=f"scat_{i}", label_visibility="collapsed")
        rows[i]["cat"] = selected.split(" ", 1)[1] if " " in selected else selected
        rows[i]["amt"] = c2.number_input("₹/month", min_value=0, step=500, value=int(row["amt"]),
                                          key=f"samt_{i}", label_visibility="collapsed")
        if c3.button("✕", key=f"sdel_{i}", help="Remove"):
            to_delete = i

    if to_delete is not None:
        st.session_state["spend_rows"].pop(to_delete)
        st.rerun()

    # Total spend summary
    total = sum(int(r["amt"]) for r in rows if r["amt"] > 0)
    col_add, col_total = st.columns([3, 2])
    with col_add:
        if st.button("＋ Add category", key="sadd"):
            st.session_state["spend_rows"].append({"cat": SPEND_CATEGORIES[0], "amt": 1000})
            st.rerun()
    col_total.markdown(f"""
<div style="text-align:right;padding-top:6px">
  <span style="color:#64748b;font-size:0.8rem">Monthly total </span>
  <span style="color:{T['primary_light']};font-weight:700;font-size:1rem">₹{total:,}</span>
  <span style="color:#64748b;font-size:0.8rem"> · ₹{total*12:,}/yr</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Find best card(s) for me →", type="primary", use_container_width=True):
        spend = {r["cat"]: int(r["amt"]) for r in rows if r["amt"] > 0}

        spend_int = {k: int(v) for k, v in spend.items()}
        is_demo = spend_int in (DEMO_SPEND, DEMO_SPEND_2)

        with st.spinner("🧠 Analysing your spend profile..."):
            try:
                owned = [] if is_demo else get_all_cards()
                result = recommend_cards(spend, owned)
            except Exception as e:
                st.error(f"Gemini error — please try again in a few seconds. ({type(e).__name__})")
                result = {}
                owned = []

        owned_labels = {f"{c['bank_name']} {c['card_name']}".lower() for c in owned}

        top_cards = result.get("top_cards") or []
        combo = result.get("best_combo")

        if not top_cards:
            err = result.get("_error", "")
            st.error(f"Could not generate recommendations — please try again. {('(' + err + ')') if err else ''}")
        else:
            _section_header("🏆", "Best Individual Cards", "Ranked by net annual benefit for your spend")

            def _rec_card_html(card, i, owned_labels):
                label = f"{card.get('bank','')} {card.get('card','')}".strip()
                already = card.get("already_owned") or label.lower() in owned_labels
                medal = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉")
                annual_fee = card.get("annual_fee") or 0
                net = card.get("net_annual_benefit") or 0
                annual_savings = card.get("estimated_annual_savings") or 0
                border = f"border:1px solid {T['primary']};" if i == 0 else "border:1px solid #ffffff15;"
                cat_rows = "".join(
                    f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#94a3b8;margin:3px 0">'
                    f'<span>{html.escape(b.get("category",""))}</span>'
                    f'<span style="color:{T["primary_light"]}">{html.escape(b.get("benefit",""))}'
                    f' <b style="color:#4ade80">+₹{b.get("monthly_saving",0):,.0f}/mo</b></span></div>'
                    for b in (card.get("category_benefits") or [])
                )
                tnc_rows = "".join(
                    f'<div style="color:#64748b;font-size:0.76rem;margin:2px 0">• {html.escape(t)}</div>'
                    for t in (card.get("key_tnc") or [])
                )
                owned_badge = (
                    '<span style="background:#14532d;color:#4ade80;border-radius:4px;padding:1px 8px;font-size:0.72rem;margin-left:8px">✓ You have this</span>'
                    if already else ""
                )
                waiver = (
                    f'<div style="color:#64748b;font-size:0.78rem;margin-top:2px">{html.escape(card.get("fee_waiver",""))}</div>'
                    if card.get("fee_waiver") else ""
                )
                return f"""
<div style="background:#1e293b;{border}border-radius:12px;padding:14px 16px;margin-bottom:10px;font-family:sans-serif">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div style="flex:1">
      <span style="font-size:1.05rem;font-weight:700;color:#f0f0f0">{medal} {html.escape(label)}</span>
      {owned_badge}
      <div style="color:#94a3b8;font-size:0.8rem;margin-top:4px">{html.escape(card.get('why',''))}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="color:#4ade80;font-weight:700;font-size:1rem">₹{annual_savings:,.0f}/yr saved</div>
      <div style="color:#64748b;font-size:0.78rem">Fee: ₹{annual_fee:,.0f} · Net: ₹{net:,.0f}</div>
    </div>
  </div>
  <div style="margin-top:10px;border-top:1px solid #ffffff0d;padding-top:8px">{cat_rows}</div>
  {f'<div style="margin-top:8px;border-top:1px solid #ffffff0d;padding-top:6px">{tnc_rows}</div>' if tnc_rows else ''}
  <div style="margin-top:6px;color:#64748b;font-size:0.78rem">Annual fee: ₹{annual_fee:,.0f} {waiver}</div>
</div>"""

            cards_html = "".join(_rec_card_html(c, i, owned_labels) for i, c in enumerate(top_cards))
            components.html(f"<div style='background:transparent'>{cards_html}</div>",
                            height=len(top_cards) * 200 + 20, scrolling=False)

            if combo:
                _section_header("🃏", "Best 2-Card Combo", "Maximum coverage across all your categories")
                combo_cards_label = " + ".join(combo.get("cards") or [])
                combined_savings = combo.get("combined_annual_savings") or 0
                combined_fees = combo.get("combined_annual_fees") or 0
                net_combo = combo.get("net_annual_benefit") or 0
                split_rows = "".join(
                    f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#94a3b8;margin:3px 0">'
                    f'<span style="color:{T["accent"]};font-weight:600">{html.escape(s.get("card",""))}</span>'
                    f'<span>Use for: {html.escape(", ".join(s.get("use_for",[])))}'
                    f' · <b style="color:#4ade80">+₹{s.get("monthly_saving",0):,.0f}/mo</b></span></div>'
                    for s in (combo.get("split") or [])
                )
                combo_html = f"""
<div style="background:#1e293b;border:1px solid {T['accent']}55;border-radius:12px;padding:14px 16px;font-family:sans-serif">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div style="flex:1">
      <span style="font-size:1.05rem;font-weight:700;color:#f0f0f0">🃏 {html.escape(combo_cards_label)}</span>
      <div style="color:#94a3b8;font-size:0.8rem;margin-top:4px">{html.escape(combo.get('why',''))}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="color:#4ade80;font-weight:700;font-size:1rem">₹{combined_savings:,.0f}/yr saved</div>
      <div style="color:#64748b;font-size:0.78rem">Fees: ₹{combined_fees:,.0f} · Net: ₹{net_combo:,.0f}</div>
    </div>
  </div>
  <div style="margin-top:10px;border-top:1px solid #ffffff0d;padding-top:8px">{split_rows}</div>
</div>"""
                components.html(f"<div style='background:transparent'>{combo_html}</div>",
                                height=180 + len(combo.get("split") or []) * 28, scrolling=False)
