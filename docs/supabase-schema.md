# Supabase Schema — Voters table

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
