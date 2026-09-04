# Günlük İlerleme Notları

Bu notlar, Git commitleri ile test ve benchmark çıktılarından doğrulanabilen çalışmaları özetler. Her gün için 3-5 kısa madde tutulur; yapılmayan bir çalışma yapılmış gibi yazılmaz.

## Gün 1 - 3 Eylül 2026

- Görev 1 için FastAPI, CLI ve kütüphane olarak kullanılabilen e-posta doğrulama akışı tamamlandı.
- Sözdizimi, MX/A/AAAA, disposable domain, rol hesabı, typo ve liste örüntüsü kontrolleri eklendi.
- SQLAlchemy repository katmanı kuruldu; normal çalışma MySQL, izole birim testleri SQLite kullanacak şekilde ayrıldı.
- Null MX, DNS cache ve Windows uyumlu 10.000 adres benchmark kontrolleri eklendi.
- GitHub Actions üzerinde Python 3.11/3.12 ve MySQL entegrasyon testleri çalıştırıldı.

## Gün 2 - 4 Eylül 2026

- Görev 2 için Spamhaus ZEN/DBL, SpamCop, Barracuda, SURBL ve SORBS sağlayıcı tanımları eklendi.
- Resmî test girdilerini kullanan belirleyici sahte DNS modu, dönüş kodu yorumlama ve durum değişikliği bildirimleri tamamlandı.
- Saatlik zamanlayıcı, kalıcı kalp atışı, kaçırılan tur tespiti ve 30 günlük geçmiş raporu eklendi.
- Canlı DNS istemcisinde TXT sebep kaydı, NXDOMAIN ve teknik hata ayrımı test edildi; canlı mod varsayılan olarak kapalı tutuldu.
- MySQL tarih hassasiyeti düzeltildi; yerelde 45 test ve GitHub Actions başarıyla tamamlandı.

## Sonraki kayıt şablonu

```text
## Gün N - GG Ay YYYY
- Tamamlanan iş
- Eklenen veya güncellenen test
- Karşılaşılan sorun ve çözüm
- Ölçüm veya doğrulama sonucu
- Sonraki adım
```
