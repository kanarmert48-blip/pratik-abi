# Shorts Otomasyonu

Her gün otomatik olarak 1 adet dikey (9:16) Türkçe sesli Shorts videosu üretir ve Discord'a gönderir. Yüklemeyi sen yaparsın.

## Nasıl çalışır
- `scripts.json` → 30 hazır video senaryosu (fikir + metin)
- `make_video.py` → animasyonlu görüntü + Türkçe seslendirme + altyazı → MP4
- `sayac.txt` → sıradaki senaryo numarası (otomatik artar)
- Her video için: `.mp4`, kapak `.jpg`, başlık/açıklama/etiketler `.txt`

## Kurulum
1. Discord'da bir kanal → Ayarlar → Entegrasyonlar → Webhook oluştur → URL'yi kopyala.
2. GitHub repo → Settings → Secrets and variables → Actions → New secret
   - Ad: `DISCORD_WEBHOOK`  Değer: webhook URL'si
3. Actions sekmesi → **shorts-uret** → **Run workflow** ile ilk videoyu dene.

Her gün 09:00'da kendiliğinden çalışır. GitHub zamanlaması aksarsa cron-job.org ile `workflow_dispatch` tetikleyebilirsin.

Discord yoksa: Actions'taki çalıştırmanın altındaki **Artifacts** bölümünden videoyu indir.

## Yeni fikir eklemek
`fikir_bankasi.py` içindeki listeye ekle, sonra:
```
python fikir_bankasi.py scripts.json
```
