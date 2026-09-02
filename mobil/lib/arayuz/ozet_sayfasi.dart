/// Özet: bugün en çok yükselen ve düşen fonlar.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import '../cekirdek/modeller.dart';
import 'ana_kabuk.dart';
import 'detay_sayfasi.dart';
import 'grafik.dart';

class OzetSayfasi extends StatelessWidget {
  const OzetSayfasi({super.key});

  @override
  Widget build(BuildContext context) {
    final durum = Kapsam.of(context);
    final veri = durum.veri;
    if (veri == null) return const SizedBox.shrink();

    final yukselen = durum.gunlukUcler(yukselen: true);
    final dusen = durum.gunlukUcler(yukselen: false);

    return RefreshIndicator(
      onRefresh: () => durum.tazele(),
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: [
          const SizedBox(height: 12),
          const VeriTarihiRozeti(),
          const SizedBox(height: 16),
          _SayilarKarti(veri: veri),
          if (veri.ongoruGucu != null) ...[
            const SizedBox(height: 16),
            OngoruGucuKarti(guc: veri.ongoruGucu!),
          ],
          const SizedBox(height: 20),
          _UclerBolumu(
            baslik: 'Bugün en çok yükselen 10 fon',
            simge: Icons.trending_up,
            renk: Colors.green.shade600,
            fonlar: yukselen,
          ),
          const SizedBox(height: 20),
          _UclerBolumu(
            baslik: 'Bugün en çok düşen 10 fon',
            simge: Icons.trending_down,
            renk: Colors.red.shade600,
            fonlar: dusen,
          ),
          const SorumlulukNotu(),
        ],
      ),
    );
  }
}

/// Sıralamanın ÖLÇÜLMÜŞ öngörü gücü.
///
/// NEDEN EN ÜSTTE: uygulama fonları puanlayıp "kategori sırası 1" diye
/// gösteriyor ve bu bir iddia. İddia toplayıcıda ileri yürüyüşle sınandı
/// ve geçmiş getiriye göre sıralamanın geleceği tutmadığı çıktı. Bunu
/// söylememek, kullanıcının sıralamayı bir tavsiye sanmasına yol açar.
///
/// Ölçüm HER TOPLAMADA yeniden yapılıyor; burada sabit bir metin yok.
class OngoruGucuKarti extends StatelessWidget {
  final OngoruGucu guc;
  const OngoruGucuKarti({super.key, required this.guc});

  @override
  Widget build(BuildContext context) {
    if (!guc.olculdu) return const SizedBox.shrink();
    final tema = Theme.of(context);
    final calisiyor = guc.calisiyor;
    final renk = calisiyor ? Colors.green.shade700 : Colors.orange.shade800;

    return Card(
      color: renk.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: renk.withValues(alpha: 0.4)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(calisiyor ? Icons.verified : Icons.science_outlined,
                    size: 18, color: renk),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Sıralama geleceği tutuyor mu?',
                    style: tema.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold, color: renk),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(guc.ozet, style: tema.textTheme.bodySmall?.copyWith(
                height: 1.45)),
            const SizedBox(height: 8),
            Text(
              'Bu ölçüm her veri toplamada yeniden yapılır. Sıralamayı bir '
              'tavsiye değil, geçmişin tasviri olarak okuyun.',
              style: tema.textTheme.bodySmall?.copyWith(
                  color: tema.colorScheme.onSurfaceVariant,
                  fontStyle: FontStyle.italic),
            ),
          ],
        ),
      ),
    );
  }
}

class _SayilarKarti extends StatelessWidget {
  final Veri veri;

  const _SayilarKarti({required this.veri});

  @override
  Widget build(BuildContext context) {
    final puanlanan = veri.fonlar.where((f) => f.puan != null).length;
    final kategoriSayisi =
        veri.kategoriler.where((k) => k.puanlanabilir).length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _Sayi(sayi: '${veri.fonlar.length}', etiket: 'fon izleniyor'),
            _Sayi(sayi: '$puanlanan', etiket: 'fon puanlandı'),
            _Sayi(sayi: '$kategoriSayisi', etiket: 'kategori'),
          ],
        ),
      ),
    );
  }
}

class _Sayi extends StatelessWidget {
  final String sayi;
  final String etiket;

  const _Sayi({required this.sayi, required this.etiket});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Column(
      children: [
        Text(sayi,
            style: tema.textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        Text(etiket, style: tema.textTheme.bodySmall),
      ],
    );
  }
}

class _UclerBolumu extends StatelessWidget {
  final String baslik;
  final IconData simge;
  final Color renk;
  final List<Fon> fonlar;

  const _UclerBolumu({
    required this.baslik,
    required this.simge,
    required this.renk,
    required this.fonlar,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(simge, color: renk, size: 20),
            const SizedBox(width: 8),
            Text(baslik,
                style: tema.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        if (fonlar.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text('Günlük getiri verisi yok.',
                style: tema.textTheme.bodySmall),
          )
        else
          Card(
            margin: EdgeInsets.zero,
            child: Column(
              children: [
                for (var i = 0; i < fonlar.length; i++) ...[
                  if (i > 0) const Divider(height: 1, indent: 16, endIndent: 16),
                  FonSatiri(fon: fonlar[i], sira: i + 1),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

/// Listelerde kullanılan tek satırlık fon gösterimi.
class FonSatiri extends StatelessWidget {
  final Fon fon;
  final int? sira;
  final double? puan;

  const FonSatiri({super.key, required this.fon, this.sira, this.puan});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final g = fon.getiri.gunluk;
    final renk = g == null
        ? tema.colorScheme.onSurfaceVariant
        : (g >= 0 ? Colors.green.shade600 : Colors.red.shade600);

    return ListTile(
      dense: true,
      leading: sira == null
          ? null
          : SizedBox(
              width: 26,
              child: Text('$sira.',
                  style: tema.textTheme.bodySmall,
                  textAlign: TextAlign.right),
            ),
      title: Row(
        children: [
          Text(fon.kod,
              style: tema.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(fon.ad,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: tema.textTheme.bodySmall),
          ),
        ],
      ),
      subtitle: Text(
        puan != null
            ? '${fon.kategori} · puan ${trSayi(puan!, ondalik: 2)}'
            : fon.kategori,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: tema.textTheme.bodySmall,
      ),
      trailing: Text(
        trYuzde(g),
        style: tema.textTheme.titleSmall
            ?.copyWith(color: renk, fontWeight: FontWeight.bold),
      ),
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => DetaySayfasi(kod: fon.kod),
      )),
    );
  }
}
