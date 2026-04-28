# ✋ Air Typing System

Real-time hands-free virtual keyboard using computer vision and hand gesture recognition.
Type in mid-air — no physical keyboard needed.

---

## How It Works

```
Camera Feed → MediaPipe Hand Landmarks → Finger Position Tracking
     → Virtual Keyboard Hover Detection → Pinch Gesture = Key Press
     → Debounced Input → Live Text Display
```

### Gesture Controls

| Gesture | Action |
|---|---|
| Point index finger | Hover/navigate over keys |
| Pinch (thumb + index close) | Press the hovered key |
| Hold pinch on ⌫ | Fast backspace (repeats) |
| Hold pinch on SPACE | Fast space (repeats) |

### AI / ML Components

- **MediaPipe Hands** — Google's ML pipeline for real-time hand landmark detection (21 3D landmarks per hand)
- **Pinch distance normalization** — hand-size-relative threshold so detection works at any camera distance
- **Velocity tracking** — 6-frame position history for smooth cursor movement
- **Gesture debouncer** — prevents accidental multi-fires with configurable cooldown + hold-repeat

---

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

### Options

```bash
python main.py --camera 0       # webcam device ID
python main.py --width 1280     # frame width
python main.py --height 720     # frame height
```

---

## File Structure

```
air_typing/
├── main.py          # Entry point, camera loop, key event handler
├── air_typer.py     # Core engine: tracker, debouncer, renderer, keyboard layout
├── requirements.txt
└── README.md
```

---

## Performance Tips

- **Lighting** — bright, even light on your hand for best detection
- **Background** — plain, non-cluttered background improves tracking
- **Distance** — 40–70 cm from camera is optimal
- **Speed** — type deliberately; a ~0.5s cooldown between keys prevents misfires

---

## Tuning Parameters

In `air_typer.py`:

| Parameter | Default | Effect |
|---|---|---|
| `min_detection_confidence` | 0.72 | Higher = fewer false detections |
| `min_tracking_confidence` | 0.65 | Higher = more stable tracking |
| `GestureDebouncer(cooldown)` | 0.55s | Lower = faster typing possible |
| `HOLD_REPEAT_RATE` | 0.12s | Backspace/space hold-repeat speed |
| Pinch threshold `< 0.28` | 0.28 | Normalized: lower = tighter pinch needed |

---

## Requirements

- Python 3.9+
- Webcam or USB camera
- `opencv-python >= 4.8`
- `mediapipe >= 0.10`
- `numpy >= 1.24`
