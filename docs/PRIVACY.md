# Privacy & Biometric Data Handling

This document describes how VoteChain handles biometric data and voter information. It is intentionally concise — for legal compliance, please consult your organisation's counsel.

- Data stored: the system stores biometric templates (fingerprint templates) and a mapping to a voter identifier (e.g., hashed Aadhaar ID). No raw fingerprint images are stored by default.
- Identifiers: Aadhaar numbers or other government IDs are hashed (SHA-256) before storage in audit logs. The Supabase `voters` table holds minimal metadata to support check-in and auditing.
- Retention policy: default retention is 1 year of session data. Adjust retention in Supabase policies and make backups according to local regulations.
- Export / Erase: Admins may export session reports via `docs/SESSION_REPORTS.md` flow. To erase a voter record, remove the row from Supabase and rotate any derived audit entries where feasible.

Recommendations:

- Minimise storage of personally-identifying fields; use hashed IDs for audit logs.
- Ensure informed consent is collected before enrollment (on-site consent form or digital confirmation).
- Maintain a documented data-retention schedule and a process for deletion requests.

Legal note: biometric and voting data may be subject to strict local laws. Engage legal counsel before production deployment.
