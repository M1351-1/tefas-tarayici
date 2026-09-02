# -*- coding: utf-8 -*-
"""Puanlamanin ONGORU GUCUNU olcer.

NEDEN BU MODUL VAR
==================

Uygulama fonlari puanlayip "kategori sirasi 1" diye gosteriyor. Bu bir
IDDIA: "bu fon digerlerinden iyi". Iddianin sinanmasi gerekir.

Sinandi (2488 fon, 2025-07..2026-08) ve sonuc su:

    bilesen           agirlik   ileri Spearman
    aylik getiri       0,35        0,07
    uc aylik getiri    0,25        0,05
    haftalik getiri    0,20        0,07
    volatilite         0,20        0,76   <-- TEK CALISAN BILESEN

    Ust %20'nin ileri getirisi vs alt %20:
        1 ay   %3,1  vs  %3,2
        3 ay   %9,2  vs  %9,4
        6 ay  %17,2  vs %19,1   <-- alt dilim DAHA IYI

Yani gecmis getiriye gore siralama gelecegi TUTMUYOR; oynaklik ise guclu
bicimde kaliciydi. "Bu fon oynak" demek gelecege dair gercek bir ifade,
"bu fon gecen ay iyi getirdi" degil.

Bu modul olcumu HER TOPLAMADA yeniden yapar - sabit bir sayi gomulmez,
cunku piyasa degisirse olcum de degismeli. Sonuc JSON'a yazilir ve
uygulamada siralamanin yaninda gosterilir.

YONTEM
======

Ileri yuruyus: her T aninda fonlar GECMIS penceredeki degere gore
siralanir, T+ufuk arasindaki GERCEK sonuca bakilir. Kategori icinde
yapilir - para piyasasi fonuyla hisse fonunu ayni sirada yaristirmak
zaten anlamsiz.

Olculen iki sey:
  * Spearman sira korelasyonu: siralama ne kadar korunuyor
  * Ust/alt %20 dilimlerin ileri sonucu: pratikte fark var mi

Ikincisi daha anlasilir: "ust sirayi secseydin ne kazanirdin".
"""
from __future__ import annotations

import math
from collections import defaultdict

# Siralamanin dayandigi gecmis pencere (islem gunu). Puanlamadaki en
# agirlikli getiri bileseni uc aylik oldugu icin 63 gun.
GECMIS_PENCERE = 63

# Hangi ufuklarda sinanacak (islem gunu).
UFUKLAR = (21, 63, 126)

# Bir kategorinin olcume girmesi icin gereken en az fon sayisi.
# Az fonlu kategoride sira korelasyonu gurultuden ibaret olur.
ASGARI_FON = 15

# T noktalari arasindaki adim. Her gun olcmek ortusen pencereleri
# sisirir ve bagimsiz gozlem sayisini abartir.
ADIM = 21

# Dilim buyuklugu: ust/alt %20.
DILIM = 5


def _siralar(degerler: list) -> list:
    """Ortalama sirali siralama (beraberlik duzeltmeli).

    BERABERLIKLER ORTALAMA SIRA ALIR. Once sort sirasina gore ayri sira
    veriliyordu ve bu SAHTE korelasyon uretiyordu: butun degerleri ayni
    olan bir dizi (ornegin para piyasasi kategorisinde yuvarlanmis
    volatiliteler) Spearman = 1,00 donduruyordu. Yani "hicbir bilgi yok"
    durumu "mukemmel ongoru" gibi gorunuyordu.
    """
    n = len(degerler)
    sira = sorted(range(n), key=lambda i: degerler[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and degerler[sira[j + 1]] == degerler[sira[i]]:
            j += 1
        ortalama = (i + j) / 2.0
        for k in range(i, j + 1):
            r[sira[k]] = ortalama
        i = j + 1
    return r


def _spearman(cift: list) -> float | None:
    """Sira korelasyonu. cift: [(gecmis_deger, ileri_deger), ...]"""
    n = len(cift)
    if n < 3:
        return None
    rg = _siralar([c[0] for c in cift])
    rf = _siralar([c[1] for c in cift])
    mg, mf = sum(rg) / n, sum(rf) / n
    kov = sum((rg[i] - mg) * (rf[i] - mf) for i in range(n))
    sg = math.sqrt(sum((v - mg) ** 2 for v in rg))
    sf = math.sqrt(sum((v - mf) ** 2 for v in rf))
    if sg * sf == 0:
        return None
    return kov / (sg * sf)


def _getiri(fiyatlar: dict, tarihler: list, i0: int, i1: int) -> float | None:
    t0, t1 = tarihler[i0], tarihler[i1]
    p0, p1 = fiyatlar.get(t0), fiyatlar.get(t1)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return (p1 / p0 - 1) * 100


def _volatilite(fiyatlar: dict, tarihler: list, i0: int, i1: int):
    p = [fiyatlar[t] for t in tarihler[i0:i1] if t in fiyatlar]
    if len(p) < 20:
        return None
    g = [(p[i] / p[i - 1] - 1) for i in range(1, len(p)) if p[i - 1] > 0]
    if len(g) < 15:
        return None
    ort = sum(g) / len(g)
    var = sum((x - ort) ** 2 for x in g) / len(g)
    return math.sqrt(var) * math.sqrt(252) * 100


ISLEVLER = {"getiri": _getiri, "volatilite": _volatilite}


def olc(seriler: dict, kategoriler: dict, olcut: str = "getiri") -> dict:
    """Bir olcutun ongoru gucunu olcer.

    seriler: {fon_kodu: {tarih: fiyat}}
    kategoriler: {fon_kodu: (fon_tipi, kategori_ad)}
    olcut: "getiri" | "volatilite"

    Doner: {ufuk_gun: {spearman, ust_dilim, alt_dilim, olcum_sayisi}}
    """
    islev = ISLEVLER.get(olcut)
    if islev is None:
        return {}

    tarihler = sorted({t for s in seriler.values() for t in s})
    sonuc = {}

    for ufuk in UFUKLAR:
        ro_list, ust_list, alt_list = [], [], []
        for ti in range(GECMIS_PENCERE, len(tarihler) - ufuk, ADIM):
            gruplar = defaultdict(list)
            for fon, fiyatlar in seriler.items():
                gecmis = islev(fiyatlar, tarihler, ti - GECMIS_PENCERE, ti)
                ileri = islev(fiyatlar, tarihler, ti, ti + ufuk)
                if gecmis is None or ileri is None:
                    continue
                gruplar[kategoriler.get(fon, ("?", "?"))].append(
                    (gecmis, ileri))

            for cift in gruplar.values():
                if len(cift) < ASGARI_FON:
                    continue
                ro = _spearman(cift)
                if ro is not None:
                    ro_list.append(ro)
                sirali = sorted(cift, key=lambda c: -c[0])
                k = max(1, len(cift) // DILIM)
                ust_list.append(sum(c[1] for c in sirali[:k]) / k)
                alt_list.append(sum(c[1] for c in sirali[-k:]) / k)

        if not ro_list:
            continue
        sonuc[ufuk] = {
            "spearman": round(sum(ro_list) / len(ro_list), 3),
            "ust_dilim": round(sum(ust_list) / len(ust_list), 2),
            "alt_dilim": round(sum(alt_list) / len(alt_list), 2),
            "olcum_sayisi": len(ro_list),
        }
    return sonuc


def yorumla(getiri_gucu: dict, vol_gucu: dict,
            istikrar_gucu: dict | None = None) -> dict:
    """Olcumleri kullaniciya soylenecek cumleye cevirir."""
    if not getiri_gucu:
        return {"durum": "olculemedi",
                "ozet": "Öngörü gücü ölçülemedi (yeterli geçmiş yok)."}

    # 3 aylik ufuk temsili alinir: ne cok kisa ne cok uzun.
    g = getiri_gucu.get(63) or list(getiri_gucu.values())[0]
    v = (vol_gucu or {}).get(63)

    fark = g["ust_dilim"] - g["alt_dilim"]
    calisiyor = g["spearman"] >= 0.20 and fark > 1.0

    ozet = (
        "ÖLÇÜLDÜ: geçmiş getiriye göre sıralama geleceği tutmuyor. "
        "Üç ay sonrasına bakıldığında üst %%20'lik dilimin getirisi "
        "%%%.1f, alt %%20'lik dilimin %%%.1f — aradaki fark %+.1f puan. "
        "Sıra korelasyonu %.2f (0 = hiç bilgi yok)."
        % (g["ust_dilim"], g["alt_dilim"], fark, g["spearman"])
    ) if not calisiyor else (
        "ÖLÇÜLDÜ: geçmiş getiriye göre sıralamanın bir miktar öngörü "
        "gücü var. Üst %%20 dilim %%%.1f, alt %%20 dilim %%%.1f getirdi "
        "(sıra korelasyonu %.2f)."
        % (g["ust_dilim"], g["alt_dilim"], g["spearman"])
    )

    if v:
        ozet += (
            " Buna karşılık OYNAKLIK kalıcı: sıra korelasyonu %.2f. "
            "Yani \"bu fon oynak\" demek geleceğe dair gerçek bir ifade, "
            "\"bu fon geçen ay iyi getirdi\" değil."
            % v["spearman"]
        )

    # ISTIKRAR: "duzenli olarak akranlarini gecmek" AYRI bir sorudur ve
    # akilli filtre buna dayaniyor. Olculdu: 3 ayda 0,09 (ust dilim alt
    # dilimden KOTU), 6 ayda 0,17 ama yalnizca 20 olcum noktasiyla.
    # Ham getiriden biraz iyi, guvenilir bir sinyal degil.
    i = (istikrar_gucu or {}).get(126) or (istikrar_gucu or {}).get(63)
    if i:
        ozet += (
            " İSTİKRAR (düzenli olarak akranlarını geçmek) ayrı ölçüldü: "
            "sıra korelasyonu %.2f, üst %%20 dilim %%%.1f, alt %%20 dilim "
            "%%%.1f. Ham getiriden biraz iyi ama güvenilir sayılacak kadar "
            "değil — %d ölçüm noktası var."
            % (i["spearman"], i["ust_dilim"], i["alt_dilim"],
               i["olcum_sayisi"])
        )

    return {
        "durum": "calisiyor" if calisiyor else "calismiyor",
        "ozet": ozet,
        "getiri": getiri_gucu,
        "volatilite": vol_gucu or {},
        "istikrar": istikrar_gucu or {},
    }


def istikrar_olc(seriler: dict, kategoriler: dict) -> dict:
    """ISTIKRARIN ongoru gucu: duzenli olarak akranlarini gecen, gecmeye
    devam ediyor mu?

    Getiri SEVIYESI tutmuyor (Spearman ~0,05) ama "duzenli ustunluk" AYRI
    bir sorudur ve ayri sinanmali. Akilli filtre bu olcute dayaniyor.

    Olculdu: 3 ayda 0,11 (ust dilim alt dilimden KOTU), 6 ayda 0,19
    (ust dilim biraz iyi, ama yalnizca 20 olcum noktasi). Yani ham
    getiriden biraz iyi, ama guvenilir bir sinyal degil.
    """
    tarihler = sorted({t for s in seriler.values() for t in s})
    gecmis = 126        # istikrar icin daha uzun pencere gerekir
    sonuc = {}

    def aylik(f, i0, i1):
        dilim = tarihler[i0:i1]
        out = []
        for j in range(21, len(dilim), 21):
            a, o = dilim[j], dilim[j - 21]
            if a in f and o in f and f[o] > 0:
                out.append(f[a] / f[o] - 1)
        return out

    for ufuk in (63, 126):
        ro_list, ust_list, alt_list = [], [], []
        for ti in range(gecmis, len(tarihler) - ufuk, ADIM):
            kat_getiri = defaultdict(lambda: defaultdict(list))
            gecmisler = {}
            for fon, f in seriler.items():
                g = aylik(f, ti - gecmis, ti)
                if len(g) < 4:
                    continue
                gecmisler[fon] = g
                for j, v in enumerate(g):
                    kat_getiri[kategoriler.get(fon, ("?", "?"))][j].append(v)

            medyan = {}
            for k, d in kat_getiri.items():
                medyan[k] = {}
                for j, v in d.items():
                    s = sorted(v)
                    medyan[k][j] = s[len(s) // 2]

            gruplar = defaultdict(list)
            for fon, g in gecmisler.items():
                anahtar = kategoriler.get(fon, ("?", "?"))
                ust = sum(1 for j, v in enumerate(g)
                          if medyan[anahtar].get(j) is not None
                          and v > medyan[anahtar][j])
                oran = ust / len(g)
                f = seriler[fon]
                t0, t1 = tarihler[ti], tarihler[ti + ufuk]
                if t0 not in f or t1 not in f or f[t0] <= 0:
                    continue
                gruplar[anahtar].append((oran, (f[t1] / f[t0] - 1) * 100))

            for cift in gruplar.values():
                if len(cift) < ASGARI_FON:
                    continue
                ro = _spearman(cift)
                if ro is not None:
                    ro_list.append(ro)
                sirali = sorted(cift, key=lambda c: -c[0])
                k = max(1, len(cift) // DILIM)
                ust_list.append(sum(c[1] for c in sirali[:k]) / k)
                alt_list.append(sum(c[1] for c in sirali[-k:]) / k)

        if ro_list:
            sonuc[ufuk] = {
                "spearman": round(sum(ro_list) / len(ro_list), 3),
                "ust_dilim": round(sum(ust_list) / len(ust_list), 2),
                "alt_dilim": round(sum(alt_list) / len(alt_list), 2),
                "olcum_sayisi": len(ro_list),
            }
    return sonuc
