# AGENTS.md - AIOS Mini-Games

## Project Summary
A simulated AI Operating System containing three distinct mini-games: Memory Match, Arena Shooter, and Poker Hands. The OS features a functional desktop, app grid, taskbar, and clock.

## Core Loop
- **Launcher**: Open apps from the desktop.
- **Memory Match**: Find 8 matching pairs of tech icons.
- **Arena Shooter**: Survive enemy drone waves and score points using WASD/Arrows and Mouse aiming.
- **Poker Hands**: Select cards from a hand to match a quantum goal (Pair, Three of a Kind, etc.).

## Important Files
- `/index.html`: Main OS structure and global styles.
- `/main.js`: OS logic, app switching, and audio management.
- `/MemoryGame.js`: Pair matching logic.
- `/ShooterGame.js`: Top-down canvas shooter.
- `/PokerGame.js`: Hand selection challenge.

## Assets & Audio
- `assets/os_bg.webp`: Desktop wallpaper.
- `assets/audio/os_ambient_loop.mp3`: Ambient OS music.
- `assets/audio/shooter_music_loop.mp3`: Arcade shooter music.
- `assets/player_ship.webp`, `assets/enemy_drone.webp`: Shooter sprites.
- `assets/icon_*.webp`: 8 tech icons for games.

## Controls
- **Global**: Mouse click to open apps, taskbar mute toggle.
- **Memory**: Click cards to flip.
- **Shooter**: WASD/Arrows to move, Mouse to aim/shoot.
- **Poker**: Click cards to select/deselect, click 'ANALYZE' to score.

## Status
- Final validation: Pass.
- Runtime smoke test: Pass.