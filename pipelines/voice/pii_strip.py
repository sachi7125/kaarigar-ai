"""Strip identifier-like digit runs before publish — step 4 (Roadmap Day 2).

An artisan reading her product description aloud will sometimes recite her phone
number or an Aadhaar number ("...call me on nine eight seven..."). A listing page is
public and permanent, so those digits must never reach it (DPDP; also middleman
capture — the only contact route is the structured offer inbox).

What is REMOVED:
  - `+91`-prefixed numbers, with any spacing/dashes
  - runs of >= `min_digits` digits (default 7), counted across spaces and dashes,
    which covers 10-digit mobiles and 12-digit Aadhaar
  - Devanagari digits as well as Latin

What is KEPT (this matters — pricing and stock depend on it):
  - short numbers: prices ("400 rupaye"), dimensions ("12 inch"), counts ("6 diye")
  - years and any run under the threshold

Returns the cleaned text plus a list of what was taken out, so the read-back can say
"I removed a phone number" instead of silently changing her words.

CLI:  python -m pipelines.voice.pii_strip "<text>"
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, asdict

# Latin + Devanagari digits
_D = r"0-9०-९"
# a "number run": digits, optionally broken by single spaces / dashes / dots
_RUN = re.compile(rf"[{_D}](?:[\s\-.]?[{_D}])*")
# explicit +91 / 0091 mobile prefix
# must END on a digit, or the match swallows the following space
_INTL = re.compile(rf"(?:\+\s?91|\b0091)[\s\-]?(?:[{_D}][\s\-]?){{6,}}[{_D}]")

DEFAULT_PLACEHOLDER = "[removed]"


@dataclass
class Redaction:
    original: str
    kind: str          # "phone" | "digits"
    digits: int

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class PIIResult:
    text: str
    redactions: list[Redaction]

    @property
    def changed(self) -> bool:
        return bool(self.redactions)

    def as_dict(self) -> dict:
        return {"text": self.text, "redactions": [r.as_dict() for r in self.redactions],
                "changed": self.changed}


def _digit_count(s: str) -> int:
    return sum(1 for ch in s if ch.isdigit())


def strip_pii(text: str, min_digits: int = 7,
              placeholder: str = DEFAULT_PLACEHOLDER) -> PIIResult:
    """Remove identifier-like digit runs; keep prices, sizes and counts."""
    if not (text or "").strip():
        return PIIResult(text=text or "", redactions=[])

    redactions: list[Redaction] = []

    def _intl(m: re.Match) -> str:
        hit = m.group(0)
        redactions.append(Redaction(hit.strip(), "phone", _digit_count(hit)))
        return placeholder

    out = _INTL.sub(_intl, text)

    def _run(m: re.Match) -> str:
        hit = m.group(0)
        n = _digit_count(hit)
        if n < min_digits:
            return hit                      # price / size / count — keep it
        kind = "phone" if n in (10, 11) else "digits"
        redactions.append(Redaction(hit.strip(), kind, n))
        return placeholder

    out = _RUN.sub(_run, out)
    # collapse any double spacing the substitution left behind
    out = re.sub(r"[ \t]{2,}", " ", out).strip()
    return PIIResult(text=out, redactions=redactions)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m pipelines.voice.pii_strip "<text>"')
        raise SystemExit(2)
    r = strip_pii(sys.argv[1])
    print(r.text)
    for red in r.redactions:
        print(f"  removed {red.kind}: {red.original!r} ({red.digits} digits)")
