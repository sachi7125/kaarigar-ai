"""Device token for the artisan-only endpoints (Day 7, middleman guard).

Roadmap: "account & QR bound to her own number, earnings only in her view".
Until now anyone who knew her artisan id — it's in her public storefront URL
and on her stall QR — could list her offers, accept one and receive the
buyer's contact, or read her earnings. Now those endpoints need the token her
phone got when it registered her number or verified it by OTP.

One token per artisan: verifying on another phone replaces it, which signs
the old phone out. If a middleman takes over her number, her own app stops
working, so she notices.

The limit, disclosed: OTP delivery is still mocked (D18 — the code comes back
in the response instead of by SMS), so today anyone can complete the OTP for
any number. The token only becomes real protection once SMS is wired in; the
endpoints and the app are already built for that.
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Artisan
from app.db.session import get_db

_SIGN_IN_AGAIN = "this phone is no longer signed in — verify your number again"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(artisan: Artisan) -> str:
    """New token for this artisan, replacing any earlier one. Only the hash
    is stored; the caller commits and returns the plain token once."""
    token = secrets.token_urlsafe(32)
    artisan.auth_token_hash = hash_token(token)
    return token


def require_artisan(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Artisan:
    scheme, _, token = (authorization or "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="sign-in required",
                            headers={"WWW-Authenticate": "Bearer"})
    artisan = db.query(Artisan).filter(Artisan.auth_token_hash == hash_token(token)).first()
    if artisan is None:
        raise HTTPException(status_code=401, detail=_SIGN_IN_AGAIN,
                            headers={"WWW-Authenticate": "Bearer"})
    return artisan


def ensure_owner(me: Artisan, artisan_id: str) -> None:
    if me.id != artisan_id:
        raise HTTPException(status_code=403, detail="this is not your shop")
