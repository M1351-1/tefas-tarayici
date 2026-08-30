/// Fiyat grafiği — CustomPainter ile doğrudan çizilir.
///
/// Hazır paket kullanmama sebebi: Türkçe sayı biçimi, dokunmalı okuma ve
/// APK boyutu. Üç şey de kendi çizimimizde daha basit.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Türkçe sayı biçimi: 1234.5 -> "1.234,5"
String trSayi(double deger, {int ondalik = 2}) {
  final negatif = deger < 0;
  final metin = deger.abs().toStringAsFixed(ondalik);
  final parcalar = metin.split('.');

  final tampon = StringBuffer();
  final tam = parcalar[0];
  for (var i = 0; i < tam.length; i++) {
    if (i > 0 && (tam.length - i) % 3 == 0) tampon.write('.');
    tampon.write(tam[i]);
  }

  final sonuc = parcalar.length > 1 ? '$tampon,${parcalar[1]}' : '$tampon';
  return negatif ? '-$sonuc' : sonuc;
}

/// Yüzde biçimi, işaretiyle: "+%12,34" / "-%3,10"
String trYuzde(double? deger, {int ondalik = 2}) {
  if (deger == null) return '—';
  final isaret = deger >= 0 ? '+' : '';
  return '$isaret%${trSayi(deger, ondalik: ondalik)}';
}

/// Büyük TL tutarlarını kısaltır: 5472249354 -> "5,47 milyar TL"
String trTutar(double? deger) {
  if (deger == null) return '—';
  if (deger >= 1e9) return '${trSayi(deger / 1e9)} milyar TL';
  if (deger >= 1e6) return '${trSayi(deger / 1e6)} milyon TL';
  if (deger >= 1e3) return '${trSayi(deger / 1e3, ondalik: 0)} bin TL';
  return '${trSayi(deger)} TL';
}

/// "2026-08-28" -> "28.08.2026"
String trTarih(String iso) {
  final p = iso.split('-');
  return p.length == 3 ? '${p[2]}.${p[1]}.${p[0]}' : iso;
}

class FiyatGrafigi extends StatefulWidget {
  final List<String> tarihler;
  final List<double> fiyatlar;
  final Color renk;

  const FiyatGrafigi({
    super.key,
    required this.tarihler,
    required this.fiyatlar,
    required this.renk,
  });

  @override
  State<FiyatGrafigi> createState() => _FiyatGrafigiDurumu();
}

class _FiyatGrafigiDurumu extends State<FiyatGrafigi> {
  int? _secili;

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    if (widget.fiyatlar.length < 2) {
      return SizedBox(
        height: 220,
        child: Center(
          child: Text('Grafik için yeterli veri yok',
              style: tema.textTheme.bodySmall),
        ),
      );
    }

    final ilk = widget.fiyatlar.first;
    final son = widget.fiyatlar.last;
    final degisim = (son / ilk - 1) * 100;
    // Dönem içinde yükselmişse yeşil, düşmüşse kırmızı.
    final renk = degisim >= 0 ? Colors.green.shade600 : Colors.red.shade600;

    final i = _secili;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              i == null
                  ? '${trSayi(son, ondalik: 6)} TL'
                  : '${trSayi(widget.fiyatlar[i], ondalik: 6)} TL',
              style: tema.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            Text(
              i == null ? trYuzde(degisim) : trTarih(widget.tarihler[i]),
              style: tema.textTheme.titleSmall?.copyWith(
                color: i == null ? renk : tema.colorScheme.onSurfaceVariant,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 200,
          child: LayoutBuilder(
            builder: (context, kisit) {
              void guncelle(Offset yerel) {
                final oran = (yerel.dx / kisit.maxWidth).clamp(0.0, 1.0);
                final idx = (oran * (widget.fiyatlar.length - 1)).round();
                if (idx != _secili) setState(() => _secili = idx);
              }

              return GestureDetector(
                onTapDown: (d) => guncelle(d.localPosition),
                onHorizontalDragUpdate: (d) => guncelle(d.localPosition),
                onHorizontalDragEnd: (_) => setState(() => _secili = null),
                onTapCancel: () => setState(() => _secili = null),
                child: CustomPaint(
                  size: Size(kisit.maxWidth, 200),
                  painter: _FiyatCizer(
                    fiyatlar: widget.fiyatlar,
                    renk: renk,
                    secili: _secili,
                    izgaraRengi: tema.dividerColor,
                    etiketRengi: tema.colorScheme.onSurfaceVariant,
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(trTarih(widget.tarihler.first),
                style: tema.textTheme.bodySmall),
            Text('parmağını basılı tutup kaydır',
                style: tema.textTheme.bodySmall
                    ?.copyWith(fontStyle: FontStyle.italic)),
            Text(trTarih(widget.tarihler.last),
                style: tema.textTheme.bodySmall),
          ],
        ),
      ],
    );
  }
}

class _FiyatCizer extends CustomPainter {
  final List<double> fiyatlar;
  final Color renk;
  final int? secili;
  final Color izgaraRengi;
  final Color etiketRengi;

  _FiyatCizer({
    required this.fiyatlar,
    required this.renk,
    required this.secili,
    required this.izgaraRengi,
    required this.etiketRengi,
  });

  @override
  void paint(Canvas tuval, Size boyut) {
    final enAz = fiyatlar.reduce(math.min);
    final enCok = fiyatlar.reduce(math.max);
    // Düz çizgi (tüm fiyatlar aynı) olursa sıfıra bölmeyi önle.
    final aralik = (enCok - enAz).abs() < 1e-12 ? 1.0 : enCok - enAz;
    const ustBosluk = 12.0;
    final yukseklik = boyut.height - ustBosluk * 2;

    double x(int i) => i / (fiyatlar.length - 1) * boyut.width;
    double y(double f) =>
        ustBosluk + yukseklik - ((f - enAz) / aralik) * yukseklik;

    // Yatay ızgara
    final izgara = Paint()
      ..color = izgaraRengi.withValues(alpha: 0.35)
      ..strokeWidth = 1;
    for (var k = 0; k <= 4; k++) {
      final yy = ustBosluk + yukseklik * k / 4;
      tuval.drawLine(Offset(0, yy), Offset(boyut.width, yy), izgara);
    }

    // Çizgi ve altındaki dolgu
    final yol = Path()..moveTo(x(0), y(fiyatlar[0]));
    for (var i = 1; i < fiyatlar.length; i++) {
      yol.lineTo(x(i), y(fiyatlar[i]));
    }
    final dolgu = Path.from(yol)
      ..lineTo(boyut.width, boyut.height)
      ..lineTo(0, boyut.height)
      ..close();
    tuval.drawPath(
        dolgu,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [renk.withValues(alpha: 0.28), renk.withValues(alpha: 0.0)],
          ).createShader(Rect.fromLTWH(0, 0, boyut.width, boyut.height)));
    tuval.drawPath(
        yol,
        Paint()
          ..color = renk
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke
          ..strokeJoin = StrokeJoin.round);

    // Seçili nokta
    final s = secili;
    if (s != null && s >= 0 && s < fiyatlar.length) {
      final sx = x(s);
      tuval.drawLine(Offset(sx, 0), Offset(sx, boyut.height),
          Paint()..color = etiketRengi.withValues(alpha: 0.5)..strokeWidth = 1);
      tuval.drawCircle(Offset(sx, y(fiyatlar[s])), 4.5,
          Paint()..color = renk);
      tuval.drawCircle(Offset(sx, y(fiyatlar[s])), 4.5,
          Paint()
            ..color = Colors.white
            ..strokeWidth = 1.5
            ..style = PaintingStyle.stroke);
    }

    // En yüksek / en düşük etiketi
    void etiket(String metin, double yy, Alignment hiza) {
      final tp = TextPainter(
        text: TextSpan(
            text: metin,
            style: TextStyle(fontSize: 10, color: etiketRengi)),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(tuval, Offset(boyut.width - tp.width - 2, yy));
    }

    etiket(trSayi(enCok, ondalik: 4), 0, Alignment.topRight);
    etiket(trSayi(enAz, ondalik: 4), boyut.height - 12, Alignment.bottomRight);
  }

  @override
  bool shouldRepaint(_FiyatCizer eski) =>
      eski.secili != secili ||
      eski.fiyatlar != fiyatlar ||
      eski.renk != renk;
}

/// Portföy dağılımı pastası.
///
/// Dilim renkleri sabit bir paletten sırayla verilir; TEFAS'ın varlık
/// sınıflarına anlam yükleyen bir renk şeması UYDURMUYORUZ (kırmızı = riskli
/// gibi). Böyle bir şema, olmayan bir yargıyı varmış gibi gösterirdi.
const List<Color> dagilimRenkleri = [
  Color(0xFF00897B), // teal
  Color(0xFF3949AB), // indigo
  Color(0xFFF9A825), // amber
  Color(0xFF6D4C41), // brown
  Color(0xFF00ACC1), // cyan
  Color(0xFF7CB342), // light green
  Color(0xFF8E24AA), // purple
  Color(0xFFEF6C00), // orange
  Color(0xFF546E7A), // blue grey
];

class DagilimPastasi extends StatelessWidget {
  /// (etiket, yüzde) çiftleri, büyükten küçüğe.
  final List<(String, double)> kalemler;

  const DagilimPastasi({super.key, required this.kalemler});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    if (kalemler.isEmpty) {
      return Text('Bu fon için dağılım verisi yok.',
          style: tema.textTheme.bodySmall);
    }

    final toplam = kalemler.fold<double>(0, (a, b) => a + b.$2);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Center(
          child: SizedBox(
            width: 172,
            height: 172,
            child: CustomPaint(
              painter: _PastaCizer(
                kalemler: kalemler,
                zemin: tema.colorScheme.surface,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        for (var i = 0; i < kalemler.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 11,
                  height: 11,
                  margin: const EdgeInsets.only(top: 3),
                  decoration: BoxDecoration(
                    color: dagilimRenkleri[i % dagilimRenkleri.length],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(kalemler[i].$1,
                      style: tema.textTheme.bodySmall),
                ),
                const SizedBox(width: 8),
                Text('%${trSayi(kalemler[i].$2)}',
                    style: tema.textTheme.bodySmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        // Toplam 100 etmiyorsa sustuğumuz bir şey var demektir; söyleyelim.
        if ((toplam - 100).abs() > 1.5)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              'Kalemler toplamı %${trSayi(toplam)}. TEFAS bazı küçük '
              'kalemleri ayrı raporlamıyor.',
              style: tema.textTheme.bodySmall?.copyWith(
                  color: tema.colorScheme.onSurfaceVariant, fontSize: 11),
            ),
          ),
      ],
    );
  }
}

class _PastaCizer extends CustomPainter {
  final List<(String, double)> kalemler;
  final Color zemin;

  _PastaCizer({required this.kalemler, required this.zemin});

  @override
  void paint(Canvas tuval, Size boyut) {
    final merkez = Offset(boyut.width / 2, boyut.height / 2);
    final yaricap = math.min(boyut.width, boyut.height) / 2;
    final toplam = kalemler.fold<double>(0, (a, b) => a + b.$2);
    if (toplam <= 0) return;

    var baslangic = -math.pi / 2; // saat 12'den başla
    for (var i = 0; i < kalemler.length; i++) {
      final aci = (kalemler[i].$2 / toplam) * 2 * math.pi;
      tuval.drawArc(
        Rect.fromCircle(center: merkez, radius: yaricap),
        baslangic,
        aci,
        true,
        Paint()..color = dagilimRenkleri[i % dagilimRenkleri.length],
      );
      baslangic += aci;
    }

    // Ortası boş halka: dilimler birbirinden daha kolay ayırt ediliyor.
    tuval.drawCircle(merkez, yaricap * 0.55, Paint()..color = zemin);
  }

  @override
  bool shouldRepaint(_PastaCizer eski) =>
      eski.kalemler != kalemler || eski.zemin != zemin;
}
