/// Ana kabuk: alt gezinme çubuğu ve ortak parçalar.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import 'arama_sayfasi.dart';
import 'ayarlar_sayfasi.dart';
import 'favoriler_sayfasi.dart';
import 'kategoriler_sayfasi.dart';
import 'ozet_sayfasi.dart';
import 'secici_sayfasi.dart';
import 'tablo_sayfasi.dart';

class AnaKabuk extends StatefulWidget {
  const AnaKabuk({super.key});

  @override
  State<AnaKabuk> createState() => _AnaKabukDurumu();
}

class _AnaKabukDurumu extends State<AnaKabuk> {
  int _sekme = 0;

  // Favoriler alt çubukta değil, üstteki yıldız düğmesinde: alt çubukta
  // beşten fazla sekme sıkışıyor ve etiketler okunmaz oluyor.
  static const _basliklar = [
    'Özet',
    'Akıllı Filtre',
    'Kategoriler',
    'Tüm Fonlar',
    'Ayarlar',
  ];

  @override
  Widget build(BuildContext context) {
    final durum = Kapsam.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(_basliklar[_sekme]),
        actions: [
          if (durum.hazir) ...[
            IconButton(
              icon: const Icon(Icons.search),
              tooltip: 'Fon ara',
              onPressed: () => showSearch(
                  context: context, delegate: FonArama(durum)),
            ),
            IconButton(
              icon: const Icon(Icons.star_outline),
              tooltip: 'Favoriler',
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => Scaffold(
                  appBar: AppBar(title: const Text('Favoriler')),
                  body: Kapsam(durum: durum, child: const FavorilerSayfasi()),
                ),
              )),
            ),
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Veriyi yenile',
              onPressed: () => durum.tazele(),
            ),
          ],
        ],
      ),
      body: switch (durum.durum) {
        YuklemeDurumu.basliyor ||
        YuklemeDurumu.yukleniyor when durum.veri == null =>
          const _Yukleniyor(),
        YuklemeDurumu.hata => _HataEkrani(
            mesaj: durum.hata,
            oneri: durum.hataOneri,
            tekrar: () => durum.tazele(),
          ),
        _ => IndexedStack(
            index: _sekme,
            children: const [
              OzetSayfasi(),
              SeciciSayfasi(),
              KategorilerSayfasi(),
              TabloSayfasi(),
              AyarlarSayfasi(),
            ],
          ),
      },
      bottomNavigationBar: NavigationBar(
        selectedIndex: _sekme,
        onDestinationSelected: (i) => setState(() => _sekme = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Özet'),
          NavigationDestination(
              icon: Icon(Icons.auto_awesome_outlined),
              selectedIcon: Icon(Icons.auto_awesome),
              label: 'Akıllı'),
          NavigationDestination(
              icon: Icon(Icons.category_outlined),
              selectedIcon: Icon(Icons.category),
              label: 'Kategori'),
          NavigationDestination(
              icon: Icon(Icons.table_chart_outlined),
              selectedIcon: Icon(Icons.table_chart),
              label: 'Tablo'),
          NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings),
              label: 'Ayarlar'),
        ],
      ),
    );
  }
}

class _Yukleniyor extends StatelessWidget {
  const _Yukleniyor();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Fon verileri indiriliyor...'),
          ],
        ),
      );
}

class _HataEkrani extends StatelessWidget {
  final String mesaj;
  final String oneri;
  final VoidCallback tekrar;

  const _HataEkrani(
      {required this.mesaj, required this.oneri, required this.tekrar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off,
                size: 56, color: tema.colorScheme.onSurfaceVariant),
            const SizedBox(height: 16),
            Text(mesaj,
                textAlign: TextAlign.center,
                style: tema.textTheme.titleMedium),
            if (oneri.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(oneri,
                  textAlign: TextAlign.center,
                  style: tema.textTheme.bodySmall),
            ],
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: tekrar,
              icon: const Icon(Icons.refresh),
              label: const Text('Tekrar dene'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Her ekranın altında duran zorunlu uyarı.
class SorumlulukNotu extends StatelessWidget {
  const SorumlulukNotu({super.key});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final metin = durum.veri?.sorumlulukNotu ??
        'Bu uygulama yatırım danışmanlığı değildir. Gösterilen sıralamalar '
            'geçmiş fiyat verilerinden hesaplanmış istatistiklerdir. Geçmiş '
            'getiri gelecek getiriyi göstermez. Veriler TEFAS\'tan alınmıştır, '
            'hata içerebilir.';
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 24, 4, 28),
      child: Text(
        metin,
        style: tema.textTheme.bodySmall?.copyWith(
          color: tema.colorScheme.onSurfaceVariant,
          fontSize: 11,
        ),
      ),
    );
  }
}

/// Veri tarihi rozeti — verinin ne kadar taze olduğunu her ekranda göster.
class VeriTarihiRozeti extends StatelessWidget {
  const VeriTarihiRozeti({super.key});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final veri = durum.veri;
    if (veri == null) return const SizedBox.shrink();

    final p = veri.veriTarihi.split('-');
    final tarih = p.length == 3 ? '${p[2]}.${p[1]}.${p[0]}' : veri.veriTarihi;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: veri.onbellekten
            ? tema.colorScheme.errorContainer.withValues(alpha: 0.4)
            : tema.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(veri.onbellekten ? Icons.wifi_off : Icons.event,
              size: 14, color: tema.colorScheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Text(
            veri.onbellekten
                ? 'Kayıtlı veri · $tarih'
                : 'Veri tarihi: $tarih',
            style: tema.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
