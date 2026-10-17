#!/bin/bash
# Yeni oturumda video altyapısını geri kurar: kod + varlıklar + araçlar.
set -e
cd "$(dirname "$0")"
rm -rf /home/claude/shorts-oto && cp -r shorts-oto /home/claude/shorts-oto
bash ../tools/araclar_kur.sh
echo "altyapı hazır: /home/claude/shorts-oto"
