# Raspberry Pi / Kiosk Hardware Setup

This document summarises the hardware used by the kiosk and quick setup hints.

Recommended hardware

- Raspberry Pi 5 (or Pi 4 with sufficient CPU)
- R307 fingerprint scanner (UART)
- 128x64 or similar OLED display (SPI)
- Push buttons for candidate selection and start flow
- LEDs and piezo buzzer for feedback

Wiring notes

- Fingerprint (R307): connect via UART to `/dev/ttyAMA0` (TX/RX), power with 5V (or recommended V) and common ground.
- OLED display (SPI): connect to MOSI/MISO/SCLK/CS with DC and RST pins as per `kiosk_main.py` configuration.
- Buttons and LEDs: use BCM pin mappings shown in `README.md` under Hardware Pin Mapping.

Driver & package installs (Raspberry Pi OS)

```bash
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install RPi.GPIO luma.oled adafruit-circuitpython-fingerprint requests pyserial
```

Permissions

- Add the kiosk user to `dialout` for serial access:

```bash
sudo usermod -aG dialout $USER
```

Emulation mode

- To test the kiosk on a development machine without hardware, run kiosk_main.py with `--emulate` (see code comments) or set `EMULATE_HARDWARE=1` in the environment.

## Kiosk behavior notes (receipt handling)

- After submitting a vote to the backend, the kiosk will:
  1. Read `receipt_code` from the `/api/vote` response if present and display it on the OLED.
  2. If `receipt_code` is not returned immediately, the kiosk will poll `/api/lookup-receipt` (with the `tx_hash`) for a short window (default ~60s) to discover a late-inserted code.
  3. If no short code is found within the poll window, the kiosk shows a fallback receipt composed of the truncated transaction hash (e.g., first 10 characters) and instructions to verify on the admin/verify UI.

- Ensure the kiosk can reach the backend (default `http://127.0.0.1:3000` on local deployments). If the kiosk is remote, set the backend URL in `kiosk_main.py` or via environment variable.
