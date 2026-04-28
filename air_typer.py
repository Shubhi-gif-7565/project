"""
Air Typing System — Core Engine
Real-time hand gesture recognition → keyboard input using MediaPipe + OpenCV
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class FingerState:
    tip_x: float = 0.0
    tip_y: float = 0.0
    is_pinching: bool = False
    pinch_distance: float = 1.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0

@dataclass
class TypingSession:
    text: str = ""
    cursor_pos: int = 0
    last_char_time: float = 0.0
    last_key: str = ""
    repeat_count: int = 0

    def insert(self, char: str):
        self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
        self.cursor_pos += len(char)
        self.last_char_time = time.time()
        self.last_key = char

    def backspace(self):
        if self.cursor_pos > 0:
            self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
            self.cursor_pos -= 1
            self.last_char_time = time.time()
            self.last_key = "⌫"

    def clear(self):
        self.text = ""
        self.cursor_pos = 0


# ─── Virtual Keyboard Layout ──────────────────────────────────────────────────

KEYBOARD_ROWS = [
    ["Q","W","E","R","T","Y","U","I","O","P"],
    ["A","S","D","F","G","H","J","K","L"],
    ["Z","X","C","V","B","N","M"],
    ["⌫", "SPACE", "⏎"],
]

SPECIAL_KEYS = {"⌫", "SPACE", "⏎"}

@dataclass
class KeyRect:
    key: str
    x1: int; y1: int
    x2: int; y2: int

    @property
    def cx(self): return (self.x1 + self.x2) // 2
    @property
    def cy(self): return (self.y1 + self.y2) // 2
    @property
    def w(self): return self.x2 - self.x1
    @property
    def h(self): return self.y2 - self.y1

    def contains(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


def build_keyboard(frame_w: int, frame_h: int) -> list[KeyRect]:
    """Generate keyboard key rects scaled to frame size."""
    keys = []
    kb_w = int(frame_w * 0.90)
    kb_h = int(frame_h * 0.42)
    kb_x = int(frame_w * 0.05)
    kb_y = int(frame_h * 0.54)

    row_h = kb_h // len(KEYBOARD_ROWS)
    gap = 4

    for r_idx, row in enumerate(KEYBOARD_ROWS):
        n = len(row)
        # Calculate total width for this row
        if row == KEYBOARD_ROWS[-1]:
            # Special bottom row
            widths = {"⌫": 0.18, "SPACE": 0.55, "⏎": 0.18}
            offset_x = kb_x + int(kb_w * 0.045)
            for key in row:
                w = int(kb_w * widths[key])
                x1 = offset_x + gap
                y1 = kb_y + r_idx * row_h + gap
                x2 = offset_x + w - gap
                y2 = kb_y + (r_idx + 1) * row_h - gap
                keys.append(KeyRect(key, x1, y1, x2, y2))
                offset_x += w
        else:
            key_w = kb_w // 10
            row_offset = kb_x + (kb_w - n * key_w) // 2
            for c_idx, key in enumerate(row):
                x1 = row_offset + c_idx * key_w + gap
                y1 = kb_y + r_idx * row_h + gap
                x2 = row_offset + (c_idx + 1) * key_w - gap
                y2 = kb_y + (r_idx + 1) * row_h - gap
                keys.append(KeyRect(key, x1, y1, x2, y2))
    return keys


# ─── Hand Tracker ─────────────────────────────────────────────────────────────

class HandTracker:
    THUMB_TIP  = 4
    INDEX_TIP  = 8
    MIDDLE_TIP = 12
    RING_TIP   = 16
    PINKY_TIP  = 20
    WRIST      = 0

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.72,
            min_tracking_confidence=0.65,
        )
        self._prev_index: tuple[float, float] = (0.0, 0.0)
        self._pos_history: deque = deque(maxlen=6)

    def process(self, frame_rgb: np.ndarray) -> tuple[Optional[object], FingerState]:
        results = self.hands.process(frame_rgb)
        fs = FingerState()

        if not results.multi_hand_landmarks:
            return None, fs

        lm = results.multi_hand_landmarks[0]
        h, w = frame_rgb.shape[:2]

        def px(idx):
            return lm.landmark[idx].x * w, lm.landmark[idx].y * h

        ix, iy = px(self.INDEX_TIP)
        tx, ty = px(self.THUMB_TIP)

        pinch_dist = math.hypot(ix - tx, iy - ty)
        # Normalize by hand size
        wx, wy = px(self.WRIST)
        hand_size = math.hypot(ix - wx, iy - wy) + 1e-6
        norm_pinch = pinch_dist / hand_size

        fs.tip_x = ix
        fs.tip_y = iy
        fs.pinch_distance = norm_pinch
        # More deliberate pinch: reduced from 0.28 to 0.21
        fs.is_pinching = norm_pinch < 0.21

        # Velocity (smoothed)
        self._pos_history.append((ix, iy))
        if len(self._pos_history) >= 3:
            prev = self._pos_history[-3]
            fs.velocity_x = ix - prev[0]
            fs.velocity_y = iy - prev[1]

        return lm, fs


# ─── Gesture Debouncer ────────────────────────────────────────────────────────

class GestureDebouncer:
    """Prevent accidental rapid-fire keypresses."""
    def __init__(self, cooldown: float = 0.55):
        self.cooldown = cooldown
        self._last_fire: dict[str, float] = {}
        self._pinch_was_active = False
        self._pinch_start: float = 0.0
        self._pinch_key: Optional[str] = None
        self.HOLD_REPEAT_DELAY = 0.90
        self.HOLD_REPEAT_RATE  = 0.12

    def check(self, fs: FingerState, hovered_key: Optional[str]) -> Optional[str]:
        now = time.time()
        fired = None

        if fs.is_pinching and not self._pinch_was_active:
            # Fresh pinch start
            self._pinch_was_active = True
            self._pinch_start = now
            self._pinch_key = hovered_key
            if hovered_key:
                last = self._last_fire.get(hovered_key, 0)
                if now - last >= self.cooldown:
                    self._last_fire[hovered_key] = now
                    fired = hovered_key

        elif fs.is_pinching and self._pinch_was_active:
            # Held pinch — repeat for backspace/space
            if self._pinch_key in ("⌫", "SPACE"):
                hold_duration = now - self._pinch_start
                if hold_duration > self.HOLD_REPEAT_DELAY:
                    last = self._last_fire.get("__hold__", 0)
                    if now - last >= self.HOLD_REPEAT_RATE:
                        self._last_fire["__hold__"] = now
                        fired = self._pinch_key

        elif not fs.is_pinching and self._pinch_was_active:
            self._pinch_was_active = False
            self._pinch_key = None
            self._last_fire.pop("__hold__", None)

        return fired


# ─── Renderer ─────────────────────────────────────────────────────────────────

PALETTE = {
    "bg_overlay": (15, 12, 25),      # Deep indigo
    "key_base":   (45, 40, 60),      # Muted violet
    "key_hover":  (100, 80, 240),    # Vibrant purple
    "key_press":  (0, 255, 180),     # Neon spring green
    "key_special":(70, 60, 100),     # Dark lavender
    "text_white": (255, 255, 255),
    "text_dim":   (180, 180, 210),
    "accent":     (0, 220, 255),     # Electric cyan
    "glow":       (0, 180, 255),
    "pinch_ring": (0, 255, 150),
    "pinch_off":  (255, 50, 100),     # Soft red
    "display_bg": (10, 8, 18),
    "cursor":     (0, 200, 255),
}

class Renderer:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles
        self._mp_hands = mp.solutions.hands
        self._flash_key: Optional[str] = None
        self._flash_time: float = 0.0

    def flash(self, key: str):
        self._flash_key = key
        self._flash_time = time.time()

    def draw(
        self,
        frame: np.ndarray,
        keys: list[KeyRect],
        fs: FingerState,
        session: TypingSession,
        hovered_key: Optional[str],
        landmarks,
        fps: float,
    ) -> np.ndarray:
        # Dark Glass Overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), PALETTE["bg_overlay"], -1)
        frame = cv2.addWeighted(frame, 0.40, overlay, 0.60, 0)

        # Draw keyboard
        self._draw_keyboard(frame, keys, hovered_key, fs.is_pinching)
        # Draw text display
        self._draw_display(frame, session)
        # Draw landmarks
        if landmarks:
            self._draw_landmarks(frame, landmarks)
        # Draw finger cursor
        self._draw_cursor(frame, fs)
        # HUD
        self._draw_hud(frame, fs, fps)

        return frame

    def _draw_keyboard(self, frame, keys, hovered_key, is_pinching):
        now = time.time()
        flash_alive = (now - self._flash_time) < 0.18

        for k in keys:
            is_hover  = (k.key == hovered_key)
            is_flash  = (k.key == self._flash_key) and flash_alive
            is_special = k.key in SPECIAL_KEYS

            if is_flash:
                color = PALETTE["key_press"]
                text_col = (20, 20, 20)
            elif is_hover and is_pinching:
                color = PALETTE["key_press"]
                text_col = (20, 20, 20)
            elif is_hover:
                color = PALETTE["key_hover"]
                text_col = PALETTE["text_white"]
            elif is_special:
                color = PALETTE["key_special"]
                text_col = PALETTE["text_dim"]
            else:
                color = PALETTE["key_base"]
                text_col = PALETTE["text_white"]

            # Rounded-rect simulation via two rects + circles
            r = 6
            cv2.rectangle(frame, (k.x1 + r, k.y1), (k.x2 - r, k.y2), color, -1)
            cv2.rectangle(frame, (k.x1, k.y1 + r), (k.x2, k.y2 - r), color, -1)
            for cx_, cy_ in [(k.x1+r, k.y1+r),(k.x2-r, k.y1+r),(k.x1+r, k.y2-r),(k.x2-r, k.y2-r)]:
                cv2.circle(frame, (cx_, cy_), r, color, -1)

            # Key shadow/glow
            if is_hover:
                glow_thickness = 4 if not is_pinching else 6
                glow_color = PALETTE["accent"] if not is_pinching else PALETTE["key_press"]
                cv2.rectangle(frame, (k.x1-2, k.y1-2), (k.x2+2, k.y2+2), glow_color, 1, cv2.LINE_AA)

            # Key label
            label = k.key if k.key not in ("SPACE", "⏎", "⌫") else \
                    ("SPACE" if k.key == "SPACE" else ("↵" if k.key == "⏎" else "⌫"))
            font_scale = 0.55 if k.key not in SPECIAL_KEYS else 0.45
            font_thick = 1
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thick)
            tx = k.cx - tw // 2
            ty = k.cy + th // 2
            cv2.putText(frame, label, (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_col, font_thick, cv2.LINE_AA)

    def _draw_display(self, frame, session: TypingSession):
        x1, y1 = int(self.w * 0.04), int(self.h * 0.04)
        x2, y2 = int(self.w * 0.96), int(self.h * 0.46)

        # Display bg
        cv2.rectangle(frame, (x1, y1), (x2, y2), PALETTE["display_bg"], -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), PALETTE["accent"], 2)

        # Title
        cv2.putText(frame, "AIR TYPER", (x1 + 14, y1 + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, PALETTE["accent"], 1, cv2.LINE_AA)

        # Typed text with cursor blink
        text = session.text
        blink = int(time.time() * 2) % 2 == 0
        display = text[:session.cursor_pos] + ("|" if blink else " ") + text[session.cursor_pos:]

        # Word-wrap
        max_chars = 52
        lines = []
        while len(display) > max_chars:
            lines.append(display[:max_chars])
            display = display[max_chars:]
        lines.append(display)

        for i, line in enumerate(lines[-4:]):  # show last 4 lines
            cv2.putText(frame, line, (x1 + 14, y1 + 60 + i * 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, PALETTE["text_white"], 1, cv2.LINE_AA)

        # Char count
        count_str = f"{len(session.text)} chars"
        cv2.putText(frame, count_str, (x2 - 90, y2 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, PALETTE["text_dim"], 1, cv2.LINE_AA)

    def _draw_landmarks(self, frame, landmarks):
        h, w = frame.shape[:2]
        # Draw connections
        connections = mp.solutions.hands.HAND_CONNECTIONS
        for conn in connections:
            a, b = conn
            ax = int(landmarks.landmark[a].x * w)
            ay = int(landmarks.landmark[a].y * h)
            bx = int(landmarks.landmark[b].x * w)
            by = int(landmarks.landmark[b].y * h)
            cv2.line(frame, (ax, ay), (bx, by), (60, 80, 120), 1, cv2.LINE_AA)

        # Draw joints
        for lm in landmarks.landmark:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 3, (100, 140, 200), -1, cv2.LINE_AA)

    def _draw_cursor(self, frame, fs: FingerState):
        if fs.tip_x == 0 and fs.tip_y == 0:
            return
        cx, cy = int(fs.tip_x), int(fs.tip_y)
        
        # Dynamic color based on pinch proximity (Pre-Pinch)
        # norm_pinch goes from ~0.5 down to <0.21
        proximity = max(0, min(1, (fs.pinch_distance - 0.21) / 0.3))
        # Fade from Cyber Cyan to White/Green
        r = int(255 * (1 - proximity))
        g = 255
        b = int(255 * proximity)
        cursor_color = (b, g, r)

        radius = 12 if fs.is_pinching else 16
        cv2.circle(frame, (cx, cy), radius + 2, (0,0,0), 2, cv2.LINE_AA) # shadow
        cv2.circle(frame, (cx, cy), radius, cursor_color, 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 4, cursor_color, -1, cv2.LINE_AA)
        # Crosshair
        cv2.line(frame, (cx - 22, cy), (cx - 12, cy), cursor_color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx + 12, cy), (cx + 22, cy), cursor_color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - 22), (cx, cy - 12), cursor_color, 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy + 12), (cx, cy + 22), cursor_color, 1, cv2.LINE_AA)

        # Pinch indicator
        status = "● PINCH" if fs.is_pinching else "○ OPEN"
        col = PALETTE["pinch_ring"] if fs.is_pinching else PALETTE["text_dim"]
        cv2.putText(frame, status, (cx + 24, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)

    def _draw_hud(self, frame, fs: FingerState, fps: float):
        # FPS
        cv2.putText(frame, f"FPS {fps:.0f}", (self.w - 80, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, PALETTE["text_dim"], 1, cv2.LINE_AA)
        # Pinch meter
        bar_w = 80
        bar_h = 8
        bx, by = 14, self.h - 30
        fill = max(0, min(1, 1.0 - fs.pinch_distance / 0.4))
        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (40, 40, 60), -1)
        filled_w = int(bar_w * fill)
        bar_col = PALETTE["pinch_ring"] if fs.is_pinching else PALETTE["accent"]
        if filled_w > 0:
            cv2.rectangle(frame, (bx, by), (bx + filled_w, by + bar_h), bar_col, -1)
        cv2.putText(frame, "PINCH", (bx, by - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, PALETTE["text_dim"], 1, cv2.LINE_AA)

        # Instructions
        hints = [
            "Index finger → hover key",
            "Pinch (thumb+index) → press",
            "Hold pinch → repeat (⌫/SPC)",
            "Q → quit",
        ]
        for i, h_text in enumerate(hints):
            cv2.putText(frame, h_text, (self.w - 240, self.h - 80 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, PALETTE["text_dim"], 1, cv2.LINE_AA)

if __name__ == "__main__":
    import os
    import subprocess
    print("\n" + "="*50)
    print("  [!] ERROR: You are running 'air_typer.py'")
    print("  This is a library file and does not show the UI.")
    print("="*50)
    print("\n[*] TO START THE APP: Please run 'main.py' instead.")
    
    # Try to launch main.py for them using the correct Python 3.10
    py310 = r"C:\Users\palbh\AppData\Local\Programs\Python\Python310\python.exe"
    if os.path.exists(py310):
        print("\n[*] AUTO-LAUNCHING main.py for you using Python 3.10...")
        subprocess.run([py310, "main.py"])
    else:
        print("\n[!] Please run this command: ")
        print("    python main.py")
