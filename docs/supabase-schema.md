# Supabase Schema

This project expects a Supabase table `voters` to support check-in and vote auditing.

## Table: `voters`

Columns:

- `aadhaar_id` TEXT UNIQUE NOT NULL — 12-digit ID used for check-in
- `name` TEXT NOT NULL — voter full name
- `fingerprint_id` TEXT NULL — optional identifier for biometric device
- `photo_url` TEXT NULL — optional photo URL
- `has_voted` BOOLEAN NOT NULL DEFAULT FALSE — backend sets to true after successful vote

### SQL (create table)

```sql
create table if not exists public.voters (
  aadhaar_id text primary key,
  name text not null,
  fingerprint_id text,
  photo_url text,
  has_voted boolean not null default false
);

-- Optional index to speed up lookups
create index if not exists voters_has_voted_idx on public.voters(has_voted);
```

### Sample seed data

```sql
insert into public.voters (aadhaar_id, name, fingerprint_id, photo_url, has_voted) values
  ('123456789012', 'Alice Sharma', 'fp-001', null, false),
  ('234567890123', 'Bob Patel',   'fp-002', null, false),
  ('345678901234', 'Carol Singh', 'fp-003', null, false)
  on conflict (aadhaar_id) do nothing;
```

### Notes

- The backend never stores Aadhaar IDs in logs; it writes an SHA-256 hash in the audit log for privacy.
- Ensure your service role key is used server-side only and not exposed to browsers.
- Use Row Level Security (RLS) as appropriate; backend uses the service role to update `has_voted`.

## Table: `enrollment_requests`
*Used to queue enrollment commands for kiosks.*

Columns:
- `id` SERIAL PRIMARY KEY
- `aadhaar_id` TEXT NOT NULL
- `name` TEXT NOT NULL
- `constituency` TEXT
- `target_finger_id` INTEGER NOT NULL
- `status` TEXT DEFAULT 'PENDING' (PENDING, WAITING_FOR_KIOSK, COMPLETED, FAILED)
- `created_at` TIMESTAMPTZ DEFAULT NOW()

### SQL
```sql
create table if not exists public.enrollment_requests (
  id serial primary key,
  aadhaar_id text not null,
  name text not null,
  constituency text,
  target_finger_id integer not null,
  status text not null default 'PENDING',
  created_at timestamptz not null default now()
);
```

## Table: `receipts`
*Maps human-friendly short codes to blockchain transactions.*

Columns:
- `id` BIGSERIAL PRIMARY KEY
- `code` VARCHAR(32) UNIQUE NOT NULL
- `tx_hash` VARCHAR(66) UNIQUE NOT NULL (May be 'PENDING_nonce' during processing)
- `is_confirmed` BOOLEAN DEFAULT FALSE
- `inserted_at` TIMESTAMPTZ DEFAULT NOW()

### SQL
```sql
create table if not exists public.receipts (
  id bigserial primary key,
  code varchar(32) not null unique,
  tx_hash varchar(66) not null unique,
  is_confirmed boolean default false,
  inserted_at timestamptz default now()
);
```

### Notes
- The backend uses a server-side `voteQueue` to sign and submit transactions sequentially.
- Voters marked with `has_voted = true` are blocked from further attempts, even if the blockchain transaction is still pending.
