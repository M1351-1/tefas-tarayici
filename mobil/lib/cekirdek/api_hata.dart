/// Anthropic API hatalarının Türkçeye çevrilmesi.
///
/// Ayrı dosyada olmasının sebebi teknik: `danisman.dart` Flutter'a bağımlı
/// (güvenli depo, http). Bu mantığın Flutter'a ihtiyacı yok ve burada
/// durursa `dart test` ile koşulabiliyor — bu makinede Windows Uygulama
/// Denetimi `flutter test`'i engellediği için tek test yolu bu.
library;

import 'dart:convert';

class DanismanHatasi implements Exception {
  final String mesaj;
  final String oneri;

  const DanismanHatasi(this.mesaj, [this.oneri = '']);

  @override
  String toString() => oneri.isEmpty ? mesaj : '$mesaj $oneri';
}

/// API'nin KENDİ hata mesajını çıkarır.
///
/// Bu fonksiyon bir hatanın bedeliyle yazıldı: önce HTTP 400 için
/// "seçili model adı yanlış olabilir" diye SABİT bir tahmin
/// gösteriliyordu. Model adı doğruydu, sorun başkaydı ve kullanıcı
/// ayarlarda boşuna model değiştirmeye uğraştı. Sunucu zaten ne olduğunu
/// söylüyor; tahmin etmek yerine onu göstermek gerekiyor.
///
/// Yanıt gövdesi şu biçimde:
///   {"type":"error","error":{"type":"...","message":"..."}}
DanismanHatasi hataCevir(int kod, List<int> govde) {
  String? apiMesaji;
  try {
    final j = jsonDecode(utf8.decode(govde)) as Map<String, dynamic>;
    final h = j['error'];
    if (h is Map && h['message'] is String) apiMesaji = h['message'] as String;
  } catch (_) {
    // Gövde JSON değilse aşağıdaki genel metne düşeriz.
  }

  final baslik = switch (kod) {
    401 => 'API anahtarı kabul edilmedi.',
    403 => 'Bu anahtarın yetkisi yok.',
    429 => 'İstek sınırına takıldınız.',
    400 => 'Claude isteği reddetti.',
    >= 500 => 'Anthropic sunucusunda geçici sorun.',
    _ => 'Claude $kod döndürdü.',
  };

  var oneri = switch (kod) {
    401 => 'Ayarlardan anahtarınızı kontrol edin.',
    402 || 403 => 'Hesabınızda bakiye olduğundan emin olun.',
    429 => 'Biraz bekleyip tekrar deneyin.',
    >= 500 => 'Birkaç dakika sonra tekrar deneyin.',
    _ => '',
  };

  // Çalışma alanı kimliği eksikse ne yapılacağını Türkçe söyle.
  //
  // Sunucunun mesajı doğru ama İngilizce ve nereden alınacağını
  // söylemiyor. Bu hata, kimliğe bağlı (identity-linked) anahtarlarda
  // çıkıyor: anahtar birden fazla çalışma alanına erişebildiği için
  // hangisinde işlem yapıldığını ayrıca bildirmek gerekiyor.
  if (apiMesaji != null && calismaAlaniGerekiyor(apiMesaji)) {
    oneri = 'Anahtarınız hangi çalışma alanında işlem yapacağını da '
        'istiyor. Ayarlar → "Çalışma alanı kimliği" alanına '
        'platform.claude.com/settings/workspaces adresindeki '
        'wrkspc_ ile başlayan değeri girin.';
  }

  // Sunucunun kendi mesajı varsa onu ekle: asıl teşhis orada.
  return DanismanHatasi(
      baslik, apiMesaji != null ? '$oneri\n\nSunucu: $apiMesaji'.trim() : oneri);
}

/// Hata mesajı "çalışma alanı kimliği lazım" diyor mu?
bool calismaAlaniGerekiyor(String apiMesaji) {
  final m = apiMesaji.toLowerCase();
  return m.contains('workspace') && m.contains('required');
}
