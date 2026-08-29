/// Akıllı filtre: profil sorularından kısa liste.
///
/// Ekranın en üstündeki uyarı bilinçli: bu bir eleme aracıdır, tavsiye
/// motoru değildir. Kullanıcının "uygulama bana bunu önerdi" diye
/// anlamaması için dil boyunca "kalan fonlar", "kısıtlarınıza uyanlar"
/// deniyor, "önerilen" denmiyor.
library;

import 'package:flutter/material.dart';

import '../cekirdek/durum.dart';
import '../cekirdek/secici.dart';
import 'ana_kabuk.dart';
import 'danisman_sayfasi.dart';
import 'detay_sayfasi.dart';
import 'grafik.dart';

class SeciciSayfasi extends StatefulWidget {
  const SeciciSayfasi({super.key});

  @override
  State<SeciciSayfasi> createState() => _SeciciSayfasiDurumu();
}

class _SeciciSayfasiDurumu extends State<SeciciSayfasi> {
  Profil _profil = const Profil();
  SecimSonucu? _sonuc;

  void _calistir() {
    final durum = Kapsam.of(context);
    final veri = durum.veri;
    if (veri == null) return;
    setState(() => _sonuc = sec(veri.fonlar, _profil));
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    if (durum.veri == null) return const SizedBox.shrink();

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: tema.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.filter_alt_outlined,
                  size: 18, color: tema.colorScheme.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Kısıtlarınızı söyleyin, binlerce fonu eleyip kalanları '
                  'gerekçesiyle listeleyeyim. Bu bir tavsiye değil, bir '
                  'filtredir — kararı siz verirsiniz.',
                  style: tema.textTheme.bodySmall,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // ------------------------------------------------------ risk
        Text('Ne kadar dalgalanmaya katlanabilirsiniz?',
            style: tema.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        RadioGroup<RiskToleransi>(
          groupValue: _profil.risk,
          onChanged: (v) => setState(() {
            _profil = _profil.kopyala(risk: v);
            _sonuc = null;
          }),
          child: Column(
            children: [
              for (final r in RiskToleransi.values)
                RadioListTile<RiskToleransi>(
                  value: r,
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(r.ad),
                  subtitle: Text(
                    r.oynaklikTavani == null
                        ? r.aciklama
                        : '${r.aciklama} · oynaklık en fazla %'
                            '${r.oynaklikTavani!.toStringAsFixed(0)}',
                    style: tema.textTheme.bodySmall,
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // ------------------------------------------------------ vade
        Text('Parayı ne kadar süre tutmayı düşünüyorsunuz?',
            style: tema.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        SegmentedButton<Vade>(
          segments: [
            for (final v in Vade.values)
              ButtonSegment(
                  value: v,
                  label: Text(switch (v) {
                    Vade.kisa => 'Kısa',
                    Vade.orta => 'Orta',
                    Vade.uzun => 'Uzun',
                  })),
          ],
          selected: {_profil.vade},
          showSelectedIcon: false,
          onSelectionChanged: (s) => setState(() {
            _profil = _profil.kopyala(vade: s.first);
            _sonuc = null;
          }),
        ),
        const SizedBox(height: 4),
        Text(_profil.vade.ad, style: tema.textTheme.bodySmall),
        const SizedBox(height: 20),

        // --------------------------------------------------- tercihler
        Text('Hangi tür fonlara bakalım?',
            style: tema.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text('Hiçbirini seçmezseniz hepsine bakarım.',
            style: tema.textTheme.bodySmall),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            for (final t in Tercih.values)
              FilterChip(
                label: Text(t.ad),
                selected: _profil.tercihler.contains(t),
                onSelected: (secili) => setState(() {
                  final yeni = Set<Tercih>.from(_profil.tercihler);
                  if (secili) {
                    yeni.add(t);
                  } else {
                    yeni.remove(t);
                  }
                  _profil = _profil.kopyala(tercihler: yeni);
                  _sonuc = null;
                }),
              ),
          ],
        ),
        const SizedBox(height: 8),
        SwitchListTile(
          value: _profil.emeklilikDahil,
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: const Text('Emeklilik (BES) fonları da dahil olsun'),
          subtitle: Text(
            'Emeklilik fonlarının kategorisi fon adından çıkarılmıştır, '
            'TEFAS bu tipte kategori bilgisi vermiyor.',
            style: tema.textTheme.bodySmall,
          ),
          onChanged: (v) => setState(() {
            _profil = _profil.kopyala(emeklilikDahil: v);
            _sonuc = null;
          }),
        ),
        const SizedBox(height: 16),

        FilledButton.icon(
          onPressed: _calistir,
          icon: const Icon(Icons.playlist_add_check),
          label: const Text('Kısa listeyi çıkar'),
        ),
        const SizedBox(height: 24),

        if (_sonuc != null) ..._sonucBolumu(_sonuc!, tema),
        const SorumlulukNotu(),
      ],
    );
  }

  List<Widget> _sonucBolumu(SecimSonucu s, ThemeData tema) {
    if (s.adaylar.isEmpty) {
      final darBogaz = s.ozet.darBogaz;
      return [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Kısıtlarınıza uyan fon kalmadı',
                    style: tema.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  darBogaz == null
                      ? 'Filtreleri gevşetmeyi deneyin.'
                      : 'En çok eleyen kısıt: $darBogaz. Onu gevşetmeyi '
                          'deneyin.',
                  style: tema.textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                _ElemeOzeti(ozet: s.ozet),
              ],
            ),
          ),
        ),
      ];
    }

    return [
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('Kalan ${s.adaylar.length} fon',
              style: tema.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          Text('${s.ozet.kalan} fon elemeyi geçti',
              style: tema.textTheme.bodySmall),
        ],
      ),
      const SizedBox(height: 4),
      Text(
        'Sıralama, seçtiğiniz vadeye uygun ağırlıklarla yapıldı '
        '(${_profil.vade.ad.toLowerCase()}).',
        style: tema.textTheme.bodySmall,
      ),
      const SizedBox(height: 12),
      for (final a in s.adaylar) _AdayKarti(aday: a),
      const SizedBox(height: 8),
      _ElemeOzeti(ozet: s.ozet),
      const SizedBox(height: 16),
      OutlinedButton.icon(
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => DanismanSayfasi(
            fonlar: s.adaylar.map((a) => a.fon).toList(),
            profil: _profil,
          ),
        )),
        icon: const Icon(Icons.chat_bubble_outline),
        label: const Text('Bu liste hakkında Claude\'a sor'),
      ),
    ];
  }
}

class _ElemeOzeti extends StatelessWidget {
  final ElemeOzeti ozet;

  const _ElemeOzeti({required this.ozet});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tema.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Eleme dökümü',
              style: tema.textTheme.bodySmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          _satir(tema, 'Başlangıç', '${ozet.baslangic} fon'),
          _satir(tema, 'Puanlanamadı', '−${ozet.puansizElendi}'),
          _satir(tema, 'Tür tercihi', '−${ozet.kategoriElendi}'),
          _satir(tema, 'Oynaklık sınırı', '−${ozet.oynaklikElendi}'),
          _satir(tema, 'Kayıp sınırı', '−${ozet.dususElendi}'),
          const Divider(height: 14),
          _satir(tema, 'Kalan', '${ozet.kalan} fon', kalin: true),
        ],
      ),
    );
  }

  Widget _satir(ThemeData tema, String a, String b, {bool kalin = false}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 1),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(a,
                style: tema.textTheme.bodySmall?.copyWith(
                    fontWeight: kalin ? FontWeight.bold : null)),
            Text(b,
                style: tema.textTheme.bodySmall?.copyWith(
                    fontWeight: kalin ? FontWeight.bold : null)),
          ],
        ),
      );
}

class _AdayKarti extends StatelessWidget {
  final Aday aday;

  const _AdayKarti({required this.aday});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final f = aday.fon;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => DetaySayfasi(kod: f.kod),
        )),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 13,
                    backgroundColor: tema.colorScheme.primaryContainer,
                    child: Text('${aday.sira}',
                        style: tema.textTheme.bodySmall?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: tema.colorScheme.onPrimaryContainer)),
                  ),
                  const SizedBox(width: 10),
                  Text(f.kod,
                      style: tema.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const Spacer(),
                  Text(trYuzde(f.getiri.aylik),
                      style: tema.textTheme.titleSmall?.copyWith(
                        color: (f.getiri.aylik ?? 0) >= 0
                            ? Colors.green.shade600
                            : Colors.red.shade600,
                        fontWeight: FontWeight.bold,
                      )),
                ],
              ),
              const SizedBox(height: 6),
              Text(f.ad,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: tema.textTheme.bodySmall),
              const SizedBox(height: 4),
              Wrap(
                spacing: 6,
                children: [
                  _Etiket(metin: f.kategori),
                  if (f.katilim) const _Etiket(metin: 'katılım'),
                  _Etiket(
                      metin: 'oynaklık %'
                          '${(f.volatilite ?? 0).toStringAsFixed(0)}'),
                ],
              ),
              const SizedBox(height: 10),
              for (final g in aday.gerekceler)
                Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.check, size: 14,
                          color: Colors.green.shade600),
                      const SizedBox(width: 6),
                      Expanded(
                          child: Text(g, style: tema.textTheme.bodySmall)),
                    ],
                  ),
                ),
              if (aday.uyarilar.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final u in aday.uyarilar)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          u.ciddi ? Icons.error_outline : Icons.info_outline,
                          size: 14,
                          color: u.ciddi
                              ? tema.colorScheme.error
                              : tema.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(u.metin,
                              style: tema.textTheme.bodySmall?.copyWith(
                                color: u.ciddi
                                    ? tema.colorScheme.error
                                    : tema.colorScheme.onSurfaceVariant,
                              )),
                        ),
                      ],
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Etiket extends StatelessWidget {
  final String metin;

  const _Etiket({required this.metin});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: tema.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(metin,
          style: tema.textTheme.bodySmall?.copyWith(fontSize: 10)),
    );
  }
}
