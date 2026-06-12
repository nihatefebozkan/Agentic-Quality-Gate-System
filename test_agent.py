"""
Tavsiye Değerlendirme Agent'ı (Quality Gate)
============================================
Kariyer danışmanının ürettiği tavsiyeyi değerlendirir. Kullanıcı bilgilerini ve
tavsiyeyi girdi olarak alır, Groq API ile 5 kritere göre 0-100 arası skor üretir
ve sonucu JSON formatında döner.

Kriterler:
  1) Bütçe için bir zaman dilimi (aylık/toplam) belirtilmiş mi?
  2) Tavsiye, kullanıcının deneyim seviyesine uygun mu?
  3) Lokasyona özel (uzaktan/ofis/hibrit/şehir) öneriler var mı?
  4) Tavsiye somut ve uygulanabilir mi?
  5) Eksik veya atlanmış bilgi var mı?

Kullanım (kütüphane olarak):
    from test_agent import tavsiyeyi_degerlendir
    sonuc = tavsiyeyi_degerlendir(bilgiler, tavsiye)

Doğrudan çalıştırma (örnek veriyle):
    python test_agent.py
"""

import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

DEGERLENDIRME_PROMPTU = (
    "Sen bir kalite değerlendirme uzmanısın. Bir kariyer danışmanının ürettiği "
    "tavsiyeyi, kullanıcının verdiği bilgilere göre değerlendiriyorsun. "
    "Aşağıdaki 5 kritere göre 0-100 arası TEK bir genel skor ver:\n"
    "1) Bütçe için zaman dilimi (aylık mı, toplam mı) net belirtilmiş mi?\n"
    "2) Tavsiye kullanıcının deneyim seviyesine uygun mu?\n"
    "3) Tavsiye lokasyona (uzaktan/ofis/hibrit/şehir) özel mi?\n"
    "4) Tavsiye somut ve uygulanabilir mi (genel-geçer değil)?\n"
    "5) Atlanan veya eksik kalan önemli bir bilgi var mı?\n\n"
    "Yanıtını SADECE şu JSON şemasında ver, başka metin ekleme:\n"
    "{\n"
    '  "skor": <0-100 arası tam sayı>,\n'
    '  "kriter_skorlari": {\n'
    '    "butce_zaman_dilimi": <0-20>,\n'
    '    "deneyim_uygunlugu": <0-20>,\n'
    '    "lokasyon_ozgunlugu": <0-20>,\n'
    '    "somutluk": <0-20>,\n'
    '    "eksiksizlik": <0-20>\n'
    "  },\n"
    '  "neden_dusuk": ["<skoru düşüren neden>", ...],\n'
    '  "yapilmasi_gerekenler": ["<somut iyileştirme önerisi>", ...]\n'
    "}\n"
    "Tüm metinleri Türkçe yaz. kriter_skorlari toplamı genel skora eşit olmalı."
)


def _bilgileri_metne_cevir(bilgiler: dict) -> str:
    """Kullanıcı bilgileri sözlüğünü okunabilir metne dönüştürür."""
    satirlar = []
    etiketler = {
        "hedef_pozisyon": "Hedef pozisyon",
        "deneyim": "Deneyim",
        "butce": "Bütçe",
        "lokasyon": "Lokasyon",
        "sehir": "Şehir",
    }
    for anahtar, etiket in etiketler.items():
        if anahtar in bilgiler:
            satirlar.append(f"- {etiket}: {bilgiler[anahtar]}")
    # Bilinen etiketlerin dışındaki ek anahtarları da ekle (örn. serbest mesaj).
    for anahtar, deger in bilgiler.items():
        if anahtar not in etiketler:
            satirlar.append(f"- {anahtar}: {deger}")
    return "\n".join(satirlar)


def tavsiyeyi_degerlendir(bilgiler: dict, tavsiye: str, client: Groq = None) -> dict:
    """Verilen kullanıcı bilgileri ve tavsiyeyi değerlendirip skor sözlüğü döner."""
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY bulunamadı. .env dosyasına ekleyin.")
        client = Groq(api_key=api_key)

    kullanici_mesaji = (
        "KULLANICI BİLGİLERİ:\n"
        f"{_bilgileri_metne_cevir(bilgiler)}\n\n"
        "DEĞERLENDİRİLECEK TAVSİYE:\n"
        f"{tavsiye}"
    )

    yanit = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": DEGERLENDIRME_PROMPTU},
            {"role": "user", "content": kullanici_mesaji},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(yanit.choices[0].message.content)


def _ornek_calistir():
    """Örnek veriyle değerlendirmeyi çalıştırıp sonucu yazdırır."""
    ornek_bilgiler = {
        "hedef_pozisyon": "Backend Developer",
        "deneyim": "3 yıl Python",
        "butce": "5000 TL",
        "lokasyon": "hibrit",
        "sehir": "İstanbul",
    }
    ornek_tavsiye = (
        "Backend developer olmak için Python öğrenmeye devam et. "
        "Bazı online kurslara bakabilirsin. İş ilanlarına başvur."
    )

    try:
        sonuc = tavsiyeyi_degerlendir(ornek_bilgiler, ornek_tavsiye)
    except Exception as e:
        print(f"HATA: Değerlendirme başarısız oldu: {e}")
        sys.exit(1)

    print(json.dumps(sonuc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _ornek_calistir()
