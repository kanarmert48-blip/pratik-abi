# Günlük otomatik Short (zamanlanmış görev çalışma kılavuzu)

Kullanıcının kuralı: her gün 2 Short. Saatler Türkiye saati (Europe/Istanbul).

| Slot | Araştırma | Üretim | YouTube kontrolü | Kullanıcıya soru | Cevap yoksa yükleme |
|------|-----------|--------|------------------|------------------|---------------------|
| A    | 11:30     | 12:00  | 12:30            | 13:00            | 13:30               |
| B    | 16:30     | 17:00  | 17:30            | 18:00            | 18:30               |

Kanal durumu:
- **Pratik Abi** (@PratikAbii): aktif. Yükleme Metricool üzerinden (blogId `7502348`, YouTube bağlı).
- **DinoFlash** (@DinoFlash1): hazır değil. Gerekenler: (1) DinoFlash üretim kodu bu repoda `dinoflash/` altında,
  (2) kullanıcının GitHub secrets'a eklediği `DINO_YT_CLIENT_ID`, `DINO_YT_CLIENT_SECRET`, `DINO_YT_REFRESH_TOKEN`.
  Yükleme `yt-yukle` iş akışıyla yapılır (aşağıda).
- **3. kanal**: henüz açılmadı.

## 0. Kurulum (yeni oturum)
- `/home/claude/pratik-abi` yoksa: `add_repo` (owner `kanarmert48-blip`, repo `pratik-abi`, access `push`) ve verdiği komutla klonla.
- `/home/claude/shorts-oto` yoksa: `bash /home/claude/pratik-abi/pipeline/geri_yukle.sh`.
- `pratik-abi-video` skill'ini yükle ve uygula. Hafızadan `/areas/pratik-abi.md` ve `/areas/youtube-otomasyon.md` oku.
- `tools/dogal_dil.md` dosyasını oku. Senaryo, başlık ve açıklama bu kurallara uymak zorunda.

## 1. Konu (araştırma saati)
- `kanal` release'inden `kanal_son.json` indir. Son videolarda neyin tuttuğuna bak.
- `tools/onerilenler.md`: 2. satır **yapılmış** konular, asla tekrar etme. 3. satır önerilmiş konular, oradan seçebilirsin.
- Doyuma ulaşmış kalıp formatları seçme (aynı tip illüzyon/test videosunu art arda yapma). Konu ilk 1–2 sn'de durduracak kancaya sahip olsun.
- Bilgileri en az 2 güvenilir kaynakla doğrula.
- **Konuyu hemen rezerve et:** 2. satırın sonuna `<konu> (<no>, oto <YYYY-MM-DD> <A|B>)` ekle, commit + push.
  Push çakışırsa rebase et ve konunun diğer slot tarafından alınmadığını tekrar kontrol et.

## 2. Üretim
- Video no: `pipeline/shorts-oto/pro/video<N>_*.py` içindeki en büyük N + 1.
- Skill'deki tüm kurallar (ses ayarları, 2K, Abi sol altta, ~30 sn, sonda "Daha fazlası için takip etmeyi de unutma" + TAKİP ET).
- Müzik işini ve medya isteğini en başta paralel başlat.

## 3. YouTube kontrolü
- `tools/dogal_dil.md` "Son kontrol" + "YouTube politika kontrolü" maddelerini tek tek uygula.
- Son 5 başlıkla kalıp tekrarına bak. Videodan 5 kare çıkarıp bak. Sesin son 0,5 sn'si sessiz mi kontrol et.

## 4. Barındırma
- `yayin` release'i yoksa oluştur. `gh release upload yayin <no>-<ad>.mp4 --clobber`.
- Herkese açık adres: `https://github.com/kanarmert48-blip/pratik-abi/releases/download/yayin/<no>-<ad>.mp4`.

## 5. Soru (13:00 / 18:00)
- Video erken biterse `send_later` ile tam soru saatine kendine mesaj kur ve o mesaj gelince sor.
- Sorarken: `SendUserFile` (video + kapak), `SendUserMessage` (başlık, açıklama, etiketler ve
  "Yükleyeyim mi? 30 dk içinde cevap gelmezse <saat>'te kendim yüklüyorum."), `PushNotification`.
- Hemen ardından `send_later` ile 30 dk sonrasına "otomatik yükleme zamanı" mesajı kur.
- Üretim gecikirse: hazır olunca sor, yükleme sorudan 30 dk sonra.

## 6. Karar
- "yükle / tamam / evet" → hemen yükle. Sonra gelen otomatik yükleme mesajında tekrar yükleme yapma.
- "yükleme / dur / iptal" → yükleme. Log'a `iptal` yaz.
- Değişiklik isterse → düzelt, yeniden gönder, yeniden sor, yeni 30 dk say.
- 30 dk içinde hiç cevap yok → yükle.

## 7. Yükleme
### Pratik Abi (Metricool)
`createScheduledPost`: blogId `7502348`, `date` = şimdi + 3 dk (Europe/Istanbul, ISO 8601), `info`:
```json
{"autoPublish": true, "draft": false, "text": "<açıklama>", "media": ["<yayin adresi>"],
 "providers": [{"network": "youtube"}],
 "publicationDate": {"dateTime": "YYYY-MM-DDTHH:mm:ss", "timezone": "Europe/Istanbul"},
 "youtubeData": {"title": "<başlık>", "type": "short", "privacy": "public", "tags": ["..."],
                 "category": "EDUCATION", "madeForKids": false, "isAiGeneratedContent": false}}
```
`isAiGeneratedContent` sadece gerçekçi yapay zekâ görüntüsü varsa `true`. Kapak alanlarını (videoThumbnailUrl) gönderme.
Sonra `getScheduledPosts` ile sıraya girdiğini doğrula, kullanıcıya "yüklendi" de.

### DinoFlash (hazır olunca)
`jobs/yukle-<id>/meta.json` = `{"kanal": "dinoflash", "video": "<yayin'daki dosya adı>", "title": "...",
"description": "...", "tags": ["..."], "categoryId": "27", "ai": false}` push et, sonra:
`gh api -X POST repos/kanarmert48-blip/pratik-abi/actions/workflows/yt-yukle.yml/dispatches -f ref=main -f "inputs[job]=jobs/yukle-<id>"`.
Sonucu `yukleme` release'indeki `<id>_sonuc.json` dosyasından oku.

## 8. Kayıt
- `tools/yayin_log.md` sonuna: `| tarih | slot | kanal | no | konu | başlık | durum |`.
- Video scriptini `pipeline/shorts-oto/pro/` altına yedekle, commit + push.
- Bilgisayar bağlıysa `D:\PratikAbi\<no>-<ad>.mp4` ve `_kapak.jpg` olarak da kaydet. Değilse atla.

## Değişmez yasaklar
- API anahtarı, token ya da şifre hiçbir yere girilmez. Kullanıcı secrets'ı kendisi ekler.
- vidIQ kullanılmaz. Kullanıcının e-postası ilgisiz servislere gönderilmez. YouTube politikası atlatılmaz.
- `D:\nişan` klasörüne dokunulmaz. Bilgisayardaki hiçbir dosya silinmez.
- Telifli ya da ünlü fotoğrafı kullanılmaz. Yapılmış konu tekrar edilmez. Ses hızlandırılmaz, whoosh kazancı 0.05.
