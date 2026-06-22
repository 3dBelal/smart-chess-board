# Smart Chess Board

A physical chess board that detects piece positions automatically using reed switches, infers moves using a legal move engine, evaluates positions with Stockfish, and displays the evaluation on a WS2812B LED bar.

Built with an ESP32 microcontroller, a custom Android app, and fully original 3D printed chess pieces.

---

## Features

- Detects all 64 squares via reed switches — no cameras or manual input
- Identifies pieces by legal move inference, not hardware
- Handles castling, en passant, and promotion automatically
- Fully offline — no internet required
- Hot-swappable phone — any phone with the app can join mid-game
- Physical evaluation bar always visible without the phone
- Player profiles with win/loss history
- Game backup and cloud sync when internet is available

---

## Architecture
Physical board (64 reed switches)

└── 8× 74HC165 shift registers

└── ESP32 (board scan, move inference, BLE, LED bar)

└── Android app (Stockfish, board display, chess clock, profiles)

## Project Structure
smart-chess-board/

├── simulation/          # Python simulation layer (complete)

│   ├── board_state.py   # 64-element board array, FEN import/export

│   ├── move_detection.py# Reed switch change detection

│   ├── move_inference.py# Legal move filter — castling, en passant, promotion

│   ├── game_state.py    # Full game state manager, clocks, desync/resync

│   ├── ble_protocol.py  # BLE message format and hot-swap protocol

│   └── simulator.py     # Visual pygame simulator using real game logic

├── firmware/            # ESP32 C++ firmware (coming soon)

├── android/             # Android app — Kotlin (coming soon)

├── hardware/            # Wiring diagrams and schematics (coming soon)

└── docs/                # Build guide and documentation (coming soon)

## Build Status

| Layer | Status |
|---|---|
| Python simulation | Complete |
| ESP32 firmware | In progress |
| Android app | In progress |
| Hardware prototype | Pending components |

---

## Hardware

| Component | Qty | Purpose |
|---|---|---|
| ESP32 DevKit v1 | 1 | Main microcontroller |
| 74HC165 shift register | 8 | Read 64 switches with 3 GPIO pins |
| Reed switch NO 14mm | 64 | Piece detection per square |
| Neodymium magnet 8×3mm | 32 | Embedded in piece bases |
| WS2812B LED strip | 1 | Evaluation bar |
| 10kΩ resistors | 64 | Pull-down for reed switches |

---

## Chess Pieces

All pieces are original designs, modelled in SolidWorks and 3D printed with embedded magnet slots in the base.

---

## Author

Belal — [github.com/3dBelal](https://github.com/3dBelal)
