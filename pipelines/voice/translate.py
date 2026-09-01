"""Regional-language text -> English pivot — mandated feature 2, step 2 (Roadmap Day 2).

DESIGN (see decisions D11, revised 1 Sep): there is **no standalone MT model** in the
pipeline. The bilingual listing text is produced by the Gemini step (step 3), which
takes the regional-language transcript directly and emits EN + HI. A separate
IndicTrans2 / HuggingFace `transformers` stage was tried and cut: `import transformers`
stalled for ~20 min on the dev machine (it enumerates every distribution on sys.path,
which the anaconda-based venv makes enormous), and nothing else in the project needs
`torch`. Two heavy-ML-dep swamps in two days (rembg, then this) — not worth it.

So `translate()` is a **passthrough** that keeps the `TranslationResult` contract stable
for any caller that already expects it. It returns the source text unchanged with
`translated=False`. `source_lang` is normalised and carried through so the Gemini step
knows what language it is being handed.

An optional real-MT path is kept behind `KAARIGAR_MT=indictrans2` for later use on a
clean (non-conda) machine — it is never touched unless that env var is set, and imports
stay lazy. Do not rely on it for the demo.

CLI:  python -m pipelines.voice.translate "<text>" <src_lang>
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, asdict

# our language codes; anything else -> carried through untouched.
_LANGS = {"hi", "bn", "ta", "mr", "en"}


@dataclass
class TranslationResult:
    text: str                 # English pivot, OR source text unchanged (passthrough)
    source_text: str
    source_lang: str          # normalised: hi/bn/ta/mr/en, or whatever was passed
    translated: bool          # False for passthrough
    backend: str              # "passthrough" | "indictrans2"
    model: str
    error: str | None = None  # note explaining a passthrough / degraded result

    def as_dict(self) -> dict:
        return asdict(self)


def _passthrough(text: str, src: str, note: str | None) -> TranslationResult:
    return TranslationResult(
        text=text, source_text=text, source_lang=src, translated=False,
        backend="passthrough", model="", error=note,
    )


def translate(text: str, source_lang: str) -> TranslationResult:
    """Return an English pivot for `text`.

    Default behaviour is passthrough (translation is done by the Gemini step). Set
    KAARIGAR_MT=indictrans2 to attempt a real IndicTrans2 translation instead — only
    on a machine where `import transformers` is not pathologically slow.
    Never raises for a translation failure; inspect `.translated`.
    """
    text = (text or "").strip()
    src = (source_lang or "").strip().lower() or "en"

    if not text:
        return _passthrough("", src, "empty input")
    if src == "en":
        return _passthrough(text, src, None)

    note = None if src in _LANGS else f"unknown source language {src!r}; carried through"

    if os.environ.get("KAARIGAR_MT", "").strip().lower() == "indictrans2":
        try:
            return _translate_indictrans2(text, src)
        except Exception as e:
            return _passthrough(text, src, f"KAARIGAR_MT set but failed "
                                           f"({e.__class__.__name__}: {e}); passthrough")

    return _passthrough(
        text, src,
        note or "translation deferred to the Gemini step (no standalone MT model)",
    )


# --------------------------------------------------------------------------- #
# Optional: real IndicTrans2, only when KAARIGAR_MT=indictrans2. Lazy imports.  #
# Not used for the demo. See D11.                                              #
# --------------------------------------------------------------------------- #
_IT2_LANG = {"hi": "hin_Deva", "bn": "ben_Beng", "ta": "tam_Taml",
             "mr": "mar_Deva", "en": "eng_Latn"}
_IT2_CACHE: dict = {}


def _translate_indictrans2(text: str, src: str) -> TranslationResult:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    model_id = "ai4bharat/indictrans2-indic-en-dist-200M"
    if model_id not in _IT2_CACHE:
        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
        mdl.eval()
        try:
            from IndicTransToolkit.processor import IndicProcessor
            proc = IndicProcessor(inference=True)
        except Exception:
            proc = None
        _IT2_CACHE[model_id] = (tok, mdl, proc)
    tok, mdl, proc = _IT2_CACHE[model_id]

    s, t = _IT2_LANG.get(src, "hin_Deva"), "eng_Latn"
    batch = (proc.preprocess_batch([text], src_lang=s, tgt_lang=t)
             if proc is not None else [f"{s} {t} {text}"])
    enc = tok(batch, truncation=True, padding="longest", max_length=256,
              return_tensors="pt")
    with torch.no_grad():
        out = mdl.generate(**enc, num_beams=5, max_length=256, no_repeat_ngram_size=3)
    dec = tok.batch_decode(out, skip_special_tokens=True)
    eng = (proc.postprocess_batch(dec, lang=t)[0] if proc is not None else dec[0]).strip()
    if not eng:
        return _passthrough(text, src, "indictrans2 returned empty; passthrough")
    return TranslationResult(text=eng, source_text=text, source_lang=src,
                             translated=True, backend="indictrans2", model=model_id,
                             error=None if proc is not None else "no IndicTransToolkit")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('usage: python -m pipelines.voice.translate "<text>" <src_lang>')
        raise SystemExit(2)
    r = translate(sys.argv[1], sys.argv[2])
    print(f"backend    : {r.backend}  ({r.model or '-'})")
    print(f"translated : {r.translated}")
    if r.error:
        print(f"note       : {r.error}")
    print("-" * 60)
    print(r.text)
