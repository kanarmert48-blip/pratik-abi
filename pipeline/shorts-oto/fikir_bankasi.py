import json, sys

CTA = [
    "Bunu kaydet, işine yarayacak. Daha fazlası için takip et!",
    "Hangisini zaten yapıyorsun? Yorumlara yaz, takip etmeyi unutma.",
    "Faydalı bulduysan bir arkadaşına gönder ve takip et.",
    "Yarın yeni bir ipucuyla geliyorum. Takipte kal!",
]
BASE_TAGS = ["#shorts", "#tasarruf", "#paraipuçları", "#bütçe"]
LIFE_TAGS = ["#shorts", "#pratikbilgiler", "#hayatkolaylaştıran", "#günlükhayat"]

V = [
 ("butce-5-kural", "PARA", "5 Basit Bütçe Kuralı", "Maaş ayın ortasında bitiyor mu?", "Maaşın ayın ortasında bitiyorsa, bu beş basit kural tam sana göre.", [
   ("Önce kendine öde", "Maaş yattığı gün, küçük de olsa bir miktarı hemen kenara ayır."),
   ("Her harcamayı yaz", "Bir hafta boyunca her harcamanı not al. Paranın nereye gittiğini göreceksin."),
   ("50 30 20 kuralı", "Gelirin yüzde ellisi ihtiyaçlara, otuzu isteklere, yirmisi birikime."),
   ("24 saat bekle", "Plansız bir şey almak istediğinde bir gün bekle. Çoğu zaman vazgeçersin."),
   ("Nakit zarf yöntemi", "Market ve eğlence gibi kalemler için ayrı bir bütçe belirle ve aşma.")], BASE_TAGS),
 ("market-tasarruf", "MARKET", "Markette Daha Az Harca", "Markette fazla harcamanın sebebi bu", "Markette her seferinde planladığından fazla mı harcıyorsun? İşte nedeni ve çözümü.", [
   ("Listeyle git", "Listesiz alışveriş, plansız harcamanın bir numaralı sebebi."),
   ("Tok git", "Aç karnına alışverişe gidersen sepetin kendiliğinden dolar."),
   ("Alt ve üst raflara bak", "Pahalı ürünler göz hizasında durur. Ucuz alternatifler genelde aşağıda."),
   ("Birim fiyatı karşılaştır", "Büyük paket her zaman ucuz değildir. Kilo ya da litre fiyatına bak."),
   ("Sepet değil, file al", "Küçük taşıma aracı, gereksiz ürünleri almanı zorlaştırır.")], BASE_TAGS),
 ("fatura-dusur", "EV", "Faturaları Düşürmenin 4 Yolu", "Faturaların her ay artıyor mu?", "Faturaların her ay artıyorsa, bu dört küçük alışkanlık fark yaratır.", [
   ("Bekleme modunu kapat", "Kullanmadığın cihazları prizden çek. Bekleme modu da elektrik yakar."),
   ("Çamaşırı soğuk yıka", "Çoğu çamaşır otuz derecede temizlenir. Isıtma en çok enerjiyi harcar."),
   ("Tam dolu çalıştır", "Bulaşık ve çamaşır makinesini yarım değil, tam dolu çalıştır."),
   ("Kombi derecesini düşür", "Petek ayarını bir kademe düşürmek bile fark edilir tasarruf sağlar.")], BASE_TAGS),
 ("abonelik-kontrol", "PARA", "Unuttuğun Abonelikler", "Fark etmeden para ödüyor olabilirsin", "Şu an fark etmeden her ay para ödediğin bir abonelik olabilir.", [
   ("Ekstreni aç", "Son üç ayın kart ekstresine bak, tekrar eden ödemeleri işaretle."),
   ("Kullanmadığını iptal et", "Son bir ayda açmadığın uygulamanın aboneliğini hemen iptal et."),
   ("Aile paketine geç", "Bazı hizmetlerde aile paketi kişi başı çok daha ucuza gelir."),
   ("Deneme süresine not düş", "Ücretsiz deneme başlattığında bitişinden bir gün öncesine hatırlatıcı kur.")], BASE_TAGS),
 ("acil-durum-fonu", "BİRİKİM", "Acil Durum Fonu Nedir?", "Beklenmedik masraf geldiğinde ne yaparsın?", "Bozulan bir telefon ya da beklenmedik bir masraf geldiğinde ne yaparsın?", [
   ("Ayrı bir hesap aç", "Acil durum parasını günlük harcama hesabından ayrı tut."),
   ("Küçük başla", "İlk hedefin tek bir aylık temel giderin olsun."),
   ("Otomatik talimat ver", "Maaş günü küçük bir tutarın otomatik aktarılmasını ayarla."),
   ("Sadece acil için kullan", "Tatil ya da indirim acil durum değildir. Bu kurala sadık kal.")], BASE_TAGS),
 ("indirim-tuzaklari", "DİKKAT", "İndirim Tuzakları", "İndirim seni nasıl kandırıyor?", "Her indirim gerçekten indirim değil. Bu tuzaklara dikkat et.", [
   ("Sahte eski fiyat", "Bazı ürünlerin fiyatı indirimden önce yükseltilir. Fiyat geçmişine bak."),
   ("İkinci ürün bedava", "İhtiyacın olmayan ikinci ürün, kazanç değil fazladan harcamadır."),
   ("Son birkaç saat baskısı", "Geri sayım sayaçları acele ettirip düşünmeni engellemek için var."),
   ("Kargo bedava sınırı", "Kargo için sepete eklediğin ürün, kargo ücretinden pahalıya gelebilir.")], BASE_TAGS),
 ("kahve-hesabi", "HESAP", "Küçük Harcamaların Gücü", "Günlük kahven sana yılda kaça mal oluyor?", "Her gün aldığın küçük şeylerin yıllık toplamını hiç hesapladın mı?", [
   ("Günlük tutarı yaz", "Her gün tekrar eden küçük bir harcamanı seç ve tutarını yaz."),
   ("Üç yüz altmış beşle çarp", "Sonucu yılın gün sayısıyla çarp. Rakam seni şaşırtacak."),
   ("Tamamen bırakma", "Amaç yasak değil. Haftada birkaç günü evde hazırlamak bile yeter."),
   ("Farkı biriktir", "Evde yaptığın günlerde o tutarı ayrı bir kumbaraya at.")], BASE_TAGS),
 ("yemek-planlama", "MUTFAK", "Haftalık Yemek Planı", "Dışarıdan yemek bütçeni eritiyor mu?", "Dışarıdan söylenen yemekler bütçeni eritiyorsa, haftalık plan tam çözüm.", [
   ("Pazar planla", "Haftanın yemeklerini tek seferde, pazar günü belirle."),
   ("Ortak malzeme seç", "Aynı malzemeyle birden fazla yemek yapılabilecek tarifler seç."),
   ("Toplu pişir", "Bir kerede büyük tencere yap, porsiyonlayıp dondur."),
   ("Artanı değerlendir", "Artan yemekleri ertesi gün farklı bir tarifte kullan.")], BASE_TAGS),
 ("israf-onle", "MUTFAK", "Mutfakta İsrafı Bitir", "Aldığın yiyeceğin bir kısmını çöpe atıyorsun", "Fark etmesen de aldığın yiyeceklerin bir kısmı çöpe gidiyor olabilir.", [
   ("Önce eskiyi öne al", "Buzdolabında yeni aldıklarını arkaya, eskileri öne koy."),
   ("Ekmeği dondur", "Ekmeği dilimleyip dondurursan bayatlamadan istediğin kadar kullanırsın."),
   ("Sebzeyi doğru sakla", "Yeşillikleri nemli bir havluya sararak saklarsan daha uzun dayanır."),
   ("Son kullanma tarihine bak", "Alışverişten önce dolabı kontrol et, aynı ürünü tekrar alma.")], BASE_TAGS),
 ("borc-kartopu", "BORÇ", "Borçtan Kurtulma Yöntemi", "Birden fazla borcun mu var?", "Birden fazla borcun varsa, bu yöntem motivasyonunu korumana yardım eder.", [
   ("Hepsini listele", "Tüm borçlarını tutarı ve faiziyle birlikte bir kağıda yaz."),
   ("Minimumları öde", "Gecikme olmaması için her borcun asgari ödemesini aksatma."),
   ("Birine odaklan", "Ekstra paranı tek bir borca yönlendir; ya en küçüğüne ya en yüksek faizlisine."),
   ("Zinciri sürdür", "Bir borç bittiğinde onun ödemesini sıradaki borca ekle.")], BASE_TAGS),
 ("kart-kullanimi", "KART", "Kredi Kartını Doğru Kullan", "Kredi kartı seni zengin de eder, batırır da", "Kredi kartı doğru kullanılırsa avantajlıdır, yanlış kullanılırsa pahalıya patlar.", [
   ("Asgariyle yetinme", "Sadece asgari tutarı ödersen kalan borca faiz işler."),
   ("Limiti düşük tut", "İhtiyacından yüksek limit, harcamayı kolaylaştırır."),
   ("Taksiti planla", "Her taksit, gelecek ayların bütçesinden bir parçadır."),
   ("Kesim tarihini bil", "Büyük alışverişi kesimden hemen sonra yaparsan ödemeye daha çok zamanın olur.")], BASE_TAGS),
 ("dolap-duzen", "DÜZEN", "Dolabını 10 Dakikada Topla", "Dolabın sürekli dağınık mı?", "Dolabın sürekli dağınıksa, bu dört adım on dakikada işini görür.", [
   ("Hepsini çıkar", "Bir rafı tamamen boşalt. Ne olduğunu ancak böyle görürsün."),
   ("Üç grup yap", "Tut, bağışla, at. Bir yıldır giymediğini düşünmeden ayır."),
   ("Dikey katla", "Tişörtleri dikey katlarsan hepsini tek bakışta görürsün."),
   ("Bir girerse bir çıksın", "Yeni bir kıyafet aldığında eski birini çıkar.")], LIFE_TAGS),
 ("sabah-rutini", "RUTİN", "Güne Hızlı Başlamanın Sırrı", "Sabahları hep geç mi kalıyorsun?", "Sabahları hep koşturuyorsan, işin sırrı aslında bir önceki akşamda.", [
   ("Kıyafeti akşamdan seç", "Yarın giyeceklerini akşamdan hazırla, sabah karar vermekle uğraşma."),
   ("Çantanı kapının yanına koy", "Anahtar, cüzdan ve çanta hep aynı yerde dursun."),
   ("Alarmı uzağa koy", "Telefonu yataktan uzağa koyarsan erteleme tuşuna basamazsın."),
   ("Bir bardak su iç", "Uyanır uyanmaz bir bardak su, güne daha zinde başlamanı sağlar.")], LIFE_TAGS),
 ("telefon-pil", "TEKNO", "Telefon Şarjı Daha Uzun Gitsin", "Şarjın öğlene kadar bitiyor mu?", "Telefonunun şarjı öğlene kadar bitiyorsa, bu ayarları kontrol et.", [
   ("Ekran parlaklığı", "Otomatik parlaklığı aç ve ekran zaman aşımını kısalt."),
   ("Arka plan uygulamaları", "Arka planda konum ve veri kullanan uygulamaları kısıtla."),
   ("Karanlık mod", "Bazı ekranlarda karanlık mod pil tüketimini azaltır."),
   ("Aşırı sıcaktan koru", "Telefonu güneşte ya da sıcak yerde şarj etme. Pil ömrünü kısaltır.")], LIFE_TAGS),
 ("temizlik-sirke", "EV", "Sirkeyle Ev Temizliği", "Pahalı temizlik ürünlerine gerek yok", "Birçok temizlik işi için pahalı ürünlere gerek yok. Sirke çoğunu halleder.", [
   ("Kireç lekeleri", "Musluk ve duş başlığındaki kireci sirkeli bezle sararak çözebilirsin."),
   ("Cam ve ayna", "Su ve sirke karışımı camlarda iz bırakmadan temizler."),
   ("Çamaşır yumuşatıcı", "Son durulamaya biraz sirke eklemek yumuşatıcı etkisi yapar."),
   ("Dikkat et", "Mermer ve doğal taşta sirke kullanma, yüzeye zarar verebilir.")], LIFE_TAGS),
 ("bir-dakika-kurali", "ALIŞKANLIK", "Bir Dakika Kuralı", "Ev neden hep dağınık?", "Evin bir türlü toplanmıyorsa, bu basit kural hayatını değiştirir.", [
   ("Kural basit", "Bir işi yapmak bir dakikadan kısa sürüyorsa hemen yap."),
   ("Örnekler", "Bardağı yıka, ceketi as, postayı aç. Hepsi bir dakikadan az."),
   ("Neden işe yarar", "Küçük işler birikince büyük ve göz korkutan bir yığına dönüşür."),
   ("Sonuç", "Birkaç gün içinde evin ve kafanın daha düzenli olduğunu fark edersin.")], LIFE_TAGS),
 ("odaklanma", "VERİM", "Odaklanma Sorunu Yaşıyorsan", "Beş dakikada bir telefona mı bakıyorsun?", "Çalışırken sürekli telefona bakıyorsan, bu yöntemleri dene.", [
   ("Yirmi beş dakika kuralı", "Yirmi beş dakika tek işe odaklan, sonra beş dakika mola ver."),
   ("Telefonu başka odaya koy", "Göz önünde olmayan telefon, dikkatini daha az böler."),
   ("Tek sekme", "Bilgisayarda sadece o işle ilgili sekmeyi açık tut."),
   ("Bitirme listesi", "Güne başlamadan bitirmek istediğin üç işi yaz.")], LIFE_TAGS),
 ("ikinci-el", "PARA", "İkinci El Alırken Dikkat", "İkinci el alırken kazıklanma", "İkinci el ürün almak çok tasarruf sağlar ama dikkat etmezsen kazıklanırsın.", [
   ("Sıfır fiyatına bak", "Önce ürünün yeni fiyatını öğren, ikinci el fiyatı mantıklı mı karşılaştır."),
   ("Yerinde dene", "Elektronik ürünleri mutlaka çalışırken gör ve dene."),
   ("Kapora gönderme", "Görmediğin ürüne önceden para gönderme."),
   ("Faturayı sor", "Fatura ve garanti belgesi varsa ürünün geçmişi hakkında fikir verir.")], BASE_TAGS),
 ("tatil-butcesi", "PLAN", "Ucuza Tatil Planı", "Tatil pahalı olmak zorunda değil", "Tatil pahalı olmak zorunda değil. Bu dört ipucu bütçeni korur.", [
   ("Sezon dışı git", "Aynı yer, sezon dışında çok daha uygun fiyatlı olabilir."),
   ("Erken rezervasyon", "Ulaşım ve konaklamayı erken ayarlamak genelde daha ucuzdur."),
   ("Mutfaklı konaklama", "Kahvaltıyı kendin hazırlarsan yemek masrafı ciddi düşer."),
   ("Günlük limit koy", "Tatilde de günlük harcama sınırı belirle.")], BASE_TAGS),
 ("kumbara-meydan", "BİRİKİM", "52 Hafta Birikim Oyunu", "Birikim yapmayı oyuna çevir", "Birikim yapmakta zorlanıyorsan, bunu bir oyuna çevirebilirsin.", [
   ("Nasıl oynanır", "İlk hafta küçük bir tutar biriktir, her hafta bu tutarı biraz artır."),
   ("Tersten başla", "Zorlanırsan büyük tutardan başlayıp her hafta azalt."),
   ("Tabloyu as", "Elli iki kutulu bir tablo yap, her hafta bir kutuyu boya."),
   ("Yıl sonu", "Bir yılın sonunda düzenli bir birikim alışkanlığın olur.")], BASE_TAGS),
 ("elektrik-mutfak", "MUTFAK", "Pişirirken Enerji Tasarrufu", "Ocakta farkında olmadan para yakıyorsun", "Yemek pişirirken farkında olmadan fazladan enerji harcıyor olabilirsin.", [
   ("Kapağı kapat", "Tencerenin kapağını kapatmak suyu çok daha hızlı kaynatır."),
   ("Tencere ocağa uysun", "Küçük tencereyi büyük gözde pişirmek enerjiyi boşa harcar."),
   ("Fırını açıp bakma", "Fırın kapağını her açışında ısı kaçar, pişirme uzar."),
   ("Kalan ısıyı kullan", "Ocağı birkaç dakika erken kapatıp yemeği kalan ısıyla bitir.")], BASE_TAGS),
 ("maas-gunu", "PARA", "Maaş Günü Yapılacaklar", "Maaş yatınca ilk ne yapıyorsun?", "Maaş yattığı gün yaptığın ilk şey, ayın nasıl geçeceğini belirler.", [
   ("Faturaları öde", "Sabit giderleri hemen öde, sonra ne kaldığını net gör."),
   ("Birikimi ayır", "Harcamaya başlamadan birikim payını ayrı hesaba aktar."),
   ("Haftalara böl", "Kalan parayı dört haftaya böl, her hafta kendi payını kullansın."),
   ("Ödül payı bırak", "Küçük bir keyif bütçesi, kuralları bozmamanı kolaylaştırır.")], BASE_TAGS),
 ("uyku-duzen", "SAĞLIKLI", "Daha İyi Uyumak İçin", "Uyuyamıyor musun?", "Yatağa girince uyuyamıyorsan, bu alışkanlıklar yardımcı olabilir.", [
   ("Aynı saatte yat", "Hafta sonu dahil her gün benzer saatlerde yatıp kalk."),
   ("Ekranı bırak", "Yatmadan önce bir süre ekrana bakmamaya çalış."),
   ("Odayı serin tut", "Serin, karanlık ve sessiz bir oda uykuyu kolaylaştırır."),
   ("Akşam kafeinine dikkat", "Öğleden sonra kafein tüketimini azaltmayı dene.")], LIFE_TAGS),
 ("camasir-ipucu", "EV", "Çamaşır Hataları", "Kıyafetlerin çabuk mu eskiyor?", "Kıyafetlerin çabuk eskiyorsa, bu çamaşır hatalarından birini yapıyor olabilirsin.", [
   ("Ters çevir", "Koyu ve baskılı kıyafetleri ters çevirip yıka, renkleri korunur."),
   ("Fazla deterjan koyma", "Fazla deterjan daha temiz yapmaz, kumaşta kalıntı bırakır."),
   ("Etikete bak", "Yıkama etiketi kıyafetin ömrünü uzatmanın en kolay yolu."),
   ("Kurutucuyu azalt", "Mümkünse havada kurut. Hem kumaş korunur hem fatura düşer.")], LIFE_TAGS),
 ("fiyat-takip", "ALIŞVERİŞ", "Online Alışverişte Tasarruf", "Online alışverişte fazla mı ödüyorsun?", "Online alışveriş yaparken çoğu kişi aynı ürüne fazla para ödüyor.", [
   ("Sepette beklet", "Ürünü sepete ekleyip birkaç gün bekle. Bazen fiyat düşer."),
   ("Birkaç siteye bak", "Aynı ürünün fiyatını farklı satıcılarda karşılaştır."),
   ("Yorumları oku", "Ucuz ama kalitesiz ürün, iki kez almak demektir."),
   ("Kart bilgisini kaydetme", "Kayıtlı kart, tek tıkla plansız alışverişi kolaylaştırır.")], BASE_TAGS),
 ("hediye-butce", "PLAN", "Bütçe Dostu Hediye Fikirleri", "Hediye almak bütçeni zorluyor mu?", "Özel günlerde hediye almak bütçeni zorluyorsa, bu fikirleri dene.", [
   ("El yapımı", "Kendi yaptığın bir şey, pahalı bir hediyeden daha akılda kalıcı olabilir."),
   ("Deneyim hediye et", "Birlikte yapılacak bir aktivite, eşyadan daha değerli olabilir."),
   ("Yıllık liste tut", "Özel günleri baştan yaz, hediye bütçesini aylara yay."),
   ("İndirimde topla", "Uygun bir fırsat gördüğünde ileride vereceğin hediyeyi şimdiden al.")], BASE_TAGS),
 ("araba-yakit", "YAKIT", "Daha Az Yakıt Harca", "Yakıt masrafın çok mu yüksek?", "Yakıt masrafın yüksekse, sürüş alışkanlıklarını değiştirmek fark yaratır.", [
   ("Yumuşak kalk", "Sert hızlanma ve ani fren yakıt tüketimini artırır."),
   ("Lastik basıncı", "Düşük lastik basıncı aracın daha çok yakmasına neden olur."),
   ("Bagajı boşalt", "Gereksiz yük taşımak da yakıt demektir."),
   ("Rölantide bekleme", "Uzun süre bekleyeceksen motoru kapatmak daha mantıklı.")], BASE_TAGS),
 ("dijital-temizlik", "TEKNO", "Telefon Hafızan Dolu mu?", "Depolama alanı dolu uyarısı mı aldın?", "Telefonunda sürekli depolama dolu uyarısı alıyorsan, şunları dene.", [
   ("Mesaj medyası", "Mesajlaşma uygulamalarındaki eski fotoğraf ve videoları temizle."),
   ("Kullanmadığın uygulamalar", "Son birkaç ayda açmadığın uygulamaları kaldır."),
   ("Önbelleği temizle", "Bazı uygulamaların önbelleği zamanla çok büyür."),
   ("Yedekle ve sil", "Fotoğrafları yedekledikten sonra cihazdan kaldırabilirsin.")], LIFE_TAGS),
 ("ihtiyac-istek", "PARA", "İhtiyaç mı, İstek mi?", "Bunu gerçekten istiyor musun?", "Bir şey almadan önce kendine bu dört soruyu sor.", [
   ("Olmasa ne olur?", "Bu ürün olmasa hayatında gerçekten bir şey eksik kalır mı?"),
   ("Benzeri var mı?", "Evde aynı işi gören başka bir şeyin var mı?"),
   ("Kaç kez kullanırım?", "Fiyatı kullanım sayısına böl. Gerçek maliyeti göreceksin."),
   ("Kaç saatlik emek?", "Bu ürün için kaç saat çalışman gerektiğini hesapla.")], BASE_TAGS),
 ("haftalik-temizlik", "DÜZEN", "Günde 15 Dakika Temizlik", "Hafta sonun temizlikle mi geçiyor?", "Hafta sonun hep temizlikle geçiyorsa, işi güne yaymayı dene.", [
   ("Her güne bir oda", "Pazartesi mutfak, salı banyo gibi her güne bir alan ver."),
   ("Zamanlayıcı kur", "On beş dakika kur, süre bitince bırak."),
   ("Yukarıdan aşağı", "Önce raflar, sonra yüzeyler, en son yer. İş tekrar etmez."),
   ("Akşam toparlama", "Yatmadan önce beş dakika ortalığı toplamak sabahı kolaylaştırır.")], LIFE_TAGS),
]

out = []
for i, (vid, badge, title, hook, hook_say, items, tags) in enumerate(V):
    scenes = [{"kind": "hook", "text": hook, "say": hook_say}]
    for n, (t, s) in enumerate(items, 1):
        scenes.append({"kind": "item", "num": n, "text": t, "say": s})
    scenes.append({"kind": "cta", "text": "Takip et!", "say": CTA[i % len(CTA)]})
    out.append({
        "id": f"{i+1:02d}-{vid}", "badge": badge, "title": title + " #shorts",
        "description": f"{hook_say} {title} hakkında kısa ve pratik ipuçları.",
        "hashtags": tags, "scenes": scenes,
    })
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "senaryo")
