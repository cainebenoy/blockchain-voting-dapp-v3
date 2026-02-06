# Troubleshooting & FAQ

This page collects common issues and how to resolve them quickly.

If the above steps do not resolve the issue, check `backend/server.log` and open an issue with logs attached (sanitize secrets first).

## Common errors seen during E2E

- `Database save failed` on `/api/kiosk/enrollment-complete`
  - Symptoms: kiosk reports enrollment complete but backend returns `Database save failed`.
  - Likely causes: Supabase RLS policy prevents insert/update for the key being used, invalid `SUPABASE_KEY`, or unique constraint violation (e.g., duplicate `aadhaar_id`).
  - Steps to debug:

    ```sql
    select * from public.voters where aadhaar_id = '123456789012';
    ```

    Ensure `SUPABASE_KEY` is the `service_role` key and RLS policies allow the service role to insert into `voters`.
    If unique constraints are the issue, remove/cleanup test rows before re-running E2E.

- `Double voting detected!`
  - Symptoms: `/api/vote` returns this error for a test Aadhaar.
  - Likely causes: the `voters` row already exists with `has_voted = true` or the backend detected a prior vote on-chain.
  - Steps to debug:

    ```sql
    select aadhaar_id, has_voted from public.voters where aadhaar_id = '123456789012';
    ```

    If `has_voted` is true and this is a test row, reset it for E2E testing or use a separate test Aadhaar.
    Check backend logs for the double-vote detection path and any on-chain evidence.

## When to open an issue

- Attach the backend logs (redact keys), the exact API calls and payloads you used, and the results of the SQL queries above.
