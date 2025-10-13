# Frontend Specification — Blockchain Voting dApp

This spec is framework-agnostic (works for React/Vue/Svelte or plain HTML). It defines pages, components, states, and contract interactions needed to implement the UI.

## 1) User roles and flows
- Admin (deployer address):
  - Add candidates (name)
  - Authorize voter addresses
  - End election
- Voter (any EOA):
  - If authorized and election active → can vote once for a candidate
  - If unauthorized → cannot vote
  - After election ends → view winner

## 2) Pages / Views (routes)
- / (Dashboard)
  - Sections: Connection, Election status, Candidate list, Actions (contextual by role)
- /admin (optional separate route; can also be a tab/accordion on Dashboard)
  - Add Candidate form
  - Authorize Voter form
  - End Election button + confirmation modal
- /vote (optional separate route; can be a tab)
  - Candidate selection + Vote button (only when authorized & active)
- /results (optional separate route; can be a panel on Dashboard)
  - Winner details (only after end), full candidate list
- /settings (optional modal/route)
  - Network switch prompts, contract address override (dev only)

Note: A single-page layout with tabs (Dashboard | Admin | Vote | Results) is fine.

## 3) Global UI components
- WalletConnectButton
  - States: disconnected, connecting, connected (show address short), wrong-network
  - Actions: connect, switch to Sepolia (11155111), add network if missing
- NetworkBadge
  - Shows current chain name + id; warning style if not Sepolia
- AddressBadge
  - Copy-to-clipboard, checksum display
- Notification/Toast system
  - Types: success, error, info; show transaction hashes with explorer links
- LoadingSpinner
  - Used during reads/writes
- Modal (confirmations)
  - Used for End Election confirmation
- CandidateCard / CandidateRow
  - id, name, votes (live-updating), selected state for voter

## 4) Dashboard sections and elements
A. Connection
- Elements: WalletConnectButton, NetworkBadge, Admin address label (if admin)
- States: disconnected, connected-wrong-network, connected

B. Election Status
- isElectionActive() boolean → badge (Active/Ended)
- Totals: totalCandidates, totalVotes (optional, kept in contract)

C. Candidates List
- Table/List: id | name | voteCount
- Empty state: “No candidates yet” (admin hint to add)

D. Admin Actions (visible only if connected address == admin)
- Add Candidate
  - Input: name (string; min 1 char; trim)
  - Button: Add
  - Validation: non-empty, reasonable length (<= 64)
- Authorize Voter
  - Input: voter address (0x-prefixed checksum)
  - Button: Authorize
  - Validation: isAddress
- End Election
  - Button: End Election
  - Confirm modal: “This action is irreversible. Continue?”
  - Disabled if already ended or if 0 candidates

E. Voter Panel (visible to any connected address)
- Voter status from getVoterInfo(address)
  - Not authorized → show info + disable vote
  - Authorized & not voted & active → show candidate selector + Vote button
  - Authorized & already voted → show info (votedCandidateId)
- Candidate selector (radio list or dropdown)
- Vote button

F. Results Panel
- If ended → show getWinnerDetails(): id, name, voteCount
- Always show full candidate list (with final tallies)

## 5) Contract interactions
Contract: Voting (ABI provided in repo)
- Reads (no gas):
  - isElectionActive()
  - getAllCandidates() → array of { id, name, voteCount }
  - getVoterInfo(address)
  - getWinnerDetails() (only after end)
- Writes (gas):
  - addCandidate(name) [admin]
  - authorizeVoter(address) [admin]
  - vote(candidateId) [authorized voter]
  - endElection() [admin]
- Events (subscribe and update UI in real-time):
  - CandidateAdded(candidateId, name)
  - VoterAuthorized(voter)
  - VoteCast(voter, candidateId)
  - ElectionEnded(winnerCandidateId, winnerName, winningVoteCount)

## 6) Network and provider
- Target chain: Sepolia (chainId 11155111)
- Provider: MetaMask injected provider
- On connect:
  - If wrong network → prompt `wallet_switchEthereumChain` (and `wallet_addEthereumChain` fallback)
  - Rebuild provider/signer/contract after successful switch

## 7) State management & data model
- Global app state:
  - connection: { status: 'disconnected' | 'connecting' | 'connected', address, chainId }
  - isAdmin: boolean
  - election: { active: boolean, totalCandidates?: number, totalVotes?: number }
  - candidates: Array<{ id: number, name: string, voteCount: string }>
  - voter: { isAuthorized: boolean, hasVoted: boolean, votedCandidateId: number }
  - winner?: { id: number, name: string, voteCount: string } (after end)
- Derived flags:
  - canVote = connection.connected && election.active && voter.isAuthorized && !voter.hasVoted
  - canEnd = isAdmin && election.active && candidates.length > 0

## 8) Error & empty states (must-haves)
- Disconnected: Disable all write buttons; show connect prompt
- Wrong network: Show banner with "Switch to Sepolia" action
- Not admin: Hide admin controls (or disable with tooltip)
- Not authorized: Disable vote with message
- Double vote attempt: Show specific error toast
- Invalid candidate: Show input error
- Election ended: Disable vote/add/authorize; show results
- Transaction errors: Surface revert messages; link to explorer

## 9) Validation rules
- Candidate name: required, trim, 1–64 chars
- Address: must pass isAddress; checksum display
- Button disabled states should mirror contract preconditions to avoid unnecessary reverts

## 10) Accessibility & UX
- Keyboard navigation for all controls
- Proper labels for inputs; ARIA roles for modals
- High-contrast badges for Active/Ended state
- Toasts should be dismissible and not obstruct controls

## 11) Performance notes
- Batch reads where possible (e.g., rely on getAllCandidates instead of per-candidate calls)
- Subscribe to events to avoid polling
- Debounce expensive re-renders on rapid event emissions

## 12) Wireframe outline (textual)
Header:
[Logo/Title] [NetworkBadge] [WalletConnectButton]

Main:
- Status Card: Election [Active|Ended] + Totals
- Tabs: [Candidates] [Vote] [Results] [Admin (if admin)]

Candidates Tab:
- List of CandidateRow

Vote Tab:
- Voter status + Candidate selector + Vote button

Results Tab:
- Winner details (if ended) + Candidate list

Admin Tab:
- Add Candidate (input+button)
- Authorize Voter (address+button)
- End Election (button+confirm)

Footer:
- Contract address (shortened) + Explorer link

## 13) Acceptance criteria
- Can fully manage election lifecycle end-to-end from the UI
- Role-aware controls: admin-only actions hidden from non-admins
- Real-time updates via events; no manual refresh needed
- Clear, actionable errors (wrong network, not authorized, already voted, etc.)
- Mobile-responsive layout for common breakpoints

## 14) Dev setup pointers
- Use Ethers.js with MetaMask provider (UMD or bundler)
- Contract address should come from an environment-specific config (or a UI input in /settings for dev)
- Include a small utility to shorten addresses (0xabc…1234)

## 15) Mock data (for UI dev without chain)
```json
{
  "election": { "active": true, "totalCandidates": 2, "totalVotes": 1 },
  "candidates": [
    { "id": 1, "name": "Alice", "voteCount": "1" },
    { "id": 2, "name": "Bob", "voteCount": "0" }
  ],
  "voter": { "isAuthorized": true, "hasVoted": false, "votedCandidateId": 0 },
  "winner": null
}
```

## 16) Contract reference
Functions: addCandidate(name), authorizeVoter(addr), vote(id), endElection()
Views: isElectionActive(), getAllCandidates(), getVoterInfo(addr), getWinnerDetails()
Events: CandidateAdded, VoterAuthorized, VoteCast, ElectionEnded

Target chain: Sepolia (11155111)
