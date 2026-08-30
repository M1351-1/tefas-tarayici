/// Claude bağlantısı — serbest soru sorma katmanı.
///
/// TAMAMEN İSTEĞE BAĞLIDIR. Anahtar girilmezse uygulamanın hiçbir özelliği
/// kapanmaz; akıllı filtre, sıralama, grafikler cihazda çalışmaya devam eder.
///
/// Ne gönderiliyor: sadece sorduğunuz soru ve ekranda zaten görünen fonların
/// TEFAS'tan gelen kamuya açık sayıları (kod, ad, getiri, oynaklık, puan).
/// Anahtarınız, favorileriniz ve cihaz bilgileriniz gönderilmez.
///
/// Ne YAPMIYOR: gelecek getiriyi tahmin etmiyor. Bir dil modeli fon fiyatını
/// bilemez; buradaki işi ekrandaki sayıları karşılaştırıp Türkçe açıklamak.
library;

export 'api_hata.dart' show DanismanHatasi, hataCevir;

import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'api_hata.dart';
import 'modeller.dart';
import 'secici.dart';

const String _uc = 'https://api.anthropic.com/v1/messages';
const String _surum = '2023-06-01';

/// Varsayılan model. Ayarlardan değiştirilebilir.
const String varsayilanModel = 'claude-sonnet-5';

/// Yedek liste. Gerçek liste API'den (`/v1/models`) çekilir; bu sadece
/// anahtar girilmeden önce dropdown boş kalmasın diye var.
const Map<String, String> modelSecenekleri = {
  'claude-haiku-4-5': 'Haiku 4.5 — en ucuz, en hızlı',
  'claude-sonnet-5': 'Sonnet 5 — dengeli (önerilen)',
  'claude-opus-5': 'Opus 5 — en güçlü',
};

/// `output_config.effort` destekleyen modeller.
///
/// Haiku 4.5 desteklemiyor; ona gönderirsek istek 400 döner. Bu yüzden
/// effort'u sadece destekleyen modellere yolluyoruz.
const Set<String> _effortDestekleyen = {
  'claude-fable-5',
  'claude-opus-5',
  'claude-sonnet-5',
  'claude-opus-4-8',
  'claude-opus-4-7',
  'claude-opus-4-6',
  'claude-sonnet-4-6',
};

/// max_tokens, DÜŞÜNME + YANIT toplamının sınırıdır.
///
/// Önce 1400 yazılmıştı; bu modellerde düşünme varsayılan olarak açık
/// olduğu için o kadar dar bir sınır yanıtı yarıda kesebiliyor. 4096
/// rahat bir tavan ve maliyeti artırmıyor: üretilmeyen token'ın ücreti
/// yok, bu yalnızca üst sınır.
const int azamiToken = 4096;

/// Sohbet için `low` effort öneriliyor: bu ekranda yapılan iş ekrandaki
/// tabloyu okuyup karşılaştırmak, uzun uzun düşünmeyi gerektirmiyor.
/// Hem daha hızlı hem kullanıcının cebinden daha az çıkıyor.
const String sohbetEffort = 'low';

const String _sistemTalimati = '''
Sen TEFAS fon verilerini okuyan bir analiz yardımcısısın. Türkiye'deki
yatırım fonlarının geçmiş istatistiklerini kullanıcıya açıklıyorsun.

KURALLAR:
1. Her zaman TÜRKÇE yanıt ver.
2. SADECE sana verilen tablodaki sayıları kullan. Tabloda olmayan bir fonu,
   bir getiriyi veya bir oranı UYDURMA. Bilmiyorsan "bu veri elimde yok" de.
3. Gelecek getiri TAHMİNİ YAPMA. "Yükselecek", "kazandırır", "iyi bir giriş
   noktası" gibi ifadeler kullanma. Geçmiş veriyi tarif et, karşılaştır,
   riskleri göster.
4. "Şunu al", "şundan çık", "portföyünü şöyle kur" DEME. Sen yatırım
   danışmanı değilsin ve bu yasal olarak danışmanlık sayılır.
5. Kısa ve somut yaz. Madde işaretleri kullan. Sayıları yüzde ve Türkçe
   biçimle ver (%12,4 gibi).
6. Bir fonun yüksek getirisi varsa oynaklığını ve maksimum düşüşünü de
   söyle. Getiriyi riskten ayrı sunma.
7. Kullanıcı doğrudan tavsiye isterse kibarca reddet ve bunun yerine
   karşılaştırma sun.

Yanıtının sonuna şu cümleyi ekle:
"Bu bir yatırım tavsiyesi değildir; geçmiş verilerin özetidir."
''';

class AnahtarDeposu {
  static const _anahtar = 'claude_api_anahtari';
  static const _model = 'claude_model';
  static const _calismaAlani = 'claude_calisma_alani';

  final FlutterSecureStorage _depo = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  Future<String?> oku() async {
    try {
      return await _depo.read(key: _anahtar);
    } catch (e) {
      debugPrint('Anahtar okunamadı: $e');
      return null;
    }
  }

  Future<void> yaz(String deger) async {
    final temiz = deger.trim();
    if (temiz.isEmpty) {
      await _depo.delete(key: _anahtar);
    } else {
      await _depo.write(key: _anahtar, value: temiz);
    }
  }

  Future<void> sil() => _depo.delete(key: _anahtar);

  Future<String> modelOku() async =>
      (await _depo.read(key: _model)) ?? varsayilanModel;

  Future<void> modelYaz(String m) => _depo.write(key: _model, value: m);

  /// Çalışma alanı kimliği (wrkspc_...).
  ///
  /// Kimliğe bağlı (identity-linked) anahtarlarda ZORUNLU: anahtar
  /// birden fazla çalışma alanına erişebildiği için API hangisinde
  /// işlem yapıldığını ayrıca soruyor. Diğer anahtarlarda boş kalır.
  Future<String?> calismaAlaniOku() async {
    try {
      return await _depo.read(key: _calismaAlani);
    } catch (_) {
      return null;
    }
  }

  Future<void> calismaAlaniYaz(String deger) async {
    final temiz = deger.trim();
    if (temiz.isEmpty) {
      await _depo.delete(key: _calismaAlani);
    } else {
      await _depo.write(key: _calismaAlani, value: temiz);
    }
  }

  Future<bool> anahtarVar() async {
    final a = await oku();
    return a != null && a.isNotEmpty;
  }
}

/// Fon listesini modele gönderilecek kompakt tabloya çevirir.
///
/// Neden kompakt: her fonun tam JSON'unu göndermek hem pahalı hem gereksiz.
/// Modelin ihtiyacı olan alanlar bunlar.
String tabloYap(List<Fon> fonlar, {int azami = 25}) {
  final t = StringBuffer()
    ..writeln('kod | ad | kategori | gunluk% | haftalik% | aylik% | '
        '3aylik% | yillik% | oynaklik% | maks_dusus% | puan | kategori_sira');
  for (final f in fonlar.take(azami)) {
    String s(double? d) => d == null ? '-' : d.toStringAsFixed(2);
    t.writeln('${f.kod} | ${f.ad} | ${f.kategori} | '
        '${s(f.getiri.gunluk)} | ${s(f.getiri.haftalik)} | '
        '${s(f.getiri.aylik)} | ${s(f.getiri.ucAylik)} | '
        '${s(f.getiri.yillik)} | ${s(f.volatilite)} | ${s(f.maksDusus)} | '
        '${s(f.puan)} | ${f.sira ?? "-"}/${f.kategoriFonSayisi ?? "-"}');
  }
  return t.toString();
}

/// Profili modele anlatan kısa metin.
String profilMetni(Profil p) {
  final t = p.tercihler.isEmpty
      ? 'belirtilmemiş'
      : p.tercihler.map((e) => e.ad).join(', ');
  return 'Risk toleransı: ${p.risk.ad}. Vade: ${p.vade.ad}. '
      'Tercih edilen türler: $t.';
}

class Danisman {
  final String anahtar;
  final String model;
  final String? calismaAlani;
  final Duration zamanAsimi;

  const Danisman({
    required this.anahtar,
    this.model = varsayilanModel,
    this.calismaAlani,
    this.zamanAsimi = const Duration(seconds: 60),
  });

  /// Soru sorar, Türkçe yanıt döndürür.
  Future<String> sor({
    required String soru,
    required String baglam,
    List<({String rol, String metin})> gecmis = const [],
  }) async {
    final mesajlar = <Map<String, dynamic>>[
      for (final g in gecmis) {'role': g.rol, 'content': g.metin},
      {
        'role': 'user',
        'content': 'Aşağıdaki fon verilerine bakarak soruma cevap ver.\n\n'
            '=== VERİ ===\n$baglam\n=== VERİ SONU ===\n\nSORU: $soru',
      },
    ];

    late http.Response yanit;
    try {
      yanit = await http
          .post(
            Uri.parse(_uc),
            headers: {
              'content-type': 'application/json',
              'x-api-key': anahtar,
              'anthropic-version': _surum,
              // Sadece doluysa gönder: gereksiz yere göndermek diğer
              // anahtar tiplerinde soruna yol açabilir.
              if (calismaAlani != null && calismaAlani!.isNotEmpty)
                'anthropic-workspace-id': calismaAlani!,
            },
            body: jsonEncode({
              'model': model,
              'max_tokens': azamiToken,
              'system': _sistemTalimati,
              'messages': mesajlar,
              if (_effortDestekleyen.contains(model))
                'output_config': {'effort': sohbetEffort},
            }),
          )
          .timeout(zamanAsimi);
    } catch (e) {
      throw const DanismanHatasi(
        'Claude\'a ulaşılamadı.',
        'İnternet bağlantınızı kontrol edip tekrar deneyin.',
      );
    }

    if (yanit.statusCode != 200) {
      throw hataCevir(yanit.statusCode, yanit.bodyBytes);
    }

    try {
      final j = jsonDecode(utf8.decode(yanit.bodyBytes)) as Map<String, dynamic>;
      final parcalar = (j['content'] as List?) ?? const [];
      final metin = parcalar
          .where((p) => (p as Map)['type'] == 'text')
          .map((p) => (p as Map)['text'] as String)
          .join('\n')
          .trim();
      if (metin.isEmpty) {
        throw const DanismanHatasi('Claude boş yanıt döndürdü.');
      }
      return metin;
    } on DanismanHatasi {
      rethrow;
    } catch (e) {
      throw const DanismanHatasi('Yanıt çözümlenemedi.');
    }
  }
}

/// Bir modelin kimliği ve okunur adı.
class ModelBilgisi {
  final String kimlik;
  final String ad;

  const ModelBilgisi(this.kimlik, this.ad);
}

/// Hesabın erişebildiği modelleri API'den sorar.
///
/// Neden sabit liste değil: hangi modellerin var olduğunu tahmin etmek,
/// kullanıcıyı var olmayan bir modele yönlendirmek demek. API zaten
/// biliyor; sormak bir istek ve kesin cevap.
///
/// Aynı zamanda BAĞLANTI SINAMASI olarak kullanılıyor: bu çağrı
/// başarılıysa anahtar geçerli ve ağ açık demektir.
Future<List<ModelBilgisi>> modelleriGetir(String anahtar,
    {String? calismaAlani,
    Duration zamanAsimi = const Duration(seconds: 30)}) async {
  late http.Response yanit;
  try {
    yanit = await http.get(
      Uri.parse('https://api.anthropic.com/v1/models?limit=50'),
      headers: {
        'x-api-key': anahtar,
        'anthropic-version': _surum,
        if (calismaAlani != null && calismaAlani.isNotEmpty)
          'anthropic-workspace-id': calismaAlani,
      },
    ).timeout(zamanAsimi);
  } catch (_) {
    throw const DanismanHatasi(
      'Anthropic sunucusuna ulaşılamadı.',
      'İnternet bağlantınızı kontrol edin.',
    );
  }

  if (yanit.statusCode != 200) {
    throw hataCevir(yanit.statusCode, yanit.bodyBytes);
  }

  try {
    final j = jsonDecode(utf8.decode(yanit.bodyBytes)) as Map<String, dynamic>;
    final liste = <ModelBilgisi>[];
    for (final m in (j['data'] as List? ?? const [])) {
      if (m is! Map) continue;
      final kimlik = m['id'];
      if (kimlik is! String) continue;
      liste.add(ModelBilgisi(
          kimlik, (m['display_name'] as String?) ?? kimlik));
    }
    if (liste.isEmpty) {
      throw const DanismanHatasi('Model listesi boş döndü.');
    }
    return liste;
  } on DanismanHatasi {
    rethrow;
  } catch (_) {
    throw const DanismanHatasi('Model listesi çözümlenemedi.');
  }
}
