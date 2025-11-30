# Security Guidance

This document provides recommended practices for managing keys, secrets, and incident response.

## Security Best Practices

- Use strong passwords.
- Enable two-factor authentication.

Recommendations

Incident response (brief)

Notes

- You requested no rotation of secrets at this time; these steps are advisory and should be executed by the project owner if required.

## Server secrets & service role keys

- **Service role key**: Supabase `service_role` keys grant wide privileges. They must only be present in the backend environment and never exposed to client code or public UIs.
- **Private keys**: Backend signing keys (`SERVER_PRIVATE_KEY`) should be stored in a secure secrets manager or in protected environment files with restricted filesystem permissions.
- **Rotation**: Plan a rotation schedule for service and signing keys and test key rollover in a staging environment before production rotation.

## Incident response (brief)

- If a server key is suspected compromised: immediately revoke it (Supabase/hosting provider), rotate keys, and investigate logs for suspicious API usage.
