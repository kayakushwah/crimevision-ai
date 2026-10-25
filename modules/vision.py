"""Epic 2 - simulated RT-DETR scene tagger (deterministic per image hash, so results are reproducible)."""
import io
import hashlib
import random
from PIL import Image, ImageDraw

COLORS = {"Person": "#4cc9f0", "Firearm": "#ef233c", "Edged weapon": "#ff9f1c",
          "Blood spatter": "#b5179e", "Forced entry point": "#f8961e"}
SCENES = {
    "Burglary": ["Forced entry point", "Forced entry point", "Person"],
    "Homicide": ["Person", "Firearm", "Blood spatter", "Blood spatter"],
    "Vandalism": ["Forced entry point", "Person"],
    "Assault": ["Person", "Person", "Edged weapon", "Blood spatter"],
}
WEIGHT = {"Firearm": 3.0, "Edged weapon": 2.0, "Blood spatter": 1.5, "Forced entry point": 1.0, "Person": 0.5}
LEADS = {
    "Firearm": "Secure firearm; request ballistics, serial trace and latent prints.",
    "Edged weapon": "Bag blade separately; swab for DNA and check wound-pattern match.",
    "Blood spatter": "Photograph with scale; collect samples and run bloodstain-pattern analysis.",
    "Forced entry point": "Cast tool marks; dust frame for prints; check nearby CCTV for approach route.",
    "Person": "Identify and interview all persons; log positions relative to evidence.",
}


def _threat(score):
    return "Critical" if score >= 5 else "High" if score >= 3 else "Medium" if score >= 1.5 else "Low"


def analyze(data):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = img.size
    rng = random.Random(int(hashlib.sha256(data).hexdigest(), 16) % (2 ** 32))
    scene = rng.choice(list(SCENES))
    dets = []
    for label in SCENES[scene]:
        bw, bh = rng.uniform(.1, .25) * W, rng.uniform(.12, .3) * H
        x, y = rng.uniform(0, W - bw), rng.uniform(0, H - bh)
        dets.append({"label": label, "conf": round(rng.uniform(.72, .98), 2),
                     "bbox": [int(x), int(y), int(bw), int(bh)]})
    score = sum(WEIGHT[d["label"]] * d["conf"] for d in dets)
    ann = img.copy()
    dr = ImageDraw.Draw(ann)
    for d in dets:
        x, y, w, h = d["bbox"]
        dr.rectangle([x, y, x + w, y + h], outline=COLORS[d["label"]], width=max(2, W // 300))
        dr.text((x + 3, max(0, y - 12)), "%s %.2f" % (d["label"], d["conf"]), fill=COLORS[d["label"]])
    leads, seen = [], set()
    for d in sorted(dets, key=lambda d: -WEIGHT[d["label"]]):
        if d["label"] not in seen:
            seen.add(d["label"])
            leads.append(LEADS[d["label"]])
    return {"scene": scene, "threat": _threat(score), "detections": dets, "leads": leads,
            "annotated": ann, "model": "RT-DETR (simulated)"}
