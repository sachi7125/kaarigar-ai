#!/usr/bin/env bash
# Start the backend in one of two modes (Day 7).
#
#   scripts/run_server.sh lan     Local Wi-Fi demo. Listens on every network
#                                 interface and builds QR codes and links from
#                                 this Mac's Wi-Fi address, so any phone on the
#                                 same Wi-Fi or hotspot can open the storefront.
#                                 Uses the local SQLite database, so it works
#                                 with the internet off (the Day 7 gate).
#   scripts/run_server.sh online  Shared cloud database. Reads DATABASE_URL and
#                                 KAARIGAR_PUBLIC_URL (the Vercel address) from
#                                 .env.vercel (`scripts/deploy_vercel.sh pull-env`
#                                 writes it), so listings published here show up
#                                 on the public Vercel pages.
#
# lan mode exposes an unauthenticated dev server to everyone on that network:
# use your own phone's hotspot, not venue Wi-Fi. macOS only (ipconfig).
set -euo pipefail

MODE="${1:-lan}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
PORT="${PORT:-8000}"

case "$MODE" in
  lan)
    IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
    if [ -z "$IP" ]; then
      echo "No Wi-Fi address found. Connect this Mac to Wi-Fi or your phone's hotspot first." >&2
      exit 1
    fi
    export KAARIGAR_PUBLIC_URL="http://$IP:$PORT"
    # Force the local database even if .env points DATABASE_URL at the cloud
    # one — the offline demo can't reach a cloud database.
    export DATABASE_URL="sqlite:///$REPO/backend/data/kaarigar.db"
    HOST=0.0.0.0
    echo "mode:        lan (local database)"
    echo "public URL:  $KAARIGAR_PUBLIC_URL"
    ;;
  online)
    if [ ! -f "$REPO/.env.vercel" ]; then
      echo "No .env.vercel yet. Run: scripts/deploy_vercel.sh pull-env" >&2
      exit 1
    fi
    set -a; . "$REPO/.env.vercel"; set +a
    unset VERCEL  # pulled along with the rest; it would switch this Mac to serverless pooling
    for key in DATABASE_URL KAARIGAR_PUBLIC_URL; do
      if [ -z "${!key:-}" ]; then
        echo "online mode needs $key — add it to the Vercel project's environment variables, then pull-env again." >&2
        exit 1
      fi
    done
    HOST=127.0.0.1
    echo "mode:        online (cloud database)"
    echo "public URL:  $KAARIGAR_PUBLIC_URL"
    ;;
  *)
    echo "usage: $0 [lan|online]" >&2
    exit 2
    ;;
esac

cd "$REPO/backend"
exec "$PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
