/// Çekirdek mantık testleri: JSON çözümleme, yeniden puanlama, akıllı filtre.
///
/// Hiçbiri ağa çıkmaz.
///
/// `flutter test` ile DEĞİL, `dart test` ile koşar: bu makinede Windows
/// Uygulama Denetimi ilkesi flutter_tester.exe'yi engelliyor. Test edilen
/// çekirdek Flutter'a bağımlı olmadığı için saf Dart VM yeterli.
library;

import 'dart:convert';

import 'package:test/test.dart';
import 'package:tefas_mobil/cekirdek/modeller.dart';
import 'package:tefas_mobil/cekirdek/puanlama.dart';
import 'package:tefas_mobil/cekirdek/secici.dart';

/// Toplayıcının ürettiği biçimde tek bir fon kaydı.
Map<String, dynamic> fonJson({
  String kod = 'AAA',
  String kategori = 'Hisse Senedi',
  String tip = 'YAT',
  String kaynak = 'api',
  bool katilim = false,
  double? aylik = 10,
  double? ucAylik = 30,
  double? haftalik = 2,
  double? yillik = 60,
  double? gunluk = 0.5,
  double? volatilite = 20,
  double? maksDusus = -12,
  double? puan = 1.0,
  int? sira = 1,
  int? kisi = 5000,
  double? buyukluk = 100000000,
  int? gozlem = 250,
  int? kategoriFonSayisi = 40,
  bool kirilimVar = true,
}) =>
    {
      'kod': kod,
      'ad': '$kod PORTFÖY TEST FONU',
      'tip': tip,
      'tip_ad': 'Yatırım Fonu',
      'kategori': kategori,
      'kategori_kaynak': kaynak,
      'katilim': katilim,
      'tarih': '2026-08-28',
      'fiyat': 1.5,
      'kisi_sayisi': kisi,
      'buyukluk': buyukluk,
      'gozlem': gozlem,
      'getiri': {
        'gunluk': gunluk,
        'haftalik': haftalik,
        'aylik': aylik,
        'uc_aylik': ucAylik,
        'yillik': yillik,
        'yilbasindan': 40,
      },
      'volatilite': volatilite,
      'maks_dusus': maksDusus,
      'puan': puan,
      'sira': sira,
      'kategori_fon_sayisi': kategoriFonSayisi,
      'kirilim': kirilimVar
          ? {
              'aylik_getiri': {
                'deger': aylik,
                'kategori_ortalamasi': 8.0,
                'z': 1.0,
                'agirlik': 0.35,
                'katki': 0.35,
              },
              'uc_aylik_getiri': {
                'deger': ucAylik,
                'kategori_ortalamasi': 25.0,
                'z': 0.8,
                'agirlik': 0.25,
                'katki': 0.20,
              },
              'haftalik_getiri': {
                'deger': haftalik,
                'kategori_ortalamasi': 1.5,
                'z': 0.5,
                'agirlik': 0.20,
                'katki': 0.10,
              },
              'volatilite': {
                'deger': volatilite,
                'kategori_ortalamasi': 25.0,
                'z': 0.6,
                'agirlik': 0.20,
                'katki': 0.12,
              },
            }
          : null,
    };

void main() {
  group('JSON çözümleme', () {
    test('fon alanları doğru okunur', () {
      final f = Fon.jsondan(fonJson(kod: 'AFA', aylik: 12.5));
      expect(f.kod, 'AFA');
      expect(f.getiri.aylik, 12.5);
      expect(f.volatilite, 20);
      expect(f.puanlandi, isTrue);
      expect(f.kirilim.length, 4);
    });

    test('eksik alanlar çökertmez', () {
      final f = Fon.jsondan({'kod': 'XXX', 'getiri': {}});
      expect(f.kod, 'XXX');
      expect(f.getiri.aylik, isNull);
      expect(f.puan, isNull);
      expect(f.puanlandi, isFalse);
      expect(f.kategori, 'Bilinmiyor');
    });

    test('kırılım ağırlığa göre büyükten küçüğe sıralanır', () {
      final f = Fon.jsondan(fonJson());
      expect(f.kirilim.first.agirlik, 0.35);
    });

    test('kurucu fon adından çıkarılır', () {
      final f = Fon.jsondan({
        'kod': 'AFA',
        'ad': 'AK PORTFÖY AMERİKA YABANCI HİSSE SENEDİ FONU',
        'getiri': {},
      });
      expect(f.kurucu, 'AK PORTFÖY');
    });

    test('PORTFÖY geçmeyen adda ilk iki kelime alınır', () {
      final f = Fon.jsondan({'kod': 'X', 'ad': 'BİR İKİ ÜÇ DÖRT', 'getiri': {}});
      expect(f.kurucu, 'BİR İKİ');
    });

    test('katılım bayrağı okunur', () {
      final f = Fon.jsondan(fonJson(katilim: true));
      expect(f.katilim, isTrue);
    });

    test('tüm dosya çözümlenir', () {
      final ham = jsonEncode({
        'surum': 1,
        'veri_tarihi': '2026-08-28',
        'uretim_zamani': '2026-08-29T22:00:00+03:00',
        'sorumluluk_notu': 'Yatırım tavsiyesi değildir.',
        'ayarlar': {
          'agirliklar': {'aylik_getiri': 0.35, 'volatilite': 0.20}
        },
        'kategoriler': [
          {
            'tip': 'YAT',
            'tip_ad': 'Yatırım Fonu',
            'ad': 'Hisse Senedi',
            'adet': 170,
            'puanlanabilir': true,
            'api_adet': 169,
            'cikarim_adet': 1,
          }
        ],
        'fonlar': [fonJson(kod: 'AAA'), fonJson(kod: 'BBB')],
      });
      final v = Veri.jsondan(jsonDecode(ham) as Map<String, dynamic>);
      expect(v.fonlar.length, 2);
      expect(v.veriTarihi, '2026-08-28');
      expect(v.agirliklar['aylik_getiri'], 0.35);
      expect(v.kategoriler.first.cikarimAgirlikli, isFalse);
    });

    test('çıkarım ağırlıklı kategori işaretlenir', () {
      final k = KategoriOzeti.jsondan({
        'tip': 'EMK',
        'ad': 'Değişken',
        'adet': 133,
        'puanlanabilir': true,
        'api_adet': 0,
        'cikarim_adet': 133,
      });
      expect(k.cikarimAgirlikli, isTrue);
    });
  });

  group('Yeniden puanlama', () {
    test('varsayılan ağırlıkla toplayıcının puanına yakın çıkar', () {
      final f = Fon.jsondan(fonJson());
      final p = puanHesapla(f, const {
        'aylik_getiri': 0.35,
        'uc_aylik_getiri': 0.25,
        'haftalik_getiri': 0.20,
        'volatilite': 0.20,
      });
      // 0.35*1.0 + 0.25*0.8 + 0.20*0.5 + 0.20*0.6 = 0.77
      expect(p, closeTo(0.77, 1e-9));
    });

    test('ağırlık değişince puan değişir', () {
      final f = Fon.jsondan(fonJson());
      final a = puanHesapla(f, const {'aylik_getiri': 1.0});
      final b = puanHesapla(f, const {'volatilite': 1.0});
      expect(a, closeTo(1.0, 1e-9));
      expect(b, closeTo(0.6, 1e-9));
      expect(a, isNot(b));
    });

    test('kırılımı olmayan fon puanlanmaz', () {
      final f = Fon.jsondan(fonJson(kirilimVar: false));
      expect(puanHesapla(f, const {'aylik_getiri': 1.0}), isNull);
    });

    test('katkılar mutlak değere göre sıralanır', () {
      final f = Fon.jsondan(fonJson());
      final k = katkilar(f, const {
        'aylik_getiri': 0.1,
        'uc_aylik_getiri': 0.9,
        'haftalik_getiri': 0.0,
        'volatilite': 0.0,
      });
      expect(k.first.kirilim.metrik, 'uc_aylik_getiri');
    });

    test('yeniden puanlama kategori içinde sıralar', () {
      final fonlar = [
        Fon.jsondan(fonJson(kod: 'DUSUK', aylik: 1)),
        Fon.jsondan(fonJson(kod: 'YUKSEK', aylik: 50)),
      ];
      // z değerleri sabit olduğu için puanlar eşit; sıra kod bazlı kararlı olmalı
      final sonuc = yenidenPuanla(fonlar, const {'aylik_getiri': 1.0});
      expect(sonuc.length, 2);
      expect(sonuc.every((p) => p.sira != null), isTrue);
    });
  });

  group('Akıllı filtre', () {
    List<Fon> evren() => [
          Fon.jsondan(fonJson(
              kod: 'SAKIN', volatilite: 3, maksDusus: -2,
              kategori: 'Para Piyasası')),
          Fon.jsondan(fonJson(
              kod: 'ORTA', volatilite: 18, maksDusus: -15,
              kategori: 'Borçlanma Araçları')),
          Fon.jsondan(fonJson(
              kod: 'SERT', volatilite: 55, maksDusus: -40,
              kategori: 'Hisse Senedi')),
          Fon.jsondan(fonJson(
              kod: 'ALTIN', volatilite: 25, maksDusus: -18,
              kategori: 'Kıymetli Madenler', katilim: true)),
          Fon.jsondan(fonJson(
              kod: 'EMEKLI', volatilite: 10, maksDusus: -5,
              tip: 'EMK', kategori: 'Standart (BES)')),
        ];

    test('düşük risk yüksek oynaklığı eler', () {
      final s = sec(evren(), const Profil(risk: RiskToleransi.dusuk));
      final kodlar = s.adaylar.map((a) => a.fon.kod).toSet();
      expect(kodlar.contains('SERT'), isFalse);
      expect(kodlar.contains('SAKIN'), isTrue);
    });

    test('yüksek risk hiçbir şeyi elemez', () {
      final s = sec(evren(), const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar.map((a) => a.fon.kod), contains('SERT'));
    });

    test('emeklilik fonu varsayılan olarak dışarıda', () {
      final s = sec(evren(), const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar.map((a) => a.fon.kod).contains('EMEKLI'), isFalse);
    });

    test('emeklilik açıkça istenince gelir', () {
      final s = sec(evren(),
          const Profil(risk: RiskToleransi.yuksek, emeklilikDahil: true));
      expect(s.adaylar.map((a) => a.fon.kod), contains('EMEKLI'));
    });

    test('katılım tercihi kategoriye değil bayrağa bakar', () {
      // ALTIN fonu "Kıymetli Madenler" kategorisinde ama katılım esaslı.
      // Kategori adına bakan bir filtre bunu kaçırırdı.
      final s = sec(evren(),
          const Profil(risk: RiskToleransi.yuksek, tercihler: {Tercih.katilim}));
      expect(s.adaylar.map((a) => a.fon.kod), ['ALTIN']);
    });

    test('tür tercihi filtreler', () {
      final s = sec(evren(),
          const Profil(risk: RiskToleransi.yuksek, tercihler: {Tercih.hisse}));
      expect(s.adaylar.map((a) => a.fon.kod), ['SERT']);
    });

    test('puanlanmamış fon kısa listeye giremez', () {
      final fonlar = [Fon.jsondan(fonJson(kod: 'PUANSIZ', kirilimVar: false))];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar, isEmpty);
      expect(s.ozet.puansizElendi, 1);
    });

    test('eleme özeti dar boğazı bildirir', () {
      final s = sec(evren(), const Profil(risk: RiskToleransi.dusuk));
      expect(s.ozet.baslangic, 5);
      expect(s.ozet.darBogaz, isNotNull);
    });

    test('sonuç boşsa dar boğaz en çok eleyeni gösterir', () {
      final fonlar = [
        Fon.jsondan(fonJson(kod: 'A', volatilite: 90, maksDusus: -5)),
        Fon.jsondan(fonJson(kod: 'B', volatilite: 91, maksDusus: -5)),
      ];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.dusuk));
      expect(s.adaylar, isEmpty);
      expect(s.ozet.darBogaz, 'oynaklık sınırı');
    });

    test('vade ağırlıkları toplamı 1', () {
      for (final v in Vade.values) {
        final toplam = v.agirliklar.values.fold<double>(0, (a, b) => a + b);
        expect(toplam, closeTo(1.0, 1e-9), reason: '${v.ad} ağırlıkları');
      }
    });

    test('uzun vade haftalık getiriye az ağırlık verir', () {
      expect(Vade.uzun.agirliklar['haftalik_getiri']!,
          lessThan(Vade.kisa.agirliklar['haftalik_getiri']!));
    });
  });

  group('Tutarlılık uyarıları', () {
    test('aylık güçlü ama yıllık negatifse ciddi uyarı verilir', () {
      final fonlar = [
        Fon.jsondan(fonJson(kod: 'TUZAK', aylik: 20, yillik: -15))
      ];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar.first.ciddiUyariVar, isTrue);
      expect(s.adaylar.first.uyarilar.first.metin, contains('1 yıllık'));
    });

    test('derin düşüş uyarı üretir', () {
      final fonlar = [
        Fon.jsondan(fonJson(kod: 'DERIN', maksDusus: -50, yillik: 60))
      ];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar.first.uyarilar.any((u) => u.metin.contains('tepeden')),
          isTrue);
    });

    test('az yatırımcılı fon uyarı üretir', () {
      final fonlar = [Fon.jsondan(fonJson(kod: 'KUCUK', kisi: 40))];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.yuksek));
      expect(
          s.adaylar.first.uyarilar.any((u) => u.metin.contains('yatırımcısı')),
          isTrue);
    });

    test('sağlıklı fon gereksiz uyarı almaz', () {
      final fonlar = [
        Fon.jsondan(fonJson(
            kod: 'SAGLAM', aylik: 4, ucAylik: 15, yillik: 60,
            maksDusus: -8, kisi: 20000, gozlem: 250, kategoriFonSayisi: 80))
      ];
      final s = sec(fonlar, const Profil(risk: RiskToleransi.yuksek));
      expect(s.adaylar.first.uyarilar, isEmpty);
    });

    test('her aday en az bir gerekçe taşır', () {
      final s = sec(evrenBasit(), const Profil(risk: RiskToleransi.yuksek));
      for (final a in s.adaylar) {
        expect(a.gerekceler, isNotEmpty);
      }
    });
  });

  group('Geçmiş', () {
    test('son N gözlem alınır', () {
      final g = Gecmis(
        kod: 'A',
        tarihler: List.generate(100, (i) => '2026-01-${i + 1}'),
        fiyatlar: List.generate(100, (i) => i.toDouble()),
      );
      final k = g.son(21);
      expect(k.fiyatlar.length, 21);
      expect(k.fiyatlar.last, 99.0);
    });

    test('istenen sayı gözlemden çoksa hepsi döner', () {
      const g = Gecmis(kod: 'A', tarihler: ['x'], fiyatlar: [1.0]);
      expect(g.son(252).fiyatlar.length, 1);
    });
  });

  dagilimTestleri();
}

List<Fon> evrenBasit() => [
      Fon.jsondan(fonJson(kod: 'A')),
      Fon.jsondan(fonJson(kod: 'B')),
    ];

// ------------------------------------------------------- portföy dağılımı

void dagilimTestleri() {
  group('Portföy dağılımı', () {
    Gecmis ornek() => Gecmis.jsondan({
          'kod': 'AFA',
          'tarihler': ['2026-08-27', '2026-08-28'],
          'fiyatlar': [1.2, 1.29],
          'dagilim': [
            {'kod': 'yhs', 'ad': 'Yabancı Hisse Senedi', 'yuzde': 96.99},
            {'kod': 'yyf', 'ad': 'Yatırım Fonları Katılma Payları', 'yuzde': 1.74},
            {'kod': 'tr', 'ad': 'Ters-Repo', 'yuzde': 1.26},
          ],
        });

    test('dağılım çözümlenir', () {
      final g = ornek();
      expect(g.dagilim.length, 3);
      expect(g.dagilim.first.ad, 'Yabancı Hisse Senedi');
      expect(g.dagilim.first.yuzde, 96.99);
    });

    test('dağılım yoksa boş liste', () {
      final g = Gecmis.jsondan({'kod': 'X', 'tarihler': [], 'fiyatlar': []});
      expect(g.dagilim, isEmpty);
    });

    test('son() dağılımı kırpmaz', () {
      // Dağılım tek bir güne aittir; dönem seçimi onu etkilememeli.
      final g = ornek().son(1);
      expect(g.fiyatlar.length, 1);
      expect(g.dagilim.length, 3);
    });

    test('birleştirilmiş "Diğer" satırı tanınır', () {
      final g = Gecmis.jsondan({
        'kod': 'X',
        'tarihler': <String>[],
        'fiyatlar': <double>[],
        'dagilim': [
          {'kod': 'hs', 'ad': 'Hisse Senedi', 'yuzde': 60.0},
          {'kod': '_diger', 'ad': 'Diğer (9 kalem)', 'yuzde': 40.0},
        ],
      });
      expect(g.dagilim.first.toplananDiger, isFalse);
      expect(g.dagilim.last.toplananDiger, isTrue);
    });

    test('bozuk kalem çökertmez', () {
      final g = Gecmis.jsondan({
        'kod': 'X',
        'tarihler': <String>[],
        'fiyatlar': <double>[],
        'dagilim': [<String, dynamic>{}],
      });
      expect(g.dagilim.length, 1);
      expect(g.dagilim.first.yuzde, 0);
    });
  });
}
