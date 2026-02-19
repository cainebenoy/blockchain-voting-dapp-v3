# Entity Relationship Diagram — VoteChain V3

This document describes all data entities and their relationships across the three data layers: **Supabase (off-chain)**, **Ethereum (on-chain)**, and the **Kiosk (edge)**.

---

## ER Diagram

```mermaid
erDiagram
    VOTERS {
        text aadhaar_id PK "SHA-256 salted hash"
        text name "Voter full name"
        text fingerprint_id FK "Sensor slot ID"
        text photo_url "Optional photo"
        boolean has_voted "One-person-one-vote"
    }

    ENROLLMENT_REQUESTS {
        serial id PK
        text aadhaar_id FK
        text name
        text constituency
        integer target_finger_id
        text status "PENDING | WAITING | COMPLETED | FAILED"
        timestamptz created_at
    }

    RECEIPTS {
        bigserial id PK
        varchar code UK "Short code e.g. ABC-123"
        varchar tx_hash UK "Blockchain transaction hash"
        boolean is_confirmed "On-chain confirmation"
        timestamptz inserted_at
    }

    SYSTEM_CONFIG {
        text key PK "e.g. backend_url, kiosk_pending_command"
        text value "Dynamic value"
    }

    AUDIT_LOG {
        bigserial id PK
        text action "VOTE_CAST | ENROLL | WIPE | etc."
        jsonb details "Hashed voter ID, metadata"
        timestamptz timestamp
    }

    VOTING_V3_CONTRACT {
        address admin "Contract deployer"
        address officialSigner "Backend wallet"
        bytes32 voterListRoot "Merkle Root of voter registry"
        boolean electionActive "Election state"
    }

    CANDIDATES_ON_CHAIN {
        uint256 candidate_id PK "On-chain index"
        string name "Candidate name"
        uint256 voteCount "Total votes received"
    }

    VOTES_ON_CHAIN {
        uint256 voter_nonce PK "Kiosk nonce - replay prevention"
        uint256 candidate_id FK "Who was voted for"
        address signer "Backend wallet that signed"
    }

    MERKLE_TREE {
        bytes32 root "Anchored on-chain"
        bytes32 leaf "keccak256 of salted hash"
        bytes32[] proof "Sibling hashes for verification"
    }

    FINGERPRINT_SENSOR {
        integer slot_id PK "Sensor memory slot 1-127"
        blob template "Fingerprint template data"
    }

    %% === RELATIONSHIPS ===

    VOTERS ||--o| ENROLLMENT_REQUESTS : "created by"
    VOTERS ||--o| RECEIPTS : "receives after voting"
    VOTERS ||--o| AUDIT_LOG : "actions logged"
    VOTERS }|--|| MERKLE_TREE : "hashed into leaves"
    VOTERS ||--|| FINGERPRINT_SENSOR : "biometric link"

    ENROLLMENT_REQUESTS }|--|| SYSTEM_CONFIG : "kiosk polls for commands"

    RECEIPTS ||--|| VOTES_ON_CHAIN : "tx_hash references"

    VOTING_V3_CONTRACT ||--|{ CANDIDATES_ON_CHAIN : "stores"
    VOTING_V3_CONTRACT ||--|{ VOTES_ON_CHAIN : "records"
    VOTING_V3_CONTRACT ||--|| MERKLE_TREE : "anchors root"

    CANDIDATES_ON_CHAIN ||--|{ VOTES_ON_CHAIN : "receives"
```

---

## Data Layer Map

```mermaid
flowchart TB
    subgraph SUPABASE["☁️ Supabase (Off-Chain Database)"]
        V[voters]
        E[enrollment_requests]
        R[receipts]
        SC[system_config]
        AL[audit_log]
    end

    subgraph ETHEREUM["⛓️ Ethereum Sepolia (On-Chain)"]
        VC[VotingV3 Contract]
        C[Candidates]
        VT[Votes + Nonces]
        MR[voterListRoot]
    end

    subgraph KIOSK["🖥️ Kiosk (Edge Device)"]
        FS[Fingerprint Sensor]
        OLED[OLED Display]
    end

    subgraph MERKLE["🌳 Merkle Tree (Ephemeral)"]
        MT[Generated at election start]
    end

    V -->|salted hashes| MT
    MT -->|root anchored| MR
    MT -->|proof served via API| AUDITOR[Auditor Page]
    V -->|check-in| FS
    FS -->|verified| VT
    VT -->|tx_hash| R
    SC -->|commands| FS
    E -->|enrollment| FS
```

---

## Entity Details

### Supabase Tables

| Table | Primary Key | Purpose | RLS |
|-------|------------|---------|-----|
| `voters` | `aadhaar_id` (salted SHA-256) | Voter registry with biometric mapping | Service-role only for writes |
| `enrollment_requests` | `id` (serial) | Queue for kiosk enrollment commands | PII protected, no public read |
| `receipts` | `id` (bigserial) | Maps short codes to blockchain tx hashes | Public read, service-role write |
| `system_config` | `key` (text) | Service discovery, kiosk commands | Public read, service-role write |
| `audit_log` | `id` (bigserial) | Tamper-evident action log | Service-role only |

### Smart Contract State (VotingV3)

| State Variable | Type | Purpose |
|---------------|------|---------|
| `admin` | `address` | Contract owner (deployer) |
| `officialSigner` | `address` | Backend wallet authorized to sign votes |
| `voterListRoot` | `bytes32` | Merkle Root of the voter registry (set once) |
| `electionActive` | `bool` | Whether voting is currently open |
| `candidates[]` | `Candidate[]` | Array of candidates with vote counts |
| `usedNonces[]` | `mapping` | Prevents replay attacks via kiosk nonce |

### Kiosk (Edge)

| Component | Data Stored | Persistence |
|-----------|------------|-------------|
| Fingerprint Sensor | Templates (slots 1–127) | Non-volatile, survives reboot |
| OLED Display | None | Ephemeral display only |
| evdev Keyboard | None | Input device only |

---

## Key Relationships

1. **Voter → Receipt**: A voter who casts a vote receives a short-code receipt (`ABC-123`) linked to their blockchain transaction.
2. **Voter → Merkle Leaf**: Each voter's salted hash is Keccak-256'd into a Merkle leaf. The tree root is anchored on-chain.
3. **Receipt → Blockchain**: The `tx_hash` in the receipt maps 1:1 to an on-chain vote transaction.
4. **Enrollment → Kiosk**: Enrollment requests are queued in Supabase and polled by the kiosk via `system_config`.
5. **Contract → Merkle Root**: The `voterListRoot` is set once at election start and is immutable thereafter.

---

## References

- [supabase-schema.md](supabase-schema.md) — SQL create statements
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [PRIVACY.md](PRIVACY.md) — Data privacy and hashing details
- [SECURITY.md](SECURITY.md) — RLS policies and incident response
