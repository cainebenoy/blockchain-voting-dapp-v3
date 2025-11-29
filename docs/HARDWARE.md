## Raspberry Pi / Kiosk Hardware Setup

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
