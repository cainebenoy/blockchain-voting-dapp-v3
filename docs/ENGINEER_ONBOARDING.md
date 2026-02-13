# VoteChain V3 | Engineer Onboarding & Architecture Guide

Welcome, Engineer. This guide provides the technical "ground truth" for the VoteChain V3 ecosystem. Follow this to understand, deploy, and modify the system safely.

---

## 🏗️ System Overview

VoteChain V3 is a **cyber-physical voting infrastructure** designed to eliminate "trust" as a prerequisite for fair elections. It bridges physical biometric identity with immutable blockchain ledgers.

### Hardware-Software Stack
- **Edge (Kiosk):** Raspberry Pi 5 + R307 Optical Fingerprint Sensor. Runs Python for local biometric matching and GUI orchestration.
- **Backend (Official):** Node.js / Express. Acts as the "Signer". It validates biometric sessions, proxies transactions to Ethereum, and manages the Supabase state.
- **Persistence (Hybrid):** 
    - **Supabase:** Real-time database for voter registry, system configuration, and enrollment queues.
    - **Ethereum Sepolia:** The source of truth for the ballot tally and Merkle anchors.
- **Frontend (Portals):** Static HTML/Tailwind/ethers.js hosted on GitHub Pages. Uses **Service Discovery** to locate the Pi backend dynamically.

### Deployment Model
The system uses a **Hybrid Cloud-Edge** model:
1. The **Pi** sits behind a local network (e.g., in a polling booth).
2. **Cloudflare Tunnel** (`cloudflared`) exposes the Pi to the internet without port forwarding.
3. A **Python Heartbeat** updates Supabase with the latest tunnel URL.
4. **GitHub Pages** queries Supabase to find where the Pi is "living" today.

---

## 🔄 Core Lifecycles

### 1. Enrollment Flow
*Purpose: Adding a new voter to the physical system.*
1. **Admin Portal:** Admin submits Aadhaar ID and Name to `/api/admin/add-voter`.
2. **Backend:** Adds entry to Supabase `voters` table with `enrollment_status='pending'`.
3. **Kiosk:** `kiosk_main.py` polls Supabase, sees pending enrollment, and triggers the R307 sensor.
4. **Physical:** User places finger on sensor. Sensor extracts template; Kiosk saves template locally (mapped to Aadhaar).
5. **Sync:** Kiosk updates Supabase to `enrollment_status='completed'`.

### 2. Voting Flow
*Purpose: Casting a cryptographically signed ballot.*
1. **Check-In:** Voter enters Aadhaar on Kiosk; Kiosk calls `/api/voter/check-in`.
2. **Biometric Challenge:** Kiosk enters "Match Mode". User places finger. Sensor performs **1:1 match** against the stored template for that Aadhaar.
3. **Session Signing:** On match, Kiosk sends `auth_token` to Backend.
4. **On-Chain Vote:** Backend executes `contract.vote(candidateId, voterHash)` using the server's private key.
5. **Receipt Generation:** Backend generates a short-code (e.g., `ABC-123`) and maps it to the `tx_hash` in Supabase.

### 3. Verification Flow
*Purpose: Proving the vote was counted.*
1. **User:** Enters receipt code in `verify.html`.
2. **Discovery:** `verify.html` fetches the backend URL from Supabase.
3. **Resolution:** Frontend calls `BACKEND/api/verify-code` to get the `tx_hash`.
4. **Blockchain Audit:** Frontend uses `ethers.js` to query the Sepolia network directly, confirming block height and transaction status.

---

## 🗺️ Code Navigation Map

| Concern | Primary Files/Directories |
| :--- | :--- |
| **Smart Contracts** | `contracts/VotingV2.sol`, `hardhat.config.ts` |
| **Biometrics/Kiosk** | `kiosk/hardware.py` (drivers), `kiosk/kiosk_main.py` (UI/Logic) |
| **API Endpoints** | `backend/server.js`, `backend/routes/vote.js`, `backend/routes/admin.js` |
| **Services** | `backend/services/ethereumService.js` (Ethers v6 integration) |
| **Frontend Portals** | `admin.html`, `results.html`, `verify.html`, `auditor.html` |
| **Infrastructure** | `bin/start_tunnel.py` (Cloudflare tunnel manager) |
| **Database** | `db/supabase-setup.sql` (Schema and RLS) |

---

## 🛠️ "If you want to change X, edit Y" Cheatsheet

- **Change Election Candidates:** 
    - Edit `admin.html` (UI) and call the `addCandidate` function on the contract via `backend/routes/admin.js`.
- **Change Receipt Code Format:** 
    - Modify `generateShortCode()` in `backend/routes/vote.js`.
- **Change Fingerprint Retry Limit:** 
    - Modify `verify_voter()` timeout logic in `kiosk/kiosk_main.py`.
- **Switch Blockchain Networks:** 
    - Update `RPC_URL` and `contractAddress` in `playwright.config.ts`, `.env`, and frontend portal config sections.
- **Add a New Node Health Parameter:** 
    - Update `backend/routes/public.js` (`/api/health`) and the `healthStatus` UI in `admin.html`.
- **Change Supabase Policy (RLS):** 
    - Edit `db/supabase-setup.sql` and re-run in Supabase SQL editor.

---

## ⚠️ Notes on Divergence (Docs vs. Code)
- **Merkle Proofs:** While `auditor.html` implements the logic for proof verification, the *generation* of proofs currently requires manual extraction of the voter list. A future update should automate the "Export Proof" flow in the Admin Portal.
- **Biometric Template Storage:** Templates are stored **locallly on the R307 hardware buffer/internal flash** for performance, with a reference ID stored in the local SQLite/mapping. They are *never* uploaded to Supabase or the cloud for privacy reasons.

---
**Status:** Ready to Ship.
**Last Reviewed:** 2026-02-12
