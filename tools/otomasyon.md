# Günlük otomatik Short (zamanlanmış görev çalışma kılavuzu)

Kullanıcının kuralı: her gün 2 Short. Saatler Türkiye saati (Europe/Istanbul).

**KURAL DEĞİŞTİ (09.11.2026): Claude YÜKLEME YAPMAZ.** Kullanıcı: "Sen sadece video hazırla, konu sor, yüklemeyi ben yaparım."
Claude konu sorar, videoyu hazırlar, başlık/açıklama/etiketle birlikte teslim eder. Yüklemeyi kullanıcı yapar. Metricool'a ya da YouTube'a hiçbir şey gönderilmez.

| Slot | Konu sorusu | Üretim + kontrol | Teslim |
|------|-------------|------------------|--------|
| A    | ~11:15      | konu seçilince   | 13:00'ten önce |
| B    | ~16:15      | konu seçilince   | 18:00'den önce |

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
- Kurulum: `bash /home/claude/pratik-abi/tools/oto_kur.sh` (HAFİF kurulum: motor + whisper). `geri_yukle.sh` / `araclar_kur.sh` ÇALIŞTIRMA:
  ağır modelleri (~3 GB) indirip diski dolduruyor, 09.11'deki iki çalışma büyük ihtimalle bu yüzden çöktü.
- Ses: `ses/raw1.wav` → `python3 /home/claude/araclar/whb.py` (kelime zamanları) → `python3 /home/claude/araclar/kes3.py` (sessizlik sıkılaştırma, `ses/v1.wav` + `ses/v1.json`).
  Whisper sonda uydurma kelime eklerse ("İzlediğiniz için teşekkür ederim") önce onları sil.
- Örnek tam video: `pipeline/shorts-oto/pro/video50_kleopatra.py` (foto + Ken Burns + zaman çizelgesi + Abi rozeti).
- `pratik-abi-video` skill'ini yükle ve uygula. Hafızadan `/areas/pratik-abi.md` ve `/areas/youtube-otomasyon.md` oku.
- `tools/dogal_dil.md` dosyasını oku. Senaryo, başlık ve açıklama bu kurallara uymak zorunda.

## 1. Konu (araştırma + kullanıcıya sor)
- Aşağıdaki kurallarla 3 aday konu çıkar, her biri tek cümlelik kancayla. `SendUserMessage` + `PushNotification` ile kullanıcıya sor:
  "Bugünkü <13:00/18:00> videosu için konu: 1) … 2) … 3) … Hangisi?"
- `send_later` ile 30 dk sonrasına hatırlatıcı kur. Kullanıcı seçerse onu yap. 30 dk içinde cevap yoksa en yüksek puanlı adayı seç,
  "cevap gelmedi, 1'i yapıyorum" diye kısa yaz ve devam et.
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

## 4. Barındırma (artık gerekmiyor, yükleme yok)
- `bash tools/yayin_yukle.sh <no>-<ad>.mp4` → herkese açık adresi yazdırır
  (`https://raw.githubusercontent.com/kanarmert48-blip/pratik-abi/yayin/<no>-<ad>.mp4`). Bu oturum release oluşturamaz, bu yüzden dal kullanılıyor.

## 5. Teslim (13:00 / 18:00'den önce)
- `SendUserFile` (video + kapak) ve `SendUserMessage`: başlık, kısa açıklama (+ fotoğraf kredisi), etiketler,
  "Değiştirilmiş içerik: Evet/Hayır" ve "Kontrol: 11/11 geçti". `PushNotification` at.
- Değişiklik isterse düzelt ve yeniden gönder. **Yükleme yapma**, yüklemeyi kullanıcı yapar.

## 8. Kayıt
- `tools/yayin_log.md` sonuna: `| tarih | slot | kanal | no | konu | başlık | durum |`.
- Video scriptini `pipeline/shorts-oto/pro/` altına yedekle, commit + push.
- Bilgisayar bağlıysa `D:\PratikAbi\<no>-<ad>.mp4` ve `_kapak.jpg` olarak da kaydet. Değilse atla.

## Değişmez yasaklar
- API anahtarı, token ya da şifre hiçbir yere girilmez. Kullanıcı secrets'ı kendisi ekler.
- vidIQ kullanılmaz. Kullanıcının e-postası ilgisiz servislere gönderilmez. YouTube politikası atlatılmaz.
- `D:\nişan` klasörüne dokunulmaz. Bilgisayardaki hiçbir dosya silinmez.
- Telifli ya da ünlü fotoğrafı kullanılmaz. Yapılmış konu tekrar edilmez. Ses hızlandırılmaz, whoosh kazancı 0.05.
