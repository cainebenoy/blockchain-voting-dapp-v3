## Security Guidance

This document provides recommended practices for managing keys, secrets, and incident response.

Recommendations

- Secrets storage: use a secrets manager (HashiCorp Vault, AWS Secrets Manager, Dotenvx) for production. Keep `.env` files local and out of version control.
- Access control: limit service_role keys to backend hosts and rotate keys periodically.
- Least privilege: use a dedicated backend wallet for signing and avoid using admin/deployer keys in runtime services.
- Logging: redact sensitive values in logs. Do not store private keys in logs or uploaded diagnostic bundles.

Incident response (brief)

1. Revoke compromised keys immediately via provider consoles (Supabase, Alchemy).
2. Replace affected keys and redeploy services with new credentials.
3. If private keys were exposed, consider replacing the key and re-authorizing any dependent contracts/wallets.

Notes
- You requested no rotation of secrets at this time; these steps are advisory and should be executed by the project owner if required.
