/// Yerel yeniden puanlama.
///
/// Kullanıcı ağırlıkları değiştirdiğinde TEFAS'a tekrar gitmeye ya da
/// istatistikleri baştan hesaplamaya gerek yok: JSON'daki z-skorlar
/// AĞIRLIKTAN BAĞIMSIZDIR. z, "bu fon kategori ortalamasından kaç standart
/// sapma uzakta" demektir; ağırlık ise o z'nin puana ne kadar gireceği.
/// Dolayısıyla yeniden puanlama sadece bir ağırlıklı toplamdır.
library;

import 'modeller.dart';

/// Bir fonun verilen ağırlıklarla puanı. Kırılımı yoksa null.
double? puanHesapla(Fon fon, Map<String, double> agirliklar) {
  if (fon.kirilim.isEmpty) return null;
  var toplam = 0.0;
  for (final k in fon.kirilim) {
    toplam += (agirliklar[k.metrik] ?? 0.0) * k.z;
  }
  return toplam;
}

/// Bir fonun katkı dökümü — "neden üst sırada?" ekranı için.
List<({Kirilim kirilim, double katki})> katkilar(
    Fon fon, Map<String, double> agirliklar) {
  final liste = fon.kirilim
      .map((k) => (kirilim: k, katki: (agirliklar[k.metrik] ?? 0.0) * k.z))
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
    final puanli = grup
        .map((f) => (fon: f, puan: puanHesapla(f, agirliklar) ?? 0.0))
        .toList()
      ..sort((a, b) => b.puan.compareTo(a.puan));
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
