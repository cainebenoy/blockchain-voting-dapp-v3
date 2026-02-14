# VoteChain Walkthrough

## 🚀 Overview
VoteChain is a hybrid blockchain voting system that combines the security of Ethereum (Sepolia) with the usability of a traditional web app. It features a Raspberry Pi kiosk for biometric enrollment and a robust admin dashboard for election management.

## 🏗️ Architecture
- **Blockchain**: Ethereum Sepolia Testnet (Smart Contract: `VotingV2.sol`)
- **Backend**: Node.js Express Server
- **Database**: Supabase (PostgreSQL)
- **Frontend**: HTML5/JS (Admin Dashboard, Public Results, Kiosk Simulator)
- **Remote Access**: Ngrok Static Domain

## 🛠️ Recent Fixes & Improvements

### 1. Enable Election Deployment (Admin Dashboard)
- **Issue**: "Deploy New Election" button showed "Feature requires backend deployment script" error.
- **Root Cause**: A duplicate placeholder function in `admin.html` was overriding the real implementation.
- **Fix**: Removed the placeholder and updated the actual `deployNewElection` function.
- **Improvement**: Added `ngrok-skip-browser-warning` header to ensure the deployment request works through the tunnel.

### 2. Robust Blockchain Error Handling
- **Issue**: Technical blockchain errors (execution reverts) were shown as raw logs to the user.
- **Improvement**: 
    - **Frontend Pre-checks**: The "Start Election" button now checks if any candidates exist before calling the API, showing a friendly warning if the list is empty.
    - **Backend Error Parsing**: Updated `backend/routes/admin.js` to extract specific revert reasons (e.g., "Must have at least one candidate") from smart contract exceptions.
- **Result**: You now see clean, helpful "toast" notifications explaining exactly what went wrong.

### 3. Verify Code & Receipt Persistence
- **Issue**: Vote receipts were not being saved to the database, causing "Invalid Code" errors on the Verify page.
- **Root Cause**: The `receipts` table in Supabase was missing the `is_confirmed` and `inserted_at` columns, causing the backend `INSERT` operation to fail explicitly.
- **Fix**: Updated `backend/routes/vote.js` and `vote-queue.js` to stop trying to write to these missing columns. The system now seamlessly adapts to your current database schema.
- **Note**: If you see "Transaction Failed" during verification, it likely means the blockchain contract state is out of sync with your database (e.g., voter already voted on an old deployment). **Deploying a New Election** via the Admin Portal will resolve this clean slate.

### 4. Simulator UI Polish
- **Issue**: The "Election Closed" screen showed the raw text `lock_clock` instead of an icon.
- **Fix**: Corrected the Material Symbols class from `outlined` to `rounded` to match the project's styling.

### 5. Voter Status Update Fix
- **Issue**: Some voters were not being marked as `has_voted: true` in the Supabase table, even though their votes were queued.
- **Root Cause**: The backend was searching for voters using a plain ID but trying to update them using a hashed ID. This only worked for voters stored as hashes, not those stored as plain IDs.
- **Fix**: Refactored the `vote.js` logic to be robust. It now checks for both hashed and plain IDs (like the login flow) and uses the successful identifier to update the status.
- **Result**: Every successful vote is now correctly recorded in the `voters` table, preventing double-voting even at the database layer.

### 6. Ngrok Connectivity & Stability
- **Issue**: `ERR_NGROK_3200` (Tunnel not found) and `ERR_NGROK_4018` (Auth failed).
- **Fixes**:
    - **Heartbeat Logic**: Patched `pi/ngrok_discovery.py` to check `localhost:3000` instead of the public URL, solving a "chicken-and-egg" startup problem.
    - **Authentication**: Automatically configured the Ngrok authtoken via `npx` to enable the static domain.
    - **Backend Crash**: Fixed a critical bug in `public.js` where headers were set after the response, causing the server to crash on `ERR_HTTP_HEADERS_SENT`.
    - **Permissions**: Upgraded `pi/.env` to use the Supabase `service_role` key, allowing the discovery script to update the system config.

## 🧪 How to Test

### 1. Admin Dashboard
- **URL**: `https://remunerable-rhiannon-noncleistogamous.ngrok-free.dev/admin.html`
- **Action**: Login with secret -> Click **"Deploy New Election"**.
- **Expected**: Confirmation dialog appears -> "Initiating Deployment..." toast -> Page reloads after successful deployment.

### 2. Public Results
- **URL**: `https://remunerable-rhiannon-noncleistogamous.ngrok-free.dev/results.html`
- **Action**: View live charts and stats.
- **Expected**: Data loads instantly without CORS errors.

### 3. Kiosk Simulator
- **URL**: `https://remunerable-rhiannon-noncleistogamous.ngrok-free.dev/simulator.html`
- **Action**: Hardware connection status should be green (Online).

## 📜 Key Commands
**Start Everything (Manual Fallback)**:
```bash
# In project root
npx ngrok http --url remunerable-rhiannon-noncleistogamous.ngrok-free.dev 3000
```

**Start Backend Only**:
```bash
cd backend
npm start
```
