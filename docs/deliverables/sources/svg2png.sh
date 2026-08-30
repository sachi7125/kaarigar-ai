#!/bin/bash
SVG="$1"; OUT="$2"; W="$3"; H="$4"; SCALE="${5:-2}"
TMPH="$(mktemp -t s2p).html"
python3 - "$SVG" "$W" "$H" > "$TMPH" <<'PY'
import sys,re
svg=open(sys.argv[1],encoding='utf-8').read(); w,h=sys.argv[2],sys.argv[3]
svg=re.sub(r'<\?xml[^>]*\?>','',svg).strip()
print(f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{margin:0}}html,body{{margin:0;padding:0}}svg{{display:block;width:{w}px;height:{h}px}}</style></head><body>{svg}</body></html>')
PY
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor="$SCALE" \
  --window-size="$W,$H" --default-background-color=FFFFFFFF \
  --screenshot="$OUT" "file://$TMPH" >/dev/null 2>&1
rm -f "$TMPH"
python3 -c "from PIL import Image; print('wrote','$OUT',Image.open('$OUT').size)"
