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

## Durum kaydı (hata ayıklama için zorunlu)
Her adım bitince `tools/oto_durum.md` sonuna tek satır ekle ve hemen commit + push et:
`<YYYY-MM-DD HH:MM> <slot> <adım> OK` (kurulum, konu, ses, render, kontrol, soru, yükleme).
Bir adım hata verirse önce hata mesajının ilk 3 satırını aynı dosyaya `HATA` olarak yaz, push et, sonra kullanıcıya bildir.
Kurulum takılırsa (ör. geri_yukle.sh içindeki manim kurulumu) o paketi atla, video için gerekenlerle devam et.

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
- Konu türü dönüşümlü: **Slot A** katılımlı/dene türü (izleyici videoyu izlerken bir şey yapar: bak, dene, test et; kanalın en çok tutan türü),
  **Slot B** merak/ilginç bilgi türü (az bilinen gerçek, nostalji 2015–2020, "neden böyle?" soruları). Aynı gün iki slot aynı türde olmaz.
- 3–4 aday çıkar, her birini YouTube'da (Türkçe + yabancı) ara: benzer Shorts sayısı ve izlenmeleri. Çok kalabalık olanı ele.
- Her adayı 4 başlıkta 1–5 puanla: nadirlik, izlenme tutma (ilk 2 sn kancası), algoritma uyumu, tekrar içerik riski (ters puan). En yüksek puanlıyı seç.
- **Konuyu hemen rezerve et:** 2. satırın sonuna `<konu> (<no>, oto <YYYY-MM-DD> <A|B>)` ekle, commit + push.
  Push çakışırsa rebase et ve konunun diğer slot tarafından alınmadığını tekrar kontrol et.

## 2. Üretim
- Video no: `pipeline/shorts-oto/pro/video<N>_*.py` içindeki en büyük N + 1.
- Skill'deki tüm kurallar (ses ayarları, 2K, Abi sol altta, ~30 sn, sonda "Daha fazlası için takip etmeyi de unutma" + TAKİP ET).
- Müzik işini ve medya isteğini en başta paralel başlat.

## 3. YouTube kontrolü (12:30–13:00 / 17:30–18:00) — puan kartı
Her madde Geçti/Kaldı. Bir madde bile "Kaldı" ise düzelt, yeniden render al, tekrar kontrol et. Düzeltilemiyorsa soruda kullanıcıya söyle.

A. Metin doğal mı
1. Bitmiş videonun sesini whisper ile yazıya dök. Metni, başlığı ve açıklamayı `tools/dogal_dil.md` yasak listesine göre tara
   (ör. "değil," kalıbı, "—", "Hadi gelin", "Peki ya", "inanılmaz", "büyüleyici", "keşfet", üçlü sıralama).
2. Sesli okuma testi: her cümle günlük konuşmada böyle söylenir mi? Kitap dili ya da reklam dili varsa değiştir.
3. Başlık: son 5 videonun başlığıyla (kanal_son.json) aynı kalıpta mı? En fazla 1 emoji, en fazla 1 büyük harf kelime.

B. Ses ve görüntü doğal mı
4. Ses: hızlandırma yok, duraklar doğal, son kelime kesilmemiş (son 0,5 sn sessiz), ses seviyesi -14 ile -16 LUFS arası.
5. 6 kare çıkar (0,5 sn, 2 sn, %25, %50, %75, son kare) ve bak: yazı taşması, yapay zekâ bozulması (garip el/yüz/yazı),
   görselin o anda söylenenle uyumu.

C. YouTube'a uygun mu
6. İlk 2 sn: ilk kare + ilk cümle kaydırmayı durdurur mu, başlıkla aynı şeyi mi söylüyor?
7. Özgünlük: konu ve format son 10 videodan farklı mı (`tools/yayin_log.md` + onerilenler 2. satır)?
8. Bilgiler en az 2 güvenilir kaynakla doğrulandı mı, rakamlar temkinli mi?
9. Telif: müzik kendi üretimimiz, görseller kredili (CC/Unsplash), ünlü fotoğrafı yok.
10. Yapay içerik beyanı: gerçekçi yapay zekâ görüntüsü varsa `isAiGeneratedContent: true`, yoksa `false`.
11. Süre 20–35 sn, dikey 9:16, 2K.

Soru mesajına tek satır ekle: "Kontrol: 11/11 geçti" ya da neyin düzeltildiği.

## 4. Barındırma
- `bash tools/yayin_yukle.sh <no>-<ad>.mp4` → herkese açık adresi yazdırır
  (`https://raw.githubusercontent.com/kanarmert48-blip/pratik-abi/yayin/<no>-<ad>.mp4`). Bu oturum release oluşturamaz, bu yüzden dal kullanılıyor.

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
`jobs/yukle-<id>/meta.json` = `{"kanal": "dinoflash", "video": "<yayin dalındaki dosya adı>", "title": "...",
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
