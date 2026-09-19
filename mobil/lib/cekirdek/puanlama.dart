/// Yerel yeniden puanlama.
///
/// Kullanıcı ağırlıkları değiştirdiğinde TEFAS'a tekrar gitmeye ya da
/// istatistikleri baştan hesaplamaya gerek yok: JSON'daki z-skorlar
/// AĞIRLIKTAN BAĞIMSIZDIR. z, "bu fon kategori ortalamasından kaç standart
/// sapma uzakta" demektir; ağırlık ise o z'nin puana ne kadar gireceği.
/// Dolayısıyla yeniden puanlama sadece bir ağırlıklı toplamdır.
///
/// İKİ EKSEN, İKİ SÖZLEŞME
/// =======================
///
/// Üretici puanlamayı ikiye ayırdı: getiri ekseni (geçmişin tasviri) ve
/// risk ekseni (Sakinlik). `kirilim` artık YALNIZCA getiri bileşenlerini
/// taşıyor; oynaklık ayrı eksende ve sabit %60/%40 bileşimle üretiliyor.
///
/// Burası bir süre eski dört bileşenli sözleşmeyi kullandı ve iki hata
/// birden üretti:
///
///   1. Normalizasyon yoktu. Varsayılan ağırlıkların toplamı 1,0 ama
///      getiri bileşenlerininki 0,80; JSON'da oynaklık kırılımı
///      bulunmadığı için mobil puan üreticininkinin 0,8 KATI çıkıyordu.
///      Ölçüldü: üretici 1,4863 iken mobil 1,18904.
///   2. Oynaklık ağırlığı ÖLÜYDÜ. Eşleşen bir kırılım olmadığından
///      kaydırıcıyı sonuna kadar açmak puanı değiştirmiyordu; tamamı
///      oynaklığa verildiğinde puan 0,0 oluyordu.
///
/// Artık kullanılan ağırlıkların toplamına bölünüyor: üreticinin
/// `eksen()` fonksiyonuyla aynı kural, aynı sayı. Oynaklık tercihi de
/// gerçekten çalışıyor — ama ait olduğu yerde, RİSK ekseninde
/// (bkz. [birlesikPuan]).
library;

import 'modeller.dart';

/// Risk ekseninin ağırlığını taşıyan anahtar.
///
/// Kullanıcı ayarlarında "Düşük oynaklık" diye görünüyor; artık getiri
/// puanına değil, yayımlanan Sakinlik puanına uygulanıyor.
const String riskAgirlikAnahtari = 'volatilite';

/// GETİRİ ekseninin puanı — üreticinin `getiri_puani` değeriyle aynı.
///
/// Kullanılan ağırlıkların toplamına bölünür. Eşleşen bileşen yoksa
/// null döner; 0,0 dönmek "ortalama bir fon" gibi okunurdu.
double? puanHesapla(Fon fon, Map<String, double> agirliklar) {
  var toplam = 0.0;
  var kullanilan = 0.0;
  for (final k in fon.kirilim) {
    final a = agirliklar[k.metrik];
    if (a == null || a == 0) continue;
    toplam += a * k.z;
    kullanilan += a;
  }
  if (kullanilan <= 0) return null;
  return toplam / kullanilan;
}

/// Getiri ve risk eksenlerini kullanıcının tercihiyle birleştirir.
///
/// Sıralama için TEK sayı gerektiğinde kullanılır (akıllı seçici gibi).
/// Ayrı ayrı gösterildikleri ekranlarda birleştirilmemeli: iki eksen iki
/// ayrı bilgidir ve ölçülen öngörü güçleri çok farklıdır.
///
/// Ölçüldü, üç ayrı örneklemde (üç aylık ileri Spearman):
///
///     örneklem                        getiri puanı   Sakinlik
///     yerel DB   (30 Ağu, 2335 fon)      0,024         0,667
///     yayımlanan (18 Eyl, 2320 fon)      0,148         0,668
///     ayrı ölçüm (2488 fon)              0,095         0,726
///
/// Getiri ekseni örneklemden örnekleme 6 KAT oynuyor, Sakinlik %9
/// içinde duruyor. Yani getiri ekseni yalnızca zayıf değil, KARARSIZ
/// da — tek bir değeri "ölçülen sayı" diye yazmak bunu gizler.
/// Sakinlik ise hem güçlü hem tekrarlanabilir çıkıyor; risk ağırlığının
/// gerçekten bir şey yapması bu yüzden gerekiyor.
///
/// Güncel sayılar her toplamada yeniden ölçülüp JSON'a yazılıyor;
/// burada gömülü DEĞİL, uygulamadaki ölçüm şeridinden okunur.
double? birlesikPuan(Fon fon, Map<String, double> agirliklar) {
  final getiri = puanHesapla(fon, agirliklar);
  final risk = fon.riskPuani;
  final riskAgirlik = agirliklar[riskAgirlikAnahtari] ?? 0.0;
  final getiriAgirlik = agirliklar.entries
      .where((e) => e.key != riskAgirlikAnahtari)
      .fold(0.0, (t, e) => t + e.value);

  var toplam = 0.0;
  var kullanilan = 0.0;
  if (getiri != null && getiriAgirlik > 0) {
    toplam += getiriAgirlik * getiri;
    kullanilan += getiriAgirlik;
  }
  if (risk != null && riskAgirlik > 0) {
    toplam += riskAgirlik * risk;
    kullanilan += riskAgirlik;
  }
  if (kullanilan <= 0) return null;
  return toplam / kullanilan;
}

/// Bir fonun katkı dökümü — "neden üst sırada?" ekranı için.
///
/// [puanHesapla] ile AYNI normalizasyonu kullanır; yoksa döküm puanı
/// açıklamaz. Üretici tarafında da aynı hata vardı: puan yeniden
/// normalize ediliyor, katkılar edilmiyordu.
List<({Kirilim kirilim, double katki})> katkilar(
    Fon fon, Map<String, double> agirliklar) {
  var kullanilan = 0.0;
  for (final k in fon.kirilim) {
    final a = agirliklar[k.metrik];
    if (a == null || a == 0) continue;
    kullanilan += a;
  }
  if (kullanilan <= 0) return const [];

  final liste = fon.kirilim
      .where((k) => (agirliklar[k.metrik] ?? 0.0) != 0)
      .map((k) => (
            kirilim: k,
            katki: (agirliklar[k.metrik] ?? 0.0) * k.z / kullanilan,
          ))
      .toList();
  // Puana en çok etki edeni başa al (mutlak değere göre).
  liste.sort((a, b) => b.katki.abs().compareTo(a.katki.abs()));
  return liste;
}

/// Fon listesini verilen ağırlıklarla yeniden puanlayıp kategori içinde
/// sıralar. Dönen kayıtta puan ve sıra yeni ağırlıklara göredir.
class PuanliFon {
  final Fon fon;
  final double? puan;
  final int? sira;

  const PuanliFon({required this.fon, this.puan, this.sira});
}

List<PuanliFon> yenidenPuanla(List<Fon> fonlar, Map<String, double> agirliklar) {
  // Puanlanabilir olanları kategori+tip içinde grupla.
  final gruplar = <String, List<Fon>>{};
  final puansiz = <Fon>[];
  for (final f in fonlar) {
    if (f.kirilim.isEmpty) {
      puansiz.add(f);
    } else {
      gruplar.putIfAbsent('${f.tip}|${f.kategori}', () => []).add(f);
    }
  }

  final cikti = <PuanliFon>[];
  for (final grup in gruplar.values) {
    // PUANI HESAPLANAMAYAN FON 0,0 SAYILMAZ.
    //
    // Önce `?? 0.0` yazıyordu: puanı olmayan bir fon kategorinin tam
    // ortasına yerleşiyordu. "Ölçülemedi" ile "ortalama" aynı şey değil;
    // puansız olanlar sıralamanın dışında kalır.
    final puanli = <({Fon fon, double puan})>[];
    for (final f in grup) {
      final p = puanHesapla(f, agirliklar);
      if (p == null) {
        puansiz.add(f);
      } else {
        puanli.add((fon: f, puan: p));
      }
    }
    puanli.sort((a, b) => b.puan.compareTo(a.puan));
    for (var i = 0; i < puanli.length; i++) {
      cikti.add(PuanliFon(
          fon: puanli[i].fon, puan: puanli[i].puan, sira: i + 1));
    }
  }
  for (final f in puansiz) {
    cikti.add(PuanliFon(fon: f));
  }
  return cikti;
}
