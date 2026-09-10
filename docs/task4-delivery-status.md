# Görev 4 Teslim Durumu

## Tamamlananlar

- SES-benzeri düz olayları, yerel SES `Bounce`/`Complaint` nesnelerini ve SNS zarfını okuyan sınıflandırıcı kütüphanesi
- Çok alıcılı SES bildirimlerini CLI/toplu API'de alıcı başına ayırma ve tek olay API'sinde sessiz veri kaybını engelleme
- Tek olay ve en fazla 1.000 olay için FastAPI uçları
- JSON/JSONL giriş ve güvenli JSONL/özet çıkışı üreten CLI
- Dokuz ana kategori, alt sebep, aksiyon, güven, kalıcılık ve eşleşen kural kimliği
- SES alanları, SMTP kodları, RFC 3463 durumları ve tanı metni kullanan 22 sıralı kural
- Gmail, Outlook, Yahoo, Yandex, SES ve kurumsal kapsam notlarıyla resmî kaynaklar
- Python kodu değiştirmeden JSON üzerinden yeni kural ekleme ve hatalı kural alanını başlangıçta reddetme desteği
- Her kural için otomatik olumlu/karşı örnek testi ve öncelik çakışması testleri
- Açık e-posta/tanı metni çıkarmayan; alıcıyı HMAC, mesajı SHA-256 ile eşleyen gizlilik katmanı
- 360 anonim sentetik olay, kategori metrikleri ve kalıcı/geçici hata ayrımı
- Bilinmeyen oranı, en sık 20 güvenli örüntü ve yeni kural ekleme sonraki adımı

## Yerel doğrulama

- `147 passed, 4 skipped`
- Atlanan dört test, yalnızca gerçek MySQL bağlantısı tanımlandığında çalışan entegrasyon testleridir.
- Görev 4 taslak veri kümesi: 360 olay, %100 sentetik şartname uyumu
- Kalıcı hata recall: %100
- Geçici hata recall: %100
- Geçiciyi kalıcı sayma: 0 / 160
- Bilinmeyen: 40 / 360 (%11,11); bu oran bilinmeyen sınıfını ölçmek için veri kümesine bilinçli eklenmiştir.

## Açık kabul kalemi

Gerçek anonim `ses_events` dışa aktarımı sağlanmadı. Bu nedenle mevcut veri kümesi
sentetiktir ve gerçek sağlayıcı dağılımı/üretim doğruluğu iddiası taşımaz. Ayrıca
`evaluation/bounce-human-review.csv` içindeki en az 300 örnek bağımsız bir insan
tarafından henüz etiketlenmemiştir. Kod ve değerlendirme akışı hazırdır; bu kontrol
tamamlanmadan PDF'deki “300 insan etiketli örnek” kabul maddesi tamamlandı denmemelidir.
