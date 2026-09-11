#!/usr/bin/env bash
# Assemble the buyer-facing app into build/kaarigar-storefront/ for Vercel (Day 7).
#
# A whitelist, not a blacklist: only the files named below are copied, so the
# dev database, uploaded photos and voice notes, .env and the ML stack can't
# end up in a deployment by accident. The folder name becomes the Vercel
# project name on the first deploy.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/build/kaarigar-storefront"

FILES=(
  backend/app/__init__.py
  backend/app/auth.py
  backend/app/config.py
  backend/app/public_main.py
  backend/app/api/__init__.py
  backend/app/api/offers.py
  backend/app/api/storefront.py
  backend/app/db/__init__.py
  backend/app/db/models.py
  backend/app/db/session.py
  backend/app/services/__init__.py
  backend/app/services/nudge.py
  backend/app/services/offer_validation.py
  backend/app/services/photos.py
  backend/app/services/stock.py
  backend/app/web/__init__.py
  backend/app/web/media.py
  backend/app/web/storefront_page.py
  backend/app/web/templates/listing.html
  backend/app/web/templates/storefront.html
  pipelines/__init__.py
  pipelines/common.py
  config/config.yaml
)

# Keep .vercel/ (the link to the Vercel project) across rebuilds.
if [ -d "$OUT" ]; then
  find "$OUT" -mindepth 1 -maxdepth 1 ! -name .vercel -exec rm -rf {} +
fi
mkdir -p "$OUT"

for f in "${FILES[@]}"; do
  mkdir -p "$OUT/$(dirname "$f")"
  cp "$REPO/$f" "$OUT/$f"
done
cp "$REPO/deploy/vercel/index.py" "$REPO/deploy/vercel/requirements.txt" "$OUT/"

echo "built $OUT ($(find "$OUT" -type f -not -path '*/.vercel/*' | wc -l | tr -d ' ') files)"
