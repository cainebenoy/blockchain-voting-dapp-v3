-- Create a table to track kiosk enrollment requests
create table public.enrollment_requests (
    id uuid not null default gen_random_uuid(),
    created_at timestamp with time zone not null default now(),
    target_id integer not null, -- matches the ID in Smart Contract's candidates/voters mapping if needed, or just a kiosk ID
    aadhaar_hash text not null, -- store HASH only for privacy or encrypted value
    name text not null,
    constituency text not null,
    status text not null default 'PENDING', -- PENDING, COMPLETED, FAILED
    kiosk_id text, -- optional, to track which kiosk handled it
    error_message text,
    constraint enrollment_requests_pkey primary key (id)
);

-- Enable RLS
alter table public.enrollment_requests enable row level security;

-- Policies
create policy "Enable read access for all users"
on "public"."enrollment_requests"
as PERMISSIVE
for SELECT
to public
using (true);

create policy "Enable insert for authenticated users only"
on "public"."enrollment_requests"
as PERMISSIVE
for INSERT
to authenticated
with check (true);

create policy "Enable update for service role only"
on "public"."enrollment_requests"
as PERMISSIVE
for UPDATE
to service_role
using (true);
