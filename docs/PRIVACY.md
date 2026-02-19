# Privacy & Biometric Data Handling

This document describes how VoteChain handles biometric data, voter information, and the Merkle Tree privacy architecture.

## Aadhaar ID Privacy (Multi-Stage Hashing)

VoteChain **never** stores raw Aadhaar IDs in the database or on the blockchain. The system uses a multi-stage hashing approach:

1. **Salted SHA-256 Hash**: During enrollment, the Aadhaar ID is concatenated with a secret salt (`AADHAAR_SALT`) and hashed using SHA-256. This salted hash is stored in the Supabase `voters` table.
2. **Keccak-256 Merkle Leaf**: When the election starts, each salted hash is further hashed using Keccak-256 to produce the Merkle Tree leaf. These leaves are **never stored** — they are computed on-the-fly.
3. **Merkle Root On-Chain**: Only the final 32-byte Merkle Root is written to the `VotingV3` smart contract. It is mathematically impossible to reverse this root to recover any voter's identity.

```
Raw Aadhaar → SHA-256(id + salt) → Stored in DB (private)
                                  → Keccak-256(hash) → Merkle Leaf (ephemeral)
                                                      → Merkle Root → On-Chain (public, irreversible)
```

## Biometric Data

- The system stores **fingerprint templates** (mathematical representations), not raw fingerprint images.
- Templates are stored on the local fingerprint sensor module and indexed by a numeric ID.
- The mapping between `fingerprint_id` and `aadhaar_hash` is stored in the Supabase `voters` table.

## Blockchain Data

Votes recorded on the Ethereum blockchain contain:
- Candidate ID (numeric index)
- Kiosk nonce (replay prevention)
- Voter Merkle Root (registry hash — not voter-specific)

**No personally identifiable information is stored on-chain.**

## Receipts & Audit Trail

The short-code receipt system stores only a short alphanumeric `code` and the corresponding `tx_hash` in the `receipts` table. This mapping does not include PII.

- Do not store Aadhaar numbers or identifiable fields in `receipts`.
- Limit retention according to your privacy policy; receipts can be purged after the audit window.

## Data Retention & Erasure

- Default retention: 1 year of session data.
- Admins may export session reports via `docs/SESSION_REPORTS.md`.
- To erase a voter record, remove the row from Supabase and rotate any derived audit entries.
- **Important**: If `AADHAAR_SALT` is changed, all existing voter hashes become invalid. Only change the salt when starting a completely new election cycle.

## Recommendations

- Minimise storage of personally-identifying fields; use hashed IDs for audit logs.
- Ensure informed consent is collected before enrollment.
- Maintain a documented data-retention schedule and a process for deletion requests.
- Engage legal counsel before production deployment — biometric and voting data may be subject to strict local laws.

