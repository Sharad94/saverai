CREATE TABLE IF NOT EXISTS credit_cards (
    id bigserial PRIMARY KEY,
    bank_name text NOT NULL,
    card_name text NOT NULL,
    card_network text,
    benefits jsonb DEFAULT '[]'::jsonb,
    screenshot bytea,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vouchers (
    id bigserial PRIMARY KEY,
    platform text,
    title text,
    discount_type text,
    discount_value numeric,
    discount_label text,
    promo_code text,
    min_order_value numeric,
    max_discount numeric,
    expiry_date date,
    expiry_raw text,
    category text,
    applicable_on text,
    terms jsonb,
    screenshot bytea,
    is_used boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    source_text text
);
