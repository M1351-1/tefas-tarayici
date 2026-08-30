/// Claude'a soru sorma ekranı.
///
/// Anahtar yoksa ekran kapanmaz; ne olduğunu ve nasıl açılacağını anlatır.
library;

import 'package:flutter/material.dart';

import '../cekirdek/danisman.dart';
import '../cekirdek/modeller.dart';
import '../cekirdek/secici.dart';
import 'ayarlar_sayfasi.dart';

/// Kullanıcıya hazır sunulan sorular — boş ekrana bakıp ne soracağını
/// bilememe sorununu çözer.
const _hazirSorular = [
  'Bu listedeki fonların riskleri nasıl farklılaşıyor?',
  'İlk üç fonu getiri ve oynaklık açısından karşılaştır.',
  'Bu fonlardan hangilerinin yükselişi sadece son aya sıkışmış?',
  'Listedeki en düşük oynaklıklı fon hangisi ve bedeli ne olmuş?',
];

class _Mesaj {
  final String rol; // 'user' | 'assistant'
  final String metin;

  const _Mesaj(this.rol, this.metin);
}

class DanismanSayfasi extends StatefulWidget {
  final List<Fon> fonlar;
  final Profil? profil;

  const DanismanSayfasi({super.key, required this.fonlar, this.profil});

  @override
  State<DanismanSayfasi> createState() => _DanismanSayfasiDurumu();
}

class _DanismanSayfasiDurumu extends State<DanismanSayfasi> {
  final _depo = AnahtarDeposu();
  final _girdi = TextEditingController();
  final _kaydirma = ScrollController();

  String? _anahtar;
  String _model = varsayilanModel;
  bool _hazirlaniyor = true;
  bool _bekleniyor = false;
  String? _hata;
  final List<_Mesaj> _mesajlar = [];

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    final a = await _depo.oku();
    final m = await _depo.modelOku();
    if (mounted) {
      setState(() {
        _anahtar = a;
        _model = m;
        _hazirlaniyor = false;
      });
    }
  }

  @override
  void dispose() {
    _girdi.dispose();
    _kaydirma.dispose();
    super.dispose();
  }

  Future<void> _sor(String soru) async {
    final anahtar = _anahtar;
    if (anahtar == null || anahtar.isEmpty || soru.trim().isEmpty) return;

    setState(() {
      _mesajlar.add(_Mesaj('user', soru.trim()));
      _bekleniyor = true;
      _hata = null;
      _girdi.clear();
    });
    _asagiKaydir();

    final baglam = StringBuffer();
    if (widget.profil != null) {
      baglam.writeln('KULLANICI PROFİLİ: ${profilMetni(widget.profil!)}');
      baglam.writeln();
    }
    baglam.writeln('FON TABLOSU:');
    baglam.write(tabloYap(widget.fonlar));

    try {
      final yanit = await Danisman(anahtar: anahtar, model: _model).sor(
        soru: soru.trim(),
        baglam: baglam.toString(),
        // Önceki tur soru-cevabı bağlam olarak taşı ki takip sorusu
        // sorulabilsin. Sadece son iki turu taşıyoruz: uzun geçmiş her
        // istekte tekrar ücretlendirilir.
        gecmis: _mesajlar
            .take(_mesajlar.length - 1)
            .toList()
            .reversed
            .take(4)
            .toList()
            .reversed
            .map((m) => (rol: m.rol, metin: m.metin))
            .toList(),
      );
      if (mounted) {
        setState(() {
          _mesajlar.add(_Mesaj('assistant', yanit));
          _bekleniyor = false;
        });
        _asagiKaydir();
      }
    } on DanismanHatasi catch (e) {
      if (mounted) {
        setState(() {
          _bekleniyor = false;
          _hata = e.oneri.isEmpty ? e.mesaj : '${e.mesaj} ${e.oneri}';
        });
      }
    }
  }

  void _asagiKaydir() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_kaydirma.hasClients) {
        _kaydirma.animateTo(
          _kaydirma.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);

    if (_hazirlaniyor) {
      return Scaffold(
        appBar: AppBar(title: const Text('Claude\'a sor')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_anahtar == null || _anahtar!.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Claude\'a sor')),
        body: _AnahtarYok(
          onAyarlar: () async {
            await Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => const AyarlarSayfasi(tekBasina: true),
            ));
            _yukle();
          },
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Claude\'a sor'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(22),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 6, left: 16, right: 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '${widget.fonlar.length} fon gönderiliyor · '
                '${modelSecenekleri[_model]?.split(" — ").first ?? _model}',
                style: tema.textTheme.bodySmall,
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              controller: _kaydirma,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                const SizedBox(height: 12),
                _GizlilikNotu(fonSayisi: widget.fonlar.length),
                const SizedBox(height: 16),
                if (_mesajlar.isEmpty) ...[
                  Text('Örnek sorular',
                      style: tema.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  for (final s in _hazirSorular)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: ActionChip(
                        label: Text(s, style: tema.textTheme.bodySmall),
                        onPressed: () => _sor(s),
                      ),
                    ),
                ],
                for (final m in _mesajlar) _Balon(mesaj: m),
                if (_bekleniyor)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                if (_hata != null)
                  Container(
                    margin: const EdgeInsets.symmetric(vertical: 12),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: tema.colorScheme.errorContainer
                          .withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    // Seçilebilir: sunucunun kendi hata mesajı burada
                    // görünüyor ve kopyalanabilmesi teşhisi kolaylaştırıyor.
                    child: SelectableText(_hata!,
                        style: tema.textTheme.bodySmall),
                  ),
                const SizedBox(height: 12),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _girdi,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      onSubmitted: _bekleniyor ? null : _sor,
                      decoration: const InputDecoration(
                        hintText: 'Sorunuzu yazın...',
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed:
                        _bekleniyor ? null : () => _sor(_girdi.text),
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GizlilikNotu extends StatelessWidget {
  final int fonSayisi;

  const _GizlilikNotu({required this.fonSayisi});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tema.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.lock_outline, size: 18,
              color: tema.colorScheme.onSurfaceVariant),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Anthropic sunucusuna sadece sorunuz ve ekrandaki $fonSayisi '
              'fonun TEFAS\'tan gelen kamuya açık sayıları gidiyor. API '
              'anahtarınız, favorileriniz ve cihaz bilgileriniz '
              'gönderilmiyor. Her soru hesabınızdan ücretlendirilir.',
              style: tema.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _Balon extends StatelessWidget {
  final _Mesaj mesaj;

  const _Balon({required this.mesaj});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final benim = mesaj.rol == 'user';
    return Align(
      alignment: benim ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.86),
        decoration: BoxDecoration(
          color: benim
              ? tema.colorScheme.primaryContainer
              : tema.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: SelectableText(
          mesaj.metin,
          style: tema.textTheme.bodyMedium,
        ),
      ),
    );
  }
}

class _AnahtarYok extends StatelessWidget {
  final VoidCallback onAyarlar;

  const _AnahtarYok({required this.onAyarlar});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Icon(Icons.key_off_outlined,
            size: 52, color: tema.colorScheme.onSurfaceVariant),
        const SizedBox(height: 16),
        Text('Claude bağlantısı kapalı',
            textAlign: TextAlign.center,
            style: tema.textTheme.titleMedium),
        const SizedBox(height: 12),
        Text(
          'Bu özellik isteğe bağlıdır. Uygulamanın geri kalanı — sıralama, '
          'akıllı filtre, grafikler — anahtar olmadan tam çalışır.\n\n'
          'Serbest soru sormak isterseniz kendi Anthropic API anahtarınızı '
          'girmeniz gerekir. Anahtar cihazınızın şifreli deposunda saklanır '
          've sadece Anthropic\'e gönderilir. Sorular hesabınızdan '
          'ücretlendirilir.',
          style: tema.textTheme.bodyMedium,
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: onAyarlar,
          icon: const Icon(Icons.settings),
          label: const Text('Ayarlara git'),
        ),
      ],
    );
  }
}
