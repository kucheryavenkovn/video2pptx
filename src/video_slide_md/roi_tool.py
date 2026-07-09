# FILE: src/video_slide_md/roi_tool.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Graphical ROI selector — OpenCV window, mouse drag rect, print coordinates to stdout
#   SCOPE: Two entry points: select_roi() returns coordinates, command-level wrapper prints them
#   DEPENDS: opencv-python, video_decode
#   LINKS: M-ROI-TOOL
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   select_roi - OpenCV window with mouse drag, returns (x1, y1, x2, y2) or None
#   roi_tool_main - CLI-friendly wrapper: open video, call select_roi, print result
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from loguru import logger


def select_roi(
    image: np.ndarray,
    window_name: str = "Select ROI — drag rectangle, Enter to confirm, Esc to cancel",
) -> tuple[int, int, int, int] | None:
    # START_CONTRACT: select_roi
    #   PURPOSE: Show image in OpenCV window, let user drag rectangle, return coordinates
    #   INPUTS: { image: np.ndarray — RGB frame to display, window_name: str }
    #   OUTPUTS: (x1, y1, x2, y2) tuple or None if cancelled
    #   SIDE_EFFECTS: opens OpenCV GUI window, blocks until keypress
    #   LINKS: M-ROI-TOOL
    # END_CONTRACT: select_roi

    ix: int = -1
    iy: int = -1
    drawing: bool = False
    rect: tuple[int, int, int, int] | None = None
    display = image.copy()

    def _on_mouse(event: int, x: int, y: int, flags: int, param) -> None:
        nonlocal ix, iy, drawing, rect, display

        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
            rect = None

        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            display = image.copy()
            cv2.rectangle(display, (ix, iy), (x, y), (0, 255, 0), 2)

        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            x1, y1 = min(ix, x), min(iy, y)
            x2, y2 = max(ix, x), max(iy, y)
            if x2 - x1 > 5 and y2 - y1 > 5:
                rect = (x1, y1, x2, y2)
                cv2.rectangle(display, (ix, iy), (x, y), (0, 255, 0), 2)
                label = f"{x1},{y1},{x2},{y2}"
                cv2.putText(display, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, _on_mouse)

    result: tuple[int, int, int, int] | None = None

    while True:
        cv2.imshow(window_name, display)
        key = cv2.waitKey(30) & 0xFF

        if key == 13 or key == ord(" "):  # Enter or Space
            result = rect
            break
        if key == 27:  # Esc
            break

    cv2.destroyWindow(window_name)
    cv2.waitKey(1)  # Allow window to close

    return result


def roi_tool_main(video_path: Path, frame_ts: float | None = None) -> None:
    # START_CONTRACT: roi_tool_main
    #   PURPOSE: Open video, extract frame, call select_roi, print coordinates to stdout
    #   INPUTS: { video_path: Path, frame_ts: float | None — frame timestamp }
    #   OUTPUTS: None — prints "x1,y1,x2,y2" to stdout if selected
    #   SIDE_EFFECTS: opens GUI window, prints to stdout
    #   LINKS: M-ROI-TOOL
    # END_CONTRACT: roi_tool_main

    from video_slide_md.video_decode import VideoDecoder

    decoder = VideoDecoder(video_path=video_path, sample_fps=30.0)
    info = decoder.get_info()
    logger.info(f"[RoiTool][roi_tool_main] Video opened | {info.width}x{info.height}")

    if frame_ts is not None:
        target = frame_ts
    else:
        target = info.duration * 0.15  # ~15% into video, likely a representative frame

    for vf in decoder.iter_frames():
        if vf.timestamp >= target:
            image_rgb = vf.image
            break
    else:
        logger.warning("[RoiTool][roi_tool_main] No frame found, using first available")
        for vf in decoder.iter_frames():
            image_rgb = vf.image
            break
        else:
            logger.error("[RoiTool][roi_tool_main] No frames in video")
            return

    logger.info(f"[RoiTool][roi_tool_main] Displaying frame at ~{target:.1f}s")
    result = select_roi(image_rgb)

    if result is not None:
        x1, y1, x2, y2 = result
        output = f"{x1},{y1},{x2},{y2}"
        print(output)
        logger.info(f"[RoiTool][roi_tool_main] ROI selected | {output}")
    else:
        logger.info("[RoiTool][roi_tool_main] ROI selection cancelled")
