# VoteChain V3 Kiosk Frontend - Design Specification

## Project Overview
**System Name:** VoteChain V3 - Blockchain Voting Kiosk System  
**Architecture:** 4-Tier Cyber-Physical Voting System  
**Target Device:** Raspberry Pi 5 with Touchscreen (Kiosk Mode)  
**User Type:** In-person voters at polling booth (no crypto wallet required)

---

## 1. SYSTEM CONTEXT & WORKFLOW

### Complete User Journey
1. **Check-In** → Voter arrives at front desk, staff enters Aadhaar ID
2. **Biometric Verification** → Fingerprint scan + Live face photo capture
3. **Voting Interface** → Voter selects candidate on touchscreen
4. **Confirmation** → Vote submitted to blockchain, receipt displayed
5. **Exit** → Voter leaves, kiosk resets for next person

### Backend Integration Points
- **API Base URL:** `http://localhost:3000` (or production server IP)
- **Endpoint 1:** `POST /api/voter/check-in` - Verify voter eligibility
- **Endpoint 2:** `POST /api/vote` - Submit vote to blockchain

---

## 2. FRONTEND APPLICATION STRUCTURE

### Technology Stack Recommendations
- **Framework:** React.js or Vue.js (for component-based UI)
- **Alternative:** Electron.js (for full-screen kiosk app with hardware access)
- **Styling:** Tailwind CSS or Material-UI (for accessibility & responsive design)
- **State Management:** React Context API or Vuex
- **HTTP Client:** Axios for API calls
- **Hardware Integration:** Python scripts called via Node.js child processes

### Screen Flow Architecture
```
┌─────────────────────┐
│   Idle Screen       │ ← Attracts attention, "Touch to Start"
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Check-In Screen    │ ← Staff enters Aadhaar ID
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Biometric Screen    │ ← Fingerprint + Face capture
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Voting Screen      │ ← Candidate selection
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Confirmation Screen │ ← Success/Error message
└──────────┬──────────┘
           ↓
     [Back to Idle]
```

---

## 3. DETAILED SCREEN SPECIFICATIONS

### SCREEN 1: Idle / Welcome Screen

**Purpose:** Attract voters and provide instructions when kiosk is not in use

**Visual Elements:**
- **Logo:** VoteChain logo/seal (top center, ~150x150px)
- **Primary Text:** "Welcome to VoteChain Electronic Voting"
- **Subtext:** "Touch anywhere to begin voting"
- **Animation:** Pulsing "Tap Here" icon or gentle fade-in/fade-out text
- **Background:** Clean white/light blue gradient (official, non-partisan)
- **Language Toggle:** Small flags/icons in bottom corner (English, Hindi, Regional)

**Interaction:**
- Touch anywhere on screen → Transition to Check-In Screen
- Auto-reset to this screen after 30 seconds of inactivity on any other screen

**Design Notes:**
- Large, readable fonts (min 36px for primary text)
- High contrast for visibility in polling booth lighting
- No scrolling required - all content visible on one screen

---

### SCREEN 2: Check-In Screen

**Purpose:** Staff enters voter's Aadhaar ID to verify eligibility

**Visual Layout:**
```
┌────────────────────────────────────────┐
│  [VoteChain Logo]                      │
│                                        │
│        Voter Check-In                  │
│                                        │
│  Enter Aadhaar Number:                 │
│  ┌──────────────────────────────────┐ │
│  │ [12-digit number input field]    │ │
│  └──────────────────────────────────┘ │
│                                        │
│         [Verify Voter] Button          │
│                                        │
│  Status Message Area (hidden/visible) │
│                                        │
│          [← Back] [Cancel X]           │
└────────────────────────────────────────┘
```

**UI Elements:**

1. **Input Field:**
   - Type: Numeric keyboard only
   - Max length: 12 digits (Aadhaar format: XXXX XXXX XXXX)
   - Auto-format with spaces (e.g., 1234 5678 9012)
   - Large font size: 32px
   - Validation: Red border if invalid length on blur

2. **Verify Button:**
   - Size: 200px × 60px (large, easy to tap)
   - Color: Primary blue (#135bec)
   - Text: "Verify Voter" (white, bold, 24px)
   - States:
     - Default: Blue background
     - Hover: Darker blue
     - Disabled: Gray (until 12 digits entered)
     - Loading: Show spinner + "Verifying..."

3. **Status Message Area:**
   - Initially hidden
   - Success State (green background):
     - "✓ Voter Found: [Name]"
     - "Proceeding to biometric verification..."
     - Auto-advance after 2 seconds
   - Error States (red background):
     - "✗ Voter not found in database"
     - "✗ Voter has already voted"
     - Stay on screen, allow retry

4. **Navigation Buttons:**
   - Back button: Top-left, returns to Idle
   - Cancel button: Top-right, returns to Idle

**API Integration:**
```javascript
// Sample API call
POST /api/voter/check-in
Headers: { "Content-Type": "application/json" }
Body: { "aadhaar_id": "123456789012" }

// Expected Response (Success):
{
  "status": "success",
  "message": "Voter eligible.",
  "data": {
    "name": "John Doe",
    "fingerprint_id": "FP-001",
    "photo_url": "https://supabase.co/storage/voters/photo.jpg"
  }
}

// Expected Response (Error):
{
  "status": "error",
  "message": "Voter not found." // or "Voter has already voted."
}
```

**State Management:**
- Store voter data (name, fingerprint_id, photo_url) in component state
- Pass data to next screen via props/context
- Clear state when returning to Idle

---

### SCREEN 3: Biometric Verification Screen

**Purpose:** Capture fingerprint and live face photo to confirm voter identity

**Visual Layout:**
```
┌────────────────────────────────────────┐
│  Verifying: [Voter Name]               │
│                                        │
│  Step 1: Place finger on scanner      │
│  ┌──────────────────────────────────┐ │
│  │   [Fingerprint Icon Animation]   │ │
│  │   Status: Scanning... / Match ✓  │ │
│  └──────────────────────────────────┘ │
│                                        │
│  Step 2: Look at camera                │
│  ┌──────────────────┬────────────────┐│
│  │  [Live Camera    │ [Reference     ││
│  │   Feed - 320x240]│  Photo from DB]││
│  └──────────────────┴────────────────┘│
│                                        │
│     [Capture Photo & Verify] Button    │
│                                        │
│  Progress: ████████░░ (80%)            │
└────────────────────────────────────────┘
```

**UI Elements:**

1. **Voter Name Display:**
   - Top banner, bold, 28px
   - Format: "Verifying: John Doe"

2. **Fingerprint Section:**
   - Large fingerprint icon (SVG animation)
   - Animation: Pulsing rings while scanning
   - Status text updates:
     - "Place finger on scanner..."
     - "Scanning fingerprint..." (spinner)
     - "✓ Fingerprint matched!" (green checkmark)
     - "✗ Fingerprint mismatch. Try again." (red X)
   - Background color changes: gray → blue (scanning) → green (match) / red (fail)

3. **Face Verification Section:**
   - **Live Camera Feed:** 
     - Size: 320×240px
     - Frame rate: 15-30 FPS
     - Border: Thick border, changes color (gray → green when face detected)
     - Overlay: Face detection rectangle (using ML library like face-api.js)
   - **Reference Photo:**
     - Same size: 320×240px
     - Loaded from `photo_url` in API response
     - Border: Thin gray border
     - Label: "Database Photo"

4. **Capture Button:**
   - Only enabled after fingerprint match
   - Text: "Capture Photo & Verify"
   - Size: 250px × 60px
   - Action: 
     - Takes snapshot from camera feed
     - Compares with reference photo (local ML or send to backend)
     - If match confidence > 70% → Proceed to Voting Screen
     - If failed → Show error, allow 2 more attempts

5. **Progress Bar:**
   - Shows completion percentage (fingerprint = 50%, face = 100%)
   - Color: Blue → Green when complete

**Hardware Integration:**
- **Fingerprint Reader (R307):** 
  - Python script: `read_fingerprint.py` returns fingerprint_id
  - Call via Node.js: `const {exec} = require('child_process'); exec('python read_fingerprint.py')`
  - Compare returned ID with `fingerprint_id` from database
- **Camera (Raspberry Pi Camera Module):**
  - Access via browser WebRTC API: `navigator.mediaDevices.getUserMedia({video: true})`
  - Capture frame: Canvas element `.toDataURL('image/jpeg')`

**Face Matching Options:**
- **Option A (Local):** Use face-api.js or TensorFlow.js for browser-side face comparison
- **Option B (Backend):** Send captured photo to new endpoint `POST /api/verify-face` for server-side matching

**Error Handling:**
- Fingerprint fails 3 times → Show "Contact Polling Official" message
- Face match fails 3 times → Same override option
- Camera not detected → Show error + manual override button for staff

---

### SCREEN 4: Voting Screen (PRIMARY INTERACTION)

**Purpose:** Display candidates and allow voter to select one

**Visual Layout:**
```
┌────────────────────────────────────────┐
│  Voting for: [Election Name]           │
│  Voter: [Name] (ID: XXXX)              │
│                                        │
│  Select Your Candidate:                │
│  ┌──────────────────────────────────┐ │
│  │ ┌──────┐                         │ │
│  │ │Photo │  Candidate 1 Name       │ │
│  │ │100px │  Party: XYZ             │ │
│  │ └──────┘  [   Select   ]         │ │
│  ├──────────────────────────────────┤ │
│  │ ┌──────┐                         │ │
│  │ │Photo │  Candidate 2 Name       │ │
│  │ │100px │  Party: ABC             │ │
│  │ └──────┘  [   Select   ]         │ │
│  ├──────────────────────────────────┤ │
│  │ ┌──────┐                         │ │
│  │ │Photo │  Candidate 3 Name       │ │
│  │ │100px │  Party: DEF             │ │
│  │ └──────┘  [   Select   ]         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  [NOTA - None of the Above] Button     │
└────────────────────────────────────────┘
```

**Data Source:**
- Fetch candidates from blockchain contract via backend
- New endpoint (optional): `GET /api/candidates` which calls `contract.getAllCandidates()`
- Or: Store candidates in frontend config if static for election duration

**Candidate Data Structure:**
```javascript
{
  id: 1,
  name: "Candidate Name",
  party: "Party Name",
  photo_url: "https://path/to/photo.jpg" // or default avatar
  voteCount: 0 // Don't display to voter (privacy)
}
```

**UI Elements:**

1. **Candidate Cards:**
   - Layout: Vertical list (scrollable if > 5 candidates)
   - Card structure:
     - Photo: 100×100px circle, left-aligned
     - Name: Bold, 26px, primary color
     - Party: Regular, 18px, gray
     - Select Button: Right-aligned, 120×50px, primary blue
   - Hover state: Entire card highlights with border
   - Selected state: Card background turns light blue, checkmark appears

2. **Select Button:**
   - Text: "Select" (unselected) → "Selected ✓" (after click)
   - Color: Blue (unselected) → Green (selected)
   - Only ONE candidate can be selected at a time (radio button behavior)
   - After selection, show confirmation dialog

3. **NOTA Option:**
   - Separate button below candidate list
   - Size: Full width, 300×60px
   - Color: Gray/neutral
   - Text: "NOTA - None of the Above"
   - Same selection behavior as candidate buttons

4. **Confirmation Dialog (Modal):**
   - Appears after clicking any Select button
   - Content:
     ```
     Confirm Your Vote
     
     You have selected:
     [Candidate Name]
     [Party Name]
     
     This action is PERMANENT and cannot be changed.
     
     [← Go Back]  [Confirm Vote ✓]
     ```
   - Go Back: Closes dialog, stays on voting screen
   - Confirm Vote: Submits vote via API → Proceeds to Confirmation Screen

**Accessibility Features:**
- Large buttons (min 120×50px) for easy touch on all candidate options
- High contrast text (WCAG AA compliant)
- Voice-over support (optional): Text-to-speech reads candidate names
- Language toggle (if multilingual support needed)

**API Integration:**
```javascript
// Vote submission
POST /api/vote
Headers: { "Content-Type": "application/json" }
Body: { 
  "aadhaar_id": "123456789012", // from previous screen state
  "candidate_id": 1 
}

// Expected Response (Success):
{
  "status": "success",
  "message": "Vote officially recorded on-chain.",
  "transaction_hash": "0xabc123..."
}

// Expected Response (Error):
{
  "status": "error",
  "message": "Double voting detected!" // or "Blockchain transaction failed."
}
```

**Loading States:**
- Show spinner overlay during API call
- Text: "Submitting your vote to blockchain... This may take a few seconds."
- Disable all buttons during submission

---

### SCREEN 5: Confirmation Screen

**Purpose:** Display vote submission result and receipt

**Visual Layout (Success):**
```
┌────────────────────────────────────────┐
│        ✓ Vote Successfully Cast!       │
│                                        │
│  Your vote has been permanently        │
│  recorded on the blockchain.           │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Receipt Details:                 │ │
│  │ Voter: [Name]                    │ │
│  │ Aadhaar: XXXX-XXXX-9012          │ │
│  │ Date: Nov 20, 2025 14:30         │ │
│  │ Transaction: 0xabc1...3456       │ │
│  │ [QR Code - optional]             │ │
│  └──────────────────────────────────┘ │
│                                        │
│  Thank you for voting in a secure      │
│  and transparent election!             │
│                                        │
│  [Print Receipt] [Exit] (auto 10s)     │
└────────────────────────────────────────┘
```

**Visual Layout (Error):**
```
┌────────────────────────────────────────┐
│        ✗ Vote Submission Failed        │
│                                        │
│  Error: [Error message from backend]   │
│  (e.g., "Double voting detected!")     │
│                                        │
│  Please contact a polling official     │
│  for assistance.                       │
│                                        │
│  Error Code: #E-12345                  │
│  Time: Nov 20, 2025 14:30              │
│                                        │
│  [Try Again]  [Contact Official]       │
└────────────────────────────────────────┘
```

**UI Elements (Success State):**

1. **Success Icon:**
   - Large green checkmark (SVG, 120×120px)
   - Fade-in animation on screen load

2. **Receipt Box:**
   - White card with border, centered
   - Contents:
     - Voter name (partially masked for privacy)
     - Aadhaar: Show only last 4 digits (XXXX-XXXX-9012)
     - Date/Time: Local timestamp
     - Transaction Hash: First 10 + last 6 characters (0xabc1...3456)
     - QR Code (optional): Encodes transaction hash for verification app
   - Font: Monospace for transaction hash (for clarity)

3. **Buttons:**
   - **Print Receipt:** Opens browser print dialog (if printer connected)
   - **Exit:** Returns to Idle Screen immediately
   - **Auto-exit:** Screen auto-returns to Idle after 10 seconds countdown
     - Show timer: "Returning to home in 10..."

**UI Elements (Error State):**

1. **Error Icon:**
   - Large red X icon
   - Shake animation on load

2. **Error Message:**
   - Display exact error from backend API
   - Common errors:
     - "Voter has already voted." → Offer "View Receipt" option (if stored)
     - "Blockchain transaction failed." → Offer "Try Again"
     - "Network error." → "Check internet connection"

3. **Action Buttons:**
   - **Try Again:** Return to Voting Screen (if transient error)
   - **Contact Official:** Show polling booth phone number or open help dialog

**Data Display:**
- Parse `transaction_hash` from API response
- Format timestamp: Use `new Date().toLocaleString()` or moment.js
- QR Code generation: Use library like `qrcode.react` to encode TX hash

---

## 4. GLOBAL UI ELEMENTS

### Header Bar (Present on all screens except Idle)
- **Position:** Fixed top, 60px height
- **Elements:**
  - Left: VoteChain logo (40×40px) + App Name (18px)
  - Center: Screen title (e.g., "Check-In", "Biometric Verification")
  - Right: 
    - Timer icon + Session time (e.g., "2:45" for 2 min 45 sec)
    - Help icon (opens help dialog)
    - Exit icon (returns to Idle with confirmation)

### Footer Bar (Present on all screens)
- **Position:** Fixed bottom, 40px height
- **Elements:**
  - Left: "Powered by VoteChain V3"
  - Right: Current time + Network status indicator (green dot = online)

### Loading Spinner Component
- **Type:** Full-screen overlay with semi-transparent backdrop
- **Spinner:** Custom SVG animation (rotating circles)
- **Text:** Context-specific (e.g., "Verifying voter...", "Submitting vote...")

### Error/Success Toast Notifications
- **Position:** Top-center, 400px width
- **Duration:** 5 seconds auto-dismiss (or manual close)
- **Types:**
  - Success: Green background, checkmark icon
  - Error: Red background, X icon
  - Warning: Yellow background, exclamation icon

---

## 5. DESIGN SYSTEM & BRANDING

### Color Palette
```css
/* Primary Colors */
--primary-blue: #135bec;
--primary-blue-hover: #0d47b8;
--primary-blue-light: rgba(19, 91, 236, 0.1);

/* Semantic Colors */
--success-green: #10b981;
--error-red: #ef4444;
--warning-yellow: #f59e0b;

/* Neutral Colors */
--background-light: #f6f6f8;
--background-dark: #101622;
--text-primary: #1f2937;
--text-secondary: #6b7280;
--border-gray: #d1d5db;

/* Election-specific (non-partisan) */
--voting-card-bg: #ffffff;
--kiosk-bg-gradient: linear-gradient(135deg, #f6f6f8 0%, #e5e7eb 100%);
```

### Typography
```css
/* Font Family */
--font-primary: 'Inter', 'Segoe UI', sans-serif; /* Clean, readable */
--font-mono: 'Roboto Mono', monospace; /* For transaction hashes */

/* Font Sizes */
--text-xs: 12px;   /* Small labels */
--text-sm: 14px;   /* Secondary text */
--text-base: 16px; /* Body text */
--text-lg: 18px;   /* Subheadings */
--text-xl: 24px;   /* Headings */
--text-2xl: 32px;  /* Large headings */
--text-3xl: 48px;  /* Welcome screen */

/* Font Weights */
--weight-normal: 400;
--weight-medium: 500;
--weight-bold: 700;
```

### Button Styles
```css
/* Primary Button */
.btn-primary {
  background: var(--primary-blue);
  color: white;
  padding: 16px 32px;
  border-radius: 8px;
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(19, 91, 236, 0.3);
  transition: all 0.3s ease;
}
.btn-primary:hover {
  background: var(--primary-blue-hover);
  transform: translateY(-2px);
}

/* Secondary Button (Gray/Neutral) */
.btn-secondary {
  background: #f3f4f6;
  color: var(--text-primary);
  border: 2px solid var(--border-gray);
}

/* Success Button */
.btn-success {
  background: var(--success-green);
  color: white;
}

/* Danger/Cancel Button */
.btn-danger {
  background: var(--error-red);
  color: white;
}
```

### Card/Panel Styles
```css
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--border-gray);
}

.card-hover {
  transition: all 0.3s ease;
}
.card-hover:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: var(--primary-blue);
}
```

### Icon Library
- **Recommendation:** Use Heroicons or Material Icons (free, SVG-based)
- **Required Icons:**
  - Checkmark (success)
  - X / Close (error, cancel)
  - Fingerprint (biometric)
  - Camera (photo capture)
  - User (voter profile)
  - Clock (time/countdown)
  - Document (receipt)
  - Warning triangle
  - Information circle
  - Arrow left/right (navigation)

---

## 6. RESPONSIVE DESIGN & SCREEN SIZES

### Primary Target Device
- **Device:** Raspberry Pi 5 with official 7-inch touchscreen
- **Resolution:** 800×480 pixels (landscape) or 480×800 (portrait)
- **Touch Input:** Capacitive touch (min button size: 44×44px per Apple HIG)

### Orientation
- **Recommended:** Landscape (800×480) for better candidate list view
- **Alternative:** Portrait (480×800) if mounted vertically (may require scrolling)

### Scalability Guidelines
- All elements should scale proportionally if deployed on larger displays (e.g., 10" or 15" kiosks)
- Use `rem` units for font sizes (base: 16px)
- Use percentage or `vh`/`vw` for layout dimensions
- Test on both orientations during development

---

## 7. ACCESSIBILITY REQUIREMENTS

### WCAG 2.1 Level AA Compliance
- **Color Contrast:** 
  - Text: Minimum 4.5:1 ratio for normal text, 3:1 for large text
  - Interactive elements: 3:1 ratio for borders/icons
- **Touch Targets:**
  - Minimum size: 44×44px (Apple) or 48×48px (Material Design)
  - Spacing: Minimum 8px between adjacent touchable elements
- **Keyboard Navigation:** Not required for touchscreen-only kiosk, but tab order should be logical if keyboard used
- **Screen Reader Support:** 
  - Use semantic HTML (buttons, headings, labels)
  - Add `aria-label` attributes for icon buttons
  - Announce status changes (e.g., "Vote submitted successfully")

### Multilingual Support (If Required)
- **Language Switcher:** Flag icons or dropdown in top-right corner
- **Supported Languages:** English (default), Hindi, [Regional Language]
- **Translation Files:** JSON format (`en.json`, `hi.json`, etc.)
- **Right-to-Left (RTL):** Plan for future Arabic/Urdu support if needed

### Timeout & Auto-Reset
- **Idle Timeout:** Return to Idle Screen after 60 seconds of no interaction on Check-In screen
- **Security Timeout:** Auto-logout after 5 minutes on Biometric/Voting screens (to prevent voter walking away mid-session)
- **Countdown Warning:** Show "Session expiring in 30 seconds..." dialog with "Continue" button

---

## 8. SECURITY & PRIVACY CONSIDERATIONS

### Data Handling
- **PII (Personally Identifiable Information):**
  - Aadhaar ID: Only last 4 digits displayed on receipt
  - Voter Name: Only first name + last initial on receipt (e.g., "John D.")
  - Photos: Live camera feed NOT stored permanently (deleted after verification)
- **Local Storage:**
  - Clear all voter data from browser/app after each session ends
  - No persistent cookies or localStorage containing PII
- **Network Security:**
  - API calls to backend over HTTPS (even on local network)
  - Validate SSL certificates in production

### Fraud Prevention UI Elements
- **Dual Verification Indicators:**
  - Show green checkmarks for both fingerprint AND face match before allowing vote
  - Display "Verification Status: 2/2 Complete" counter
- **"Already Voted" Warning:**
  - If API returns "has_voted: true", display prominent red banner:
    - "STOP: This Aadhaar ID has already voted in this election."
    - "Contact polling official if you believe this is an error."
- **Transaction Hash Display:**
  - Always show TX hash on receipt for audit trail
  - Provide QR code for voters to independently verify on blockchain explorer

---

## 9. PERFORMANCE REQUIREMENTS

### Response Times
- **Page Load:** < 2 seconds for any screen transition
- **API Calls:** 
  - Check-in: < 1 second response time
  - Vote submission: < 5 seconds (blockchain confirmation)
  - Show loading spinner if > 2 seconds
- **Camera Feed:** 15-30 FPS (minimum for smooth face detection)
- **Hardware Interaction:**
  - Fingerprint scan: < 3 seconds
  - Face capture: < 1 second

### Network Resilience
- **Offline Detection:**
  - If no internet, show red "Offline" indicator in footer
  - Disable voting (blockchain requires network)
  - Show error message: "Network unavailable. Please check connection."
- **Retry Logic:**
  - Auto-retry failed API calls up to 3 times with exponential backoff
  - Show "Retrying... (Attempt 2/3)" message to user

### Memory & Storage
- **App Size:** Target < 50 MB (excluding dependencies)
- **Local Storage:** Clear session data after each voter (prevent memory leaks)
- **Image Optimization:** 
  - Candidate photos: Max 200 KB each, compressed JPG/PNG
  - Reference photos: Max 100 KB, compressed

---

## 10. TESTING SCENARIOS FOR DESIGNER/DEVELOPER

### Functional Testing Checklist
1. **Happy Path:**
   - [ ] Idle → Check-In (valid Aadhaar) → Biometric (both match) → Voting → Confirm → Success receipt
2. **Error Paths:**
   - [ ] Invalid Aadhaar format (non-numeric, wrong length)
   - [ ] Aadhaar not found in database
   - [ ] Voter already voted (database flag)
   - [ ] Fingerprint mismatch (3 attempts)
   - [ ] Face mismatch (3 attempts)
   - [ ] Network failure during vote submission
   - [ ] Blockchain transaction revert (double-vote on-chain)
3. **Edge Cases:**
   - [ ] Camera not detected (hardware error)
   - [ ] Fingerprint reader not detected
   - [ ] Session timeout during voting
   - [ ] Multiple rapid button presses (prevent double-submission)
   - [ ] Browser back button pressed (should be disabled in kiosk mode)

### Visual Testing
- [ ] All text is readable from 2 feet away (polling booth distance)
- [ ] Buttons are large enough for elderly voters with shaky hands
- [ ] Color-blind mode test (ensure green/red are distinguishable)
- [ ] High-contrast mode for low-vision users

---

## 11. MOCKUP REFERENCES & ASSETS NEEDED

### Assets to Provide to Designer
1. **VoteChain Logo:**
   - SVG format (scalable)
   - PNG fallback (300×300px, transparent background)
   - Variations: Full color, monochrome, white-on-dark

2. **Candidate Photos:**
   - Format: Square (1:1 ratio), 400×400px minimum
   - File size: < 200 KB each
   - Background: Solid color or neutral
   - Naming: `candidate-1.jpg`, `candidate-2.jpg`, etc.

3. **Icons:**
   - Fingerprint scan icon (animated SVG if possible)
   - Camera/photo icon
   - Success checkmark icon
   - Error X icon
   - NOTA symbol (if specific icon needed)
   - All 24×24px and 48×48px sizes

4. **Animations:**
   - Loading spinner (SVG animation)
   - Fingerprint scanning pulse effect
   - Success confetti (optional, subtle)
   - Error shake effect

5. **Sample Data (for mockups):**
   - 3-5 dummy candidate profiles (name, party, photo)
   - Sample Aadhaar IDs: 123456789012, 987654321098
   - Sample voter name: "John Doe", "Priya Sharma"

---

## 12. BACKEND API SUMMARY (For Frontend Integration)

### Endpoint Reference
```
BASE_URL: http://localhost:3000 (development)
          https://your-server.com (production)

Endpoints:
1. POST /api/voter/check-in
   Body: { aadhaar_id: string }
   Returns: { status, message, data: { name, fingerprint_id, photo_url } }

2. POST /api/vote
   Body: { aadhaar_id: string, candidate_id: number }
   Returns: { status, message, transaction_hash }

3. GET /api/candidates (optional, if not hardcoded)
   Returns: { candidates: [ { id, name, party, photo_url } ] }
```

### Error Handling
- **HTTP Status Codes:**
  - 200: Success
  - 400: Bad request (invalid data format)
  - 403: Forbidden (already voted)
  - 404: Not found (Aadhaar not in database)
  - 500: Server error (blockchain/database failure)
- **Error Response Format:**
  ```json
  {
    "status": "error",
    "message": "User-friendly error message here"
  }
  ```

---

## 13. DEVELOPER HANDOFF NOTES

### Technology Setup
1. **Install Dependencies:**
   ```bash
   npm install react react-dom axios
   npm install tailwindcss postcss autoprefixer
   npm install qrcode.react # For QR codes
   npm install face-api.js # For face detection (optional)
   ```

2. **Environment Variables (.env file):**
   ```
   REACT_APP_API_BASE_URL=http://localhost:3000
   REACT_APP_ELECTION_NAME="2025 General Election"
   ```

3. **Camera Permissions:**
   - Add to `index.html` or `App.js`:
   ```javascript
   navigator.mediaDevices.getUserMedia({ video: true })
     .then(stream => { /* Use stream */ })
     .catch(err => console.error('Camera access denied', err));
   ```

### State Management Example (React Context)
```javascript
// contexts/VoterContext.js
import { createContext, useState } from 'react';

export const VoterContext = createContext();

export const VoterProvider = ({ children }) => {
  const [voterData, setVoterData] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  return (
    <VoterContext.Provider value={{
      voterData, setVoterData,
      selectedCandidate, setSelectedCandidate
    }}>
      {children}
    </VoterContext.Provider>
  );
};
```

### Routing Setup (React Router or state-based)
```javascript
// App.js (simplified)
const [currentScreen, setCurrentScreen] = useState('idle');

return (
  <VoterProvider>
    {currentScreen === 'idle' && <IdleScreen onStart={() => setCurrentScreen('checkin')} />}
    {currentScreen === 'checkin' && <CheckInScreen onNext={() => setCurrentScreen('biometric')} />}
    {currentScreen === 'biometric' && <BiometricScreen onNext={() => setCurrentScreen('voting')} />}
    {currentScreen === 'voting' && <VotingScreen onNext={() => setCurrentScreen('confirmation')} />}
    {currentScreen === 'confirmation' && <ConfirmationScreen onExit={() => setCurrentScreen('idle')} />}
  </VoterProvider>
);
```

### Kiosk Mode Configuration
- **Disable Browser UI:**
  - Run in Electron with `frame: false` or use Chromium in kiosk mode:
  ```bash
  chromium-browser --kiosk --incognito http://localhost:3000
  ```
- **Disable Context Menu:** Add to `index.html`:
  ```javascript
  document.addEventListener('contextmenu', e => e.preventDefault());
  ```
- **Disable F11/Escape Keys:** Capture keydown events and prevent default

---

## 14. FINAL DESIGN DELIVERABLES CHECKLIST

### For Designer to Provide:
- [ ] High-fidelity mockups for all 5 screens (Figma/Sketch/Adobe XD)
- [ ] Interactive prototype (click-through flow) to demo user journey
- [ ] Design system documentation (colors, typography, spacing)
- [ ] Component library (buttons, cards, inputs, modals)
- [ ] Icon set (SVG files, 24px and 48px)
- [ ] Animation specifications (duration, easing, keyframes)
- [ ] Responsive breakpoints (if supporting multiple display sizes)
- [ ] Accessibility audit report (color contrast, touch target sizes)

### For Developer to Provide:
- [ ] Frontend application (React/Vue/Electron build)
- [ ] API integration layer (Axios service with error handling)
- [ ] Hardware interface scripts (camera, fingerprint reader)
- [ ] Kiosk deployment guide (Raspberry Pi setup instructions)
- [ ] User testing report (usability findings from pilot voters)

---

## 15. ADDITIONAL CONSIDERATIONS

### Future Enhancements (Out of Scope for V1)
- **Admin Dashboard:** Separate web app for election officials to monitor kiosk status, view live vote counts
- **Multi-Factor Auth:** SMS OTP backup if biometric fails
- **Blockchain Explorer Integration:** Link to public blockchain explorer for voters to independently verify their vote
- **Receipt Printing:** Thermal printer integration for paper receipts
- **Voice Guidance:** Audio instructions for visually impaired voters
- **Sign Language Videos:** Embedded video guides for deaf voters

### Legal & Compliance
- **Data Protection:** Ensure GDPR/DPDP Act compliance (if in EU/India)
- **Audit Trail:** All voter interactions logged (anonymized) for election commission review
- **Certification:** Election technology may require certification from election commission (varies by country)

---

## CONTACT FOR QUESTIONS

**Project Lead:** [Your Name]  
**Backend Developer:** [Backend Dev Name]  
**Frontend Designer:** [Designer Name]  
**Hardware Engineer:** [Hardware Dev Name]  

**Repository:** https://github.com/cainebenoy/blockchain-voting-dapp-v3  
**API Documentation:** [Link to Swagger/Postman collection]

---

**Document Version:** 1.0  
**Last Updated:** November 20, 2025  
**Status:** Ready for Design & Development  
