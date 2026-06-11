import psycopg2
import psycopg2.extras

LOCAL_URL = "postgresql://sharadmaheshwari@localhost/saverai"
NEON_URL = "postgresql://neondb_owner:npg_dz4HknStRZX8@ep-wild-field-apowgx8a.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    local = psycopg2.connect(LOCAL_URL)
    neon  = psycopg2.connect(NEON_URL)
    neon.autocommit = False

    try:
        # ── VOUCHERS ──────────────────────────────────────────────────
        local_cur = local.cursor()
        local_cur.execute("SELECT * FROM vouchers ORDER BY id")
        rows = local_cur.fetchall()
        cols = [d[0] for d in local_cur.description]
        print(f"Migrating {len(rows)} vouchers...")

        neon_cur = neon.cursor()
        neon_cur.execute("TRUNCATE vouchers RESTART IDENTITY CASCADE")

        import json
        for row in rows:
            r = dict(zip(cols, row))
            if not isinstance(r.get("terms"), str):
                r["terms"] = json.dumps(r["terms"] or [])
            neon_cur.execute("""
                INSERT INTO vouchers
                  (platform, title, discount_type, discount_value, discount_label,
                   promo_code, min_order_value, max_discount, expiry_date, expiry_raw,
                   category, applicable_on, terms, screenshot, is_used, created_at, source_text)
                VALUES
                  (%(platform)s, %(title)s, %(discount_type)s, %(discount_value)s,
                   %(discount_label)s, %(promo_code)s, %(min_order_value)s, %(max_discount)s,
                   %(expiry_date)s, %(expiry_raw)s, %(category)s, %(applicable_on)s,
                   %(terms)s::jsonb, %(screenshot)s, %(is_used)s, %(created_at)s, %(source_text)s)
            """, r)
            print(f"  ✓ [{r['id']}] {r.get('platform','?')} — {r.get('title','')[:50]}")

        # ── CREDIT CARDS ──────────────────────────────────────────────
        local_cur.execute("SELECT * FROM credit_cards ORDER BY id")
        cards = local_cur.fetchall()
        card_cols = [d[0] for d in local_cur.description]
        print(f"\nMigrating {len(cards)} cards...")

        neon_cur.execute("TRUNCATE credit_cards RESTART IDENTITY CASCADE")

        for row in cards:
            r = dict(zip(card_cols, row))
            if not isinstance(r.get("benefits"), str):
                r["benefits"] = json.dumps(r["benefits"] or [])
            neon_cur.execute("""
                INSERT INTO credit_cards (bank_name, card_name, card_network, benefits, screenshot, created_at)
                VALUES (%(bank_name)s, %(card_name)s, %(card_network)s, %(benefits)s::jsonb, %(screenshot)s, %(created_at)s)
            """, r)
            print(f"  ✓ [{r['id']}] {r['bank_name']} {r['card_name']}")

        neon.commit()
        print("\n✅ Migration complete!")

    except Exception as e:
        neon.rollback()
        print(f"❌ Failed: {e}")
        raise
    finally:
        local.close()
        neon.close()

if __name__ == "__main__":
    migrate()
