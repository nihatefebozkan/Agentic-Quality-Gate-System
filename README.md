# Agentic Quality Gate System

Kullanıcıya cevap ulaşmadan önce arka planda kalite kontrolü yapan, test agent'ı kullanarak cevabı değerlendiren ve yetersizse düzelten bir sistem.

---

## Neden Bu Proje?

Mevcut AI sistemleri test edilmeden cevap veriyor. Kullanıcı istediği cevabı alamıyor ve tekrar sormak zorunda kalıyor. Bu sistem o problemi arka planda çözüyor — kullanıcı görmüyor ama deneyimi çok daha iyi oluyor.

Bu sistem yapay zekanın problemi olan Hallucination, Bağlam kaybı, Genel Kalıplarla cevap verme gibi problemlerinin önüne geçerek cevap verirken doğruluğu arttırarak yapay zeka kullanımında uzun vadede token tasarrufu sağlayacağı öngörülüyor. Hem RAG sistemi ile hem de kullanıcıların tek prompt ile subjektif sorularda istediği cevabı alma olasılığını arttırarak kullanıcının tekrar tekrar aynı işi yaptırmasının önüne geçecek bir sistem.

Sektördeki karşılığı: **LLM as a Judge** + **Agentic Quality Gate**

---

## İnşaat Analojisi

İki inşaat düşünün:

**1. İnşaat — 100 çırak:**
Herkes üretiyor, kimse denetlemiyor. Hızlı ilerliyor ama duvarlar yamuk. Hatayı ilk fark eden müşteri oluyor — ve en pahalı düzeltme noktası orası: yıkıp yeniden yapmak.

**2. İnşaat — 10 usta + 30 çırak:**
Çıraklar üretiyor, ustalar kontrol ediyor. Biraz daha yavaş ilerliyor ve ustaların maliyeti var. Ama duvarlar düzgün çıkıyor, yıkıp yeniden yapma yok.

Mevcut AI sistemleri 1. inşaat gibidir: cevap üretilir, denetlenmeden kullanıcıya gider. Hatayı kullanıcı fark eder ve tekrar sormak zorunda kalır — yani duvar yıkılıp yeniden örülür.

Bu sistem 2. inşaattır: ana agent üretir (çırak), test agent denetler (usta). Test maliyeti vardır ama kullanıcı tekrarını engellediği için net kazanç sağlar.

> Yıkıp yeniden yapmak, baştan doğru yapmaktan her zaman pahalıdır.

**Analojinin incelikleri:**

- **Usta ve çırak aynı kişidir** — her iki agent da aynı modeli kullanır. Fark eğitimde değil, görev tanımındadır: üretmek geniş ve dağınık bir görev, denetlemek dar ve odaklı bir görevdir. Aynı model dar görevde çok daha isabetlidir.
- **Self-preference bias riski** — usta kendi alışkanlıklarındaki hatayı başkasının duvarında da normal sanabilir. Çözüm: dışarıdan müfettiş (insan onaylı kalibrasyon verisi) veya başka firmadan usta (farklı model judge).
- **Her tuğlaya usta çağrılmaz** — temel ve kolonlar gibi kritik noktalarda denetim yapılır. Sistem de her cevabı değil, kritik cevapları test ederek token tasarrufu sağlar.

---

## Mimari

```
Kullanıcı mesaj yazar
        ↓
Niyet sınıflandırma → sohbet mi, kariyer sorusu mu?
   (önce kural tabanlı, belirsizse LLM)
        ↓ sohbet ise → kalite kapısı atlanır, normal cevap
        ↓ kariyer ise
Ana agent cevap üretir
        ↓
Test agent → cevabı kriterlere göre değerlendirir
        ↓
Skor + neden düşük + ne yapılmalı üretir
        ↓
Skor 80 altındaysa → ana agent'a geri bildirim gönderilir
        ↓
Ana agent cevabı düzeltir (maksimum 3 deneme)
        ↓
En iyi cevap kullanıcıya gider
        ↓
Her tur diske kaydedilir (kayitlar/ klasörü)
```

İleride: kullanıcı promptu RAG ile vektörlere ayrılacak ve sadece alakalı test case'ler çekilecek.

### 3 Çıktı Durumu

| Durum | Açıklama |
|-------|----------|
| Başarı | İlk denemede 80 üstü skor — direkt gönderilir |
| Kısmi başarı | 2-3 denemede düzeldi — en iyi skor gönderilir |
| Başarısız | 3 denemede düzeltemedi — raporlanır |

---

## Teknoloji Stack

- **Python** — ana agent, test agent ve orkestrasyon
- **Groq API** — LLM motoru (llama-3.3-70b-versatile)
- **Flask** — web sunucusu (app.py)
- **HTML/CSS/JS** — chat arayüzü (sadece arayüz, mantık Python'da)
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

- Kariyer danışmanı ana agent (Groq API) — pozisyon/deneyim/bütçe/lokasyon sorar, kişiye özel tavsiye üretir
- Koşullu şehir sorusu — "uzaktan" ise sorulmaz, "hibrit/ofis" ise sorulur
- Test agent — 5 kritere göre 0-100 skor + neden düşük + ne yapılmalı (JSON çıktısı)
- Maksimum 3 deneme düzeltme döngüsü
- Niyet sınıflandırma — iki katmanlı: önce kural tabanlı (token harcamadan), belirsizse LLM; sohbet mesajları kalite kapısına girmez ve skorlanmaz
- JSON kayıt sistemi — tarih damgalı dosyalar, mesaj bazlı durum takibi, genel sonuç durumu
- Crash safety — her tur diske yazılır; program aniden ölse bile (kill -9) tamamlanmış turlar korunur
- Flask backend — web arayüzü CLI ile aynı fonksiyonları kullanır, kopya mantık yok
- API anahtarı güvenliği — GROQ_API_KEY tarayıcıya gitmez, sunucu tarafında .env'den okunur

---

## Test Sonuçları

Tüm özellikler manuel test senaryolarıyla doğrulandı:

| Test | Sonuç |
|------|-------|
| Mesaj bazlı durum kaydı (3 mesajlı konuşma, ayrı skorlar) | Geçti |
| Genel durum kuralı (basari / kismi_basari / basarisiz) | Birim + canlı doğrulandı |
| Crash safety (çalışırken kill -9, JSON korundu) | Geçti |
| Niyet kural katmanı ("tesekkurler" → sohbet, LLM çağrısı yok) | Geçti |
| Tuzak mesaj ("tesekkurler ama butcemi 5000 TL yaptım" → kariyer) | Düzeltme sonrası geçti |
| Genel durum hesabında sohbet mesajlarının dışlanması | Geçti |
| Web uçtan uca (tip/skor/durum) | Geçti |

Test sırasında fault injection (çalışma anında MAKS_DUZELTME=0 override) ve negative test teknikleri kullanıldı.

---

## Bilinen Problemler

### Aktif

- **Döngü tuzağı:** Kullanıcı eksik bilgi girerse (örn. bütçe zaman dilimi belirtmezse) skor 3 turda da artmıyor. Ana agent geri bildirimi alıyor ama eksik veriyle düzeltemez. Çözüm: girdi testi katmanı — eksik/belirsiz bilgide kullanıcıya geri sorma.
- **Ret cezası:** Kullanıcının vermeyi reddettiği bilgi (örn. "bütçemi söylemek istemiyorum"), test agent'ın eksiksizlik kriterinden ceza kesmesine yol açıyor. Düzeltme döngüsü bu baskıyla ana agent'a reddedilen bilgiyi kullanıcıya tekrar sordurtuyor. Testlerle canlı olarak doğrulandı. Çözüm: ret edilen alanlar profile "reddedildi" olarak işlenmeli ve test agent bu alanların yokluğunu cezalandırmamalı.
- **Bayat profil:** Konuşma içinde güncellenen bilgiler (örn. bütçe değişikliği) kullanıcı profiline yansımıyor; test agent eski bilgiyle değerlendiriyor. Çözüm: dinamik profil — her mesajdan bilgi çıkarımı yapılıp profil güncellenmeli.
- **Niyet sınıflandırma binary:** Sadece "kariyer" ve "sohbet" sınıfları var. "Bilgi güncelleme" ve "ret/sınır" mesajları için sınıf yok, bunlar kariyer sınıfına düşüyor.
- **İki çırak problemi (self-preference bias):** Test agent ve ana agent aynı modeli kullanıyor — ortak kör noktaları paylaşıyorlar. Test agent, ana agent'ın bilmediği şeyi (örn. hallucination) yakalayamayabilir. Kalibrasyon için insan onaylı örnek cevaplar henüz yok.
- **Test case'ler sabit:** Şu an 5 sabit kriter var, RAG olmadığı için kullanıcının sorusuna göre değişmiyor. Alakasız kriterler de çalışıyor.
- **Skor tutarsızlığı:** Aynı cevaba farklı zamanlarda farklı skor verebiliyor. LLM deterministik değil.
- **Test verisi hijyeni:** Test konuşmaları gerçek kayıtlarla aynı klasöre (kayitlar/) yazılıyor. Mevcut 11 kayıt test artefaktıdır. Test modu ayrı klasör kullanmalı; yoksa ileride RAG ve kalibrasyon kirli veriden beslenir.
- **Sınıflandırma izlenebilirliği:** Niyetin kural mı LLM mi tarafından belirlendiği kayda yazılmıyor.
- **Geri bildirim döngüsü tek yönlü:** Test agent sadece ana agent'a geri bildirim gönderiyor, kullanıcıya eksik bilgi sorusu yönlendirilmiyor.

### Çözüldü

- **Sohbet mesajları yanlış puanlanıyordu (false positive):** Selamlaşma/teşekkür gibi mesajlar kariyer kriterleriyle değerlendirilip "basarisiz" işaretleniyor, istatistikleri kirletiyordu. Niyet sınıflandırma ile çözüldü.
- **Konuşmalar kaydedilmiyordu:** JSON kayıt sistemi kuruldu, her tur diske yazılıyor (crash safety dahil).
- **Çift mantık problemi:** index.html ve career_advisor.py aynı sistemin iki bağımsız kopyasıydı. Flask backend ile çözüldü — mantık tek yerde (Python), HTML sadece arayüz.
- **API anahtarı tarayıcıdaydı:** Güvenlik riski. Artık sunucu tarafında .env'den okunuyor.

---

## Yapılacaklar

### Kısa Vade
- [ ] Ret sınıfı + dinamik profil — reddedilen alanların işaretlenmesi ve konuşma içi bilgi güncellemelerinin profile yansıması (bir sonraki iş paketi)
- [ ] Girdi testi katmanı — eksik/belirsiz bilgide kullanıcıya geri soru yönlendirme (döngü tuzağı çözümü)
- [ ] Test modu — test konuşmalarının ayrı klasöre yazılması
- [ ] Sınıflandırma kaynağının (kural/LLM) kayda işlenmesi
- [ ] Skor geçmişi ve rapor çıktısı

### Orta Vade
- [ ] RAG entegrasyonu — kullanıcı promptuna göre alakalı test case'leri çekme
- [ ] Test case'leri otomatik üretme (sentetik veri)
- [ ] Gerçek kullanıcı konuşmalarından otomatik test case oluşturma
- [ ] Niyet sınıflandırmanın 4 sınıfa genişletilmesi (kariyer / bilgi güncelleme / ret / sohbet)
- [ ] Hallucination kriteri — test agent'a uydurma bilgi tespiti eklenmesi

### Uzun Vade
- [ ] Test agent kalibrasyonu — insan onaylı örnek cevaplarla
- [ ] Token optimizasyonu — kritik olmayan cevaplarda test agent'ın devreye girmemesi
- [ ] Farklı model judge — self-preference bias'ı azaltmak için
- [ ] Farklı agent tipleri için genişletme

---

## Kurulum

```bash
git clone https://github.com/nihatefebozkan/agentic-quality-gate.git
cd agentic-quality-gate
pip install groq python-dotenv flask
```

`.env` dosyası oluştur:
```
GROQ_API_KEY=your_api_key_here
```

Terminal arayüzü (CLI):
```bash
python career_advisor.py
```

Test agent'ını tek başına çalıştırma (örnek veriyle):
```bash
python test_agent.py
```

Web arayüzü:
```bash
python app.py
```
Sonra tarayıcıda `http://localhost:5000` adresini aç.

---

## Proje Durumu

Aktif geliştirme aşamasında.