/// Kullanıcı tercihleri: tema, favoriler, veri adresi, puanlama ağırlıkları.
///
/// Hepsi cihazda kalır, hiçbir yere gönderilmez.
library;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'veri.dart' show varsayilanAdres;

/// Puanlamada kullanılan metrikler ve varsayılan ağırlıkları.
/// Toplayıcıdaki ayarlar.json ile aynı olmalı.
const Map<String, double> varsayilanAgirliklar = {
  'aylik_getiri': 0.35,
  'uc_aylik_getiri': 0.25,
  'haftalik_getiri': 0.20,
  'volatilite': 0.20,
};

const Map<String, String> agirlikBasliklari = {
  'aylik_getiri': 'Aylık getiri',
  'uc_aylik_getiri': '3 aylık getiri',
  'haftalik_getiri': 'Haftalık getiri',
  'volatilite': 'Düşük oynaklık',
};

class Ayarlar extends ChangeNotifier {
  static const _kTema = 'tema';
  static const _kFavoriler = 'favoriler';
  static const _kAdres = 'veri_adresi';
  static const _kAgirlik = 'agirlik_';

  SharedPreferences? _depo;

  ThemeMode _tema = ThemeMode.system;
  Set<String> _favoriler = {};
  String _adres = varsayilanAdres;
  Map<String, double> _agirliklar = Map.of(varsayilanAgirliklar);

  ThemeMode get tema => _tema;
  Set<String> get favoriler => _favoriler;
  String get adres => _adres;
  Map<String, double> get agirliklar => Map.unmodifiable(_agirliklar);

  bool get agirliklarVarsayilan {
    for (final e in varsayilanAgirliklar.entries) {
      if ((_agirliklar[e.key] ?? 0) != e.value) return false;
    }
    return true;
  }

  /// Ağırlıkların toplamı. 1'den saparsa kullanıcıya söylüyoruz.
  double get agirlikToplami =>
      _agirliklar.values.fold(0.0, (a, b) => a + b);

  Future<void> baslat() async {
    _depo = await SharedPreferences.getInstance();
    final t = _depo!.getString(_kTema);
    _tema = switch (t) {
      'acik' => ThemeMode.light,
      'koyu' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
    _favoriler = (_depo!.getStringList(_kFavoriler) ?? const []).toSet();
    _adres = _depo!.getString(_kAdres) ?? varsayilanAdres;
    _agirliklar = {
      for (final k in varsayilanAgirliklar.keys)
        k: _depo!.getDouble('$_kAgirlik$k') ?? varsayilanAgirliklar[k]!,
    };
    notifyListeners();
  }

  Future<void> temaAyarla(ThemeMode m) async {
    _tema = m;
    await _depo?.setString(_kTema, switch (m) {
      ThemeMode.light => 'acik',
      ThemeMode.dark => 'koyu',
      ThemeMode.system => 'sistem',
    });
    notifyListeners();
  }

  bool favoriMi(String kod) => _favoriler.contains(kod);

  Future<void> favoriDegistir(String kod) async {
    if (!_favoriler.remove(kod)) _favoriler.add(kod);
    await _depo?.setStringList(_kFavoriler, _favoriler.toList()..sort());
    notifyListeners();
  }

  Future<void> adresAyarla(String yeni) async {
    _adres = yeni.trim().isEmpty ? varsayilanAdres : yeni.trim();
    await _depo?.setString(_kAdres, _adres);
    notifyListeners();
  }

  Future<void> agirlikAyarla(String metrik, double deger) async {
    _agirliklar[metrik] = deger;
    await _depo?.setDouble('$_kAgirlik$metrik', deger);
    notifyListeners();
  }

  Future<void> agirliklariSifirla() async {
    _agirliklar = Map.of(varsayilanAgirliklar);
    for (final e in varsayilanAgirliklar.entries) {
      await _depo?.setDouble('$_kAgirlik${e.key}', e.value);
    }
    notifyListeners();
  }
}
