"""Run: python -m unittest discover tests -v"""
import io, os, sys, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np
from PIL import Image
from modules import custody, vision, audio, video, fusion, report


def png():
    b = io.BytesIO(); Image.new("RGB", (640, 480), (40, 40, 60)).save(b, "PNG"); return b.getvalue()


class T(unittest.TestCase):
    def test_pipeline(self):
        d = png()
        img = {"rec": custody.register("IMG", "a.png", d, "Tester"), "res": vision.analyze(d)}
        self.assertIn(img["res"]["threat"], ["Low", "Medium", "High", "Critical"])
        self.assertEqual(vision.analyze(d)["scene"], img["res"]["scene"])  # deterministic
        segs, _ = audio.transcribe(b"x", "a.wav")
        aud = {"rec": custody.register("AUD", "a.wav", b"x"), "events": audio.extract_events(segs)}
        vid = {"rec": custody.register("VID", "v.mp4", b"y"), "res": video.analyze(b"not a video", "v.mp4")}
        L = fusion.build_ledger(img, aud, vid)
        self.assertTrue(len(L) > 5)
        a, _ = fusion.ask("Was a weapon visible before the suspect fled?", L)
        self.assertIn("[EV-", a)
        self.assertIn("Insufficient", fusion.ask("What is the capital of France?", L)[0])
        pdf = report.build_pdf("C1", "Tester", True, img, aud, vid, L, [("q", a)])
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_real_video(self):
        p = tempfile.mktemp(suffix=".mp4")
        w = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
        for i in range(80):
            f = np.zeros((240, 320, 3), np.uint8); x = 10 + i * 3
            cv2.rectangle(f, (x, 100), (x + 25, 160), (255, 255, 255), -1); w.write(f)
        w.release()
        r = video.analyze(open(p, "rb").read(), "t.mp4")
        os.remove(p)
        self.assertIn("live", r["mode"]); self.assertTrue(r["events"])


if __name__ == "__main__":
    unittest.main()
