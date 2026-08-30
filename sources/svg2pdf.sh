#!/bin/bash
# usage: svg2pdf.sh in.svg out.pdf W H
SVG="$1"; OUT="$2"; W="$3"; H="$4"
TMPH="$(mktemp -t s2p).html"
python3 - "$SVG" "$W" "$H" > "$TMPH" <<'PY'
import sys
svg=open(sys.argv[1],encoding='utf-8').read()
w,h=sys.argv[2],sys.argv[3]
# strip xml prolog if any
import re
svg=re.sub(r'<\?xml[^>]*\?>','',svg).strip()
print(f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: {w}px {h}px; margin:0; }}
html,body {{ margin:0; padding:0; }}
svg {{ display:block; width:{w}px; height:{h}px; }}
</style></head><body>{svg}</body></html>''')
PY
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$TMPH" >/dev/null 2>&1
rm -f "$TMPH"
[ -f "$OUT" ] && echo "wrote $OUT ($(du -h "$OUT"|cut -f1))" || echo "FAILED $OUT"
