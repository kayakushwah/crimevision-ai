"""Thin REST wrapper for Groq / Gemini. Returns None on any failure -> caller falls back to demo mode."""
import requests

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"


def chat(provider, key, system, user, timeout=40):
    if not key:
        return None
    try:
        if provider == "Groq":
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={"model": GROQ_MODEL, "temperature": 0,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}]},
                timeout=timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (GEMINI_MODEL, key)
        r = requests.post(url, json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0}}, timeout=timeout)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
