/// Kategoriler: fon türü listesi, dokununca o kategorinin sıralı fonları.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import '../cekirdek/modeller.dart';
import '../cekirdek/puanlama.dart';
import 'ana_kabuk.dart';
import 'detay_sayfasi.dart';
import 'grafik.dart';

class KategorilerSayfasi extends StatelessWidget {
  const KategorilerSayfasi({super.key});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final veri = durum.veri;
    if (veri == null) return const SizedBox.shrink();

    // Fon tipine göre grupla: yatırım / emeklilik / borsa yatırım
    final tipler = <String, List<KategoriOzeti>>{};
    for (final k in veri.kategoriler) {
      tipler.putIfAbsent(k.tipAd.isEmpty ? k.tip : k.tipAd, () => []).add(k);
    }

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        const SizedBox(height: 12),
        const VeriTarihiRozeti(),
        const SizedBox(height: 16),
        for (final giris in tipler.entries) ...[
          Padding(
            padding: const EdgeInsets.only(bottom: 8, top: 4),
            child: Text(giris.key,
                style: tema.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ),
          Card(
            margin: const EdgeInsets.only(bottom: 20),
            child: Column(
              children: [
                for (var i = 0; i < giris.value.length; i++) ...[
                  if (i > 0) const Divider(height: 1, indent: 16),
                  _KategoriSatiri(kategori: giris.value[i]),
                ],
              ],
            ),
          ),
        ],
        const SorumlulukNotu(),
      ],
    );
  }
}

class _KategoriSatiri extends StatelessWidget {
  final KategoriOzeti kategori;

  const _KategoriSatiri({required this.kategori});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    // "Hisse Senedi Şemsiye Fonu" -> "Hisse Senedi": ekranda şemsiye kelimesi
    // yer kaplıyor ve kullanıcıya bir şey söylemiyor.
    final ad = kategori.ad.replaceAll(' Şemsiye Fonu', '');

    return ListTile(
      title: Text(ad),
      subtitle: Text(
        kategori.puanlanabilir
            ? '${kategori.adet} fon'
            : '${kategori.adet} fon · puanlanmıyor',
        style: tema.textTheme.bodySmall?.copyWith(
          color: kategori.puanlanabilir
              ? null
              : tema.colorScheme.error.withValues(alpha: 0.8),
        ),
      ),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => KategoriDetaySayfasi(kategori: kategori),
      )),
    );
  }
}

class KategoriDetaySayfasi extends StatelessWidget {
  final KategoriOzeti kategori;

  const KategoriDetaySayfasi({super.key, required this.kategori});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final fonlar = durum.kategoridekiler(kategori.tip, kategori.ad);
    final ad = kategori.ad.replaceAll(' Şemsiye Fonu', '');

    return Scaffold(
      appBar: AppBar(
        title: Text(ad),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(24),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8, left: 16, right: 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('${kategori.tipAd} · ${fonlar.length} fon',
                  style: tema.textTheme.bodySmall),
            ),
          ),
        ),
      ),
      body: !kategori.puanlanabilir
          ? _PuanlanmiyorUyarisi(fonlar: fonlar)
          : ListView.separated(
              itemCount: fonlar.length + 2,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                if (i == 0) {
                  return kategori.cikarimAgirlikli
                      ? const _CikarimUyarisi()
                      : const SizedBox.shrink();
                }
                if (i == fonlar.length + 1) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: SorumlulukNotu(),
                  );
                }
                return _SiraliSatir(kayit: fonlar[i - 1]);
              },
            ),
    );
  }
}

/// Kategorinin TEFAS'tan değil fon adından çıkarıldığını söyler.
///
/// Bunu gizlemek kolay olurdu ama yanlış olurdu: emeklilik fonlarında
/// TEFAS kategori filtresini yok sayıp bütün fonları döndürüyor, o yüzden
/// kategoriyi fon adındaki anahtar kelimelerden çıkarıyoruz. Çoğu isim
/// çok düzenli olduğu için bu güvenilir, ama yine de bir çıkarım.
class _CikarimUyarisi extends StatelessWidget {
  const _CikarimUyarisi();

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tema.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline,
              size: 18, color: tema.colorScheme.onSurfaceVariant),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Bu kategori TEFAS\'ın sınıflamasından değil, fon adlarından '
              'çıkarıldı. TEFAS emeklilik ve borsa yatırım fonlarında '
              'kategori bilgisi vermiyor.',
              style: tema.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _PuanlanmiyorUyarisi extends StatelessWidget {
  final List<PuanliFon> fonlar;

  const _PuanlanmiyorUyarisi({required this.fonlar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final neden = fonlar.isNotEmpty
        ? fonlar.first.fon.puanlanmamaNedeni
        : null;

    return ListView(
      children: [
        Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: tema.colorScheme.errorContainer.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Bu kategori puanlanmıyor',
                  style: tema.textTheme.titleSmall
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              Text(
                neden ??
                    'Kategoride sağlıklı bir karşılaştırma yapacak kadar fon '
                        'yok. Az sayıda fon arasında hesaplanan puan yanıltıcı '
                        'olur, o yüzden üretmiyoruz.',
                style: tema.textTheme.bodySmall,
              ),
            ],
          ),
        ),
        for (final k in fonlar) ...[
          _SiraliSatir(kayit: k),
          const Divider(height: 1),
        ],
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16),
          child: SorumlulukNotu(),
        ),
      ],
    );
  }
}

class _SiraliSatir extends StatelessWidget {
  final PuanliFon kayit;

  const _SiraliSatir({required this.kayit});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final f = kayit.fon;
    final aylik = f.getiri.aylik;
    final renk = aylik == null
        ? tema.colorScheme.onSurfaceVariant
        : (aylik >= 0 ? Colors.green.shade600 : Colors.red.shade600);

    return ListTile(
      dense: true,
      leading: kayit.sira == null
          ? const SizedBox(width: 30)
          : SizedBox(
              width: 30,
              child: Text('${kayit.sira}',
                  textAlign: TextAlign.center,
                  style: tema.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: kayit.sira! <= 3
                          ? tema.colorScheme.primary
                          : tema.colorScheme.onSurfaceVariant)),
            ),
      title: Text(f.kod,
          style: tema.textTheme.titleSmall
              ?.copyWith(fontWeight: FontWeight.bold)),
      subtitle: Text(f.ad,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: tema.textTheme.bodySmall),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(trYuzde(aylik),
              style: tema.textTheme.titleSmall
                  ?.copyWith(color: renk, fontWeight: FontWeight.bold)),
          Text(
            kayit.puan == null
                ? 'aylık'
                : 'puan ${trSayi(kayit.puan!, ondalik: 2)}',
            style: tema.textTheme.bodySmall?.copyWith(fontSize: 10),
          ),
        ],
      ),
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => DetaySayfasi(kod: f.kod),
      )),
    );
  }
}
