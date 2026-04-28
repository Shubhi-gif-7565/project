"""
Air Typing System — Main Launcher
Run: python main.py
"""

import cv2
import time
import sys
import argparse
import subprocess
import os

# --- PYTHON VERSION CHECK ---
# MediaPipe has known issues with Python 3.13 on Windows.
# If we are running on 3.13, try to find and use 3.10 instead.
if sys.version_info.major == 3 and sys.version_info.minor == 13:
    print("\n[!] DETECTED PYTHON 3.13: MediaPipe is currently incompatible with this version.")
    py310_path = r"C:\Users\palbh\AppData\Local\Programs\Python\Python310\python.exe"
    
    if os.path.exists(py310_path):
        print(f"[*] AUTO-SWITCHING to Python 3.10 at: {py310_path}")
        # Re-run the current script using Python 3.10
        result = subprocess.run([py310_path] + sys.argv)
        sys.exit(result.returncode)
    else:
        print("[!] ERROR: Python 3.10 not found. Please run using: C:\\Users\\palbh\\AppData\\Local\\Programs\\Python\\Python310\\python.exe main.py")
        sys.exit(1)

# Force UTF-8 for console output to support fancy box-drawing characters
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
from air_typer import (
    HandTracker, GestureDebouncer, Renderer,
    TypingSession, build_keyboard, FingerState
)

def main(camera_id: int = 0, width: int = 1280, height: int = 720):
    print("\n╔══════════════════════════════════════════╗")
    print("║       AIR TYPING SYSTEM  v1.0            ║")
    print("║  Gesture-powered virtual keyboard        ║")
    print("╚══════════════════════════════════════════╝")
    print("\n● Starting camera...")

    # Use CAP_DSHOW for much better reliability on Windows
    cap = cv2.VideoCapture(camera_id + cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Fallback to default if DSHOW fails
        cap = cv2.VideoCapture(camera_id)
        
    if not cap.isOpened():
        print(f"✗ Cannot open camera {camera_id}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Low latency

    # Warmup the camera (some cameras need a second to initialize)
    time.sleep(1.0)
    for _ in range(5):
        cap.read()

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"● Camera opened: {actual_w}×{actual_h}")

    tracker   = HandTracker()
    debouncer = GestureDebouncer(cooldown=0.50)
    renderer  = Renderer(actual_w, actual_h)
    session   = TypingSession()
    keys      = build_keyboard(actual_w, actual_h)

    print(f"● Keyboard: {len(keys)} keys built")
    print("● Controls: Q=quit, C=clear text\n")

    fps_counter = 0
    fps_time    = time.time()
    fps_display = 0.0

    cv2.namedWindow("Air Typer", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Air Typer", actual_w, actual_h)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break

        # Mirror for intuitive use
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Hand tracking
        landmarks, fs = tracker.process(frame_rgb)

        # Find hovered key
        hovered_key = None
        if fs.tip_x > 0:
            for k in keys:
                if k.contains(fs.tip_x, fs.tip_y):
                    hovered_key = k.key
                    break

        # Gesture → keypress
        fired = debouncer.check(fs, hovered_key)
        if fired:
            if fired == "⌫":
                session.backspace()
                renderer.flash("⌫")
            elif fired == "SPACE":
                session.insert(" ")
                renderer.flash("SPACE")
            elif fired == "⏎":
                session.insert("\n")
                renderer.flash("⏎")
            else:
                session.insert(fired)
                renderer.flash(fired)

        # FPS
        fps_counter += 1
        if time.time() - fps_time >= 0.5:
            fps_display = fps_counter / (time.time() - fps_time)
            fps_counter = 0
            fps_time = time.time()

        # Render
        out = renderer.draw(frame, keys, fs, session, hovered_key, landmarks, fps_display)
        cv2.imshow("Air Typer", out)

        # Keyboard controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('c'):
            session.clear()
            print("Text cleared")

    print("\n● Session ended")
    if session.text.strip():
        print(f"● Final text:\n  {repr(session.text)}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Air Typing System")
    parser.add_argument("--camera",  type=int, default=0,    help="Camera device ID (default: 0)")
    parser.add_argument("--width",   type=int, default=1280, help="Frame width (default: 1280)")
    parser.add_argument("--height",  type=int, default=720,  help="Frame height (default: 720)")
    args = parser.parse_args()

    main(camera_id=args.camera, width=args.width, height=args.height)
