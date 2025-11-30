# Receipts Table (short-code mapping)

The backend persists a human-friendly short code mapped to the transaction hash in a `receipts` table in Supabase. Use the SQL below to create the table and enforce uniqueness.

```sql
create table if not exists public.receipts (
  id bigserial primary key,
  code varchar(32) not null unique,
  tx_hash varchar(66) not null unique,
  inserted_at timestamptz default now()
);
```

Notes:

- Add a unique index on `code` and `tx_hash` to avoid duplicates.
- Configure RLS policies to allow the backend service role to `INSERT` and `SELECT` on `receipts` while restricting client-side access. Do not expose `service_role` to browsers or kiosk devices.
- Keep retention and backup policies in mind; receipts are small but useful for audits.
