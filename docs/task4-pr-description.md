## Özet

Görev 4 kapsamında SES bounce ve şikâyet olaylarını açıklanabilir kurallarla
sınıflandıran kütüphane, CLI ve API uçları eklendi.

## Değişiklikler

- 9 ana kategori için kategori, alt sebep, aksiyon, güven ve kalıcılık çıktısı
- SES tür/alt türü, SMTP/RFC 3463 kodu ve tanı metni kullanan 22 sıralı JSON kuralı
- Kural başına sağlayıcı, resmî kaynak, olumlu örnek ve karşı örnek
- Kod değişmeden yeni kural ekleme ve kural önceliği desteği
- Açık alıcı adresi ile tanı metnini çıktıdan çıkaran gizlilik katmanı
- JSON/JSONL CLI, tek/toplu FastAPI uçları ve bilinmeyen örüntü raporu
- SNS zarfı ve çok alıcılı SES bildirimi desteği
- Kural şeması doğrulaması ve standart dışı adres biçimlerini de kapsayan gizlilik sertleştirmesi
- 360 anonim sentetik olay üzerinde kategori ve kalıcı/geçici hata ölçümü
- İnsan inceleme şablonu, teslim durumu, kaynak tablosu ve demo akışı

## Doğrulama

- Yerel: `150 passed, 4 skipped`
- 4 atlama: yerelde MySQL bağlantısı bulunmadığı için entegrasyon testleri
- Sentetik taslak doğruluk: `%100`
- Geçiciyi kalıcı sayma: `0 / 160`
- Bilinmeyen oranı: `40 / 360 (%11,11)`

## Şeffaflık notu

Değerlendirme verisi anonim ve sentetiktir; gerçek `ses_events` dışa aktarımı
kullanılmamıştır. En az 300 satırlık insan etiket kontrolü henüz beklediği için
insan-etiketli kabul kriteri tamamlanmış olarak işaretlenmemiştir.
