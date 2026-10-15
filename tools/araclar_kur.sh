#!/bin/bash
# Yeni oturumda araçları yeniden kurar: modeller 'araclar' sürümünden iner.
set -e
R=kanarmert48-blip/pratik-abi
A=/home/claude/araclar
mkdir -p $A/whisper-turbo $A/noto ~/.u2net
apt-get install -y -qq libcairo2-dev libpango1.0-dev pkg-config >/dev/null
pip install --break-system-packages -q faster-whisper rembg rlottie-python
pip install --break-system-packages -q --use-pep517 srt && pip install --break-system-packages -q manim
TOK=$(gh auth token)
gh api repos/$R/releases/tags/araclar --jq '.assets[] | "\(.id) \(.name)"' | while read id name; do
  [ "$name" = "birefnet-general-lite.onnx" ] && continue  # 7GB RAM'e sığmıyor
  curl -sSL -H "Authorization: Bearer $TOK" -H "Accept: application/octet-stream" -o "$A/$name" \
    https://api.github.com/repos/$R/releases/assets/$id
done
tar -xf $A/whisper-turbo.tar -C $A/whisper-turbo && rm $A/whisper-turbo.tar
mv $A/isnet-general-use.onnx ~/.u2net/
(cd $A/noto && python3 -c "import zipfile; zipfile.ZipFile('../noto-lottie.zip').extractall('.')") && rm $A/noto-lottie.zip
echo "araçlar hazır"
