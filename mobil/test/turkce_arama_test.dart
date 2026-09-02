/// TÜRKÇE ARAMA GERİLEME TESTİ.
///
/// Dart'ın toUpperCase()/toLowerCase() metodları Türkçe I/İ ayrımını
/// bilmez. Arama bu yüzden SESSİZCE çalışmıyordu: kullanıcı "piyasasi"
/// yazdığında hiçbir fon bulunmuyordu, çünkü fon adında "PİYASASI" var
/// ve 'PİYASASI'.contains('PIYASASI') false dönüyor.
///
/// Hata görünür bir belirti vermiyordu — sadece boş sonuç. TEFAS fon
/// adlarının neredeyse hepsinde İ, Ş, Ğ geçtiği için aramanın büyük
/// kısmı ölüydü.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:tefas_mobil/cekirdek/durum.dart';

void main() {
  group('katla', () {
    test('Türkçe büyük İ ile düz i eşleşir', () {
      expect(katla('PİYASASI'), katla('piyasasi'));
      expect(katla('PİYASASI'), 'piyasasi');
    });

    test('noktasız ı da aynı yere katlanır', () {
      expect(katla('ALTIN'), katla('altın'));
      expect(katla('ALTIN'), 'altin');
    });

    test('ş ğ ü ö ç katlanır', () {
      expect(katla('ŞGÜÖÇ'), 'sguoc');
      expect(katla('şgüöç'), 'sguoc');
    });

    test('birleştirici üst nokta temizlenir', () {
      // lower() bazı ortamlarda i + U+0307 uretiyor; iz kalmamali.
      expect(katla('i̇'), 'i');
    });

    test('ASIL SINAV: gerçek fon adı gerçek sorguyla bulunur', () {
      const ad = 'AGESA HAYAT VE EMEKLİLİK A.Ş. BİRİNCİ PARA PİYASASI '
          'EMEKLİLİK YATIRIM FONU';
      // Eski kod bu dördünde de BOŞ donuyordu.
      expect(katla(ad).contains(katla('para piyasasi')), isTrue);
      expect(katla(ad).contains(katla('PARA PİYASASI')), isTrue);
      expect(katla(ad).contains(katla('emeklilik')), isTrue);
      expect(katla(ad).contains(katla('EMEKLİLİK')), isTrue);
    });

    test('alakasız sorgu yine de eşleşmez', () {
      const ad = 'AGESA BİRİNCİ PARA PİYASASI FONU';
      expect(katla(ad).contains(katla('hisse senedi')), isFalse);
    });
  });
}
