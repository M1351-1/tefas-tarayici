/// Favoriler: yıldızlanan fonlar.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import 'ana_kabuk.dart';
import 'ozet_sayfasi.dart' show FonSatiri;

class FavorilerSayfasi extends StatelessWidget {
  const FavorilerSayfasi({super.key});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final liste = durum.favoriler();

    if (liste.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.star_outline,
                  size: 56, color: tema.colorScheme.onSurfaceVariant),
              const SizedBox(height: 16),
              Text('Henüz favori fon yok',
                  style: tema.textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                'Bir fonun detay sayfasını açıp sağ üstteki yıldıza dokunarak '
                'buraya ekleyebilirsiniz.',
                textAlign: TextAlign.center,
                style: tema.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        const SizedBox(height: 12),
        const VeriTarihiRozeti(),
        const SizedBox(height: 16),
        Card(
          margin: EdgeInsets.zero,
          child: Column(
            children: [
              for (var i = 0; i < liste.length; i++) ...[
                if (i > 0) const Divider(height: 1, indent: 16),
                FonSatiri(fon: liste[i].fon, puan: liste[i].puan),
              ],
            ],
          ),
        ),
        const SorumlulukNotu(),
      ],
    );
  }
}
