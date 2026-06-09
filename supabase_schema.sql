-- Run this in your Supabase SQL editor to set up the schema

create table vouchers (
  id              bigserial primary key,
  platform        text,
  title           text,
  discount_type   text,
  discount_value  numeric,
  discount_label  text,
  promo_code      text,
  min_order_value numeric,
  max_discount    numeric,
  expiry_date     date,
  expiry_raw      text,
  category        text,
  applicable_on   text,
  terms           text,
  screenshot_url  text,
  is_used         boolean default false,
  created_at      timestamptz default now()
);

create table credit_cards (
  id              bigserial primary key,
  bank_name       text not null,
  card_name       text not null,
  card_network    text,
  benefits        jsonb default '[]'::jsonb,
  screenshot_url  text,
  created_at      timestamptz default now()
);

-- Storage buckets (create in Supabase dashboard > Storage > New bucket)
-- 1. Name: voucher-screenshots  | Public: true
-- 2. Name: card-screenshots     | Public: true
