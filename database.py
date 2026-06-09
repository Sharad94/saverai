import json
import os
from contextlib import contextmanager
from datetime import date

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def _get_db_url() -> str:
    # Streamlit Cloud secrets take priority
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return os.environ.get("DATABASE_URL", "postgresql://sharadmaheshwari@localhost/saverai")

DATABASE_URL = _get_db_url()


@contextmanager
def _conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_dict(cursor, row) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def _deserialise_terms(row: dict) -> None:
    t = row.get("terms")
    if t is None:
        row["terms"] = []
    elif isinstance(t, str):
        try:
            row["terms"] = json.loads(t)
        except (json.JSONDecodeError, ValueError):
            row["terms"] = [t] if t else []
    elif not isinstance(t, list):
        row["terms"] = list(t)


# ── VOUCHERS ──────────────────────────────────────────────────────────────────

def save_voucher(parsed: dict, image_bytes: bytes, source_text: str | None = None) -> dict:
    sql = """
        INSERT INTO vouchers
          (platform, title, discount_type, discount_value, discount_label,
           promo_code, min_order_value, max_discount, expiry_date, expiry_raw,
           category, applicable_on, terms, screenshot, is_used, source_text)
        VALUES
          (%(platform)s, %(title)s, %(discount_type)s, %(discount_value)s,
           %(discount_label)s, %(promo_code)s, %(min_order_value)s,
           %(max_discount)s, %(expiry_date)s, %(expiry_raw)s, %(category)s,
           %(applicable_on)s, %(terms)s::jsonb, %(screenshot)s, false, %(source_text)s)
        RETURNING *
    """
    terms = parsed.get("terms")
    if isinstance(terms, list):
        terms_list = [str(t) for t in terms if t]
    elif isinstance(terms, str) and terms:
        terms_list = [terms]
    else:
        terms_list = []
    params = {k: v for k, v in parsed.items() if k not in ("terms", "source_text")}
    params["terms"] = json.dumps(terms_list, ensure_ascii=False)
    params["screenshot"] = psycopg2.Binary(image_bytes)
    params["source_text"] = source_text
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        result = _row_to_dict(cur, row)
    _deserialise_terms(result)
    result.pop("screenshot", None)
    return result


def get_all_vouchers(view: str = "active", sort: str = "expiry") -> list[dict]:
    today = date.today().isoformat()
    if view == "used":
        where = "WHERE is_used = true"
    elif view == "expired":
        where = f"WHERE is_used = false AND expiry_date IS NOT NULL AND expiry_date < '{today}'"
    else:  # active
        where = f"WHERE is_used = false AND (expiry_date IS NULL OR expiry_date >= '{today}')"
    order = "created_at DESC" if sort == "newest" else "expiry_date ASC NULLS LAST"
    sql = f"SELECT * FROM vouchers {where} ORDER BY {order}"

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        results = [_row_to_dict(cur, r) for r in rows]

    for r in results:
        r.pop("screenshot", None)
        _deserialise_terms(r)
    return results


def mark_used(voucher_id: int) -> None:
    with _conn() as conn:
        conn.cursor().execute("UPDATE vouchers SET is_used = true WHERE id = %s", (voucher_id,))


def delete_voucher(voucher_id: int) -> None:
    with _conn() as conn:
        conn.cursor().execute("DELETE FROM vouchers WHERE id = %s", (voucher_id,))


def get_voucher_screenshot(voucher_id: int) -> bytes | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT screenshot FROM vouchers WHERE id = %s", (voucher_id,))
        row = cur.fetchone()
        return bytes(row[0]) if row and row[0] else None


# ── CREDIT CARDS ──────────────────────────────────────────────────────────────

def save_card(parsed: dict, image_bytes: bytes) -> dict:
    sql = """
        INSERT INTO credit_cards (bank_name, card_name, card_network, benefits, screenshot)
        VALUES (%(bank_name)s, %(card_name)s, %(card_network)s, %(benefits)s, %(screenshot)s)
        RETURNING *
    """
    params = {
        "bank_name": parsed.get("bank_name", "Unknown"),
        "card_name": parsed.get("card_name", "Unknown"),
        "card_network": parsed.get("card_network"),
        "benefits": json.dumps(parsed.get("benefits", [])),
        "screenshot": psycopg2.Binary(image_bytes),
    }
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        result = _row_to_dict(cur, row)

    result.pop("screenshot", None)
    if isinstance(result.get("benefits"), str):
        result["benefits"] = json.loads(result["benefits"])
    return result


def get_all_cards() -> list[dict]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM credit_cards ORDER BY id DESC")
        rows = cur.fetchall()
        results = [_row_to_dict(cur, r) for r in rows]

    for r in results:
        r.pop("screenshot", None)
        if isinstance(r.get("benefits"), str):
            r["benefits"] = json.loads(r["benefits"])
    return results


def get_card_screenshot(card_id: int) -> bytes | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT screenshot FROM credit_cards WHERE id = %s", (card_id,))
        row = cur.fetchone()
        return bytes(row[0]) if row and row[0] else None


def delete_card(card_id: int) -> None:
    with _conn() as conn:
        conn.cursor().execute("DELETE FROM credit_cards WHERE id = %s", (card_id,))
