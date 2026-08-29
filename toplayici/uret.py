# -*- coding: utf-8 -*-
"""Mobil uygulamanin indirecegi JSON dosyalarini uretir.

Iki parcali cikti:

  data/fonlar.json        ~1-2 MB. Butun fonlarin metrikleri ve puanlari.
                          Uygulama her acilista bunu indirir.
  data/gecmis/AFA.json    Tek fonun fiyat serisi. Sadece kullanici o fonun
                          detayina girince indirilir.

Neden bolduk: butun fonlarin 1 yillik fiyat gecmisi tek dosyada ~10 MB
tutuyor. Her acilista 10 MB indirmek mobil veriyi yakar ve acilisi
yavaslatir; kullanici da zaten 2400 fonun grafigine bakmayacak.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

SORUMLULUK_NOTU = (
    "Bu uygulama yatırım danışmanlığı değildir. Gösterilen sıralamalar geçmiş "
    "fiyat verilerinden hesaplanmış istatistiklerdir. Geçmiş getiri gelecek "
    "getiriyi göstermez. Veriler TEFAS'tan alınmıştır, hata içerebilir."
)

TR_SAAT = timezone(timedelta(hours=3))


def _yuvarla(x, basamak=4):
    return None if x is None else round(x, basamak)


def fon_kaydi(f):
    """Bir fonu JSON'a yazilacak sozluge cevirir."""
    return {
        "kod": f["fon_kodu"],
        "ad": f.get("fon_adi") or "",
        "tip": f.get("fon_tipi"),
        "tip_ad": f.get("fon_tipi_ad"),
        "kategori": f.get("kategori_ad") or "Bilinmiyor",
        # "api" = TEFAS'in kendi kategorisi, "isim" = fon adindan cikarim.
        # Uygulama bunu kullaniciya gosteriyor; cikarim kesin bilgi gibi
        # sunulmamali.
        "kategori_kaynak": f.get("kategori_kaynak", "yok"),
        "katilim": bool(f.get("katilim")),
        "tarih": f.get("son_tarih"),
        "fiyat": f.get("son_fiyat"),
        "kisi_sayisi": f.get("kisi_sayisi"),
        "buyukluk": f.get("portfoy_buyukluk"),
        "gozlem": f.get("gozlem_sayisi"),
        "getiri": {
            "gunluk": _yuvarla(f.get("gunluk_getiri"), 2),
            "haftalik": _yuvarla(f.get("haftalik_getiri"), 2),
            "aylik": _yuvarla(f.get("aylik_getiri"), 2),
            "uc_aylik": _yuvarla(f.get("uc_aylik_getiri"), 2),
            "yillik": _yuvarla(f.get("yillik_getiri"), 2),
            "yilbasindan": _yuvarla(f.get("yilbasindan_getiri"), 2),
        },
        "volatilite": _yuvarla(f.get("volatilite"), 2),
        "maks_dusus": _yuvarla(f.get("maks_dusus"), 2),
        "puan": f.get("puan"),
        "sira": f.get("kategori_sirasi"),
        "kategori_fon_sayisi": f.get("kategori_fon_sayisi"),
        "kirilim": f.get("puan_kirilimi"),
        "puanlanmama_nedeni": f.get("puanlanmama_nedeni"),
    }


def ozet_yaz(yol, puanlanan, puanlanmayan, elenen, ayarlar, veri_tarihi):
    """data/fonlar.json dosyasini yazar, boyutu (bayt) dondurur."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)

    hepsi = [fon_kaydi(f) for f in puanlanan] + \
            [fon_kaydi(f) for f in puanlanmayan]

    # Kategori ozeti: uygulamada kategori listesi ekranini besler.
    kategoriler = {}
    for f in hepsi:
        a = (f["tip"], f["kategori"])
        k = kategoriler.setdefault(a, {
            "tip": f["tip"], "tip_ad": f["tip_ad"],
            "ad": f["kategori"], "adet": 0, "puanlanabilir": False,
            "api_adet": 0, "cikarim_adet": 0,
        })
        k["adet"] += 1
        if f["puan"] is not None:
            k["puanlanabilir"] = True
        if f["kategori_kaynak"] == "api":
            k["api_adet"] += 1
        elif f["kategori_kaynak"] == "isim":
            k["cikarim_adet"] += 1

    # Grubun kaynagi COGUNLUGA gore belirlenir.
    #
    # Once "grupta tek bir cikarim varsa hepsi cikarim sayilsin" denmisti;
    # bu yanlis cikti. TEFAS'in kategori sorgusu o gunku listeyi veriyor,
    # araya sonradan giren birkac fon haritada olmuyor ve isimden
    # cikariliyor. 170 fonluk, 168'i TEFAS'in kendi sinifamasindan gelen
    # bir kategoriyi "cikarim" diye isaretlemek gereksiz suphe yaratiyordu.
    # Kesin sayilar yine JSON'da: uygulama isterse "168 kesin, 2 cikarim"
    # diyebilir.
    for k in kategoriler.values():
        k["kaynak"] = "api" if k["api_adet"] >= k["cikarim_adet"] else "isim"

    icerik = {
        "surum": 1,
        "veri_tarihi": veri_tarihi,
        "uretim_zamani": datetime.now(TR_SAAT).isoformat(timespec="seconds"),
        "sorumluluk_notu": SORUMLULUK_NOTU,
        "ayarlar": {
            "agirliklar": ayarlar["agirliklar"],
            "asgari_gecmis_gun": ayarlar["asgari_gecmis_gun"],
            "asgari_fon_buyuklugu": ayarlar["asgari_fon_buyuklugu"],
            "asgari_kategori_fon_sayisi": ayarlar["asgari_kategori_fon_sayisi"],
            "z_kirpma": ayarlar["z_kirpma"],
        },
        "sayilar": {
            "puanlanan": len(puanlanan),
            "puanlanmayan": len(puanlanmayan),
            "elenen": len(elenen),
            "toplam": len(puanlanan) + len(puanlanmayan) + len(elenen),
        },
        "kategoriler": sorted(kategoriler.values(),
                              key=lambda k: (k["tip"], k["ad"])),
        "fonlar": hepsi,
    }

    with open(yol, "w", encoding="utf-8") as d:
        json.dump(icerik, d, ensure_ascii=False, separators=(",", ":"))
    return yol.stat().st_size


def gecmis_yaz(klasor, seriler, kodlar, gun_siniri=None):
    """Fon basina fiyat serisi dosyalari yazar. (dosya_sayisi, toplam_bayt)"""
    klasor = Path(klasor)
    if klasor.exists():
        # Listeden dusen fonun eski dosyasi kalmasin.
        shutil.rmtree(klasor)
    klasor.mkdir(parents=True, exist_ok=True)

    adet = 0
    boyut = 0
    for kod in kodlar:
        seri = seriler.get(kod) or []
        if gun_siniri:
            seri = seri[-gun_siniri:]
        if not seri:
            continue
        icerik = {
            "kod": kod,
            "tarihler": [t for t, _ in seri],
            "fiyatlar": [round(f, 6) for _, f in seri],
        }
        d_yol = klasor / (kod + ".json")
        with open(d_yol, "w", encoding="utf-8") as d:
            json.dump(icerik, d, ensure_ascii=False, separators=(",", ":"))
        adet += 1
        boyut += d_yol.stat().st_size
    return adet, boyut
