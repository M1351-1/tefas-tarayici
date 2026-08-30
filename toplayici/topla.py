# -*- coding: utf-8 -*-
"""Ana akis.

Kullanim:
    python topla.py dolum     Ilk kurulum: 400 gunluk gecmis + kategoriler
    python topla.py gunluk    Gunluk calisma: sadece eksik gunleri ceker
    python topla.py kategori  Sadece kategori eslemesini yeniler (haftalik)
    python topla.py dagilim   Sadece portfoy varlik dagilimini ceker (3 istek)
    python topla.py hesapla   Aga hic cikmadan metrik/puan/JSON yeniden uretir

'hesapla' ayri duruyor cunku ayarlar.json'daki agirliklari degistirdiginde
TEFAS'i tekrar yormaya gerek yok: veri zaten veritabaninda.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "toplayici"))

import dagilim as _dag
import istemci as _ist
import kategoriler as _kat
import metrikler as _met
import puanlama as _puan
import uret as _uret
import veritabani as _vt

VT_YOLU = KOK / "data" / "fon_gecmis.db"
JSON_YOLU = KOK / "data" / "fonlar.json"
GECMIS_KLASORU = KOK / "data" / "gecmis"
AYAR_YOLU = KOK / "toplayici" / "ayarlar.json"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def yaz(s=""):
    print(s, flush=True)


def ayarlari_oku():
    with open(AYAR_YOLU, encoding="utf-8") as d:
        a = json.load(d)
    sorunlar = _puan.agirlik_kontrolu(a)
    if sorunlar:
        yaz("AYAR HATASI:")
        for s in sorunlar:
            yaz("  - " + s)
        sys.exit(1)
    return a


# --------------------------------------------------------------- kategoriler

def kategorileri_esle(ist, depo, gun):
    """Fon -> kategori haritasini kurar.

    Kategori bilgisi fiyat yanitinda gelmiyor. Ogrenmenin tek yolu her
    kategori icin ayri sorgu atip donen kodlari o kategoriyle etiketlemek.
    Bu yuzden pahali (tip x kategori istek), ama kategoriler nadiren
    degistigi icin haftada bir yenilemek yeterli.

    DIKKAT: sfonTurKod filtresi sadece YATIRIM fonlarinda calisiyor.
    Emeklilik fonlarinda TEFAS filtreyi sessizce YOK SAYIP butun fonlari
    donduruyor. Bu tespit edilmezse her emeklilik fonu, en son islenen
    kategorinin etiketini alir ve kategori bazli siralama tamamen curur.
    Asagidaki 'filtre calisiyor mu' kontrolu tam olarak bunun icin var.
    """
    yaz("Kategoriler aliniyor...")
    kategoriler = ist.kategorileri_getir()
    yaz("  %d semsiye fon turu bulundu" % len(kategoriler))

    esleme = {}
    for tip in _ist.FON_TIPLERI:
        # Once filtresiz toplami ogren: filtreli sonuc buna esitse
        # filtre yok sayilmis demektir.
        toplam = len(ist.kategorideki_fonlar(tip, None, gun))
        yaz("  %-4s filtresiz toplam: %d fon" % (tip, toplam))

        tip_esleme = {}
        yok_sayildi = 0
        for kod, ad in kategoriler:
            try:
                fonlar = ist.kategorideki_fonlar(tip, kod, gun)
            except _ist.TefasHatasi as e:
                yaz("  ! %s / %s atlandi: %s" % (tip, ad, e.mesaj))
                continue
            if not fonlar:
                continue
            if toplam and len(fonlar) == toplam:
                # Filtre calissa bu kategoride butun fonlar cikmazdi.
                yok_sayildi += 1
                yaz("  %-4s %-38s FILTRE YOK SAYILDI (%d)"
                    % (tip, ad[:38], len(fonlar)))
                if yok_sayildi >= 2:
                    # Iki kategoride ust uste ayni sonuc: filtre bu tipte
                    # calismyor. Kalan 10 kategoriyi sormak bos yere 10
                    # istek ve ~2 dakika harcamak olur.
                    yaz("  %-4s kalan kategoriler atlandi (filtre yok)" % tip)
                    break
                continue
            for f in fonlar:
                tip_esleme[f] = (kod, ad)
            yaz("  %-4s %-38s %4d fon" % (tip, ad[:38], len(fonlar)))

        if yok_sayildi >= 2:
            yaz("  %-4s KATEGORI ESLEMESI YAPILAMADI: TEFAS bu fon tipinde "
                "kategori filtresini desteklemiyor (%d kategoride ayni "
                "sonuc dondu). Bu tipteki fonlar 'Bilinmiyor' kalacak."
                % (tip, yok_sayildi))
            continue

        esleme.update(tip_esleme)
        yaz("  %-4s toplam %d fon eslendi" % (tip, len(tip_esleme)))

    zaman = datetime.now().isoformat(timespec="seconds")
    depo.kategori_temizle()
    depo.kategori_yaz(esleme, zaman)
    yaz("Kategori haritasi kaydedildi: %d fon" % len(esleme))
    return esleme


# ------------------------------------------------------------------- cekim

def dagilimlari_cek(ist, depo, gun):
    """Portfoy varlik dagilimini ceker (fon tipi basina 1 istek).

    Ucuz: sadece en son gun icin, tarih araligi yok. Uc fon tipi = uc istek.
    """
    yaz("Portfoy dagilimlari cekiliyor...")
    hepsi = {}
    for tip in _ist.FON_TIPLERI:
        try:
            ham = ist.dagilimlar(tip, gun)
        except _ist.TefasHatasi as e:
            yaz("  ! %s atlandi: %s" % (tip, e.mesaj))
            continue
        for kod, satir in ham.items():
            kalemler = _dag.ayikla(satir)
            if kalemler:
                hepsi[kod] = kalemler
        yaz("  %-4s %d fon" % (tip, len(ham)))
    n = depo.dagilim_yaz(hepsi, str(gun))
    yaz("  %d fon icin %d kalem kaydedildi" % (len(hepsi), n))
    return hepsi


def fiyatlari_cek(ist, depo, baslangic, bitis):
    toplam = 0
    for tip in _ist.FON_TIPLERI:
        yaz("  %s (%s) cekiliyor..." % (tip, _ist.FON_TIPI_ADI[tip]))
        kayitlar = ist.fiyatlar(tip, baslangic, bitis)
        n = depo.fiyat_yaz(kayitlar)
        depo.cekim_kaydet(datetime.now().isoformat(timespec="seconds"),
                          tip, baslangic, bitis, n)
        yaz("  %s: %d kayit yazildi" % (tip, n))
        toplam += n
    return toplam


# ---------------------------------------------------------------- hesaplama

def hesapla_ve_yaz(depo, ayarlar):
    yaz("Metrikler hesaplaniyor...")
    seriler = depo.tum_seriler()
    kategori = depo.kategori_haritasi()
    son_gozlemler = depo.fon_listesi()

    fonlar = []
    for g in son_gozlemler:
        kod = g["fon_kodu"]
        seri = seriler.get(kod) or []
        f = dict(g)
        f.update(_met.hesapla(seri))
        ad, kaynak = _kat.kategori_belirle(kod, g.get("fon_adi"), kategori)
        f["kategori_ad"] = ad
        f["kategori_kaynak"] = kaynak
        f["katilim"] = _kat.katilim_mi(g.get("fon_adi"))
        f["fon_tipi_ad"] = _ist.FON_TIPI_ADI.get(g["fon_tipi"], g["fon_tipi"])
        fonlar.append(f)

    kaynaklar = {}
    for f in fonlar:
        kaynaklar[f["kategori_kaynak"]] = kaynaklar.get(f["kategori_kaynak"], 0) + 1
    yaz("  kategori kaynagi: " + ", ".join(
        "%s=%d" % (k, v) for k, v in sorted(kaynaklar.items())))
    kategorisiz = kaynaklar.get("yok", 0)
    if kategorisiz:
        yaz("  UYARI: %d fonun kategorisi belirlenemedi" % kategorisiz)

    uygun, elenen = _puan.ele(fonlar, ayarlar)
    yaz("  %d fon uygun, %d fon elendi" % (len(uygun), len(elenen)))

    puanlanan, puanlanmayan = _puan.puanla(uygun, ayarlar)
    yaz("  %d fon puanlandi, %d fon puanlanmadi (kategori kucuk)"
        % (len(puanlanan), len(puanlanmayan)))

    veri_tarihi = depo.en_son_tarih()
    boyut = _uret.ozet_yaz(JSON_YOLU, puanlanan, puanlanmayan, elenen,
                           ayarlar, veri_tarihi)
    yaz("  fonlar.json yazildi: %.2f MB" % (boyut / 1024 / 1024))

    kodlar = [f["fon_kodu"] for f in puanlanan + puanlanmayan]
    dagilimlar = depo.dagilim_haritasi()
    if dagilimlar:
        yaz("  %d fonun varlik dagilimi var" % len(dagilimlar))
    adet, gboyut = _uret.gecmis_yaz(GECMIS_KLASORU, seriler, kodlar,
                                    gun_siniri=ayarlar["grafik_gun"],
                                    dagilimlar=dagilimlar)
    yaz("  gecmis/: %d dosya, %.2f MB (ortalama %.1f KB)"
        % (adet, gboyut / 1024 / 1024, gboyut / adet / 1024 if adet else 0))
    return puanlanan, puanlanmayan, elenen


# ----------------------------------------------------------------- akislar

def dolum():
    ayarlar = ayarlari_oku()
    bitis = date.today()
    baslangic = bitis - timedelta(days=ayarlar["gecmis_gun"])
    yaz("=" * 62)
    yaz("ILK DOLUM  %s - %s  (%d gun)"
        % (baslangic, bitis, ayarlar["gecmis_gun"]))
    yaz("TEFAS dakikada 6 istek kabul ediyor; bu islem ~15 dakika surer.")
    yaz("=" * 62)
    basla = time.time()

    ist = _ist.Istemci()
    with _vt.Depo(VT_YOLU) as depo:
        # Kategori eslemesi icin dun degil, son is gunu lazim: hafta sonu
        # sorarsan bos doner.
        ref = bitis
        for _ in range(7):
            if ref.weekday() < 5:
                break
            ref -= timedelta(days=1)
        kategorileri_esle(ist, depo, ref - timedelta(days=1))

        yaz()
        yaz("Fiyat gecmisi cekiliyor...")
        fiyatlari_cek(ist, depo, baslangic, bitis)

        yaz()
        dagilimlari_cek(ist, depo, ref - timedelta(days=1))

        yaz()
        yaz("Veritabani: %d fon, %d kayit"
            % (depo.fon_sayisi(), depo.kayit_sayisi()))
        yaz()
        hesapla_ve_yaz(depo, ayarlar)

    yaz()
    yaz("BITTI. %d istek, %.1f dakika."
        % (ist.istek_sayisi, (time.time() - basla) / 60))


def gunluk():
    ayarlar = ayarlari_oku()
    ist = _ist.Istemci()
    with _vt.Depo(VT_YOLU) as depo:
        son = depo.en_son_tarih()
        if son is None:
            yaz("Veritabani bos. Once 'python topla.py dolum' calistir.")
            sys.exit(1)
        # Son gunu tekrar cekiyoruz: TEFAS ayni gunun kisi sayisini
        # aksam guncelliyor, ilk cektigimiz deger eksik olabilir.
        baslangic = datetime.strptime(son, "%Y-%m-%d").date()
        bitis = date.today()
        yaz("GUNLUK GUNCELLEME  %s - %s" % (baslangic, bitis))
        if baslangic > bitis:
            yaz("Veri zaten guncel.")
        else:
            fiyatlari_cek(ist, depo, baslangic, bitis)

        # Dagilim her gun tazelenir: fon portfoyu gunluk degisir ve
        # sadece son gun tutuldugu icin bayat kalmasi anlamsiz olur.
        yaz()
        son_isgunu = date.today()
        for _ in range(7):
            if son_isgunu.weekday() < 5:
                break
            son_isgunu -= timedelta(days=1)
        dagilimlari_cek(ist, depo, son_isgunu - timedelta(days=1))

        yaz()
        hesapla_ve_yaz(depo, ayarlar)
    yaz("BITTI. %d istek." % ist.istek_sayisi)


def kategori_yenile():
    """Sadece kategori eslemesini yeniler, fiyat cekmez.

    Kategoriler nadiren degisir; haftada bir bu komut yeter. Ayrica
    esleme mantigi degistiginde butun gecmisi tekrar cekmeden
    duzeltebilmek icin ayri duruyor.
    """
    ayarlar = ayarlari_oku()
    ist = _ist.Istemci()
    with _vt.Depo(VT_YOLU) as depo:
        ref = date.today()
        for _ in range(7):
            if ref.weekday() < 5:
                break
            ref -= timedelta(days=1)
        kategorileri_esle(ist, depo, ref - timedelta(days=1))
        yaz()
        hesapla_ve_yaz(depo, ayarlar)
    yaz("BITTI. %d istek." % ist.istek_sayisi)


def dagilim_yenile():
    """Sadece portfoy dagilimini ceker (3 istek), fiyat cekmez."""
    ayarlar = ayarlari_oku()
    ist = _ist.Istemci()
    with _vt.Depo(VT_YOLU) as depo:
        gun = date.today()
        for _ in range(7):
            if gun.weekday() < 5:
                break
            gun -= timedelta(days=1)
        dagilimlari_cek(ist, depo, gun - timedelta(days=1))
        yaz()
        hesapla_ve_yaz(depo, ayarlar)
    yaz("BITTI. %d istek." % ist.istek_sayisi)


def hesapla_sadece():
    ayarlar = ayarlari_oku()
    with _vt.Depo(VT_YOLU) as depo:
        if depo.kayit_sayisi() == 0:
            yaz("Veritabani bos. Once 'python topla.py dolum' calistir.")
            sys.exit(1)
        yaz("Aga cikilmiyor, mevcut veriden yeniden hesaplaniyor.")
        hesapla_ve_yaz(depo, ayarlar)


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    if komut == "dolum":
        dolum()
    elif komut == "gunluk":
        gunluk()
    elif komut == "kategori":
        kategori_yenile()
    elif komut == "dagilim":
        dagilim_yenile()
    elif komut == "hesapla":
        hesapla_sadece()
    else:
        yaz(__doc__)
        sys.exit(1)
