"""Generate synthetic test video with slide transitions and matching SRT."""
from pathlib import Path

import cv2
import numpy as np

FIXTURES = Path(__file__).parent
VIDEO_PATH = FIXTURES / "test_slides.mp4"
SRT_PATH = FIXTURES / "test_slides.srt"

W, H = 640, 480
FPS = 30.0
SLIDES = [
    {"color": (50, 50, 200), "duration": 3.0, "text": "Welcome to the presentation"},
    {"color": (200, 50, 50), "duration": 3.0, "text": "First topic overview"},
    {"color": (50, 200, 50), "duration": 3.0, "text": "Key concept explanation"},
    {"color": (200, 200, 50), "duration": 3.0, "text": "Example demonstration"},
]


def generate():
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    out = cv2.VideoWriter(str(VIDEO_PATH), fourcc, FPS, (W, H))
    srt_entries = []
    cue_idx = 1
    current_time = 0.0

    for slide in SLIDES:
        color = slide["color"]
        n_frames = int(slide["duration"] * FPS)
        for i in range(n_frames):
            frame = np.full((H, W, 3), color, dtype=np.uint8)
            out.write(frame)
        start_s = current_time
        end_s = current_time + slide["duration"]
        srt_entries.append((cue_idx, start_s, end_s, slide["text"]))
        cue_idx += 1
        current_time += slide["duration"]

    out.release()
    print(f"Video written: {VIDEO_PATH} ({current_time:.1f}s)")

    with open(SRT_PATH, "w", encoding="utf-8") as f:
        for idx, start, end, text in srt_entries:
            def fmt(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                s = sec % 60
                return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
            f.write(f"{idx}\n")
            f.write(f"{fmt(start)} --> {fmt(end)}\n")
            f.write(f"{text}\n\n")
    print(f"SRT written: {SRT_PATH} ({len(srt_entries)} cues)")


if __name__ == "__main__":
    generate()
