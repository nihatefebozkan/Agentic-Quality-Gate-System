# Agentic Quality Gate System

Kullanıcıya cevap ulaşmadan önce arka planda kalite kontrolü yapan, test agent'ı kullanarak cevabı değerlendiren ve yetersizse düzelten bir sistem.

---

## Neden Bu Proje?

Mevcut AI sistemleri test edilmeden cevap veriyor. Kullanıcı istediği cevabı alamıyor ve tekrar sormak zorunda kalıyor. Bu sistem o problemi arka planda çözüyor — kullanıcı görmüyor ama deneyimi çok daha iyi oluyor.
Bu sistem yapay zekanın problemi olan Hallucination, Bağlam kaybı, Genel Kalıplarla cevap verme gibi problemlerinin önüne geçerek cevap verirken doğruluğu arttırarak yapay zeka kullanımında uzun vadede token tasarrufu sağlayacağı öngörülüyor. Hem RAG sistemi ile hemde kullanıcıların tek prompt ile subjektif sorularda istediği cevabı alma olasılığını arttırarak kullanıcının tekrar tekrar aynı işi yaptırmasının önüne geçicek bir sistem.

Sektördeki karşılığı: **LLM as a Judge** + **Agentic Quality Gate**

---

## Mimari

```
Kullanıcı prompt yazar
        ↓
Prompt → RAG ile vektörlere ayrılır
        ↓
En alakalı test case'ler çekilir
        ↓
Ana agent cevap üretir
        ↓
Test agent → cevabı + test case'leri kullanarak değerlendirir
        ↓
Skor + geri bildirim üretir
        ↓
Skor %80 altındaysa → ana agent'a geri bildirim gönderilir
        ↓
Ana agent cevabı düzeltir (maksimum 3 deneme)
        ↓
En iyi cevap kullanıcıya gider
```

### 3 Çıktı Durumu

| Durum | Açıklama |
|-------|----------|
| ✅ | İlk denemede %80 üstü skor — direkt gönderilir |
| ⚠️ | 2-3 denemede düzeldi — en iyi skor gönderilir |
| ❌ | 3 denemede düzeltemedi — raporlanır |

---

## Teknoloji Stack

- **Python** — ana agent ve test agent
- **Groq API** — LLM motoru
- **HTML/CSS/JS** — chat arayüzü
- **JSON** — konuşma ve skor kayıtları
- **RAG** — ilerleyen aşamada eklenecek

---

## Neden Subjektif Görevler?

- Kod üretimi → çalıştırırsın, hata kodu zaten bilgisayar dili ile döndüğü için yapay zekalar için sonuç bellidir.
- Matematik → doğru cevap bellidir
- CV, kariyer tavsiyesi, yazı → yorum gerekir, test agent'ı lazımdır

Bu sistem subjektif görevlerde devreye girer.

---

## Şu An Çalışan Özellikler

- Kariyer danışmanı ana agent (Groq API)
- 5 sorulu kullanıcı bilgi toplama akışı
- Test agent — 5 kritere göre 0-100 skor üretiyor
- Skor + neden düşük + ne yapılmalı JSON çıktısı
- Maksimum 3 deneme döngüsü
- Chat arayüzü — sol chat, sağ Quality Gate log paneli

---

## Bilinen Problemler

- **Döngü tuzağı:** Kullanıcı eksik bilgi girerse (örn. bütçe zaman dilimi belirtmezse) skor 3 turda da artmıyor. Ana agent geri bildirimi alıyor ama eksik veriyle düzeltemez.
- **İki çırak problemi:** Örneğin "Test agentın" doğruluğunu kontrol eden bir "Test agent" daha gelistirirsek iki çırak birbirine akıl vermiş gibi oluyor. Kalibrasyon için insan onaylı örnek cevaplar henüz yok.
- **Test case'ler sabit:** Şu an 5 sabit kriter var, RAG olmadığı için kullanıcının sorusuna göre değişmiyor. Alakasız kriterler de çalışıyor.
- **Skor tutarsızlığı:** Aynı cevaba farklı zamanlarda farklı skor verebiliyor. LLM deterministik değil.
- **Geri bildirim döngüsü tek yönlü:** Test agent sadece ana agent'a geri bildirim gönderiyor, kullanıcıya değil.
- **Konuşmalar kaydedilmiyor:** Test veritabanı henüz birikmiyor, her konuşma kayboluyor.

---

## Yapılacaklar

### Kısa Vade
- [ ] Kullanıcıya eksik bilgi sorusu yönlendirme (döngü tuzağı çözümü)
- [ ] Konuşmaları JSON'a kaydetme
- [ ] Test case veritabanı oluşturma
- [ ] Skor geçmişi ve rapor çıktısı

### Orta Vade
- [ ] RAG entegrasyonu — kullanıcı promptuna göre alakalı test case'leri çekme
- [ ] Test case'leri otomatik üretme (sentetik veri)
- [ ] Gerçek kullanıcı konuşmalarından otomatik test case oluşturma

### Uzun Vade
- [ ] Test agent kalibrasyonu — insan onaylı örnek cevaplarla
- [ ] Token optimizasyonu — skor %80 üstündeyse test agent devreye girmesin
- [ ] Farklı agent tipleri için genişletme

---

## Kurulum

```bash
git clone https://github.com/nihatefebozkan/agentic-quality-gate.git
cd agentic-quality-gate
pip install groq python-dotenv
```

`.env` dosyası oluştur:
```
GROQ_API_KEY=your_api_key_here
```

Ana agent'ı çalıştır:
```bash
python career_advisor.py
```

Test agent'ını çalıştır:
```bash
python test_agent.py
```

Web arayüzü için `index.html` dosyasını tarayıcıda aç.

---

## Proje Durumu
Aktif geliştirme aşamasında
