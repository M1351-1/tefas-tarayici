/// Veri modelleri — toplayıcının ürettiği fonlar.json ile birebir eşleşir.
///
/// Toplayıcı (Python tarafı) alan adlarını değiştirirse burası da
/// değişmeli. `surum` alanı bunun için var: uyumsuz bir sürüm gelirse
/// uygulama sessizce yanlış veri göstermek yerine uyarı verir.
library;

/// Uygulamanın anladığı veri sürümü.
const int desteklenenSurum = 1;

/// Bir metriğin puana katkısının açıklaması.
class Kirilim {
  final String metrik;
  final double deger;
  final double kategoriOrtalamasi;
  final double z;
  final double agirlik;
  final double katki;

  const Kirilim({
    required this.metrik,
    required this.deger,
    required this.kategoriOrtalamasi,
    required this.z,
    required this.agirlik,
    required this.katki,
  });

  factory Kirilim.jsondan(String metrik, Map<String, dynamic> j) => Kirilim(
        metrik: metrik,
        deger: (j['deger'] as num).toDouble(),
        kategoriOrtalamasi: (j['kategori_ortalamasi'] as num).toDouble(),
        z: (j['z'] as num).toDouble(),
        agirlik: (j['agirlik'] as num).toDouble(),
        katki: (j['katki'] as num).toDouble(),
      );

  /// Ekranda gösterilecek okunur ad.
  String get baslik => switch (metrik) {
        'aylik_getiri' => 'Aylık getiri',
        'uc_aylik_getiri' => '3 aylık getiri',
        'haftalik_getiri' => 'Haftalık getiri',
        'volatilite' => 'Oynaklık (düşük olması iyi)',
        _ => metrik,
      };
}

class Getiri {
  final double? gunluk, haftalik, aylik, ucAylik, yillik, yilbasindan;

  const Getiri({
    this.gunluk,
    this.haftalik,
    this.aylik,
    this.ucAylik,
    this.yillik,
    this.yilbasindan,
  });

  factory Getiri.jsondan(Map<String, dynamic> j) => Getiri(
        gunluk: (j['gunluk'] as num?)?.toDouble(),
        haftalik: (j['haftalik'] as num?)?.toDouble(),
        aylik: (j['aylik'] as num?)?.toDouble(),
        ucAylik: (j['uc_aylik'] as num?)?.toDouble(),
        yillik: (j['yillik'] as num?)?.toDouble(),
        yilbasindan: (j['yilbasindan'] as num?)?.toDouble(),
      );
}

class Fon {
  final String kod;
  final String ad;
  final String tip;
  final String tipAd;
  final String kategori;

  /// "api" = TEFAS'ın kendi sınıflaması, "isim" = fon adından çıkarım,
  /// "yok" = belirlenemedi. Çıkarımı kesin bilgi gibi göstermiyoruz.
  final String kategoriKaynak;

  /// Katılım (faizsiz) esaslı mı? Kategoriden bağımsız bir niteliktir:
  /// "Altın Katılım" fonu Kıymetli Madenler kategorisindedir ama katılımdır.
  final bool katilim;

  final String? tarih;
  final double? fiyat;
  final int? kisiSayisi;
  final double? buyukluk;
  final int? gozlem;
  final Getiri getiri;
  final double? volatilite;
  final double? maksDusus;
  final double? puan;
  final int? sira;
  final int? kategoriFonSayisi;
  final List<Kirilim> kirilim;
  final String? puanlanmamaNedeni;

  const Fon({
    required this.kod,
    required this.ad,
    required this.tip,
    required this.tipAd,
    required this.kategori,
    required this.getiri,
    this.kategoriKaynak = 'api',
    this.katilim = false,
    this.tarih,
    this.fiyat,
    this.kisiSayisi,
    this.buyukluk,
    this.gozlem,
    this.volatilite,
    this.maksDusus,
    this.puan,
    this.sira,
    this.kategoriFonSayisi,
    this.kirilim = const [],
    this.puanlanmamaNedeni,
  });

  /// İç içe haritaları güvenle çözer.
  ///
  /// `jsonDecode` her zaman `Map<String, dynamic>` üretir, ama doğrudan
  /// kurulan haritalar (testler, elle yazılmış önbellek) `Map<dynamic,
  /// dynamic>` olabiliyor ve düz `as` cast'i çöküyor. Anahtarları metne
  /// çevirerek her iki durumu da karşılıyoruz.
  static Map<String, dynamic>? _harita(dynamic v) => v is Map
      ? v.map((anahtar, deger) => MapEntry(anahtar.toString(), deger))
      : null;

  /// Kırılımı çözer ve ağırlığa göre büyükten küçüğe sıralar.
  ///
  /// Ayrı fonksiyon olmasının sebebi bir hata: önce bu iş
  /// `ham == null ? const [] : ham.entries...toList()..sort(...)`
  /// diye tek satırda yazılmıştı. Dart'ta cascade (`..`) önceliği çok
  /// düşük olduğu için `..sort()` üçlü ifadenin TAMAMINA uygulanıyor ve
  /// ham null olduğunda `const []` sıralanmaya çalışılıp
  /// "Cannot modify an unmodifiable list" fırlatıyordu. Yani kırılımı
  /// olmayan her fon çözümlemede patlıyordu.
  static List<Kirilim> _kirilimCoz(Map<String, dynamic>? ham) {
    if (ham == null) return const [];
    final liste = <Kirilim>[];
    for (final e in ham.entries) {
      final h = _harita(e.value);
      if (h != null) liste.add(Kirilim.jsondan(e.key, h));
    }
    liste.sort((a, b) => b.agirlik.compareTo(a.agirlik));
    return liste;
  }

  factory Fon.jsondan(Map<String, dynamic> j) {
    final ham = _harita(j['kirilim']);
    return Fon(
      kod: j['kod'] as String,
      ad: (j['ad'] as String?) ?? '',
      tip: (j['tip'] as String?) ?? '',
      tipAd: (j['tip_ad'] as String?) ?? '',
      kategori: (j['kategori'] as String?) ?? 'Bilinmiyor',
      kategoriKaynak: (j['kategori_kaynak'] as String?) ?? 'api',
      katilim: (j['katilim'] as bool?) ?? false,
      tarih: j['tarih'] as String?,
      fiyat: (j['fiyat'] as num?)?.toDouble(),
      kisiSayisi: (j['kisi_sayisi'] as num?)?.toInt(),
      buyukluk: (j['buyukluk'] as num?)?.toDouble(),
      gozlem: (j['gozlem'] as num?)?.toInt(),
      getiri: Getiri.jsondan(_harita(j['getiri']) ?? const {}),
      volatilite: (j['volatilite'] as num?)?.toDouble(),
      maksDusus: (j['maks_dusus'] as num?)?.toDouble(),
      puan: (j['puan'] as num?)?.toDouble(),
      sira: (j['sira'] as num?)?.toInt(),
      kategoriFonSayisi: (j['kategori_fon_sayisi'] as num?)?.toInt(),
      kirilim: _kirilimCoz(ham),
      puanlanmamaNedeni: j['puanlanmama_nedeni'] as String?,
    );
  }

  bool get puanlandi => puan != null;

  /// Fon adının başındaki kurucu şirket. "AK PORTFÖY AMERİKA ..." -> "AK PORTFÖY"
  ///
  /// TEFAS ayrı bir kurucu alanı vermiyor; ada bakmak tek yol. "PORTFÖY"
  /// kelimesi bütün kurucularda geçtiği için ayıraç olarak onu kullanıyoruz.
  String get kurucu {
    final i = ad.indexOf('PORTFÖY');
    if (i > 0) return ad.substring(0, i + 'PORTFÖY'.length).trim();
    final parcalar = ad.split(' ');
    return parcalar.take(2).join(' ');
  }
}

class KategoriOzeti {
  final String tip;
  final String tipAd;
  final String ad;
  final int adet;
  final bool puanlanabilir;

  /// Kaç fonun kategorisi TEFAS'tan, kaçı fon adından çıkarıldı.
  final int apiAdet;
  final int cikarimAdet;

  const KategoriOzeti({
    required this.tip,
    required this.tipAd,
    required this.ad,
    required this.adet,
    required this.puanlanabilir,
    this.apiAdet = 0,
    this.cikarimAdet = 0,
  });

  factory KategoriOzeti.jsondan(Map<String, dynamic> j) => KategoriOzeti(
        tip: (j['tip'] as String?) ?? '',
        tipAd: (j['tip_ad'] as String?) ?? '',
        ad: (j['ad'] as String?) ?? '',
        adet: (j['adet'] as num?)?.toInt() ?? 0,
        puanlanabilir: (j['puanlanabilir'] as bool?) ?? false,
        apiAdet: (j['api_adet'] as num?)?.toInt() ?? 0,
        cikarimAdet: (j['cikarim_adet'] as num?)?.toInt() ?? 0,
      );

  /// Kategorinin çoğunluğu fon adından mı çıkarıldı?
  bool get cikarimAgirlikli => cikarimAdet > apiAdet;

  /// Aynı kategorinin farklı fon tipleri ayrı satırdır: anahtar ikisi birlikte.
  String get anahtar => '$tip|$ad';
}

/// Tüm veri dosyası.
class Veri {
  final int surum;
  final String veriTarihi;
  final String uretimZamani;
  final String sorumlulukNotu;
  final Map<String, double> agirliklar;
  final List<KategoriOzeti> kategoriler;
  final List<Fon> fonlar;

  /// Bu veri ağdan mı geldi, önbellekten mi? Kullanıcıya söylemek için.
  final bool onbellekten;

  const Veri({
    required this.surum,
    required this.veriTarihi,
    required this.uretimZamani,
    required this.sorumlulukNotu,
    required this.agirliklar,
    required this.kategoriler,
    required this.fonlar,
    this.onbellekten = false,
  });

  factory Veri.jsondan(Map<String, dynamic> j, {bool onbellekten = false}) {
    final ayarlar = (j['ayarlar'] as Map<String, dynamic>?) ?? {};
    final ham = (ayarlar['agirliklar'] as Map<String, dynamic>?) ?? {};
    return Veri(
      surum: (j['surum'] as num?)?.toInt() ?? 0,
      veriTarihi: (j['veri_tarihi'] as String?) ?? '',
      uretimZamani: (j['uretim_zamani'] as String?) ?? '',
      sorumlulukNotu: (j['sorumluluk_notu'] as String?) ?? '',
      agirliklar: ham.map((k, v) => MapEntry(k, (v as num).toDouble())),
      kategoriler: ((j['kategoriler'] as List?) ?? [])
          .map((e) => KategoriOzeti.jsondan(e as Map<String, dynamic>))
          .toList(),
      fonlar: ((j['fonlar'] as List?) ?? [])
          .map((e) => Fon.jsondan(e as Map<String, dynamic>))
          .toList(),
      onbellekten: onbellekten,
    );
  }

  Veri onbellekIsaretle() => Veri(
        surum: surum,
        veriTarihi: veriTarihi,
        uretimZamani: uretimZamani,
        sorumlulukNotu: sorumlulukNotu,
        agirliklar: agirliklar,
        kategoriler: kategoriler,
        fonlar: fonlar,
        onbellekten: true,
      );
}

/// Tek bir fonun fiyat geçmişi (gecmis/KOD.json).
class Gecmis {
  final String kod;
  final List<String> tarihler;
  final List<double> fiyatlar;

  const Gecmis({
    required this.kod,
    required this.tarihler,
    required this.fiyatlar,
  });

  factory Gecmis.jsondan(Map<String, dynamic> j) => Gecmis(
        kod: j['kod'] as String,
        tarihler: ((j['tarihler'] as List?) ?? []).cast<String>(),
        fiyatlar: ((j['fiyatlar'] as List?) ?? [])
            .map((e) => (e as num).toDouble())
            .toList(),
      );

  /// Son [gun] gözlemi döndürür (1A ≈ 21, 3A ≈ 63, 1Y ≈ 252 işlem günü).
  Gecmis son(int gun) {
    if (fiyatlar.length <= gun) return this;
    return Gecmis(
      kod: kod,
      tarihler: tarihler.sublist(tarihler.length - gun),
      fiyatlar: fiyatlar.sublist(fiyatlar.length - gun),
    );
  }
}
