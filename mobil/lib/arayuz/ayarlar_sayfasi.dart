/// Ayarlar: tema, puanlama ağırlıkları, Claude anahtarı, veri adresi.
library;

import 'package:flutter/material.dart';

import '../cekirdek/ayarlar.dart';
import '../cekirdek/danisman.dart';
import '../cekirdek/durum.dart';
import '../cekirdek/veri.dart';
import 'ana_kabuk.dart';
import 'grafik.dart';

class AyarlarSayfasi extends StatefulWidget {
  /// Kendi Scaffold'uyla mı açıldı (Claude ekranından gelince böyle olur).
  final bool tekBasina;

  const AyarlarSayfasi({super.key, this.tekBasina = false});

  @override
  State<AyarlarSayfasi> createState() => _AyarlarSayfasiDurumu();
}

class _AyarlarSayfasiDurumu extends State<AyarlarSayfasi> {
  final _depo = AnahtarDeposu();
  bool _anahtarVar = false;
  String _model = varsayilanModel;
  bool _yukleniyor = true;

  /// API'den çekilen gerçek model listesi. null ise henüz sınanmadı.
  List<ModelBilgisi>? _modeller;
  bool _sinaniyor = false;
  String? _sinamaHatasi;
  String? _sinamaBasarili;

  /// Anahtarı sınar ve modelleri getirir.
  ///
  /// Aynı çağrı iki işi birden yapıyor: `/v1/models` başarılıysa anahtar
  /// geçerli, ağ açık ve elimizde hesabın erişebildiği gerçek model
  /// listesi var demektir. Model adını tahmin etmektense sormak.
  Future<void> _sina() async {
    setState(() {
      _sinaniyor = true;
      _sinamaHatasi = null;
      _sinamaBasarili = null;
    });
    try {
      final anahtar = await _depo.oku();
      if (anahtar == null || anahtar.isEmpty) {
        throw const DanismanHatasi('Önce anahtar girin.');
      }
      final liste = await modelleriGetir(anahtar);
      if (!mounted) return;
      setState(() {
        _modeller = liste;
        _sinaniyor = false;
        _sinamaBasarili = 'Bağlantı çalışıyor. ${liste.length} model bulundu.';
        // Kayıtlı model listede yoksa ilkine geç: olmayan bir modele
        // istek atmaya devam etmenin anlamı yok.
        if (!liste.any((m) => m.kimlik == _model)) {
          _model = liste.first.kimlik;
          _depo.modelYaz(_model);
        }
      });
    } on DanismanHatasi catch (e) {
      if (!mounted) return;
      setState(() {
        _sinaniyor = false;
        _sinamaHatasi = e.oneri.isEmpty ? e.mesaj : '${e.mesaj}\n${e.oneri}';
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    final v = await _depo.anahtarVar();
    final m = await _depo.modelOku();
    if (mounted) {
      setState(() {
        _anahtarVar = v;
        _model = m;
        _yukleniyor = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final govde = _govde(context);
    if (!widget.tekBasina) return govde;
    return Scaffold(
      appBar: AppBar(title: const Text('Ayarlar')),
      body: govde,
    );
  }

  Widget _govde(BuildContext context) {
    final tema = Theme.of(context);
    final durum = Kapsam.of(context);
    final ayarlar = durum.ayarlar;

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        const SizedBox(height: 12),

        // ------------------------------------------------------- tema
        const _Baslik('Görünüm'),
        SegmentedButton<ThemeMode>(
          segments: const [
            ButtonSegment(value: ThemeMode.system, label: Text('Sistem')),
            ButtonSegment(value: ThemeMode.light, label: Text('Açık')),
            ButtonSegment(value: ThemeMode.dark, label: Text('Koyu')),
          ],
          selected: {ayarlar.tema},
          showSelectedIcon: false,
          onSelectionChanged: (s) => ayarlar.temaAyarla(s.first),
        ),
        const SizedBox(height: 24),

        // -------------------------------------------- puanlama ağırlıkları
        const _Baslik('Puanlama ağırlıkları'),
        Text(
          'Puan, her ölçünün kategori ortalamasından sapmasının ağırlıklı '
          'toplamıdır. Ağırlıkları değiştirdiğinizde sıralama anında '
          'yeniden hesaplanır — internete çıkılmaz.',
          style: tema.textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        for (final metrik in varsayilanAgirliklar.keys)
          _AgirlikKaydiri(
            baslik: agirlikBasliklari[metrik] ?? metrik,
            deger: ayarlar.agirliklar[metrik] ?? 0,
            onDegisti: (v) => ayarlar.agirlikAyarla(metrik, v),
          ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Toplam: ${trSayi(ayarlar.agirlikToplami)}',
              style: tema.textTheme.bodySmall?.copyWith(
                color: (ayarlar.agirlikToplami - 1.0).abs() < 0.001
                    ? null
                    : tema.colorScheme.error,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (!ayarlar.agirliklarVarsayilan)
              TextButton(
                onPressed: ayarlar.agirliklariSifirla,
                child: const Text('Varsayılana dön'),
              ),
          ],
        ),
        if ((ayarlar.agirlikToplami - 1.0).abs() >= 0.001)
          Text(
            'Toplam 1,00 değil. Sıralama yine çalışır ama puanlar farklı '
            'kategoriler arasında karşılaştırılamaz hale gelir.',
            style: tema.textTheme.bodySmall
                ?.copyWith(color: tema.colorScheme.error),
          ),
        const SizedBox(height: 24),

        // ----------------------------------------------------- Claude
        const _Baslik('Claude bağlantısı (isteğe bağlı)'),
        Text(
          'Anahtar girmezseniz uygulamanın hiçbir özelliği kapanmaz. '
          'Girdiğinizde akıllı filtre sonuçları hakkında serbest soru '
          'sorabilirsiniz. Anahtar cihazın şifreli deposunda tutulur.',
          style: tema.textTheme.bodySmall,
        ),
        const SizedBox(height: 10),
        if (_yukleniyor)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(_anahtarVar ? Icons.key : Icons.key_off_outlined,
                color: _anahtarVar ? Colors.green.shade600 : null),
            title: Text(_anahtarVar ? 'Anahtar kayıtlı' : 'Anahtar yok'),
            subtitle: Text(
                _anahtarVar
                    ? 'Serbest soru sorma açık'
                    : 'Serbest soru sorma kapalı',
                style: tema.textTheme.bodySmall),
            trailing: TextButton(
              onPressed: () => _anahtarDialog(context),
              child: Text(_anahtarVar ? 'Değiştir' : 'Ekle'),
            ),
          ),
          if (_anahtarVar) ...[
            const SizedBox(height: 4),
            Builder(builder: (_) {
              // Liste sınandıysa gerçek modeller, sınanmadıysa yedek liste.
              final secenekler = _modeller != null
                  ? {for (final m in _modeller!) m.kimlik: m.ad}
                  : Map<String, String>.from(modelSecenekleri);
              // Kayıtlı model listede yoksa ekle; yoksa dropdown çöker.
              secenekler.putIfAbsent(_model, () => _model);
              return DropdownButtonFormField<String>(
                initialValue: _model,
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: 'Model',
                  helperText: _modeller == null
                      ? 'Sınanmadı — aşağıdaki düğmeye basın'
                      : 'Hesabınızın erişebildiği modeller',
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                items: [
                  for (final e in secenekler.entries)
                    DropdownMenuItem(
                        value: e.key,
                        child: Text(e.value,
                            overflow: TextOverflow.ellipsis,
                            style: tema.textTheme.bodySmall)),
                ],
                onChanged: (v) async {
                  if (v == null) return;
                  await _depo.modelYaz(v);
                  setState(() => _model = v);
                },
              );
            }),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _sinaniyor ? null : _sina,
              icon: _sinaniyor
                  ? const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.network_check),
              label: Text(_sinaniyor
                  ? 'Sınanıyor...'
                  : 'Bağlantıyı sına ve modelleri getir'),
            ),
            if (_sinamaBasarili != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.check_circle_outline,
                        size: 16, color: Colors.green.shade600),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(_sinamaBasarili!,
                          style: tema.textTheme.bodySmall
                              ?.copyWith(color: Colors.green.shade600)),
                    ),
                  ],
                ),
              ),
            if (_sinamaHatasi != null)
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: tema.colorScheme.errorContainer.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                // Sunucunun kendi mesajı burada görünür; kopyalanabilir
                // olması hatayı bildirmeyi kolaylaştırıyor.
                child: SelectableText(_sinamaHatasi!,
                    style: tema.textTheme.bodySmall),
              ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () async {
                await _depo.sil();
                await _yukle();
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Anahtar silindi.')),
                  );
                }
              },
              icon: const Icon(Icons.delete_outline),
              label: const Text('Anahtarı sil'),
            ),
          ],
        ],
        const SizedBox(height: 24),

        // ------------------------------------------------------- veri
        const _Baslik('Veri'),
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Veri adresi'),
          subtitle: Text(ayarlar.adres, style: tema.textTheme.bodySmall),
          trailing: TextButton(
            onPressed: () => _adresDialog(context, ayarlar),
            child: const Text('Değiştir'),
          ),
        ),
        if (durum.veri != null)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Veri tarihi'),
            subtitle: Text(
              '${durum.veri!.veriTarihi} · üretim: '
              '${durum.veri!.uretimZamani.replaceFirst("T", " ").split("+").first}',
              style: tema.textTheme.bodySmall,
            ),
          ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: FilledButton.tonalIcon(
                onPressed: () => durum.tazele(),
                icon: const Icon(Icons.refresh),
                label: const Text('Veriyi yenile'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () async {
                  await VeriKaynagi(adres: ayarlar.adres).onbellegiSil();
                  await durum.tazele();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Önbellek temizlendi.')),
                    );
                  }
                },
                icon: const Icon(Icons.delete_sweep_outlined),
                label: const Text('Önbelleği sil'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),

        const _Baslik('Hakkında'),
        Text(
          'Veriler TEFAS\'ın açık uçlarından günde bir kez toplanır ve hazır '
          'bir dosya olarak sunulur. Uygulama TEFAS\'a doğrudan bağlanmaz.\n\n'
          'Kategori bilgisi yatırım fonlarında TEFAS\'ın kendi sınıflamasından '
          'gelir. Emeklilik ve borsa yatırım fonlarında TEFAS kategori '
          'bilgisi vermediği için kategori fon adından çıkarılır; bu bir '
          'çıkarımdır, kesin bilgi değildir.',
          style: tema.textTheme.bodySmall,
        ),
        const SorumlulukNotu(),
      ],
    );
  }

  Future<void> _anahtarDialog(BuildContext context) async {
    final denetleyici = TextEditingController();
    final sonuc = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Anthropic API anahtarı'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'console.anthropic.com adresinden aldığınız anahtarı yapıştırın. '
              'Anahtar cihazın şifreli deposuna yazılır, başka hiçbir yere '
              'gönderilmez.',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: denetleyici,
              obscureText: true,
              autofocus: true,
              decoration: const InputDecoration(
                hintText: 'sk-ant-...',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c), child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.pop(c, denetleyici.text),
            child: const Text('Kaydet'),
          ),
        ],
      ),
    );
    if (sonuc != null) {
      await _depo.yaz(sonuc);
      await _yukle();
    }
  }

  Future<void> _adresDialog(BuildContext context, Ayarlar ayarlar) async {
    final denetleyici = TextEditingController(text: ayarlar.adres);
    final sonuc = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Veri adresi'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'fonlar.json ve gecmis/ klasörünün bulunduğu adres. '
              'Kendi toplayıcınızı çalıştırıyorsanız burayı değiştirin.',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: denetleyici,
              autofocus: true,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c), child: const Text('Vazgeç')),
          TextButton(
            onPressed: () => Navigator.pop(c, varsayilanAdres),
            child: const Text('Varsayılan'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, denetleyici.text),
            child: const Text('Kaydet'),
          ),
        ],
      ),
    );
    if (sonuc == null || !context.mounted) return;
    // Durumu await'ten ONCE yakala: await sonrasi context olmus olabilir.
    final durum = Kapsam.of(context);
    await ayarlar.adresAyarla(sonuc);
    await durum.tazele();
  }
}

class _Baslik extends StatelessWidget {
  final String metin;

  const _Baslik(this.metin);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(metin,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
      );
}

class _AgirlikKaydiri extends StatelessWidget {
  final String baslik;
  final double deger;
  final ValueChanged<double> onDegisti;

  const _AgirlikKaydiri({
    required this.baslik,
    required this.deger,
    required this.onDegisti,
  });

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(baslik, style: tema.textTheme.bodyMedium),
            Text(trSayi(deger),
                style: tema.textTheme.bodyMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ],
        ),
        Slider(
          value: deger.clamp(0.0, 1.0),
          max: 1.0,
          divisions: 20,
          label: trSayi(deger),
          onChanged: onDegisti,
        ),
      ],
    );
  }
}
