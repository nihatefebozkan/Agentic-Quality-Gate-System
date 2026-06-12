"""
Kariyer Danışmanı + Quality Gate Web Sunucusu
=============================================
Flask backend. Tarayıcıya chat arayüzünü sunar ve Groq çağrılarını sunucu
tarafında yapar; GROQ_API_KEY tarayıcıya hiç sızmaz (.env'den okunur).

career_advisor.py'deki gerçek mantığı yeniden kullanır:
  - niyet_belirle  -> mesaj sohbet mi kariyer mi (kural + gerekirse LLM)
  - _sohbet_cevapla -> sohbet ise kalite kapısı atlanır, skorlanmaz
  - kalite_kapisi  -> kariyer ise puanlanır, skor < 80 ise en fazla 3 düzeltme
  - kaydet         -> her tur kayitlar/ içine JSON olarak yazılır (crash safety)

Her cevap, sağ paneldeki Quality Gate logunda gösterilecek tüm ayrıntıyı döner:
niyet, tur tur skorlar + geri bildirim, mesaj durumu ve genel sonuç durumu.

Çalıştırmak için:
    ./venv/bin/python app.py   ->  http://127.0.0.1:5000
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from groq import Groq

from career_advisor import (
    KAYIT_KLASORU, SISTEM_PROMPTU, _sohbet_cevapla, kalite_kapisi, kaydet,
    niyet_belirle, yeni_kayit,
)

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY bulunamadı. .env dosyasına ekleyin.")
client = Groq(api_key=api_key)


def _yeni_oturum():
    """Yeni bir konuşma durumu (geçmiş, kayıt, dosya yolu) oluşturur."""
    gecmis = [{"role": "system", "content": SISTEM_PROMPTU}]
    kayit = yeni_kayit()
    ad = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_yolu = os.path.join(KAYIT_KLASORU, f"konusma_{ad}.json")
    return {"gecmis": gecmis, "kayit": kayit, "dosya_yolu": dosya_yolu}


# Basit, tek oturumluk durum (yerel demo için yeterli).
oturum = _yeni_oturum()


@app.after_request
def cors(resp):
    """index.html dosyadan (file://) açılsa bile fetch çalışsın diye CORS izni."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    mesaj = (request.json or {}).get("mesaj", "").strip()
    if not mesaj:
        return jsonify({"hata": "Boş mesaj"}), 400

    gecmis = oturum["gecmis"]
    kayit = oturum["kayit"]
    dosya_yolu = oturum["dosya_yolu"]

    gecmis.append({"role": "user", "content": mesaj})
    kayit["kullanici_mesajlari"].append(mesaj)
    mesaj_no = len(kayit["kullanici_mesajlari"])
    tur_baslangic = len(kayit["turlar"])

    try:
        niyet = niyet_belirle(client, mesaj)
        if niyet == "sohbet":
            cevap = _sohbet_cevapla(client, gecmis, kayit, mesaj_no, dosya_yolu)
        else:
            cevap = kalite_kapisi(client, gecmis, {"kullanici_mesaji": mesaj},
                                  kayit, mesaj_no, dosya_yolu)
    except Exception as e:
        return jsonify({"hata": f"Groq API hatası: {e}"}), 500

    # Bu mesaja ait turları ve mesaj durumunu ayıkla.
    yeni_turlar = kayit["turlar"][tur_baslangic:]
    mesaj_durumu = next(
        (m for m in kayit["mesaj_durumlari"] if m["mesaj_no"] == mesaj_no), None)

    return jsonify({
        "cevap": cevap,
        "mesaj_no": mesaj_no,
        "tip": niyet,
        "turlar": yeni_turlar,
        "mesaj_durumu": mesaj_durumu,
        "sonuc_durumu": kayit["sonuc_durumu"],
        "dosya": dosya_yolu,
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    global oturum
    oturum = _yeni_oturum()
    return jsonify({"durum": "sıfırlandı"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
