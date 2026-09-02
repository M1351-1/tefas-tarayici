/// Uygulama durumu: yüklenen veri, yükleme/hata durumu ve ayarlar.
///
/// Harici bir durum yönetimi paketi kullanmıyoruz; tek bir ChangeNotifier
/// ve InheritedNotifier bu boyuttaki bir uygulama için fazlasıyla yeterli.
library;

import 'package:flutter/material.dart';

import 'ayarlar.dart';
import 'modeller.dart';
import 'puanlama.dart';
import 'veri.dart';

enum YuklemeDurumu { basliyor, yukleniyor, hazir, hata }

class UygulamaDurumu extends ChangeNotifier {
  final Ayarlar ayarlar;

  UygulamaDurumu(this.ayarlar) {
    // Ağırlık değişince yeniden puanlama gerekir.
    ayarlar.addListener(_ayarDegisti);
  }

  YuklemeDurumu _durum = YuklemeDurumu.basliyor;
  Veri? _veri;
  String _hata = '';
  String _hataOneri = '';
  List<PuanliFon> _puanli = const [];

  YuklemeDurumu get durum => _durum;
  Veri? get veri => _veri;
  String get hata => _hata;
  String get hataOneri => _hataOneri;
  List<PuanliFon> get puanli => _puanli;

  bool get hazir => _durum == YuklemeDurumu.hazir && _veri != null;

  void _ayarDegisti() {
    if (_veri != null) {
      _puanla();
      notifyListeners();
    }
  }

  void _puanla() {
    final v = _veri;
    if (v == null) return;
    _puanli = ayarlar.agirliklarVarsayilan
        // Varsayılan ağırlıklarda toplayıcının hesapladığı puan geçerli;
        // yeniden hesaplamaya gerek yok.
        ? v.fonlar
            .map((f) => PuanliFon(fon: f, puan: f.puan, sira: f.sira))
            .toList()
        : yenidenPuanla(v.fonlar, ayarlar.agirliklar);
  }

  /// Açılış: önce önbelleği göster (hızlı), sonra arka planda tazele.
  Future<void> baslat() async {
    final kaynak = VeriKaynagi(adres: ayarlar.adres);
    final onbellek = await kaynak.onbellektenOku();
    if (onbellek != null) {
      _veri = onbellek;
      _puanla();
      _durum = YuklemeDurumu.hazir;
      notifyListeners();
    } else {
      _durum = YuklemeDurumu.yukleniyor;
      notifyListeners();
    }
    await tazele(sessiz: onbellek != null);
  }

  /// Veriyi yeniden indirir.
  ///
  /// [sessiz] true ise başarısızlıkta hata ekranına geçmez — elimizde zaten
  /// önbellekten gelen bir veri var, onu göstermeye devam etmek daha iyi.
  Future<void> tazele({bool sessiz = false}) async {
    if (!sessiz) {
      _durum = YuklemeDurumu.yukleniyor;
      notifyListeners();
    }
    try {
      final kaynak = VeriKaynagi(adres: ayarlar.adres);
      _veri = await kaynak.yukle();
      _puanla();
      _durum = YuklemeDurumu.hazir;
      _hata = '';
      _hataOneri = '';
    } on VeriHatasi catch (e) {
      if (_veri == null) {
        _durum = YuklemeDurumu.hata;
        _hata = e.mesaj;
        _hataOneri = e.oneri;
      } else {
        _durum = YuklemeDurumu.hazir;
      }
    } catch (e) {
      if (_veri == null) {
        _durum = YuklemeDurumu.hata;
        _hata = 'Beklenmeyen bir hata oluştu.';
        _hataOneri = e.toString();
      } else {
        _durum = YuklemeDurumu.hazir;
      }
    }
    notifyListeners();
  }

  // ------------------------------------------------------------ sorgular

  List<PuanliFon> kategoridekiler(String tip, String kategori) {
    final liste = _puanli
        .where((p) => p.fon.tip == tip && p.fon.kategori == kategori)
        .toList();
    liste.sort((a, b) {
      if (a.sira != null && b.sira != null) return a.sira!.compareTo(b.sira!);
      if (a.sira != null) return -1;
      if (b.sira != null) return 1;
      return a.fon.kod.compareTo(b.fon.kod);
    });
    return liste;
  }

  List<PuanliFon> favoriler() =>
      _puanli.where((p) => ayarlar.favoriMi(p.fon.kod)).toList()
        ..sort((a, b) => a.fon.kod.compareTo(b.fon.kod));

  List<PuanliFon> ara(String sorgu) {
    final s = katla(sorgu.trim());
    if (s.isEmpty) return const [];
    return _puanli
        .where((p) => katla(p.fon.kod).contains(s) || katla(p.fon.ad).contains(s))
        .take(80)
        .toList()
      ..sort((a, b) {
        // Kod tam eşleşmesi en üstte.
        final ax = katla(a.fon.kod) == s ? 0 : 1;
        final bx = katla(b.fon.kod) == s ? 0 : 1;
        if (ax != bx) return ax - bx;
        return a.fon.kod.compareTo(b.fon.kod);
      });
  }

  /// Günlük getiriye göre en çok yükselen / düşen fonlar.
  ///
  /// Sadece puanlanabilir (yani elenmemiş, yeterince büyük ve geçmişi olan)
  /// fonlara bakıyoruz: elenmiş küçük bir fonun %80 sıçraması listeyi
  /// anlamsızlaştırırdı.
  List<Fon> gunlukUcler({required bool yukselen, int adet = 10}) {
    final liste = _puanli
        .map((p) => p.fon)
        .where((f) => f.getiri.gunluk != null && f.puan != null)
        .toList();
    liste.sort((a, b) => yukselen
        ? b.getiri.gunluk!.compareTo(a.getiri.gunluk!)
        : a.getiri.gunluk!.compareTo(b.getiri.gunluk!));
    return liste.take(adet).toList();
  }

  PuanliFon? fonBul(String kod) {
    for (final p in _puanli) {
      if (p.fon.kod == kod) return p;
    }
    return null;
  }

  @override
  void dispose() {
    ayarlar.removeListener(_ayarDegisti);
    super.dispose();
  }
}

/// Ağaçtan durum erişimi.
class Kapsam extends InheritedNotifier<UygulamaDurumu> {
  const Kapsam({super.key, required UygulamaDurumu durum, required super.child})
      : super(notifier: durum);

  static UygulamaDurumu of(BuildContext context) {
    final k = context.dependOnInheritedWidgetOfExactType<Kapsam>();
    assert(k != null, 'Kapsam bulunamadı');
    return k!.notifier!;
  }
}

/// TÜRKÇE ARAMA KATLAMASI.
///
/// Dart'ın `toUpperCase()`/`toLowerCase()` metodları Türkçe I/İ ayrımını
/// bilmez ve arama SESSİZCE çalışmaz hale gelir:
///
///     'AGESA BİRİNCİ PARA PİYASASI'.toUpperCase()
///         .contains('piyasasi'.toUpperCase())   // false
///
/// Kullanıcı "piyasasi" yazdığında hiçbir fon bulunmuyordu; TEFAS fon
/// adlarının neredeyse hepsinde İ, Ş, Ğ geçtiği için bu, aramayı büyük
/// ölçüde kullanılmaz kılıyordu.
///
/// Çözüm: iki tarafı da ASCII'ye katla. Yan faydası, Türkçe klavyesi
/// olmayan ya da aceleyle yazan kullanıcının "gunluk" yazıp "GÜNLÜK"
/// bulabilmesi.
String katla(String metin) {
  const harita = {
    'İ': 'i', 'I': 'i', 'ı': 'i',
    'Ş': 's', 'ş': 's',
    'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u',
    'Ö': 'o', 'ö': 'o',
    'Ç': 'c', 'ç': 'c',
    '̇': '', // birleştirici üst nokta: lower()'ın bıraktığı iz
  };
  final tampon = StringBuffer();
  for (final k in metin.split('')) {
    tampon.write(harita[k] ?? k);
  }
  return tampon.toString().toLowerCase();
}
