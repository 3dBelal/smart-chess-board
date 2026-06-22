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
