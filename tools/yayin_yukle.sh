#!/bin/bash
# Videoyu herkese açık "yayin" dalına koyar (Metricool / yt-yukle buradan çeker). Geçmiş birikmesin diye
# dal tek commit olarak zorla güncellenir, en yeni 4 video tutulur.
# Kullanım: bash tools/yayin_yukle.sh <video.mp4>   -> herkese açık adresi yazdırır
set -e
F="$1"; N=$(basename "$F")
R=$(git -C "$(dirname "$0")/.." remote get-url origin)
T=$(mktemp -d)
cd "$T"
git init -q -b yayin
git remote add origin "$R"
if timeout 300 git fetch -q --depth 1 origin yayin 2>/dev/null; then
  git checkout -q FETCH_HEAD -- . 2>/dev/null || true
fi
cp "$F" "$T/$N"
ls -t *.mp4 2>/dev/null | tail -n +5 | xargs -r rm -f
git add -A
git -c user.email=bot@pratikabi -c user.name=pratikabi commit -qm "yayin: $N"
timeout 400 git push -q -f origin yayin 2>&1 | grep -v "acknowledgments\|negotiation" || true
cd / && rm -rf "$T"
U="https://raw.githubusercontent.com/kanarmert48-blip/pratik-abi/yayin/$N"
curl -sS -o /dev/null -w "%{http_code}" -r 0-100 "$U" | grep -q 206 && echo "$U"
