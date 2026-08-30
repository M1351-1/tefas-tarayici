/// TEFAS Fon Tarayıcı — giriş noktası.
///
/// Bu uygulama yatırım danışmanlığı değildir; TEFAS'ın yayımladığı geçmiş
/// fiyatlardan istatistik hesaplayan bir karşılaştırma aracıdır.
library;

import 'package:flutter/material.dart';

import 'arayuz/ana_kabuk.dart';
import 'cekirdek/ayarlar.dart';
import 'cekirdek/durum.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final ayarlar = Ayarlar();
  await ayarlar.baslat();
  final durum = UygulamaDurumu(ayarlar);
  // Beklemiyoruz: arayüz hemen açılsın, veri gelince kendini tazeler.
  durum.baslat();
  runApp(Uygulama(durum: durum));
}

class Uygulama extends StatelessWidget {
  final UygulamaDurumu durum;

  const Uygulama({super.key, required this.durum});

  ThemeData _tema(Brightness parlaklik) {
    final renkler = ColorScheme.fromSeed(
      seedColor: const Color(0xFF00695C), // koyu yeşil — nötr, finans
      brightness: parlaklik,
    );
    return ThemeData(useMaterial3: true, colorScheme: renkler);
  }

  @override
  Widget build(BuildContext context) {
    // Kapsam MaterialApp'in USTUNDE olmak ZORUNDA.
    //
    // Önce `home: Kapsam(child: AnaKabuk())` yazılmıştı ve bu, açılış
    // ekranı dışındaki her sayfayı bozuyordu: Navigator da MaterialApp'in
    // içinde olduğu için `push` edilen sayfa Kapsam'ın altında değil,
    // KARDEŞİ oluyor. Fon detayında `Kapsam.of(context)` null dönüyor,
    // release derlemesinde assert'ler silindiği için `!` patlıyor ve
    // kullanıcı boş gri bir ekran görüyordu.
    //
    // Kapsam yukarı alınınca Navigator ve bütün rotalar onun altında kalır.
    return Kapsam(
      durum: durum,
      child: ListenableBuilder(
        listenable: durum.ayarlar,
        builder: (context, _) => MaterialApp(
          title: 'TEFAS Fon Tarayıcı',
          debugShowCheckedModeBanner: false,
          theme: _tema(Brightness.light),
          darkTheme: _tema(Brightness.dark),
          themeMode: durum.ayarlar.tema,
          home: const AnaKabuk(),
        ),
      ),
    );
  }
}
