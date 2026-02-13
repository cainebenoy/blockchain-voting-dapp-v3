# VoteChain V3 | Full-Stack Code Review Report

## Overall Health Summary
- **Strong Conceptual Core:** The hybrid deployment model (Raspberry Pi Edge + Cloudflare Tunnel + Ethereum Sepolia) is robust and well-suited for high-integrity voting in low-connectivity areas.
- **Clean Contract Logic:** `VotingV2.sol` is minimalist and correctly implements the authorized-signer pattern, effectively preventing public ballot stuffing.
- **Infrastructure Automation:** The self-healing logic in `ethereumService.js` (detecting and authorizing signers) significantly lowers operation friction.
- **Critical Security Gaps:** The system currently relies on "security through obscurity" for most internal APIs (Admin, Kiosk, and Voting endpoints), which lack proper authentication.
- **State Synchronization Risks:** State transitions (voted status in DB vs. BC) are loosely coupled, creating a risk of desynchronization if transactions fail after timeouts.

---

## 🚨 Prioritized Issue List

### [P0] - Election-Breaking / Critical Security

| ID | Category | Location | Description | Recommendation |
|:---|:---|:---|:---|:---|
| 1.1 | **Security** | `backend/routes/admin.js` | All Admin endpoints (`/deploy-contract`, `/add-voter`) are **unauthenticated**. Anyone can reset the election. | Implement JWT or API Key authentication on the `/api/admin/*` route group. |
| 1.2 | **Security** | `db/supabase-setup.sql` | The `UPDATE` policy for `system_config` uses `USING (true)`, allowing **anyone with the public key** to modify the `backend_url`. | Restrict `UPDATE` access to the `service_role` or a specific authenticated admin user. |
| 1.3 | **Security** | `backend/routes/vote.js` | `/api/vote` is unauthenticated. A malicious actor could spam votes for any Aadhaar ID, forcing the server to pay gas. | Require a signed "Biometric Session Token" from the Kiosk /api/voter/check-in to authorize voting. |

### [P1] - Robustness & Integrity

| ID | Category | Location | Description | Recommendation |
|:---|:---|:---|:---|:---|
| 2.1 | **Correctness** | `backend/routes/vote.js` | If `tx.wait(1)` hits the 60s timeout, the DB is updated to `has_voted: true` regardless of whether the tx eventually fails/reverts. | Only update Supabase *after* receipt confirmation, or implement a background "reconciliation" worker. |
| 2.2 | **Security** | `contracts/VotingV2.sol` | `setOfficialSigner` does not check for `address(0)`. | Add `require(_signer != address(0))` to the setter. |
| 2.3 | **Privacy** | `backend/routes/vote.js` | Aadhaar IDs are hashed with SHA-256 without a salt. Brute-forcing 12-digit numbers is trivial for modern GPUs. | Use a salted hash (stored in `.env`) or a pepper to increase preimage resistance. |

### [P2] - Performance & UX

| ID | Category | Location | Description | Recommendation |
|:---|:---|:---|:---|:---|
| 3.1 | **Performance** | `kiosk/kiosk_main.py` | `poll_admin_commands` and `poll_receipt` use fixed sleep intervals (1s-2s) without exponential backoff. | Implement basic backoff (e.g., 2s, 4s, 8s) if the server returns 429 or is unreachable. |
| 3.2 | **Architecture** | `kiosk/kiosk_main.py` | Hardcoded `BACKEND_URL` on line 15. | Move `BACKEND_URL` to a `.env` or config file on the Pi for easier site deployment. |

---

## ⚡ Quick Wins (< 2 Hours)
1. **[Fix 1.2]** Fix the Supabase RLS policy for `system_config` to prevent public updates.
2. **[Fix 2.2]** Add a zero-address check to `setOfficialSigner`.
3. **[Improve 1.1]** Add a simple `ADMIN_SECRET` header check to all `/api/admin` routes.
4. **[Fix 3.2]** Load Kiosk backend URL from environment variables.

## 🏗️ Deep Refactors (Design Needed)
1. **Biometric Session Management:** Integrate a session-token bridge where `/check-in` returns a short-lived HMAC token that `/vote` must present.
2. **Double-Sync Strategy:** Move the `voters.update` logic to a listener that triggers only on blockchain event confirmation (`VoteCast` event).
3. **Zero-Knowledge Identity:** Explore using ZK-Snarks (e.g., Circom) to prove "I am a registered voter" without revealing the Aadhaar hash on-chain.

---
**Reviewer:** Antigravity (Security Subagent)
**Status:** Completed
**Date:** 2026-02-12
