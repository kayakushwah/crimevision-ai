# CrimeVision AI - Intelligent Multimodal Forensic Analysis Platform

Streamlit app that fuses image, audio and video evidence into one chronological ledger, answers grounded
questions with evidence-ID citations, and exports a court-style PDF (ReportLab). No database required.

| Epic | Module |
|------|--------|
| 1 Init & env | `app.py`, `requirements.txt`, `.streamlit/config.toml`, `modules/custody.py` |
| 2 Object detection | `modules/vision.py` (simulated RT-DETR) |
| 3 Audio / Whisper | `modules/audio.py` (Groq Whisper, demo fallback) |
| 4 Video tracking | `modules/video.py` (OpenCV MOG2) |
| 5 Fusion & chat | `modules/fusion.py`, `modules/llm.py` |
| 6 Dashboard/tests/PDF | `modules/report.py`, `tests/test_smoke.py` |

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover tests -v
```
Optional API keys: paste in the sidebar or set `GROQ_API_KEY` / `GEMINI_API_KEY` in Streamlit secrets.
Without a key the app runs in DEMO mode. Outputs are AI-assisted and need human verification.
