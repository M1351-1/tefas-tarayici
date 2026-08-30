# -*- coding: utf-8 -*-
"""Portfoy varlik dagilimi.

ETIKETLER TAHMIN DEGIL. Asagidaki sozluk TEFAS'in kendi sayfasindan
alindi (sayfa HTML'ine gomulu kolon tanimlarindan). Alan kodlari
("yyf", "kmkks", "ybosb"...) kendi baslarina okunamaz; tahmin etmeye
kalksaydik kullaniciya uydurma varlik sinifi adlari gosterirdik.

Dagilim verisi fiyat gecmisinden AYRI cekilir ve sadece EN SON gun icin
tutulur: gecmise donuk dagilim ne uygulamada gosteriliyor ne de puanlamaya
giriyor, her gun icin saklamak bosuna yer kaplardi.
"""
from __future__ import annotations

# TEFAS'in resmi kolon adlari. "(%)" son eki burada kirpildi; sayilar
# zaten yuzde olarak gosteriliyor.
ETIKETLER = {
    "hs": "Hisse Senedi",
    "yhs": "Yabancı Hisse Senedi",
    "dt": "Devlet Tahvili",
    "hb": "Hazine Bonosu",
    "fb": "Finansman Bonosu",
    "bb": "Banka Bonosu",
    "ost": "Özel Sektör Tahvili",
    "eut": "Eurobond",
    "db": "Döviz Ödemeli Bono",
    "dot": "Dövize Ödemeli Tahvil",
    "vdm": "Varlığa Dayalı Menkul Kıymetler",
    "kba": "Kamu Dış Borçlanma Araçları",
    "kibd": "Döviz Cinsi Kamu İç Borçlanma Araçları",
    "osdb": "Özel Sektör Dış Borçlanma Araçları",
    "yba": "Yabancı Borçlanma Aracı",
    "ybkb": "Yabancı Kamu Borçlanma Araçları",
    "ybosb": "Yabancı Özel Sektör Borçlanma Araçları",
    "ymk": "Yabancı Menkul Kıymet",
    "kks": "Kamu Kira Sertifikaları",
    "kkstl": "Kamu Kira Sertifikaları (TL)",
    "kksd": "Kamu Kira Sertifikaları (Döviz)",
    "kksyd": "Kamu Yurt Dışı Kira Sertifikaları",
    "osks": "Özel Sektör Kira Sertifikaları",
    "oksyd": "Özel Sektör Yurt Dışı Kira Sertifikaları",
    "vm": "Vadeli Mevduat",
    "vmtl": "Mevduat (TL)",
    "vmd": "Mevduat (Döviz)",
    "vmau": "Mevduat (Altın)",
    "kh": "Katılım Hesabı",
    "khtl": "Katılma Hesabı (TL)",
    "khd": "Katılma Hesabı (Döviz)",
    "khau": "Katılma Hesabı (Altın)",
    "r": "Repo",
    "tr": "Ters-Repo",
    "tpp": "Takasbank Para Piyasası",
    "bpp": "Borsa İstanbul Para Piyasası",
    "btaa": "BİST Taahhütlü İşlem Pazarı Alım",
    "btas": "BİST Taahhütlü İşlem Pazarı Satım",
    "km": "Kıymetli Madenler",
    "kmbyf": "Kıymetli Madenler Cinsinden BYF",
    "kmkba": "Kıymetli Madenler Cinsinden Kamu Borçlanma Araçları",
    "kmkks": "Kıymetli Madenler Cinsinden Kamu Kira Sertifikaları",
    "byf": "Borsa Yatırım Fonları Katılma Payları",
    "ybyf": "Yabancı Borsa Yatırım Fonları",
    "yyf": "Yatırım Fonları Katılma Payları",
    "fkb": "Fon Katılma Belgesi",
    "gykb": "Gayrimenkul Yatırım Fonları Katılma Payları",
    "gsykb": "Girişim Sermayesi Yatırım Fonları Katılma Payları",
    "gyy": "Gayrimenkul Yatırımları",
    "gsyy": "Girişim Sermayesi Yatırımları",
    "gas": "Gayrimenkul Sertifikası",
    "t": "Türev Araçları",
    "vint": "Vadeli İşlemler Nakit Teminatları",
    "d": "Diğer",
}

# Yanitta gelen ama varlik kalemi OLMAYAN alanlar.
VARLIK_DISI = {"fonKodu", "fonUnvan", "tarih", "rn", "fonTipi", "profit",
               "rate", "return", "size"}

# Bu esigin altindaki kalemler gosterilmez: %0,004'luk bir kalem grafikte
# gorunmez ama listeyi uzatir.
ASGARI_YUZDE = 0.01


def ayikla(satir):
    """API satirindan (kod, etiket, yuzde) listesi cikarir, buyukten kucuge.

    Taninmayan bir alan kodu gelirse ATILMAZ, kodun kendisi etiket olarak
    kullanilir: TEFAS yeni bir varlik sinifi eklerse sessizce kaybolmasin,
    gorulsun ve buraya eklensin.
    """
    kalemler = []
    for kod, deger in satir.items():
        if kod in VARLIK_DISI:
            continue
        if not isinstance(deger, (int, float)) or deger is None:
            continue
        if deger < ASGARI_YUZDE:
            continue
        kalemler.append((kod, ETIKETLER.get(kod, kod), float(deger)))
    kalemler.sort(key=lambda x: -x[2])
    return kalemler


def ozetle(kalemler, azami=7):
    """Grafik icin sadelestirir: en buyuk `azami` kalem + "Diğer".

    Kendi varlik sinifi taksonomimizi UYDURMUYORUZ. 40 kalemi gruplamak
    icin "bunlar aslinda tahvil sayilir" turu kararlar vermek gerekirdi;
    yanlis gruplama, hic gruplamamaktan kotudur. Bunun yerine en buyuk
    kalemleri oldugu gibi gosterip kalanini tek satirda topluyoruz.
    """
    if len(kalemler) <= azami:
        return list(kalemler)
    bas = list(kalemler[:azami])
    kalan = kalemler[azami:]
    toplam = sum(x[2] for x in kalan)
    if toplam >= ASGARI_YUZDE:
        bas.append(("_diger", "Diğer (%d kalem)" % len(kalan), toplam))
    return bas
