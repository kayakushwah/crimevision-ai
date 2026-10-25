"""Chain-of-custody: every uploaded file gets a SHA-256 hash, Evidence ID and UTC log entry."""
import hashlib
import datetime as dt


def register(kind, name, data, investigator="Unassigned"):
    digest = hashlib.sha256(data).hexdigest()
    return {
        "evidence_id": "EV-%s-%s" % (kind, digest[:8].upper()),
        "file": name,
        "sha256": digest,
        "size_kb": round(len(data) / 1024, 1),
        "logged_utc": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "investigator": investigator or "Unassigned",
    }
