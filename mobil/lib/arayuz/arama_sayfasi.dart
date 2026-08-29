/// Fon arama: kod ya da ada göre.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import 'detay_sayfasi.dart';
import 'grafik.dart';

class FonArama extends SearchDelegate<String?> {
  final UygulamaDurumu durum;

  FonArama(this.durum)
      : super(
          searchFieldLabel: 'Fon kodu veya adı',
          textInputAction: TextInputAction.search,
        );

  @override
  List<Widget> buildActions(BuildContext context) => [
        if (query.isNotEmpty)
          IconButton(
            icon: const Icon(Icons.clear),
            onPressed: () => query = '',
          ),
      ];

  @override
  Widget buildLeading(BuildContext context) => IconButton(
        icon: const Icon(Icons.arrow_back),
        onPressed: () => close(context, null),
      );

  @override
  Widget buildResults(BuildContext context) => _sonuclar(context);

  @override
  Widget buildSuggestions(BuildContext context) => _sonuclar(context);

  Widget _sonuclar(BuildContext context) {
    final tema = Theme.of(context);
    if (query.trim().isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'Fon kodu (örnek: AFA) ya da adının bir parçasını yazın.',
            textAlign: TextAlign.center,
            style: tema.textTheme.bodyMedium,
          ),
        ),
      );
    }

    final liste = durum.ara(query);
    if (liste.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text('"$query" ile eşleşen fon bulunamadı.',
              textAlign: TextAlign.center,
              style: tema.textTheme.bodyMedium),
        ),
      );
    }

    return ListView.separated(
      itemCount: liste.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, i) {
        final f = liste[i].fon;
        final aylik = f.getiri.aylik;
        final renk = aylik == null
            ? tema.colorScheme.onSurfaceVariant
            : (aylik >= 0 ? Colors.green.shade600 : Colors.red.shade600);
        return ListTile(
          dense: true,
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
              Text('aylık',
                  style: tema.textTheme.bodySmall?.copyWith(fontSize: 10)),
            ],
          ),
          onTap: () {
            close(context, f.kod);
            Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => DetaySayfasi(kod: f.kod),
            ));
          },
        );
      },
    );
  }
}
