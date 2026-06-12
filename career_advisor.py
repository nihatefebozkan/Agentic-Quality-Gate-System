"""
Kariyer Danışmanı Agent
=======================
Kullanıcıyla konuşarak bilgi toplar (hedef pozisyon, deneyim, bütçe, lokasyon),
ardından Groq API kullanarak kişiye özel kariyer tavsiyesi üretir. Üretilen her
tavsiye bir kalite kapısından (test_agent) geçer; skor 80'in altındaysa en fazla
3 kez düzeltilir. Konuşma bitince tüm akış kayitlar/ klasörüne JSON olarak yazılır.

Çalıştırmak için:
    pip install groq python-dotenv
    python career_advisor.py
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq

from test_agent import tavsiyeyi_degerlendir

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
ESIK_SKOR = 80          # Bu skorun altı "düzeltilmesi gerekir" demek.
MAKS_DUZELTME = 3       # Skor düşükse en fazla bu kadar düzeltme turu.
KAYIT_KLASORU = "kayitlar"

# Kullanıcıdan sırayla toplanacak bilgiler.
SORULAR = [
    ("hedef_pozisyon", "Hangi pozisyonu hedefliyorsun? (örn. Backend Developer)"),
    ("deneyim", "Kaç yıl deneyimin var ve hangi alanda? (örn. 3 yıl Python)"),
    ("butce", "Eğitim için bütçen nedir? (aylık mı, toplam mı belirt)"),
    ("lokasyon", "Nerede çalışmak istiyorsun? (ofis / uzaktan / hibrit)"),
]

# Kısa mesajlarda "sohbet" saymak için kullanılan selam/teşekkür/onay kalıpları.
SOHBET_KALIPLARI = (
    "selam", "merhaba", "naber", "nasılsın", "nasilsin",
    "teşekkür", "tesekkur", "sağol", "sagol", "sağ ol", "eyvallah",
    "tamam", "peki", "evet", "harika", "süper", "super", "güzel", "guzel",
    "anladım", "anladim", "ok", "okey", "görüşürüz", "gorusuruz",
)

SISTEM_PROMPTU = (
    "Sen deneyimli bir kariyer danışmanısın. Kullanıcının verdiği bilgilere göre "
    "somut, uygulanabilir ve kişiye özel kariyer tavsiyesi ver. Türkçe yanıt ver. "
    "Tavsiyeni şu başlıklar altında topla: 1) Genel Değerlendirme, "
    "2) Öğrenmen Gereken Beceriler, 3) Bütçene Uygun Kaynaklar, "
    "4) İş Arama Stratejisi (lokasyona göre), 5) Sonraki 3 Ay İçin Eylem Planı."
)


def yeni_kayit():
    """Boş bir konuşma kayıt sözlüğü oluşturur."""
    return {
        "tarih": datetime.now().isoformat(timespec="seconds"),
        "kullanici_bilgileri": {},
        "kullanici_mesajlari": [],
        "agent_tavsiyeleri": [],
        "turlar": [],
        "mesaj_durumlari": [],
        "final_skor": None,
        "sonuc_durumu": None,
    }


def _durum(skor):
    """Bir skoru durum etiketine çevirir."""
    if skor >= ESIK_SKOR:
        return "basari"
    if skor >= 50:
        return "kismi_basari"
    return "basarisiz"


def _genel_durum(mesaj_durumlari):
    """Mesaj durumlarından genel sonuç durumunu hesaplar.

    Tüm mesajlar başarılıysa 'basari', hepsi başarısızsa 'basarisiz',
    aksi halde (en az biri başarısız veya karışık) 'kismi_basari'.
    """
    # Sohbet mesajları skorlanmadığı için genel duruma katılmaz.
    durumlar = [m["durum"] for m in mesaj_durumlari if m["durum"] != "sohbet"]
    if not durumlar:
        return None
    if all(d == "basari" for d in durumlar):
        return "basari"
    if all(d == "basarisiz" for d in durumlar):
        return "basarisiz"
    return "kismi_basari"


def _mesaj_durumu_guncelle(kayit, mesaj_no, skor):
    """Bir mesajın en iyi skorunu ve durumunu kayda işler (upsert)."""
    for m in kayit["mesaj_durumlari"]:
        if m["mesaj_no"] == mesaj_no:
            m["skor"] = skor
            m["durum"] = _durum(skor)
            return
    kayit["mesaj_durumlari"].append({
        "mesaj_no": mesaj_no, "skor": skor, "durum": _durum(skor), "tip": "kariyer",
    })


def niyet_belirle(client, mesaj):
    """Mesajın 'sohbet' mi 'kariyer' sorusu mu olduğunu belirler.

    Önce kural tabanlı: çok kısa (3 kelimeden az) ve bir selam/teşekkür/onay
    kalıbı içeriyorsa doğrudan 'sohbet'. Emin olunamazsa Groq'a tek soruluk
    bir çağrı atılır.
    """
    dusuk = mesaj.lower()
    if len(mesaj.split()) < 3 and any(k in dusuk for k in SOHBET_KALIPLARI):
        return "sohbet"

    yanit = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Bu mesaj kariyer danışmanlığı sorusu mu yoksa günlük sohbet mi? "
                "Mesaj selam/teşekkür/onay ile başlasa bile, içinde herhangi bir "
                "kariyer bilgisi, güncellemesi (bütçe, pozisyon, deneyim, lokasyon) "
                "veya sorusu varsa 'kariyer' say. Sadece tamamen günlük "
                "konuşma/nezaket ise 'sohbet' say. "
                "Tek kelime cevap ver: kariyer veya sohbet.\n\n"
                f"Mesaj: {mesaj}"
            ),
        }],
        temperature=0,
    )
    cevap = yanit.choices[0].message.content.strip().lower()
    return "sohbet" if "sohbet" in cevap else "kariyer"


def _sohbet_cevapla(client, gecmis, kayit, mesaj_no, dosya_yolu):
    """Sohbet mesajına normal cevap üretir; kalite kapısını ve skorlamayı atlar."""
    cevap = _ana_agent_cevapla(client, gecmis)
    kayit["agent_tavsiyeleri"].append(cevap)
    kayit["turlar"].append({
        "mesaj_no": mesaj_no, "tur": 1, "etiket": "Sohbet",
        "tip": "sohbet", "skor": None,
    })
    kayit["mesaj_durumlari"].append({
        "mesaj_no": mesaj_no, "skor": None, "durum": "sohbet", "tip": "sohbet",
    })
    kaydet(kayit, dosya_yolu)
    return cevap


def kullanici_bilgisi_topla():
    """Kullanıcıyla konuşarak gerekli bilgileri toplar ve sözlük döner."""
    print("=" * 55)
    print("  🎯  KARİYER DANIŞMANI")
    print("  Sana özel tavsiye için birkaç soru soracağım.")
    print("=" * 55)

    bilgiler = {}
    for anahtar, soru in SORULAR:
        while True:
            cevap = input(f"\n> {soru}\n  ").strip()
            if cevap:
                bilgiler[anahtar] = cevap
                break
            print("  (Lütfen bir yanıt gir.)")

    # Lokasyon türüne göre ek şehir sorusu.
    lokasyon = bilgiler["lokasyon"].lower()
    if "uzak" in lokasyon:
        # Uzaktan çalışacaksa şehir sormaya gerek yok.
        pass
    elif "hibrit" in lokasyon or "ofis" in lokasyon:
        while True:
            sehir = input("\n> Hangi şehirde çalışmak istiyorsun?\n  ").strip()
            if sehir:
                bilgiler["sehir"] = sehir
                break
            print("  (Lütfen bir yanıt gir.)")

    return bilgiler


def _ana_agent_cevapla(client, gecmis):
    """Mevcut geçmişle ana agent'tan bir cevap üretir ve geçmişe ekler."""
    yanit = client.chat.completions.create(
        model=MODEL,
        messages=gecmis,
        temperature=0.7,
    )
    cevap = yanit.choices[0].message.content
    gecmis.append({"role": "assistant", "content": cevap})
    return cevap


def _duzeltme_iste(gecmis, degerlendirme):
    """Quality gate geri bildirimini ana agent'a düzeltme talebi olarak iletir."""
    nedenler = "; ".join(degerlendirme.get("neden_dusuk", []))
    yapilacaklar = "; ".join(degerlendirme.get("yapilmasi_gerekenler", []))
    gecmis.append({
        "role": "user",
        "content": (
            "Önceki cevabın bir kalite denetiminden "
            f"{degerlendirme.get('skor')} puan aldı ve yetersiz bulundu.\n"
            f"Düşük puan nedenleri: {nedenler}\n"
            f"Yapman gerekenler: {yapilacaklar}\n"
            "Lütfen tavsiyeni bu eksikleri giderecek şekilde yeniden yaz."
        ),
    })


def _tur_isle(kayit, mesaj_no, tur, etiket, cevap, degerlendirme,
              en_iyi_skor, dosya_yolu):
    """Bir turun sonucunu kayda işler, mesaj durumunu günceller ve diske yazar.

    Her tur bittiğinde çağrılır; crash safety için kayıt anında dosyaya yazılır.
    """
    skor = degerlendirme.get("skor", 0)
    kayit["agent_tavsiyeleri"].append(cevap)
    kayit["turlar"].append({
        "mesaj_no": mesaj_no, "tur": tur, "etiket": etiket, "skor": skor,
        "geri_bildirim": {
            "neden_dusuk": degerlendirme.get("neden_dusuk", []),
            "yapilmasi_gerekenler": degerlendirme.get("yapilmasi_gerekenler", []),
        },
    })
    en_iyi_skor = max(en_iyi_skor, skor)
    kayit["final_skor"] = en_iyi_skor
    _mesaj_durumu_guncelle(kayit, mesaj_no, en_iyi_skor)
    kaydet(kayit, dosya_yolu)
    return en_iyi_skor


def kalite_kapisi(client, gecmis, eval_bilgiler, kayit, mesaj_no, dosya_yolu):
    """Cevap üretir, puanlar ve gerekiyorsa düzeltir. En iyi cevabı döner.

    Her tur bittiğinde kayıt diske yazılır (crash safety).
    """
    cevap = _ana_agent_cevapla(client, gecmis)
    degerlendirme = tavsiyeyi_degerlendir(eval_bilgiler, cevap, client=client)
    en_iyi_cevap = cevap
    en_iyi_skor = _tur_isle(kayit, mesaj_no, 1, "İlk cevap", cevap,
                            degerlendirme, 0, dosya_yolu)

    duzeltme = 0
    while en_iyi_skor < ESIK_SKOR and duzeltme < MAKS_DUZELTME:
        duzeltme += 1
        print(f"  ↳ Skor {en_iyi_skor} (< {ESIK_SKOR}). Düzeltme turu {duzeltme}...")
        _duzeltme_iste(gecmis, degerlendirme)
        cevap = _ana_agent_cevapla(client, gecmis)
        degerlendirme = tavsiyeyi_degerlendir(eval_bilgiler, cevap, client=client)
        skor = degerlendirme.get("skor", 0)
        if skor > en_iyi_skor:
            en_iyi_cevap = cevap
        en_iyi_skor = _tur_isle(kayit, mesaj_no, duzeltme + 1,
                                f"Düzeltme {duzeltme}", cevap, degerlendirme,
                                en_iyi_skor, dosya_yolu)

    return en_iyi_cevap


def ilk_tavsiye(client, gecmis, bilgiler, kayit, dosya_yolu):
    """Toplanan yapılandırılmış bilgilerle ilk tavsiyeyi kalite kapısından geçirir."""
    kullanici_mesaji = (
        "İşte hakkımdaki bilgiler, bana kişiye özel kariyer tavsiyesi ver:\n"
        f"- Hedef pozisyon: {bilgiler['hedef_pozisyon']}\n"
        f"- Deneyim: {bilgiler['deneyim']}\n"
        f"- Bütçe: {bilgiler['butce']}\n"
        f"- Lokasyon: {bilgiler['lokasyon']}"
    )
    if "sehir" in bilgiler:
        kullanici_mesaji += f"\n- Şehir: {bilgiler['sehir']}"

    gecmis.append({"role": "user", "content": kullanici_mesaji})
    kayit["kullanici_mesajlari"].append(kullanici_mesaji)
    return kalite_kapisi(client, gecmis, bilgiler, kayit, 1, dosya_yolu)


def sohbet_dongusu(client, gecmis, bilgiler, kayit, dosya_yolu):
    """Tavsiye sonrası takip sorularını da kalite kapısından geçirir."""
    print("\nBaşka bir sorun var mı? (çıkmak için 'çık' yaz)")
    while True:
        soru = input("\n> ").strip()
        if not soru:
            continue
        if soru.lower() in ("çık", "cik", "exit", "quit", "q"):
            print("\nGörüşürüz, kariyerinde başarılar! 👋")
            break

        gecmis.append({"role": "user", "content": soru})
        kayit["kullanici_mesajlari"].append(soru)
        mesaj_no = len(kayit["kullanici_mesajlari"])

        # Mesajı önce sınıflandır: sohbet ise kalite kapısını atla.
        if niyet_belirle(client, soru) == "sohbet":
            print("  (sohbet olarak algılandı, skorlanmadı)")
            cevap = _sohbet_cevapla(client, gecmis, kayit, mesaj_no, dosya_yolu)
        else:
            eval_bilgiler = dict(bilgiler, takip_sorusu=soru)
            cevap = kalite_kapisi(client, gecmis, eval_bilgiler, kayit,
                                  mesaj_no, dosya_yolu)
        print(f"\n{cevap}")


def kaydet(kayit, dosya_yolu):
    """Genel sonuç durumunu hesaplar ve kaydı verilen dosyaya (üzerine) yazar."""
    kayit["sonuc_durumu"] = _genel_durum(kayit["mesaj_durumlari"])
    os.makedirs(KAYIT_KLASORU, exist_ok=True)
    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=2)
    return dosya_yolu


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("HATA: GROQ_API_KEY bulunamadı. .env dosyasına ekleyin.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    # Konuşma geçmişi bir liste olarak tutulur; her tur buna eklenir.
    gecmis = [{"role": "system", "content": SISTEM_PROMPTU}]
    kayit = yeni_kayit()

    # Dosya adı konuşma başında bir kez belirlenir; her tur aynı dosyaya yazılır.
    ad = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_yolu = os.path.join(KAYIT_KLASORU, f"konusma_{ad}.json")

    bilgiler = kullanici_bilgisi_topla()
    kayit["kullanici_bilgileri"] = bilgiler

    print("\n⏳ Sana özel tavsiye hazırlanıyor (kalite kapısından geçiriliyor)...\n")
    try:
        tavsiye = ilk_tavsiye(client, gecmis, bilgiler, kayit, dosya_yolu)
        print("=" * 55)
        print(tavsiye)
        print("=" * 55)
        print(f"(Quality Gate final skoru: {kayit['final_skor']}/100)")

        sohbet_dongusu(client, gecmis, bilgiler, kayit, dosya_yolu)
    except KeyboardInterrupt:
        print("\n(Konuşma kesildi, kayıt yapılıyor...)")
    except Exception as e:
        print(f"HATA: Groq API çağrısı başarısız oldu: {e}")
    finally:
        if kayit["turlar"]:
            kaydet(kayit, dosya_yolu)
            print(f"\n📁 Konuşma kaydedildi: {dosya_yolu} "
                  f"(durum: {kayit['sonuc_durumu']})")


if __name__ == "__main__":
    main()
