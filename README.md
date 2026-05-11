# Water Intake Tracker

A minimalist desktop app that lives on the side of your screen, tracks
your daily water intake with a single big-fat-button click, and shows
priority-sorted sticky notes next to the water bar.

> **2.0 rewrite (May 2026):** webcam detection, AI mascot, and pop-up
> reminders were removed. The app is now a thin vertical bar with a
> manual gulp button and an embedded sticky-notes column. See
> [`docs/REFORMULACAO.md`](docs/REFORMULACAO.md) for the full design.

## Features

- **Manual gulp button** — click the big drop-shaped button at the
  bottom of the bar. Ripple + splash + bubbles + sound. No webcam.
- **Animated water bar** — wave, bubbles, ML marker labels.
- **Sticky notes column** — sits next to the bar, collapsed to colored
  chips by default. Hover anywhere on the column to expand.
- **3-level priority** — Agora (red), Hoje (amber), Depois (gray).
  Auto-sorted by priority then deadline.
- **Deadlines** — optional per note. Urgent badges appear when <24h.
- **JSON persistence** — `data/progress.json` (hydration, resets daily)
  and `data/notes.json` (notes, never reset).
- **System tray** — single-click toggles bar; double-click opens
  Settings; right-click for menu.

## Download

Pre-built `WaterIntakeTracker.exe` is published on the
[Releases page](../../releases).

### Windows SmartScreen note

Unsigned exe — Windows may warn on first run. Right-click the file →
Properties → check "Unblock", or click "More info → Run anyway" on
the SmartScreen dialog.

## Requirements

- Windows 10/11

That's it. No webcam, no Python, no Ollama.

## Usage

1. Launch the app — a Settings dialog opens (skip with previous values
   on subsequent launches).
2. Set your daily goal (ml) and gulp size, save.
3. The bar appears glued to the right edge of the screen.
4. **Click the drop button** to register a gulp.
5. **Hover the notes column** (the strip to the left of the bar) to
   expand it. Click "+" at the top to add a note.

### Controls

- Click drop button → +1 gulp
- Click note card → edit it
- Click ✓ on expanded card → complete (removes from active list)
- Right-click bar → menu (new note, add/undo gulp, reset, settings,
  exit, etc.)
- Drag the bar to reposition (snaps stay disabled — use "Move to
  other side" in the menu for the canonical flip)
- Tray icon: single-click hide/show; double-click open Settings;
  right-click for menu

## Data

Both files are plain JSON, editable by hand if you really need to:

- `data/progress.json` — today's hydration (resets at midnight)
- `data/notes.json` — sticky notes (never reset, completed notes are
  archived in-file rather than deleted)

## Building from source

```bash
pip install -r requirements.txt
python main.py                 # run from source
python build_installer.py      # build .exe + Inno Setup installer
```

Dependencies: `PyQt5`, `Pillow` (icon conversion only). The "no
webcam, no AI" stack is intentional — the cleanup commit history on
the `refactor/cleanup-and-sticky-notes` branch documents why.

## License

MIT — feel free to fork and tinker.
