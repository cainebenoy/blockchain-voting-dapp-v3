# System Requirements Specification (SyRS)
\n## VoteChain V3 — Blockchain Voting DApp

## 1. Introduction

This document defines the hardware, software, network, and operational requirements for deploying and running the VoteChain V3 blockchain voting system.

---

### 2. Hardware Requirements

- **Kiosk Device:** Raspberry Pi 5 (4GB RAM minimum, 8GB+ recommended)
- **Peripherals:**
  - Fingerprint scanner (R307 or compatible)
  - OLED display (I2C/SPI, 128x64 recommended)
  - Physical buttons (GPIO)
  - Official Raspberry Pi power supply
- **Storage:** 16GB microSD (32GB+ recommended)
- **Network:** Ethernet or stable Wi-Fi

---

### 3. Software Requirements

- **Operating System:**
  - Raspberry Pi OS 64-bit (Bookworm) or Ubuntu Server 24.04 LTS (arm64)
- **Backend:**
  - Node.js v18.x or v20.x (LTS)
  - Express.js v5
  - Ethers.js v6
  - Supabase JS Client v2
- **Frontend:**
  - Static HTML5, Tailwind CSS, vanilla JavaScript
  - Python 3.9+ (for kiosk hardware integration)
- **Database:**
  - Supabase (PostgreSQL, cloud-hosted)
- **Blockchain:**
  - Ethereum Sepolia testnet
  - Hardhat 3.x (for contract deployment/testing)
- **Other Tools:**
  - Cloudflare Tunnel (for secure backend exposure)
  - Systemd (for service management)
  - Git (for version control)

---

### 4. Network & Connectivity Requirements

- **Backend API:** Accessible on port 3000 (default)
- **Frontend:** Served on port 8000 (default) or via GitHub Pages
- **Service Discovery:** Supabase config table must be reachable by frontend and backend
- **Blockchain RPC:** Outbound HTTPS access to Sepolia RPC (Alchemy/Infura)
- **Cloudflare Tunnel:** Outbound HTTPS for tunnel setup

---

### 5. Security Requirements

- **Environment Variables:** All secrets (API keys, private keys) stored in `.env` files, never committed
- **Database:** Row Level Security (RLS) enabled on Supabase tables
- **API:** Rate limiting, CORS, and audit logging enabled
- **System:** Services run under dedicated user accounts with minimal privileges

---

### 6. Operational Requirements

- **Service Management:**
  - All major services (backend, kiosk, frontend) managed via systemd or `votechain.sh` script
  - Automatic restart on failure (systemd recommended)
- **Monitoring:**
  - Logs accessible via `votechain.sh logs` or systemd journal
  - Health checks via `/api/health` endpoint
- **Backup:**
  - Regular backup of `.env`, database credentials, and local state

---

### 7. Deployment & Maintenance

- **Initial Setup:**
  - Flash OS image, install dependencies, configure `.env`, deploy contract
- **Updates:**
  - Pull latest code via Git, restart services
- **Testing:**
  - Run `npx hardhat test`, `test-enrollment-flow.sh`, and `test-results-dashboard.sh`
- **Documentation:**
  - Reference `README.md`, `DEPLOYMENT.md`, and `SERVICE_DISCOVERY.md` for setup and troubleshooting

---

### 8. Environmental & Physical Requirements

- **Operating Temperature:** 0°C to 50°C (standard for Raspberry Pi)
- **Physical Security:** Kiosk should be placed in a secure, monitored location

---

### 9. Appendices

- See `docs/HARDWARE.md`, `DEPLOYMENT.md`, and `SECURITY.md` for detailed setup and security practices.
