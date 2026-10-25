"""Epic 3 - Whisper transcription (Groq Whisper API) with demo fallback + keyword event extraction."""
import requests

DEMO = [
    (2.0, "Caller", "I'm at 42 Marlow Street, someone just broke the back window."),
    (8.5, "Dispatcher", "Are you safe? Can you see the person?"),
    (12.0, "Caller", "Yes, a man in a dark hoodie. He is holding a knife, maybe a gun."),
    (21.5, "Caller", "He is running towards a grey car, he is fleeing now!"),
    (29.0, "Dispatcher", "Units are on the way. Stay on the line."),
    (35.0, "Caller", "The car drove off heading north. I saw blood on the door."),
]
EVENT_KEYS = {
    "Forced entry": ["broke", "window", "forced", "door", "break-in"],
    "Weapon sighting": ["gun", "knife", "pistol", "weapon", "blade"],
    "Suspect flight": ["running", "ran", "fled", "fleeing", "drove", "escape"],
    "Injury / blood": ["blood", "hurt", "shot", "stabbed", "injured"],
}


def transcribe(data, name, groq_key=None):
    """Returns (segments, mode). segment = {t, speaker, text}."""
    if groq_key:
        try:
            r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                              headers={"Authorization": "Bearer " + groq_key},
                              files={"file": (name, data)},
                              data={"model": "whisper-large-v3", "response_format": "verbose_json"},
                              timeout=120)
            r.raise_for_status()
            segs, spk, prev_end = [], 0, 0.0
            for s in r.json().get("segments", []):
                if s["start"] - prev_end > 1.2:
                    spk = 1 - spk          # speaker change heuristic on silence gap
                prev_end = s["end"]
                segs.append({"t": round(s["start"], 1), "speaker": "Speaker %d" % (spk + 1), "text": s["text"].strip()})
            if segs:
                return segs, "Whisper (live)"
        except Exception:
            pass
    return [{"t": t, "speaker": s, "text": x} for t, s, x in DEMO], "Demo transcript"


def extract_events(segments):
    out = []
    for s in segments:
        low = s["text"].lower()
        for label, kws in EVENT_KEYS.items():
            if any(k in low for k in kws):
                out.append({"t": s["t"], "event": label, "speaker": s["speaker"], "text": s["text"]})
                break
    return out
