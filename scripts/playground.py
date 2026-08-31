"""Day 1 playground — a tiny local page to try the image enhancer + TTS on YOUR photos.

Not the product UI (that's the Flutter app, Day 3+, and the demo, Day 6). This is a dev
tool so you can see Day 1 working on real images.

Run:  cd <repo> && source .venv/bin/activate && streamlit run scripts/playground.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from pipelines.image.enhance import enhance, HAVE_REMBG
from pipelines.voice import tts

st.set_page_config(page_title="KaarigarAI — Day 1 playground", page_icon="🪔", layout="wide")
st.title("KaarigarAI — Day 1 playground")
st.caption("Image enhancer + shared TTS. Dev tool, not the product UI.")

# ---------------- image ----------------
st.header("1 · Enhance a photo")
st.write(f"Background removal engine: **{'rembg U2-Net' if HAVE_REMBG else 'GrabCut fallback'}**")
up = st.file_uploader("Drop a craft photo (jpg/png)", type=["jpg", "jpeg", "png"])

if up is not None:
    tmp = Path(tempfile.mkdtemp())
    src = tmp / up.name
    src.write_bytes(up.read())
    with st.spinner("Enhancing…"):
        res = enhance(str(src), str(tmp / "out"))

    if res.status == "ok":
        st.success(f"Clean image produced · method={res.method} · "
                   f"coverage={res.coverage:.2f} · subject_frac={res.subject_frac:.2f}")
        c1, c2, c3 = st.columns(3)
        c1.image(str(src), caption="raw", use_column_width=True)
        c2.image(res.outputs["enhanced"], caption="enhanced", use_column_width=True)
        c3.image(res.outputs["texture"], caption="texture close-up", use_column_width=True)
    else:
        st.warning(f"Retake requested — {res.reason}. The original is kept, nothing published.")
        c1, c2 = st.columns(2)
        c1.image(str(src), caption="raw", use_column_width=True)
        c2.image(res.outputs["original_kept"], caption="original kept (for retake)",
                 use_column_width=True)

# ---------------- tts ----------------
st.header("2 · Hear a read-back")
st.write(f"TTS available: **{tts.available()}**")
text = st.text_input("Line to speak",
                     "Aapke matke ki keemat panch sau bees rupaye. Yeh sahi hai?")
lang = st.selectbox("Voice", ["hi", "en"], index=0)
if st.button("🔊 Speak it"):
    out = Path(tempfile.mkdtemp()) / "readback.aiff"
    try:
        tts.speak_to_file(text, str(out), lang=lang)
        st.audio(str(out))
    except tts.TTSUnavailable as e:
        st.error(str(e))
