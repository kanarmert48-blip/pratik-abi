#!/bin/bash
# Otomatik görevler için HAFİF kurulum (disk ve süre dostu). Sadece Short üretimi için gerekenler:
#  - video motoru (pipeline/shorts-oto -> /home/claude/shorts-oto)
#  - faster-whisper + whisper-turbo modeli (tar dosyası diske yazılmadan, akışla açılır)
# CLIP, derinlik, arka plan silme, manim gibi ağır araçlar KURULMAZ. Gerekirse tools/araclar_kur.sh ayrıca çalıştırılır.
set -e
R=kanarmert48-blip/pratik-abi
A=/home/claude/araclar
cd "$(dirname "$0")/.."
if [ ! -d /home/claude/shorts-oto ]; then cp -r pipeline/shorts-oto /home/claude/shorts-oto; fi
python3 -c "import faster_whisper" 2>/dev/null || pip install --break-system-packages -q faster-whisper
python3 -c "import cv2" 2>/dev/null || pip install --break-system-packages -q opencv-python-headless
mkdir -p $A/whisper-turbo
if [ ! -f $A/whisper-turbo/model.bin ] && [ -z "$(ls -A $A/whisper-turbo 2>/dev/null)" ]; then
  ID=$(gh api repos/$R/releases/tags/araclar --jq '.assets[] | select(.name=="whisper-turbo.tar") | .id')
  curl -sSL -H "Authorization: Bearer $(gh auth token)" -H "Accept: application/octet-stream" \
    https://api.github.com/repos/$R/releases/assets/$ID | tar -x -C $A/whisper-turbo
fi
# whisper ve sessizlik sıkılaştırma betikleri (çalışma klasöründe ses/raw1.wav bekler)
cp pipeline/shorts-oto/pro/whb.py pipeline/shorts-oto/pro/kes3.py $A/
df -h /home | tail -1
echo "oto kurulum hazır"
