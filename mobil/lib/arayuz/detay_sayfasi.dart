/// Fon detayı: fiyat grafiği, bütün metrikler, puan kırılımı.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import '../cekirdek/modeller.dart';
import '../cekirdek/puanlama.dart';
import '../cekirdek/veri.dart';
import 'ana_kabuk.dart';
import 'grafik.dart';

/// Grafik dönemleri — işlem günü sayısı olarak.
const _donemler = {'1 Ay': 21, '3 Ay': 63, '6 Ay': 126, '1 Yıl': 252};

class DetaySayfasi extends StatefulWidget {
  final String kod;

  const DetaySayfasi({super.key, required this.kod});

  @override
  State<DetaySayfasi> createState() => _DetaySayfasiDurumu();
}

class _DetaySayfasiDurumu extends State<DetaySayfasi> {
  String _donem = '1 Yıl';
  Gecmis? _gecmis;
  String? _gecmisHatasi;
  bool _yukleniyor = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _gecmisYukle());
  }

  Future<void> _gecmisYukle() async {
    final durum = Kapsam.of(context);
    try {
      final g = await VeriKaynagi(adres: durum.ayarlar.adres)
          .gecmis(widget.kod, veriTarihi: durum.veri?.veriTarihi);
      if (mounted) setState(() { _gecmis = g; _yukleniyor = false; });
    } on VeriHatasi catch (e) {
      if (mounted) setState(() { _gecmisHatasi = e.mesaj; _yukleniyor = false; });
    } catch (_) {
      if (mounted) {
        setState(() {
          _gecmisHatasi = 'Fiyat geçmişi alınamadı.';
          _yukleniyor = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final kayit = durum.fonBul(widget.kod);

    if (kayit == null) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.kod)),
        body: const Center(child: Text('Fon bulunamadı.')),
      );
    }

    final f = kayit.fon;
    final favori = durum.ayarlar.favoriMi(f.kod);

    return Scaffold(
      appBar: AppBar(
        title: Text(f.kod),
        actions: [
          IconButton(
            icon: Icon(favori ? Icons.star : Icons.star_outline),
            color: favori ? Colors.amber.shade600 : null,
            tooltip: favori ? 'Favorilerden çıkar' : 'Favorilere ekle',
            onPressed: () => durum.ayarlar.favoriDegistir(f.kod),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: [
          const SizedBox(height: 12),
          Text(f.ad, style: tema.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text('${f.kurucu} · ${f.kategori.replaceAll(" Şemsiye Fonu", "")} · '
              '${f.tipAd}', style: tema.textTheme.bodySmall),
          const SizedBox(height: 20),

          // ---------------------------------------------------- grafik
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SegmentedButton<String>(
                    segments: [
                      for (final d in _donemler.keys)
                        ButtonSegment(value: d, label: Text(d)),
                    ],
                    selected: {_donem},
                    showSelectedIcon: false,
                    onSelectionChanged: (s) =>
                        setState(() => _donem = s.first),
                    style: const ButtonStyle(
                      visualDensity: VisualDensity.compact,
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (_yukleniyor)
                    const SizedBox(
                      height: 220,
                      child: Center(child: CircularProgressIndicator()),
                    )
                  else if (_gecmis != null)
                    Builder(builder: (_) {
                      final g = _gecmis!.son(_donemler[_donem]!);
                      return FiyatGrafigi(
                        tarihler: g.tarihler,
                        fiyatlar: g.fiyatlar,
                        renk: tema.colorScheme.primary,
                      );
                    })
                  else
                    SizedBox(
                      height: 200,
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.show_chart,
                                color: tema.colorScheme.onSurfaceVariant),
                            const SizedBox(height: 8),
                            Text(_gecmisHatasi ?? 'Grafik yüklenemedi',
                                style: tema.textTheme.bodySmall),
                            TextButton(
                              onPressed: () {
                                setState(() {
                                  _yukleniyor = true;
                                  _gecmisHatasi = null;
                                });
                                _gecmisYukle();
                              },
                              child: const Text('Tekrar dene'),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // -------------------------------------------------- metrikler
          _Bolum(
            baslik: 'Getiriler',
            cocuk: Column(
              children: [
                _Satir('Günlük', trYuzde(f.getiri.gunluk), renkli: true,
                    deger: f.getiri.gunluk),
                _Satir('Haftalık', trYuzde(f.getiri.haftalik), renkli: true,
                    deger: f.getiri.haftalik),
                _Satir('Aylık', trYuzde(f.getiri.aylik), renkli: true,
                    deger: f.getiri.aylik),
                _Satir('3 Aylık', trYuzde(f.getiri.ucAylik), renkli: true,
                    deger: f.getiri.ucAylik),
                _Satir('Yıllık', trYuzde(f.getiri.yillik), renkli: true,
                    deger: f.getiri.yillik),
                _Satir('Yılbaşından', trYuzde(f.getiri.yilbasindan),
                    renkli: true, deger: f.getiri.yilbasindan),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _Bolum(
            baslik: 'Risk ve büyüklük',
            cocuk: Column(
              children: [
                _Satir(
                    'Oynaklık (yıllık)',
                    f.volatilite == null
                        ? '—'
                        : '%${trSayi(f.volatilite!)}',
                    aciklama: 'Günlük dalgalanmanın yıllığa çevrilmiş hâli. '
                        'Yüksekse fiyat sert oynuyor demektir.'),
                _Satir(
                    'En derin kayıp',
                    f.maksDusus == null ? '—' : '%${trSayi(f.maksDusus!)}',
                    aciklama: 'Son 1 yılda tepeden dibe en büyük düşüş.'),
                _Satir('Fon büyüklüğü', trTutar(f.buyukluk)),
                _Satir('Yatırımcı sayısı',
                    f.kisiSayisi == null
                        ? '—'
                        : trSayi(f.kisiSayisi!.toDouble(), ondalik: 0)),
                _Satir('Fiyat',
                    f.fiyat == null
                        ? '—'
                        : '${trSayi(f.fiyat!, ondalik: 6)} TL'),
                _Satir('Veri geçmişi',
                    f.gozlem == null ? '—' : '${f.gozlem} işlem günü'),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // ---------------------------------------------- puan kırılımı
          if (kayit.puan != null && f.kirilim.isNotEmpty)
            _PuanKirilimi(kayit: kayit, agirliklar: durum.ayarlar.agirliklar)
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Text(
                  f.puanlanmamaNedeni ??
                      'Bu fon puanlanmadı: karşılaştırma için yeterli veri '
                          'ya da yeterli sayıda rakip fon yok.',
                  style: tema.textTheme.bodySmall,
                ),
              ),
            ),

          const SorumlulukNotu(),
        ],
      ),
    );
  }
}

class _Bolum extends StatelessWidget {
  final String baslik;
  final Widget cocuk;

  const _Bolum({required this.baslik, required this.cocuk});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(baslik,
                style: tema.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            cocuk,
          ],
        ),
      ),
    );
  }
}

class _Satir extends StatelessWidget {
  final String etiket;
  final String deger2;
  final bool renkli;
  final double? deger;
  final String? aciklama;

  const _Satir(this.etiket, this.deger2,
      {this.renkli = false, this.deger, this.aciklama});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final renk = !renkli || deger == null
        ? null
        : (deger! >= 0 ? Colors.green.shade600 : Colors.red.shade600);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(etiket, style: tema.textTheme.bodyMedium),
                if (aciklama != null)
                  Text(aciklama!,
                      style: tema.textTheme.bodySmall
                          ?.copyWith(fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(deger2,
              style: tema.textTheme.bodyMedium
                  ?.copyWith(fontWeight: FontWeight.w600, color: renk)),
        ],
      ),
    );
  }
}

/// "Neden üst sırada?" — puanın hangi bileşenden geldiğini gösterir.
class _PuanKirilimi extends StatelessWidget {
  final PuanliFon kayit;
  final Map<String, double> agirliklar;

  const _PuanKirilimi({required this.kayit, required this.agirliklar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final f = kayit.fon;
    final liste = katkilar(f, agirliklar);
    final enBuyuk = liste
        .map((e) => e.katki.abs())
        .fold<double>(0.01, (a, b) => a > b ? a : b);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Neden bu sırada?',
                    style: tema.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                Text(
                  '${kayit.sira}. / ${f.kategoriFonSayisi ?? "?"}',
                  style: tema.textTheme.titleSmall
                      ?.copyWith(color: tema.colorScheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Puan, fonun kendi kategorisindeki ortalamadan ne kadar '
              'saptığından hesaplanır. Çubuklar hangi ölçünün puana ne kadar '
              'eklediğini gösterir.',
              style: tema.textTheme.bodySmall,
            ),
            const SizedBox(height: 14),
            for (final e in liste) ...[
              _KatkiCubugu(
                baslik: e.kirilim.baslik,
                deger: e.kirilim.deger,
                ortalama: e.kirilim.kategoriOrtalamasi,
                katki: e.katki,
                oran: e.katki.abs() / enBuyuk,
              ),
              const SizedBox(height: 12),
            ],
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Toplam puan',
                    style: tema.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                Text(trSayi(kayit.puan ?? 0, ondalik: 2),
                    style: tema.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _KatkiCubugu extends StatelessWidget {
  final String baslik;
  final double deger;
  final double ortalama;
  final double katki;
  final double oran;

  const _KatkiCubugu({
    required this.baslik,
    required this.deger,
    required this.ortalama,
    required this.katki,
    required this.oran,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final iyi = katki >= 0;
    final renk = iyi ? Colors.green.shade600 : Colors.red.shade600;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(child: Text(baslik, style: tema.textTheme.bodyMedium)),
            Text('${iyi ? "+" : ""}${trSayi(katki, ondalik: 2)}',
                style: tema.textTheme.bodyMedium
                    ?.copyWith(color: renk, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: oran.clamp(0.02, 1.0),
            minHeight: 6,
            backgroundColor: tema.colorScheme.surfaceContainerHighest,
            valueColor: AlwaysStoppedAnimation(renk),
          ),
        ),
        const SizedBox(height: 3),
        Text(
          'Bu fon: ${trSayi(deger)} · kategori ortalaması: ${trSayi(ortalama)}',
          style: tema.textTheme.bodySmall?.copyWith(fontSize: 11),
        ),
      ],
    );
  }
}
