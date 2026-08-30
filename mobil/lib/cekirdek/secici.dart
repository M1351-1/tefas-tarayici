/// Akıllı filtre: profil sorularından kısa liste üretir.
///
/// Bu bir tavsiye motoru DEĞİLDİR, bir eleme motorudur. Yaptığı şey:
/// binlerce fonu kullanıcının söylediği kısıtlara göre daraltmak, kalanları
/// tutarlılık açısından denetlemek ve her satır için gerekçeyi Türkçe yazmak.
/// "Şunu al" demez; "şu kısıtlarla şunlar kalıyor, şurada şu risk var" der.
///
/// Neden dil modeli değil: bir dil modeli gelecek getiriyi bilemez. Burada
/// yapılan iş ölçülebilir kısıtlar ve tutarlılık denetimleridir; bunları
/// açıkça yazılmış kurallarla yapmak hem daha doğru hem de denetlenebilir.
library;

import 'modeller.dart';
import 'puanlama.dart';

enum RiskToleransi { dusuk, orta, yuksek }

enum Vade { kisa, orta, uzun }

extension RiskAdi on RiskToleransi {
  String get ad => switch (this) {
        RiskToleransi.dusuk => 'Düşük',
        RiskToleransi.orta => 'Orta',
        RiskToleransi.yuksek => 'Yüksek',
      };

  String get aciklama => switch (this) {
        RiskToleransi.dusuk =>
          'Anaparanın korunması önemli; sert dalgalanma istemiyorum',
        RiskToleransi.orta => 'Bir miktar dalgalanmaya katlanabilirim',
        RiskToleransi.yuksek => 'Yüksek dalgalanmayı kabul ediyorum',
      };

  /// Yıllıklandırılmış oynaklık tavanı (%). null = sınırsız.
  ///
  /// Eşikler Türkiye fon evrenine göre seçildi: para piyasası fonları
  /// %1-3, borçlanma araçları %5-15, hisse fonları %25-45 bandında
  /// oynuyor. Ayarlardan değiştirilemiyor çünkü "düşük risk"in ne demek
  /// olduğu kullanıcıya göre kaymamalı; kayarsa etiket anlamını yitirir.
  double? get oynaklikTavani => switch (this) {
        RiskToleransi.dusuk => 12.0,
        RiskToleransi.orta => 30.0,
        RiskToleransi.yuksek => null,
      };

  /// Kabul edilen en derin geçmiş kayıp (%). null = sınırsız.
  double? get dususTabani => switch (this) {
        RiskToleransi.dusuk => -8.0,
        RiskToleransi.orta => -25.0,
        RiskToleransi.yuksek => null,
      };
}

extension VadeAdi on Vade {
  String get ad => switch (this) {
        Vade.kisa => 'Kısa (1 yıldan az)',
        Vade.orta => 'Orta (1-3 yıl)',
        Vade.uzun => 'Uzun (3 yıl+)',
      };

  /// Vadeye göre metrik ağırlıkları.
  ///
  /// Kısa vadede yakın dönem seyri ve sert kayıp riski önemlidir; uzun
  /// vadede haftalık dalgalanma gürültüdür, kalıcı performans önemlidir.
  Map<String, double> get agirliklar => switch (this) {
        Vade.kisa => const {
            'haftalik_getiri': 0.30,
            'aylik_getiri': 0.35,
            'uc_aylik_getiri': 0.10,
            'volatilite': 0.25,
          },
        Vade.orta => const {
            'haftalik_getiri': 0.15,
            'aylik_getiri': 0.30,
            'uc_aylik_getiri': 0.35,
            'volatilite': 0.20,
          },
        Vade.uzun => const {
            'haftalik_getiri': 0.05,
            'aylik_getiri': 0.20,
            'uc_aylik_getiri': 0.45,
            'volatilite': 0.30,
          },
      };
}

/// Kullanıcının tercih ettiği fon türleri. Boş küme = hepsi.
enum Tercih { katilim, hisse, altin, paraPiyasasi, borclanma, fonSepeti }

extension TercihAdi on Tercih {
  String get ad => switch (this) {
        Tercih.katilim => 'Katılım (faizsiz)',
        Tercih.hisse => 'Hisse senedi',
        Tercih.altin => 'Altın / kıymetli maden',
        Tercih.paraPiyasasi => 'Para piyasası',
        Tercih.borclanma => 'Borçlanma araçları',
        Tercih.fonSepeti => 'Fon sepeti',
      };

  /// Kategori adında aranacak anahtar. TEFAS kategori adları sabit olduğu
  /// için eşleşme güvenli.
  String get kategoriAnahtari => switch (this) {
        Tercih.katilim => 'Katılım',
        Tercih.hisse => 'Hisse Senedi',
        Tercih.altin => 'Kıymetli Madenler',
        Tercih.paraPiyasasi => 'Para Piyasası',
        Tercih.borclanma => 'Borçlanma Araçları',
        Tercih.fonSepeti => 'Fon Sepeti',
      };
}

class Profil {
  final RiskToleransi risk;
  final Vade vade;
  final Set<Tercih> tercihler;

  /// Emeklilik fonları da listeye girsin mi?
  final bool emeklilikDahil;

  const Profil({
    this.risk = RiskToleransi.orta,
    this.vade = Vade.orta,
    this.tercihler = const {},
    this.emeklilikDahil = false,
  });

  Profil kopyala({
    RiskToleransi? risk,
    Vade? vade,
    Set<Tercih>? tercihler,
    bool? emeklilikDahil,
  }) =>
      Profil(
        risk: risk ?? this.risk,
        vade: vade ?? this.vade,
        tercihler: tercihler ?? this.tercihler,
        emeklilikDahil: emeklilikDahil ?? this.emeklilikDahil,
      );
}

/// Bir fon hakkında kullanıcıya söylenmesi gereken uyarı.
class Uyari {
  final String metin;
  final bool ciddi;

  const Uyari(this.metin, {this.ciddi = false});
}

/// Kısa listedeki bir satır.
class Aday {
  final Fon fon;
  final double puan;
  final int sira;
  final List<String> gerekceler;
  final List<Uyari> uyarilar;

  const Aday({
    required this.fon,
    required this.puan,
    required this.sira,
    required this.gerekceler,
    required this.uyarilar,
  });

  bool get ciddiUyariVar => uyarilar.any((u) => u.ciddi);
}

/// Elenen fonların neden elendiğinin özeti — "hiç sonuç yok" ekranında
/// kullanıcıya hangi kısıtın daralttığını söylemek için.
class ElemeOzeti {
  final int baslangic;
  final int kategoriElendi;
  final int oynaklikElendi;
  final int dususElendi;
  final int puansizElendi;
  final int kalan;

  const ElemeOzeti({
    required this.baslangic,
    required this.kategoriElendi,
    required this.oynaklikElendi,
    required this.dususElendi,
    required this.puansizElendi,
    required this.kalan,
  });

  /// En çok eleyen kısıt — kullanıcıya "şunu gevşet" demek için.
  String? get darBogaz {
    final m = {
      'tercih ettiğiniz kategoriler': kategoriElendi,
      'oynaklık sınırı': oynaklikElendi,
      'kayıp sınırı': dususElendi,
    };
    var enBuyuk = 0;
    String? ad;
    m.forEach((k, v) {
      if (v > enBuyuk) {
        enBuyuk = v;
        ad = k;
      }
    });
    return enBuyuk > 0 ? ad : null;
  }
}

class SecimSonucu {
  final List<Aday> adaylar;
  final ElemeOzeti ozet;

  const SecimSonucu({required this.adaylar, required this.ozet});
}

/// Ana giriş noktası.
///
/// [olcut] verilirse gerekçelere "risksiz alternatifi şu kadar geçmiş"
/// satırı eklenir.
SecimSonucu sec(List<Fon> fonlar, Profil profil,
    {int adet = 10, Olcut? olcut}) {
  final tavan = profil.risk.oynaklikTavani;
  final taban = profil.risk.dususTabani;

  var kategoriElendi = 0;
  var oynaklikElendi = 0;
  var dususElendi = 0;
  var puansizElendi = 0;

  final uygun = <Fon>[];
  for (final f in fonlar) {
    // Puanlanamamış fon karşılaştırılamaz; kısa listeye giremez.
    if (f.puan == null || f.kirilim.isEmpty) {
      puansizElendi++;
      continue;
    }
    if (!profil.emeklilikDahil && f.tip == 'EMK') {
      kategoriElendi++;
      continue;
    }
    // Katılım bir kategori değil, bir niteliktir: "Altın Katılım" fonu
    // Kıymetli Madenler kategorisindedir ama faizsizdir. Kategori adına
    // bakarak filtrelersek faizsiz fon arayan kullanıcı bunları kaçırır.
    if (profil.tercihler.isNotEmpty &&
        !profil.tercihler.any((t) => t == Tercih.katilim
            ? f.katilim
            : f.kategori.contains(t.kategoriAnahtari))) {
      kategoriElendi++;
      continue;
    }
    if (tavan != null && (f.volatilite ?? double.infinity) > tavan) {
      oynaklikElendi++;
      continue;
    }
    if (taban != null && (f.maksDusus ?? -double.infinity) < taban) {
      dususElendi++;
      continue;
    }
    uygun.add(f);
  }

  // Vadeye uygun ağırlıklarla yeniden puanla.
  final agirliklar = profil.vade.agirliklar;
  final puanli = uygun
      .map((f) => (fon: f, puan: puanHesapla(f, agirliklar) ?? 0.0))
      .toList()
    ..sort((a, b) => b.puan.compareTo(a.puan));

  final adaylar = <Aday>[];
  for (var i = 0; i < puanli.length && i < adet; i++) {
    final f = puanli[i].fon;
    adaylar.add(Aday(
      fon: f,
      puan: puanli[i].puan,
      sira: i + 1,
      gerekceler: _gerekceler(f, agirliklar, olcut),
      uyarilar: _uyarilar(f),
    ));
  }

  return SecimSonucu(
    adaylar: adaylar,
    ozet: ElemeOzeti(
      baslangic: fonlar.length,
      kategoriElendi: kategoriElendi,
      oynaklikElendi: oynaklikElendi,
      dususElendi: dususElendi,
      puansizElendi: puansizElendi,
      kalan: uygun.length,
    ),
  );
}

/// Fonun listeye neden girdiğini Türkçe anlatır.
List<String> _gerekceler(Fon f, Map<String, double> agirliklar, Olcut? olcut) {
  final liste = <String>[];

  // İstikrar en güçlü gerekçe: getiri sıralamasının ayırt edemediği
  // şeyi ayırt eder, o yüzden başa koyuyoruz.
  final ist = f.istikrar;
  if (ist != null && ist.$2 >= 6) {
    final oran = ist.$1 / ist.$2;
    if (oran >= 0.6) {
      // Çift tırnak: metinde kesme işareti var ("10'unda"), tek tırnaklı
      // Dart dizgesinde kaçırmak gerekirdi.
      liste.add("son ${ist.$2} ayın ${ist.$1}'inde kategori medyanının "
          "üstünde kaldı");
    }
  }

  // Risksiz alternatifle kıyas — stopaj sonrası, cebe giren üzerinden.
  final net = f.netYillik;
  if (olcut != null && olcut.gecerli && net != null) {
    final fark = net - olcut.net!;
    if (fark > 2) {
      liste.add('risksiz alternatifi ${fark.toStringAsFixed(0)} puan geçmiş '
          '(stopaj sonrası)');
    }
  }
  if (f.stopajsiz) {
    liste.add('hisse yoğun fon: stopaj yok, brüt getirisi cebinize giriyor');
  }
  final k = katkilar(f, agirliklar);
  for (final e in k.take(2)) {
    if (e.katki <= 0.05) continue;
    final ad = switch (e.kirilim.metrik) {
      'aylik_getiri' => 'aylık getirisi',
      'uc_aylik_getiri' => '3 aylık getirisi',
      'haftalik_getiri' => 'haftalık getirisi',
      'volatilite' => 'oynaklığı',
      _ => e.kirilim.metrik,
    };
    final yon = e.kirilim.metrik == 'volatilite'
        ? 'kategori ortalamasının altında'
        : 'kategori ortalamasının üstünde';
    liste.add('$ad $yon');
  }
  if (f.sira != null && f.sira! <= 3) {
    liste.add('kendi kategorisinde ${f.sira}. sırada');
  }
  if (liste.isEmpty) {
    liste.add('kısıtlarınıza uyan fonlar arasında en yüksek puanlılardan');
  }
  return liste;
}

/// Sayılara bakıp "burada bir tuhaflık var" diyen tutarlılık denetimleri.
///
/// Sıralamanın en tehlikeli yanı, kısa vadeli bir sıçramanın fonu tepeye
/// taşıması. Bu denetimler tam olarak o durumu yakalayıp yüzüne söyler.
List<Uyari> _uyarilar(Fon f) {
  final u = <Uyari>[];
  final aylik = f.getiri.aylik;
  final yillik = f.getiri.yillik;
  final ucAylik = f.getiri.ucAylik;

  if (aylik != null && yillik != null && aylik > 8 && yillik < 0) {
    u.add(const Uyari(
        'Son ayda güçlü yükseldi ama 1 yıllık getirisi negatif. Kalıcı bir '
        'toparlanma mı, geçici bir sıçrama mı belli değil.',
        ciddi: true));
  }
  if (aylik != null && ucAylik != null && ucAylik > 0 && aylik > ucAylik) {
    // Aylık getiri 3 aylığı geçiyorsa yükseliş son aya sıkışmış demektir.
    u.add(const Uyari(
        'Yükselişin tamamı son aya sıkışmış; öncesinde yatay ya da düşüş var.'));
  }
  if (f.maksDusus != null && f.maksDusus! < -30) {
    u.add(Uyari(
        'Son 1 yılda tepeden dibe %${f.maksDusus!.abs().toStringAsFixed(0)} '
        'kaybettirdiği bir dönem olmuş.',
        ciddi: f.maksDusus! < -45));
  }
  if (f.kisiSayisi != null && f.kisiSayisi! < 500) {
    u.add(Uyari(
        'Sadece ${f.kisiSayisi} yatırımcısı var; alım satımda fiyat kayması '
        'yaşayabilirsiniz.'));
  }
  if (f.kategoriFonSayisi != null && f.kategoriFonSayisi! < 15) {
    u.add(Uyari(
        'Kategorisinde sadece ${f.kategoriFonSayisi} fon var; sıralama az '
        'sayıda rakip arasında yapıldı.'));
  }
  if (f.gozlem != null && f.gozlem! < 150) {
    u.add(Uyari(
        'Sadece ${f.gozlem} işlem günlük geçmişi var; istatistikler kısa bir '
        'döneme dayanıyor.'));
  }
  return u;
}
