"""CrimeVision AI - Intelligent Multimodal Forensic Analysis Platform (Skill Wallet Capstone Project 2)."""
import hashlib
import pandas as pd
import streamlit as st
from modules import custody, vision, audio, video, fusion, report

st.set_page_config(page_title="CrimeVision AI", page_icon="🕵️", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.5rem}
h1,h2,h3{letter-spacing:.3px}
.cv-badge{display:inline-block;padding:3px 12px;border-radius:12px;font-weight:700;font-size:.85rem}
.cv-Low{background:#2a9d8f}.cv-Medium{background:#e9c46a;color:#000}.cv-High{background:#f4a261;color:#000}.cv-Critical{background:#ef233c}
.cv-card{background:#141b2d;border:1px solid #26314d;border-radius:10px;padding:12px 16px;margin-bottom:8px}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in (("image", None), ("audio", None), ("video", None), ("chat", [])):
    S.setdefault(k, v)

# ---------- Sidebar: configuration, security, chain of custody ----------
with st.sidebar:
    st.title("🕵️ CrimeVision AI")
    provider = st.selectbox("LLM provider", ["Groq", "Gemini"])
    key = st.text_input("API key (optional)", type="password", help="Leave empty for demo mode. Never stored.")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY" if provider == "Groq" else "GEMINI_API_KEY", "")
        except Exception:
            key = ""
    st.success("LIVE mode") if key else st.warning("DEMO mode (no API key)")
    st.divider()
    st.subheader("Chain of Custody")
    case_id = st.text_input("Case ID", "CASE-2026-001")
    investigator = st.text_input("Investigator", "")
    signed = st.checkbox("Investigator sign-off", help="Confirms evidence reviewed by a human.")
    st.caption("Sign-off: %s" % ("✅ SIGNED" if signed and investigator else "⏳ PENDING"))
    for x in (S.image, S.audio, S.video):
        if x:
            st.code("%s\n%s UTC" % (x["rec"]["evidence_id"], x["rec"]["logged_utc"]), language=None)

st.title("CrimeVision AI")
st.caption("Intelligent Multimodal Forensic Analysis Platform - AI-assisted; all findings require human verification.")
t1, t2, t3, t4, t5 = st.tabs(["📷 Visual Evidence", "🎙️ Witness Audio", "🎥 CCTV Video", "🧩 Fusion & Evidence Chat", "📄 PDF Report"])


def load(slot, kind, f):
    """Register + cache by file hash so reruns don't recompute."""
    data = f.getvalue()
    h = hashlib.sha256(data).hexdigest()
    if S[slot] is None or S[slot]["rec"]["sha256"] != h:
        S[slot] = {"rec": custody.register(kind, f.name, data, investigator), "data": data}
        S[slot].pop("res", None)
        S.chat = []
    return S[slot]


with t1:
    f = st.file_uploader("Crime scene photograph", type=["jpg", "jpeg", "png"], key="u_img")
    if f:
        try:
            item = load("image", "IMG", f)
            if "res" not in item:
                item["res"] = vision.analyze(item["data"])
            r = item["res"]
            c1, c2 = st.columns([3, 2])
            c1.image(r["annotated"], caption="%s - %s" % (item["rec"]["evidence_id"], r["model"]), use_container_width=True)
            c2.markdown('Threat level: <span class="cv-badge cv-%s">%s</span>' % (r["threat"], r["threat"]), unsafe_allow_html=True)
            c2.metric("Scene classification", r["scene"])
            c2.markdown("**Prioritised investigative leads**")
            for i, l in enumerate(r["leads"], 1):
                c2.markdown("%d. %s" % (i, l))
            st.dataframe(pd.DataFrame([{"Item": d["label"], "Confidence": d["conf"], "x,y,w,h": str(d["bbox"])}
                                       for d in r["detections"]]), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Could not analyse image: %s" % e)

with t2:
    f = st.file_uploader("Witness statement / 911-112 call", type=["wav", "mp3", "m4a", "ogg", "flac"], key="u_aud")
    if f:
        try:
            item = load("audio", "AUD", f)
            if "res" not in item:
                with st.spinner("Transcribing..."):
                    segs, mode = audio.transcribe(item["data"], f.name, key if provider == "Groq" else None)
                item["res"], item["mode"], item["events"] = segs, mode, audio.extract_events(segs)
            st.caption("Engine: %s | %s" % (item["mode"], item["rec"]["evidence_id"]))
            st.audio(item["data"])
            st.subheader("Transcript")
            st.dataframe(pd.DataFrame(item["res"]).rename(columns={"t": "Time (s)", "speaker": "Speaker", "text": "Text"}),
                         use_container_width=True, hide_index=True)
            st.subheader("Key events & chronological markers")
            st.dataframe(pd.DataFrame(item["events"]), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Audio processing failed: %s" % e)

with t3:
    f = st.file_uploader("CCTV footage", type=["mp4", "avi", "mov", "mkv"], key="u_vid")
    if f:
        try:
            item = load("video", "VID", f)
            if "res" not in item:
                with st.spinner("Sampling frames & tracking motion..."):
                    item["res"] = video.analyze(item["data"], f.name)
            r = item["res"]
            st.caption("Engine: %s | %s" % (r["mode"], item["rec"]["evidence_id"]))
            if r["preview"] is not None:
                st.image(r["preview"], caption="Suspect trajectory overlay (red path, yellow = last position)")
            st.subheader("Chronological event log")
            st.dataframe(pd.DataFrame(r["events"]).rename(columns={"t": "Time (s)", "event": "Event", "category": "Legal category",
                                                                  "confidence": "Confidence"}),
                         use_container_width=True, hide_index=True)
            st.caption("Categories are indicative; map to your jurisdiction's penal code with legal counsel.")
        except Exception as e:
            st.error("Video analysis failed: %s" % e)

ledger = fusion.build_ledger(S.image, S.audio and {"rec": S.audio["rec"], "events": S.audio.get("events", [])},
                             S.video if S.video and "res" in S.video else None)
with t4:
    st.subheader("Master forensic event ledger")
    if ledger:
        st.dataframe(pd.DataFrame(ledger)[["clock", "source", "entry_id", "event", "category", "confidence"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Upload evidence in the previous tabs to build the ledger.")
    st.subheader("Interrogate the evidence")
    st.caption("Answers come only from the ledger and cite entry IDs. Try: *Was a weapon visible before the suspect fled?*")
    for q, a in S.chat:
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(a)
    q = st.chat_input("Ask about the evidence...")
    if q:
        a, mode = fusion.ask(q, ledger, provider, key)
        S.chat.append((q, a))
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(a)
        st.caption("Engine: %s" % mode)

with t5:
    st.subheader("Court-admissible forensic summary")
    if not (S.image or S.audio or S.video):
        st.info("No evidence yet.")
    else:
        if not (signed and investigator):
            st.warning("Report will be marked PENDING until investigator name and sign-off are provided.")
        if st.button("Generate PDF report", type="primary"):
            try:
                S.pdf = report.build_pdf(case_id, investigator, bool(signed and investigator),
                                         S.image, S.audio and {"rec": S.audio["rec"]}, S.video if S.video and "res" in S.video else None,
                                         ledger, S.chat)
            except Exception as e:
                st.error("PDF generation failed: %s" % e)
        if S.get("pdf"):
            st.download_button("⬇️ Download report", S.pdf, file_name="%s_forensic_report.pdf" % case_id, mime="application/pdf")
