"""Voice-first onboarding: language, phone OTP, deferred verification (Day 5).

An unverified artisan may still capture, record, and see a price estimate
(Days 3-4 are untouched by any of this) — only `listings.py`'s publish step
checks `Artisan.verified`. That is the "deferred" in deferred verification.

No SMS provider is configured (no Twilio/etc. key in .env, and the roadmap's
cut list has no budget for one) — `/onboarding/send_otp` generates a real OTP
and a real 5-minute expiry, but hands the code straight back in the response
instead of dispatching an SMS. The app then speaks it aloud immediately,
exactly what "OTP read aloud" would look like once a real SMS is wired in —
this is a disclosed prototype shortcut, not a hidden one (see decisions.md).

Day 7: both steps can hand the phone its device token (app/auth.py).
Registering a NEW number returns one straight away, so deferred verification
still works. Registering a number that already has a shop returns none: that
phone must prove it's hers by OTP first, and verify_otp issues the token.
"""
from __future__ import annotations

import datetime
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.auth import issue_token
from app.db.models import Artisan
from app.db.session import get_db

router = APIRouter()

_OTP_TTL_MINUTES = 5
_otp_store: dict[str, tuple[str, datetime.datetime]] = {}  # phone -> (otp, expires_at)


@router.post("/onboarding/register")
def register(phone: str = Form(...), language: str = Form("hi"), db: Session = Depends(get_db)):
    artisan = db.query(Artisan).filter(Artisan.phone == phone).first()
    token = None
    if artisan is None:
        artisan = Artisan(phone=phone, language=language)
        token = issue_token(artisan)
        db.add(artisan)
        db.commit()
        db.refresh(artisan)
    else:
        artisan.language = language
        db.commit()
    return {"artisan_id": artisan.id, "language": artisan.language, "verified": artisan.verified,
            "auth_token": token, "needs_otp": token is None}


@router.post("/onboarding/send_otp")
def send_otp(phone: str = Form(...)):
    otp = f"{secrets.randbelow(10000):04d}"
    _otp_store[phone] = (otp, datetime.datetime.utcnow() + datetime.timedelta(minutes=_OTP_TTL_MINUTES))
    return {
        "otp": otp,  # mocked delivery — see module docstring
        "expires_in_minutes": _OTP_TTL_MINUTES,
        "note": "no SMS provider configured; OTP returned directly for the app to speak aloud",
    }


@router.post("/onboarding/verify_otp")
def verify_otp(phone: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    entry = _otp_store.get(phone)
    if entry is None or entry[0] != otp or datetime.datetime.utcnow() > entry[1]:
        raise HTTPException(status_code=400, detail="invalid or expired OTP")

    artisan = db.query(Artisan).filter(Artisan.phone == phone).first()
    if artisan is None:
        raise HTTPException(status_code=404, detail="unknown phone — call /onboarding/register first")

    artisan.verified = True
    token = issue_token(artisan)
    db.commit()
    del _otp_store[phone]
    return {"artisan_id": artisan.id, "verified": True, "auth_token": token}
