"""Epic 5 - master evidence ledger + grounded Q&A. Every answer cites ledger entry IDs; no evidence -> refusal."""
import re
from modules import llm

SYN = {
    "weapon": {"weapon", "firearm", "gun", "knife", "edged", "pistol", "blade"},
    "flee": {"fled", "flee", "flight", "fleeing", "ran", "run", "running", "escape", "escaped", "rapid"},
    "blood": {"blood", "spatter", "injury", "bloodstain"},
    "vehicle": {"vehicle", "car", "truck", "bike", "drove", "getaway"},
    "entry": {"entry", "forced", "break", "broke", "window", "door", "trespass", "burglary"},
    "person": {"person", "suspect", "man", "woman", "subject", "people"},
}
STOP = set("was is were the a an of in on at to did do does any there before after visible when what who how and or "
           "by with for from it that this be been".split())
NO_EVIDENCE = "Insufficient evidence in the ledger to answer this question."


def toks(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def build_ledger(image, aud, vid):
    rows = []
    if image:
        eid = image["rec"]["evidence_id"]
        for n, d in enumerate(image["res"]["detections"], 1):
            rows.append({"entry_id": "%s-E%d" % (eid, n), "evidence_id": eid, "source": "Image", "t": None,
                         "clock": "Scene snapshot",
                         "event": "%s detected at x=%d,y=%d (conf %.2f)" % (d["label"], d["bbox"][0], d["bbox"][1], d["conf"]),
                         "category": image["res"]["scene"], "confidence": d["conf"]})
    if aud:
        eid = aud["rec"]["evidence_id"]
        for n, e in enumerate(aud["events"], 1):
            rows.append({"entry_id": "%s-E%d" % (eid, n), "evidence_id": eid, "source": "Audio", "t": e["t"],
                         "clock": "T+%05.1fs" % e["t"], "event": '%s: "%s"' % (e["speaker"], e["text"]),
                         "category": e["event"], "confidence": 0.9})
    if vid:
        eid = vid["rec"]["evidence_id"]
        for n, e in enumerate(vid["res"]["events"], 1):
            rows.append({"entry_id": "%s-E%d" % (eid, n), "evidence_id": eid, "source": "Video", "t": e["t"],
                         "clock": "T+%05.1fs" % e["t"], "event": e["event"], "category": e["category"],
                         "confidence": e["confidence"]})
    rows.sort(key=lambda r: (-1 if r["t"] is None else r["t"]))
    return rows


def _extractive(q, ledger):
    qt = toks(q)
    exp = set(qt)
    for g in SYN.values():
        if qt & g:
            exp |= g
    exp -= STOP
    if "before" in qt and qt & SYN["weapon"] and qt & SYN["flee"]:   # temporal rule
        w = [e for e in ledger if e["t"] is not None and toks(e["event"]) & SYN["weapon"]]
        f = [e for e in ledger if e["t"] is not None and toks(e["event"]) & SYN["flee"]]
        if w and f:
            w0, f0 = min(w, key=lambda e: e["t"]), min(f, key=lambda e: e["t"])
            verdict = "Yes" if w0["t"] < f0["t"] else "No"
            return "%s. Weapon first reported at %s [%s]; flight first recorded at %s [%s]." % (
                verdict, w0["clock"], w0["entry_id"], f0["clock"], f0["entry_id"])
    scored = []
    for e in ledger:
        s = len(exp & toks(e["event"] + " " + e["category"]))
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["t"] if x[1]["t"] is not None else -1))
    if not scored:
        return NO_EVIDENCE
    return "Relevant evidence found:\n" + "\n".join(
        "- %s %s (%s): %s [%s]" % (e["clock"], e["source"], e["category"], e["event"], e["entry_id"])
        for _, e in scored[:5])


def ask(q, ledger, provider="Groq", key=None):
    """Returns (answer, mode)."""
    if not ledger:
        return "No evidence has been uploaded/analysed yet.", "Guard"
    if key:
        ctx = "\n".join("[%s] %s | %s | %s" % (e["entry_id"], e["clock"], e["source"], e["event"]) for e in ledger)
        sys = ("You are a forensic evidence assistant. Answer ONLY from the ledger. Cite the entry ID in square brackets "
               "after every claim. If the ledger cannot answer, reply exactly: " + NO_EVIDENCE)
        out = llm.chat(provider, key, sys, "LEDGER:\n%s\n\nQUESTION: %s" % (ctx, q))
        if out:
            cited = set(re.findall(r"\[([^\]]+)\]", out))
            valid = {e["entry_id"] for e in ledger}
            if out.strip() == NO_EVIDENCE or (cited and cited <= valid):   # reject hallucinated citations
                return out, "LLM (grounded + citation-verified)"
    return _extractive(q, ledger), "Extractive RAG (demo)"
