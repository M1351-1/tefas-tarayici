/// Veri indirme ve önbellek.
///
/// Uygulama TEFAS'a HİÇ bağlanmaz. TEFAS dakikada 6 istek kabul ediyor ve
/// Akamai koruması var; binlerce telefonun doğrudan bağlanması hem imkânsız
/// hem de engellenmeye davetiye. Bunun yerine toplayıcı günde bir kez çalışıp
/// hazır bir JSON üretiyor, uygulama sadece onu indiriyor.
library;

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'modeller.dart';

/// Verinin duracağı varsayılan adres. Ayarlar ekranından değiştirilebilir.
///
/// `main` değil `veri` dalı: veri dosyaları ayrı bir dalda tutuluyor ve
/// her toplamada o dal tek commit olarak yeniden yazılıyor. Böylece 2335
/// geçmiş dosyasının günlük değişimi git geçmişini şişirmiyor.
const String varsayilanAdres =
    'https://raw.githubusercontent.com/M1351-1/tefas-tarayici/veri';

class VeriHatasi implements Exception {
  final String mesaj;
  final String oneri;

  const VeriHatasi(this.mesaj, [this.oneri = '']);

  @override
  String toString() => oneri.isEmpty ? mesaj : '$mesaj $oneri';
}

class VeriKaynagi {
  final String adres;
  final Duration zamanAsimi;

  VeriKaynagi({String? adres, this.zamanAsimi = const Duration(seconds: 30)})
      : adres = (adres ?? varsayilanAdres).replaceAll(RegExp(r'/+$'), '');

  /// Önbellek klasörü. Alınamazsa null döner — çağıran taraf çalışmaya
  /// devam eder, sadece önbelleksiz.
  ///
  /// Neden null dönebiliyor: path_provider her platformda yok (web'de
  /// desteklenmiyor) ve bazı cihazlarda depolama erişimi başarısız
  /// olabiliyor. Önbellek bir hızlandırmadır; onun yokluğu uygulamayı
  /// çalışmaz hale getirmemeli.
  Future<Directory?> _onbellekKlasoru() async {
    try {
      final k = await getApplicationSupportDirectory();
      final o = Directory(p.join(k.path, 'onbellek'));
      if (!await o.exists()) await o.create(recursive: true);
      return o;
    } catch (_) {
      return null;
    }
  }

  /// Önbellekteki dosyayı verir; önbellek yoksa null.
  Future<File?> _onbellekDosyasi(String ad) async {
    final klasor = await _onbellekKlasoru();
    if (klasor == null) return null;
    return File(p.join(klasor.path, ad));
  }

  // ------------------------------------------------------------ fon listesi

  /// Fon listesini indirir. Ağ yoksa önbellekten okur.
  ///
  /// [zorla] true ise önbellek atlanır ve mutlaka ağa çıkılır.
  Future<Veri> yukle({bool zorla = false}) async {
    final dosya = await _onbellekDosyasi('fonlar.json');

    try {
      final yanit = await http
          .get(Uri.parse('$adres/fonlar.json'))
          .timeout(zamanAsimi);

      if (yanit.statusCode == 404) {
        throw const VeriHatasi(
          'Veri dosyası bulunamadı.',
          'Ayarlardaki veri adresini kontrol edin.',
        );
      }
      if (yanit.statusCode != 200) {
        throw VeriHatasi(
          'Sunucu ${yanit.statusCode} döndürdü.',
          'Daha sonra tekrar deneyin.',
        );
      }

      // utf8.decode: Türkçe fon adları bozulmasın (bodyBytes, body değil).
      final metin = utf8.decode(yanit.bodyBytes);
      final veri = Veri.jsondan(jsonDecode(metin) as Map<String, dynamic>);

      if (veri.surum > desteklenenSurum) {
        throw const VeriHatasi(
          'Veri dosyası bu uygulamadan yeni.',
          'Uygulamayı güncelleyin.',
        );
      }

      // Önbelleğe yazamamak veriyi geçersiz kılmaz; sessizce geç.
      try {
        await dosya?.writeAsString(metin);
      } catch (_) {}
      return veri;
    } catch (e) {
      // Ağ başarısızsa önbelleğe düş — internetsiz de çalışsın.
      try {
        if (dosya != null && await dosya.exists()) {
          final metin = await dosya.readAsString();
          return Veri.jsondan(jsonDecode(metin) as Map<String, dynamic>,
              onbellekten: true);
        }
      } catch (_) {}
      if (e is VeriHatasi) rethrow;
      throw const VeriHatasi(
        'Veri indirilemedi ve kayıtlı veri yok.',
        'İnternet bağlantınızı kontrol edip tekrar deneyin.',
      );
    }
  }

  /// Sadece önbellekteki veriyi okur, ağa hiç çıkmaz. Açılışı hızlandırır.
  Future<Veri?> onbellektenOku() async {
    try {
      final dosya = await _onbellekDosyasi('fonlar.json');
      if (dosya == null || !await dosya.exists()) return null;
      final metin = await dosya.readAsString();
      return Veri.jsondan(jsonDecode(metin) as Map<String, dynamic>,
          onbellekten: true);
    } catch (_) {
      // Bozuk önbellek uygulamayı açılışta çökertmesin.
      return null;
    }
  }

  // --------------------------------------------------------------- geçmiş

  /// Bir fonun fiyat geçmişini indirir; indirilmişse önbellekten verir.
  ///
  /// Geçmiş dosyaları fon başına ayrıdır: hepsi tek dosyada ~10 MB tutuyor
  /// ve her açılışta indirmek anlamsız. Kullanıcı detaya girdiği fonun
  /// dosyasını indiriyoruz, o kadar.
  Future<Gecmis> gecmis(String kod, {String? veriTarihi}) async {
    File? dosya;
    final klasor = await _onbellekKlasoru();
    if (klasor != null) {
      try {
        final gk = Directory(p.join(klasor.path, 'gecmis'));
        if (!await gk.exists()) await gk.create(recursive: true);
        dosya = File(p.join(gk.path, '$kod.json'));
      } catch (_) {}
    }

    // Önbellekteki geçmiş, listedeki veri tarihiyle aynı günse tekrar
    // indirmeye gerek yok.
    if (dosya != null && await dosya.exists()) {
      try {
        final j = jsonDecode(await dosya.readAsString()) as Map<String, dynamic>;
        final g = Gecmis.jsondan(j);
        if (veriTarihi == null ||
            (g.tarihler.isNotEmpty && g.tarihler.last == veriTarihi)) {
          return g;
        }
      } catch (_) {
        // Bozuksa yeniden indir.
      }
    }

    try {
      final yanit =
          await http.get(Uri.parse('$adres/gecmis/$kod.json')).timeout(zamanAsimi);
      if (yanit.statusCode != 200) {
        throw VeriHatasi('Geçmiş verisi alınamadı (${yanit.statusCode}).');
      }
      final metin = utf8.decode(yanit.bodyBytes);
      try {
        await dosya?.writeAsString(metin);
      } catch (_) {}
      return Gecmis.jsondan(jsonDecode(metin) as Map<String, dynamic>);
    } catch (e) {
      try {
        if (dosya != null && await dosya.exists()) {
          final j =
              jsonDecode(await dosya.readAsString()) as Map<String, dynamic>;
          return Gecmis.jsondan(j);
        }
      } catch (_) {}
      if (e is VeriHatasi) rethrow;
      throw const VeriHatasi(
        'Fiyat geçmişi indirilemedi.',
        'İnternet bağlantınızı kontrol edin.',
      );
    }
  }

  /// Önbelleği siler. Ayarlar ekranındaki "veriyi sıfırla" için.
  Future<void> onbellegiSil() async {
    final klasor = await _onbellekKlasoru();
    if (klasor != null && await klasor.exists()) {
      await klasor.delete(recursive: true);
    }
  }
}
