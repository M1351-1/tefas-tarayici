# TEFAS Fon Tarayıcı

TEFAS'taki yatırım, emeklilik ve borsa yatırım fonlarının günlük verisini
toplayan, getiri ve risk metriklerini hesaplayan, **kategori içinde**
puanlayıp sıralayan iki parçalı bir sistem.

> **Bu bir yatırım tavsiyesi aracı değildir.** Gösterilen sıralamalar geçmiş
> fiyat verilerinden hesaplanmış istatistiklerdir. Geçmiş getiri gelecek
> getiriyi göstermez. Veriler TEFAS'tan alınmıştır, hata içerebilir.

---

## Nasıl çalışıyor

```
[1] TOPLAYICI (Python, günde bir kez)
       TEFAS API → SQLite → metrik + puan → JSON

[2] MOBİL UYGULAMA (Flutter, Android)
       hazır JSON'u indir → göster
```

Telefon TEFAS'a **hiç bağlanmaz.** İki sebep: TEFAS dakikada yalnızca 6 istek
kabul ediyor ve Akamai koruması var; binlerce telefonun doğrudan bağlanması
hem imkânsız hem de engellenmeye davetiye.

---

## Klasörler

| Yol | Ne var |
|---|---|
| `toplayici/` | Python veri toplayıcı |
| `toplayici/test/` | 68 test (ağa çıkmaz) |
| `data/` | SQLite veritabanı ve üretilen JSON (git'e girmez) |
| `mobil/` | Flutter uygulaması |
| `.github/workflows/` | Günlük otomatik toplama |

---

## Toplayıcı komutları

```bash
python toplayici/topla.py dolum
```
İlk kurulum. 400 günlük geçmişi çeker. **~30 dakika sürer** — TEFAS dakikada
6 istek kabul ettiği için beklemek zorundayız. Bir kez çalıştırılır.

```bash
python toplayici/topla.py gunluk
```
Günlük çalışma. Sadece eksik günleri çeker, saniyeler sürer.

```bash
python toplayici/topla.py kategori
```
Kategori eşlemesini yeniler. Haftada bir yeterli.

```bash
python toplayici/topla.py hesapla
```
**Ağa hiç çıkmaz.** `ayarlar.json`'daki ağırlıkları değiştirdikten sonra
puanları yeniden hesaplar. Saniyeler sürer.

---

## Ayarlar (`toplayici/ayarlar.json`)

| Ayar | Varsayılan | Ne yapar |
|---|---|---|
| `agirliklar` | 0,35 / 0,25 / 0,20 / 0,20 | Puanın hangi metrikten ne kadar geleceği. Toplamı 1 olmalı. |
| `asgari_gecmis_gun` | 90 | Bu kadar işlem günü verisi olmayan fon sıralanmaz |
| `asgari_fon_buyuklugu` | 10.000.000 TL | Küçük fonlar likit değildir, elenir |
| `asgari_kategori_fon_sayisi` | 10 | Bu sayıdan az fonu olan kategori puanlanmaz |
| `z_kirpma` | 3,0 | z-skorların kırpıldığı sınır |
| `gecmis_gun` | 400 | İlk dolumda kaç gün geriye gidileceği |

---

## Puanlama nasıl çalışıyor

Kara kutu bir "al bunu" tavsiyesi yok. Formül açık:

```
puan = 0,35 × z(aylık getiri)
     + 0,25 × z(3 aylık getiri)
     + 0,20 × z(haftalık getiri)
     + 0,20 × z(−oynaklık)
```

`z` = "kategori ortalamasından kaç standart sapma uzakta". Her fon için
puanın hangi bileşenden ne kadar geldiği JSON'a yazılır ve uygulamada
"Neden bu sırada?" bölümünde gösterilir.

### Üç önemli tasarım kararı

**1. Puanlama kategori İÇİNDE yapılır.** Hisse fonu %40 oynaklıkla %80
getirir, para piyasası fonu %1,6 oynaklıkla %60. Aynı listede yarıştırmak
anlamsız olur.

**2. Fon tipi de ayrı bir boyuttur.** Emeklilik fonlarının masraf ve vergi
yapısı farklıdır; aynı kategorinin emeklilik ve yatırım versiyonu ayrı
sıralanır.

**3. 10'dan az fonu olan kategori puanlanmaz.** z-skor "ortalamadan kaç
standart sapma" demektir; 4 fonluk bir kategoride ortalama da sapma da
anlamsızdır. Puan üretmek, bilimsel görünümlü çürük sayı üretmek olurdu.

> **Not:** `n` fonluk bir grupta `|z|` en fazla `(n−1)/√n` olabilir. Yani 10
> fonluk bir kategoride z asla 2,85'i geçemez ve `z_kirpma = 3,0` hiç
> devreye girmez. Kırpma, büyük kategoriler için bir emniyet supabıdır.

---

## Kategori bilgisi nereden geliyor

İki kaynak var ve **eşit değiller**:

| Kaynak | Nerede | Güvenilirlik |
|---|---|---|
| `api` | Yatırım fonları (2038 fon) | TEFAS'ın kendi sınıflaması — kesin |
| `isim` | Emeklilik + borsa yatırım fonları (434 fon) | Fon adından çıkarım |

**Neden çıkarım gerekiyor:** TEFAS'ın `sfonTurKod` kategori filtresi sadece
yatırım fonlarında çalışıyor. Emeklilik ve borsa yatırım fonlarında filtreyi
**sessizce yok sayıp bütün fonları döndürüyor.** Toplayıcı bunu tespit ediyor
(filtresiz toplamla karşılaştırarak) ve o tipte API'ye güvenmiyor.

Bu tespit olmasaydı her emeklilik fonu, işlenen son kategorinin etiketini
alırdı ve kategori bazlı sıralama tamamen çürürdü. Uygulama, kategorisi
çıkarımla belirlenmiş listelerde bunu kullanıcıya söylüyor.

**Katılım (faizsiz) bir kategori değil, bir niteliktir.** "Altın Katılım"
fonu varlık sınıfı olarak Kıymetli Madenler'dir ama katılım esaslıdır.
Kategoriyi varlık sınıfına göre veriyoruz, katılımı ayrı bir bayrak olarak
tutuyoruz.

---

## TEFAS API'si hakkında bilinmesi gerekenler

TEFAS Nisan 2026'da Next.js altyapısına geçti. Eski `/api/DB/BindHistoryInfo`
uçları **404 dönüyor**; internetteki eski kod örnekleri çalışmaz.

| Uç | Ne verir |
|---|---|
| `POST /api/funds/fonGnlBlgSiraliGetir` | Fiyat, pay sayısı, kişi sayısı, fon büyüklüğü |
| `POST /api/funds/fonTurGetir` | 12 şemsiye fon türü ve kodları |
| `POST /api/funds/dagilimSiraliGetirT` | Portföy varlık dağılımı |

- **POST + JSON gövde.** GET denerseniz "Method not found or disabled" alırsınız.
- **`Origin` ve `Referer` başlıkları zorunlu.**
- **Dakikada 6 istek.** Toplayıcıda kayan pencereli hız sınırlayıcı var.
- **Tek istekte en fazla ~28 gün.** Ama o 28 günün BÜTÜN fonlarını verir —
  fon başına değil, tarih aralığı başına istek atılır. 2038 fon tek çağrıda
  gelir.
- Tatil/hafta sonu için `"Index 0 out of bounds"` gibi mesajlar dönebilir;
  bu hata değil, "veri yok" demektir.

---

## Otomasyon

`.github/workflows/gunluk.yml` hafta içi TR saatiyle 20:00'de çalışır.

Veri dosyaları **`veri` dalına** yazılır, `main`'e değil. Her çalışmada o dal
tek commit olarak yeniden yazılır — 2335 geçmiş dosyasını her gün main'e
işlemek git geçmişini yılda gigabaytlarca şişirirdi.

SQLite veritabanı (104 MB) GitHub'ın 100 MB dosya sınırını aştığı için repoda
durmaz; GitHub Actions önbelleğinde tutulur. Önbellek düşerse iş akışı tam
dolum yapar (~30 dakika).

### Eğer GitHub Actions engellenirse

TEFAS'ta Akamai koruması var ve bulut sunucu IP'lerini engellemesi yaygın.
İş akışı sürekli başarısız oluyorsa yedek plan:

1. `toplayici/topla.py gunluk` komutunu kendi bilgisayarınızda Windows Görev
   Zamanlayıcı ile hafta içi 20:00'de çalıştırın.
2. Sonucu `veri` dalına gönderin.

Ev IP'niz engellenmez; bu dosyadaki bütün veriler o şekilde toplandı.

---

## Mobil uygulama

```bash
cd mobil
flutter analyze
dart test          # flutter test DEĞİL — aşağıya bakın
flutter build apk --release
```

> `flutter test` bu makinede çalışmıyor: Windows Uygulama Denetimi ilkesi
> `flutter_tester.exe`'yi engelliyor. Çekirdek mantık (modeller, puanlama,
> seçici) Flutter'a bağımlı olmadığı için testler `package:test` ile
> yazıldı ve `dart test` ile saf Dart VM'de koşuyor.

### Ekranlar

| Ekran | Ne yapar |
|---|---|
| **Özet** | Bugün en çok yükselen/düşen 10 fon |
| **Akıllı Filtre** | Risk/vade/tercih sorularından kısa liste + gerekçe + uyarılar |
| **Kategoriler** | Kategori listesi → o kategorinin sıralı fonları |
| **Tüm Fonlar** | Yatay kaydırmalı, sütun başlığından sıralanan tablo |
| **Fon Detay** | Fiyat grafiği (1A/3A/6A/1Y), tüm metrikler, puan kırılımı |
| **Favoriler** | Yıldızlanan fonlar (üst çubuktaki yıldız) |
| **Ayarlar** | Tema, ağırlıklar, Claude anahtarı, veri adresi |

### Akıllı filtre

Bir tavsiye motoru **değil**, bir eleme motorudur. Kullanıcının söylediği
kısıtlarla binlerce fonu daraltır, kalanları tutarlılık açısından denetler
ve her satır için gerekçesini yazar.

Tutarlılık denetimleri sıralamanın en tehlikeli yanını yakalar — kısa
vadeli bir sıçramanın fonu tepeye taşıması:

- "Son ayda güçlü yükseldi ama 1 yıllık getirisi negatif"
- "Yükselişin tamamı son aya sıkışmış"
- "Tepeden dibe %X kaybettirdiği bir dönem olmuş"
- "Sadece N yatırımcısı var; alım satımda fiyat kayması yaşayabilirsiniz"

### Claude bağlantısı (isteğe bağlı)

Ayarlardan kendi Anthropic API anahtarınızı girerseniz kısa liste hakkında
serbest soru sorabilirsiniz. **Anahtar girmezseniz hiçbir özellik kapanmaz.**

- Anahtar cihazın şifreli deposunda (Android EncryptedSharedPreferences) durur.
- Anthropic'e sadece sorunuz ve ekrandaki fonların TEFAS'tan gelen kamuya
  açık sayıları gider. Anahtarınız, favorileriniz, cihaz bilginiz gitmez.
- Her soru kendi hesabınızdan ücretlendirilir.
- Sistem talimatı modele gelecek getiri tahmini yapmayı ve "şunu al" demeyi
  yasaklar; bir dil modeli fon fiyatını bilemez, işi ekrandaki sayıları
  karşılaştırıp açıklamaktır.

---

## Yasal

Kendi kullanımınız için sorun yok. Uygulamayı yayımlayıp başkalarına fon
tavsiyesi verirseniz bu **SPK'nın yatırım danışmanlığı mevzuatı kapsamına
girebilir ve yetki belgesi gerektirir.** Yayımlamayı düşünüyorsanız önce bu
konuyu araştırın.
