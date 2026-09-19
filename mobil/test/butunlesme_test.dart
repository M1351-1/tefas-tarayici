/// ÜRETİCİNİN GERÇEK ÇIKTISIYLA BÜTÜNLEŞME TESTİ.
///
/// NEDEN BU DOSYA VAR
/// ==================
///
/// `cekirdek_test.dart` elle yazılmış bir fikstür kullanıyor. Fikstür bir
/// süre üreticinin ARTIK YAZMADIĞI bir alanı (`kirilim` içinde
/// `volatilite`) taşıdı ve testler bu yüzden geçti — oysa gerçek veride
/// mobil puan üreticininkinin 0,8 katı çıkıyordu ve oynaklık ağırlığı
/// hiçbir şey yapmıyordu. Yani iki taraf da kendi içinde tutarlıydı,
/// birbirini tutmuyordu.
///
/// Elle yazılmış bir fikstür bu sınıf hatayı asla yakalayamaz: sözleşme
/// değiştiğinde fikstürü de aynı yanlış varsayımla güncelleriz. Tek
/// çare, üreticinin GERÇEKTEN ÜRETTİĞİ dosyayı okumak.
///
/// `data/fonlar.json` yoksa test atlanır (depo klonu her zaman veriyi
/// içermeyebilir). Atlanması bir şey KANITLAMAZ; sadece o çalıştırmada
/// bu kontrolün yapılmadığı anlamına gelir.
library;

import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';
import 'package:tefas_mobil/cekirdek/modeller.dart';
import 'package:tefas_mobil/cekirdek/puanlama.dart';

/// Toplayıcıdaki ayarlar.json ile aynı olmalı.
const varsayilan = {
  'aylik_getiri': 0.35,
  'uc_aylik_getiri': 0.25,
  'haftalik_getiri': 0.20,
  'volatilite': 0.20,
};

void main() {
  final dosya = File('../data/fonlar.json');
  final varMi = dosya.existsSync();

  group('Üretici çıktısıyla bütünleşme', () {
    late List<Fon> fonlar;
    late Map<String, dynamic> kok;

    setUpAll(() {
      if (!varMi) return;
      kok = jsonDecode(dosya.readAsStringSync()) as Map<String, dynamic>;
      fonlar = (kok['fonlar'] as List)
          .cast<Map<String, dynamic>>()
          .map(Fon.jsondan)
          .toList();
    });

    test('dosya standart JSON olarak çözümlenir', () {
      // `json.dump` varsayılan olarak NaN'i `NaN` diye yazar; bu standart
      // JSON değildir ve `jsonDecode` FormatException atar. Tek bozuk
      // fon, telefondaki listeyi HİÇ açılmaz hale getirir.
      expect(kok['fonlar'], isA<List>());
      expect(fonlar, isNotEmpty);
    });

    test('mobil puan üreticinin getiri_puani değerinin AYNISI', () {
      // ASIL GERİLEME TESTİ. Ölçülmüştü: üretici 1,4863 iken mobil
      // 1,18904 (tam olarak 0,8 katı) veriyordu.
      var bakilan = 0;
      for (final f in fonlar) {
        if (f.kirilim.isEmpty || f.getiriPuani == null) continue;
        final mobil = puanHesapla(f, varsayilan);
        expect(mobil, isNotNull, reason: '${f.kod}: mobil puan üretilemedi');
        expect(mobil!, closeTo(f.getiriPuani!, 1e-3),
            reason: '${f.kod}: üretici ${f.getiriPuani}, mobil $mobil');
        bakilan++;
      }
      expect(bakilan, greaterThan(100), reason: 'yeterli fon incelenmedi');
    });

    test('katkılar toplamı puanı açıklar', () {
      var bakilan = 0;
      for (final f in fonlar) {
        if (f.kirilim.isEmpty || f.getiriPuani == null) continue;
        final toplam =
            katkilar(f, varsayilan).fold<double>(0, (t, e) => t + e.katki);
        expect(toplam, closeTo(f.getiriPuani!, 1e-3), reason: f.kod);
        bakilan++;
      }
      expect(bakilan, greaterThan(100));
    });

    test('risk kırılımı geliyor ve Sakinlik puanını açıklıyor', () {
      // Üretici bunu hesaplıyordu ama JSON'a hiç yazmıyordu.
      final riskli = fonlar.where((f) => f.riskKirilim.isNotEmpty).toList();
      expect(riskli.length, greaterThan(100),
          reason: 'risk kırılımı hiç yazılmamış');
      for (final f in riskli) {
        final toplam =
            f.riskKirilim.fold<double>(0, (t, k) => t + k.katki);
        expect(toplam, closeTo(f.riskPuani!, 1e-3), reason: f.kod);
      }
    });

    test('eksik risk bileşeni olan fonlar işaretli', () {
      // Sıfır fiyat / büyük boşluk yüzünden maksimum düşüşü
      // hesaplanamayan fonlar var; puanları YALNIZ oynaklıktan üretiliyor
      // ve bu ekranda görünmeliydi.
      final eksikli = fonlar.where((f) => f.riskEksik.isNotEmpty);
      for (final f in eksikli) {
        expect(f.riskKirilim.map((k) => k.metrik),
            isNot(contains(f.riskEksik.first)),
            reason: '${f.kod}: eksik dediği bileşen kırılımda var');
      }
    });

    test('koşullu stopaj muafiyeti işaretli geliyor', () {
      // Muafiyet son günün portföy dağılımından çıkarılıyor; süreklilik
      // ve 1 yıldan uzun elde tutma doğrulanamıyor.
      final muaf = fonlar.where((f) => f.stopajsiz).toList();
      expect(muaf, isNotEmpty);
      expect(muaf.where((f) => f.stopajKosullu).length, muaf.length,
          reason: 'muaf sayılan fonlar koşullu işaretini taşımıyor');
    });

    test('öngörü ölçümü yayımlanan puanı sınıyor', () {
      // Ölçülen ile yayımlanan aynı şey olmalı: ham 63 günlük getiri
      // sıralaması değil, ekrandaki bileşik puan.
      final o = kok['ongoru_gucu'] as Map<String, dynamic>?;
      expect(o, isNotNull);
      expect(o!['uretim_getiri'], isNotEmpty,
          reason: 'üretim puanının ölçümü JSON\'a girmemiş');
      expect(o['uretim_risk'], isNotEmpty);
      expect(o['ozet'] as String,
          contains('uygulamada gösterilen getiri puanına'));
    });
  }, skip: varMi ? false : 'data/fonlar.json yok; bu kontrol atlandı');
}
