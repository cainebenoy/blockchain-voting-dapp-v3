# Frontend Wiring Verification Checklist

This document describes how to verify that the VoteChain V3 frontend is correctly wired to the backend and blockchain.

## 🏢 Admin Console (`admin.html`)

### 1. Backend Authentication
- [ ] Click the lock icon in the navbar.
- [ ] Enter the system secret and click "Grant Access".
- [ ] **Expect**: Success toast, lock icon changes to open, status dots for Backend/Database/Kiosk update to green.

### 2. Election Lifecycle
- [ ] Add a candidate name and click "ADD".
- [ ] **Expect**: MetaMask prompt, "Deploying" toast, candidate appears in list after mining.
- [ ] Click "Start Election".
- [ ] **Expect**: MetaMask prompt, "Registry Locked" overlay appears, "End Election" button becomes active.

### 3. Voter Enrollment
- [ ] Enter a 12-digit Aadhaar ID and Name.
- [ ] Click "Initiate Hardware Enrollment".
- [ ] **Expect**: "Scanning Finger..." status on the Kiosk Telemetry card.
- [ ] (If Kiosk is active) Complete fingerprint scan.
- [ ] **Expect**: "Enrollment Success" and toast notification.

## 🔍 Audit & Verification (`verify.html`)

### 1. Receipt Verification
- [ ] Enter a known 6-character receipt code (e.g., `ABC-123`).
- [ ] Click "Verify".
- [ ] **Expect**: "Verifying..." state, followed by the "Confirmed" bento card showing block number and tx link.

### 2. Direct Hash Verification
- [ ] Enter a valid Ethereum transaction hash.
- [ ] Click "Verify".
- [ ] **Expect**: Direct blockchain lookup bypassing the backend code resolution.

## 📊 Live Dashboard (`results.html`)

### 1. Data Sync
- [ ] Open the page.
- [ ] **Expect**: Contract address loads from backend, candidate bars reflect current on-chain vote counts.
- [ ] **Expect**: "Turnout" percentage matches `(on-chain votes / registered users)`.

### 2. Real-time Updates
- [ ] Cast a vote via the kiosk/api.
- [ ] **Expect**: "Audit Ledger" at the bottom updates with a new transaction row within 15 seconds.

## 🛡️ Auditor Toolkit (`auditor.html`)

### 1. Integrity Proof
- [ ] Click "Refresh Anchor".
- [ ] **Expect**: Current Merkle Root hash appears.
- [ ] Enter a voter ID and its corresponding Merkle JSON proof.
- [ ] Click "Verify Mathematical Path".
- [ ] **Expect**: "Mathematical Proof Valid" green box.
