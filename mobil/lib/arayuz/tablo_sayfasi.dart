/// Tüm fonlar tablosu: yatay kaydırılır, sütun başlığına dokununca sıralanır.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import '../cekirdek/puanlama.dart';
import 'ana_kabuk.dart';
import 'detay_sayfasi.dart';
import 'grafik.dart';

/// Tablo sutunlari.
///
/// `puan` ve `risk` IKI AYRI EKSENDIR, tek bir kalite skorunun parcalari
/// degil. Olculdu: gecmis getiriye gore siralama gelecegi tutmuyor
/// (ileri Spearman ~0,05) ama oynaklik kalici (0,76). Ikisini tek sayida
/// toplamak, tutmayan bileseni tutan bilesenle bulaniklastiriyordu.
enum _Sutun { kod, gunluk, haftalik, aylik, ucAylik, yillik, puan, risk }

const _basliklar = {
  _Sutun.kod: 'Fon',
  _Sutun.gunluk: 'Günlük',
  _Sutun.haftalik: 'Haftalık',
  _Sutun.aylik: 'Aylık',
  _Sutun.ucAylik: '3 Aylık',
  _Sutun.yillik: 'Yıllık',
  // IKI AYRI EKSEN. Tek 'Puan' sutunu, geleceği tutmayan getiri
  // bileseniyle kalici olan risk bilesenini tek sayida topluyordu.
  _Sutun.puan: 'Getiri',
  _Sutun.risk: 'Sakinlik',
};

const _genislikler = {
  _Sutun.kod: 74.0,
  _Sutun.gunluk: 78.0,
  _Sutun.haftalik: 82.0,
  _Sutun.aylik: 78.0,
  _Sutun.ucAylik: 82.0,
  _Sutun.yillik: 82.0,
  _Sutun.puan: 70.0,
  _Sutun.risk: 78.0,
};

class TabloSayfasi extends StatefulWidget {
  const TabloSayfasi({super.key});

  @override
  State<TabloSayfasi> createState() => _TabloSayfasiDurumu();
}

class _TabloSayfasiDurumu extends State<TabloSayfasi> {
  _Sutun _sirala = _Sutun.puan;
  bool _azalan = true;

  double? _deger(PuanliFon k, _Sutun s) => switch (s) {
        _Sutun.kod => null,
        _Sutun.gunluk => k.fon.getiri.gunluk,
        _Sutun.haftalik => k.fon.getiri.haftalik,
        _Sutun.aylik => k.fon.getiri.aylik,
        _Sutun.ucAylik => k.fon.getiri.ucAylik,
        _Sutun.yillik => k.fon.getiri.yillik,
        _Sutun.puan => k.fon.getiriPuani ?? k.puan,
        _Sutun.risk => k.fon.riskPuani,
      };

  void _basligaDokun(_Sutun s) {
    setState(() {
      if (_sirala == s) {
        _azalan = !_azalan;
      } else {
        _sirala = s;
        _azalan = true;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final liste = List<PuanliFon>.from(durum.puanli);

    liste.sort((a, b) {
      if (_sirala == _Sutun.kod) {
        final c = a.fon.kod.compareTo(b.fon.kod);
        return _azalan ? -c : c;
      }
      final av = _deger(a, _sirala);
      final bv = _deger(b, _sirala);
      // Değeri olmayanlar her zaman en sonda kalsın: yoklukları
      // "en kötü" gibi görünmesin.
      if (av == null && bv == null) return a.fon.kod.compareTo(b.fon.kod);
      if (av == null) return 1;
      if (bv == null) return -1;
      return _azalan ? bv.compareTo(av) : av.compareTo(bv);
    });

    final toplamGenislik =
        _genislikler.values.fold<double>(0, (a, b) => a + b) + 16;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const VeriTarihiRozeti(),
              Text('${liste.length} fon', style: tema.textTheme.bodySmall),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SizedBox(
              width: toplamGenislik,
              child: Column(
                children: [
                  Container(
                    color: tema.colorScheme.surfaceContainerHighest,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        const SizedBox(width: 8),
                        for (final s in _Sutun.values)
                          _Baslik(
                            metin: _basliklar[s]!,
                            genislik: _genislikler[s]!,
                            aktif: _sirala == s,
                            azalan: _azalan,
                            solaHizali: s == _Sutun.kod,
                            onTap: () => _basligaDokun(s),
                          ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: ListView.separated(
                      itemCount: liste.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, i) =>
                          _Satir(kayit: liste[i], deger: _deger),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _Baslik extends StatelessWidget {
  final String metin;
  final double genislik;
  final bool aktif;
  final bool azalan;
  final bool solaHizali;
  final VoidCallback onTap;

  const _Baslik({
    required this.metin,
    required this.genislik,
    required this.aktif,
    required this.azalan,
    required this.solaHizali,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return InkWell(
      onTap: onTap,
      child: SizedBox(
        width: genislik,
        child: Row(
          mainAxisAlignment:
              solaHizali ? MainAxisAlignment.start : MainAxisAlignment.end,
          children: [
            Flexible(
              child: Text(
                metin,
                overflow: TextOverflow.ellipsis,
                style: tema.textTheme.bodySmall?.copyWith(
                  fontWeight: aktif ? FontWeight.bold : FontWeight.normal,
                  color: aktif ? tema.colorScheme.primary : null,
                ),
              ),
            ),
            if (aktif)
              Icon(azalan ? Icons.arrow_drop_down : Icons.arrow_drop_up,
                  size: 16, color: tema.colorScheme.primary),
            if (!solaHizali) const SizedBox(width: 4),
          ],
        ),
      ),
    );
  }
}

class _Satir extends StatelessWidget {
  final PuanliFon kayit;
  final double? Function(PuanliFon, _Sutun) deger;

  const _Satir({required this.kayit, required this.deger});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return InkWell(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => DetaySayfasi(kod: kayit.fon.kod),
      )),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(
          children: [
            const SizedBox(width: 8),
            SizedBox(
              width: _genislikler[_Sutun.kod],
              child: Text(kayit.fon.kod,
                  style: tema.textTheme.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ),
            for (final s in [
              _Sutun.gunluk,
              _Sutun.haftalik,
              _Sutun.aylik,
              _Sutun.ucAylik,
              _Sutun.yillik,
            ])
              _Hucre(deger: deger(kayit, s), genislik: _genislikler[s]!),
            SizedBox(
              width: _genislikler[_Sutun.puan]!,
              child: Text(
                kayit.puan == null ? '—' : trSayi(kayit.puan!, ondalik: 2),
                textAlign: TextAlign.right,
                style: tema.textTheme.bodyMedium
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 4),
          ],
        ),
      ),
    );
  }
}

class _Hucre extends StatelessWidget {
  final double? deger;
  final double genislik;

  const _Hucre({required this.deger, required this.genislik});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final renk = deger == null
        ? tema.colorScheme.onSurfaceVariant
        : (deger! >= 0 ? Colors.green.shade600 : Colors.red.shade600);
    return SizedBox(
      width: genislik,
      child: Padding(
        padding: const EdgeInsets.only(right: 4),
        child: Text(
          deger == null ? '—' : trYuzde(deger),
          textAlign: TextAlign.right,
          style: tema.textTheme.bodyMedium?.copyWith(color: renk),
        ),
      ),
    );
  }
}
