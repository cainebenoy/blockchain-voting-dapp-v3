## Troubleshooting & FAQ

This page collects common issues and how to resolve them quickly.

- Not authorized kiosk signer
  - Symptoms: backend or kiosk logs show `Not authorized kiosk signer`.
  - Fix: ensure `VOTING_CONTRACT_ADDRESS` is set and run `npx hardhat run scripts/authorize-signer.ts --network sepolia`.
  - Verify: call contract `officialSigner()` via Hardhat console or view on Etherscan.

- Supabase connection failures
  - Symptoms: backend fails at startup with missing env or database errors.
  - Fix: confirm `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env` and ensure the service role key is valid.

- Fingerprint enrollment failures
  - Symptoms: kiosk logs `sensor not found` or enrollment times out.
  - Fix: check that serial port (`/dev/ttyAMA0`) exists, that the user is in `dialout` group and that the sensor has power.

- Transaction timeouts
  - Symptoms: `tx.wait()` times out but the transaction eventually succeeds.
  - Fix: increase RPC timeout, check RPC provider health, and confirm sufficient gas/ETH balance.

- Kiosk GPIO errors
  - Fix: ensure kiosk runs with required privileges (GPIO access), use `sudo -E` where appropriate, and double-check pin mappings in `kiosk_main.py`.

If the above steps do not resolve the issue, check `backend/server.log` and open an issue with logs attached (sanitize secrets first).
