#!/usr/bin/env bash
# Deploy the buyer-facing app to Vercel (Day 7).
#
#   scripts/deploy_vercel.sh            build, then deploy to production
#   scripts/deploy_vercel.sh pull-env   save the project's environment variables
#                                       (DATABASE_URL from the attached Neon
#                                       database, KAARIGAR_PUBLIC_URL) to
#                                       .env.vercel for `run_server.sh online`
#
# One-time setup, done by you (it signs in to your account): `npx vercel login`.
# The first deploy creates the project "kaarigar-storefront" in the scope below.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/build/kaarigar-storefront"
SCOPE="${VERCEL_SCOPE:-ar555rathods-projects}"
VC=(npx --yes vercel@latest)

case "${1:-deploy}" in
  deploy)
    "$REPO/scripts/build_vercel.sh"
    cd "$OUT"
    "${VC[@]}" deploy --prod --yes --scope "$SCOPE"
    ;;
  pull-env)
    if [ ! -d "$OUT/.vercel" ]; then
      echo "Deploy once first, so this folder is linked to the Vercel project." >&2
      exit 1
    fi
    cd "$OUT"
    "${VC[@]}" env pull "$REPO/.env.vercel" --environment=production --yes --scope "$SCOPE"
    ;;
  *)
    echo "usage: $0 [deploy|pull-env]" >&2
    exit 2
    ;;
esac
