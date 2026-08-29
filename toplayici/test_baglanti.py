# -*- coding: utf-8 -*-
"""ASAMA 1 - Baglanti testi.

Tek bir fonun son fiyatini ve adini ekrana basar. Baska hicbir sey yapmaz:
dosya yazmaz, veritabani olusturmaz. Amaci sadece "TEFAS'a ulasabiliyor
muyuz" sorusunu cevaplamak.
"""
import sys
from datetime import date, timedelta

# Windows konsolu varsayilan olarak Turkce karakterleri basamayabilir.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pytefas import Crawler

FON = "AFA"

# Bugun hafta sonu veya tatil olabilir; son 10 gunu isteyip
# icindeki en son is gununu aliyoruz.
bitis = date.today()
baslangic = bitis - timedelta(days=10)

print(f"TEFAS'a baglaniliyor... ({FON}, {baslangic} - {bitis})")
print("Not: dakikada 6 istek siniri var, birkac saniye surebilir.\n")

tefas = Crawler()
df = tefas.fetch(start=baslangic, end=bitis, fund_code=FON, kind="YAT")

if df.empty:
    print(f"SONUC: Veri gelmedi. '{FON}' kodu yanlis olabilir.")
    sys.exit(1)

son = df.sort_values("date").iloc[-1]
print("BAGLANTI BASARILI\n")
print(f"  Fon kodu        : {son['fund_code']}")
print(f"  Fon adi         : {son['fund_name'].strip()}")
print(f"  Tarih           : {son['date']}")
print(f"  Fiyat           : {son['price']:.6f} TL")
print(f"  Yatirimci sayisi: {int(son['investor_count']):,}".replace(",", "."))
print(f"  Fon buyuklugu   : {son['portfolio_size']:,.0f} TL".replace(",", "."))
print(f"\n  (bu aralikta {len(df)} is gunu verisi geldi)")
