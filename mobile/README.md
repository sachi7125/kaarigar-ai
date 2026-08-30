# mobile

Flutter app. Voice-first, offline-first. Nothing essential exists only as text; every text
block has a speaker; no screen offers more than two real choices.

- `lib/screens/`  — onboarding, capture, speak/confirm, price, offer inbox, dashboard
- `lib/services/` — sync_queue, api_client, local_db, tts
- Offline: capture/record/queue fully offline; publish/price/offer need network (shown as queued).
