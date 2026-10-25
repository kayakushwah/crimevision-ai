"""Epic 4 - CCTV frame sampling, motion tracking (OpenCV MOG2) and crime-category classification."""
import os
import tempfile
import cv2
import numpy as np
from PIL import Image

CATEGORY = {
    "enter": "Criminal trespass (possible)",
    "walk": "Subject movement - no offence indicated",
    "run": "Flight from scene (post-offence conduct)",
    "still": "Suspicious loitering / reconnaissance",
    "vehicle": "Vehicle movement - potential getaway",
}
TEXT = {"enter": "Subject enters frame", "walk": "Subject walking", "run": "Rapid movement across frame",
        "still": "Subject stationary / loitering", "vehicle": "Large moving object (vehicle) in frame"}
CONF = {"enter": .80, "walk": .70, "run": .85, "still": .75, "vehicle": .78}
DEMO_EVENTS = [(3.0, "enter"), (9.0, "still"), (16.0, "run"), (22.0, "vehicle")]


def _demo(reason):
    ev = [{"t": t, "event": TEXT[k], "category": CATEGORY[k], "confidence": CONF[k]} for t, k in DEMO_EVENTS]
    return {"events": ev, "trajectory": [], "preview": None, "mode": "Demo (%s)" % reason}


def analyze(data, name="video.mp4"):
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(name)[1] or ".mp4") as f:
            f.write(data)
            path = f.name
        cap = cv2.VideoCapture(path)
        if not cap.isOpened() or cap.get(cv2.CAP_PROP_FRAME_COUNT) <= 0:
            return _demo("unreadable video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, int(fps / 2))
        bg = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=32, detectShadows=False)
        track, last, i = [], None, 0
        while len(track) < 600:
            ok, fr = cap.read()
            if not ok:
                break
            if i % step == 0:
                h, w = fr.shape[:2]
                small = cv2.resize(fr, (320, max(1, int(320 * h / w))))
                mask = cv2.morphologyEx(bg.apply(small), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
                cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cs:
                    c = max(cs, key=cv2.contourArea)
                    a = cv2.contourArea(c) / float(small.shape[0] * small.shape[1])
                    if a > 0.004:
                        x, y, bw, bh = cv2.boundingRect(c)
                        track.append((round(i / fps, 1), x + bw / 2.0, y + bh / 2.0, a))
                last = small
            i += 1
        cap.release()
        if not track:
            return {"events": [{"t": 0.0, "event": "No significant motion detected", "category": "No actionable activity",
                                "confidence": 0.5}], "trajectory": [], "preview": None, "mode": "OpenCV (live)"}
        events, prev_label = [], None
        for n, (t, x, y, a) in enumerate(track):
            if n == 0:
                label = "enter"
            else:
                pt, px, py, _ = track[n - 1]
                speed = (((x - px) ** 2 + (y - py) ** 2) ** .5 / 320.0) / max(t - pt, 0.1)
                label = "vehicle" if a > 0.08 else "run" if speed > 0.12 else "still" if speed < 0.02 else "walk"
            if label != prev_label and len(events) < 40:
                events.append({"t": t, "event": TEXT[label], "category": CATEGORY[label], "confidence": CONF[label]})
            prev_label = label
        preview = None
        if last is not None:
            pts = np.array([[int(x), int(y)] for _, x, y, _ in track], np.int32)
            cv2.polylines(last, [pts], False, (60, 60, 255), 2)
            cv2.circle(last, tuple(int(v) for v in pts[-1]), 5, (0, 255, 255), -1)
            preview = Image.fromarray(cv2.cvtColor(last, cv2.COLOR_BGR2RGB))
        return {"events": events, "trajectory": [(t, x, y) for t, x, y, _ in track], "preview": preview,
                "mode": "OpenCV MOG2 (live)"}
    except Exception as e:
        return _demo(type(e).__name__)
    finally:
        if path and os.path.exists(path):
            os.remove(path)
