# Görev 1–2 teslim durumu

## Hazırlananlar

- Windows başlatıcısı, başlattığı izleyicinin çalışmasını sağlık şartı yapar.
- Değerlendirme 258 sentetik adres ve 7 liste senaryosu içerir; otomatik
  kontroller taslak beklentilerle uyumludur. 258 etiket Elif Feyza Ünal tarafından
  kontrol edilmiş, 0 uyuşmazlıkla insan incelemesi şartı sağlanmıştır.
- Güncel şemayla 720 saatlik simülasyon, giriş/çıkış bildirimleri ve kaynak notu üretildi.
- Test, değerlendirme ve gerçek MySQL ölçümünü dosyalara kaydeden CI ve Windows
  akışları hazırlandı. 76 test geçti; bu ortamda 4 MySQL testi atlandı.
- PR #2 GitHub Actions üzerinde Python 3.11 ve 3.12 ile başarılı oldu; MySQL
  entegrasyonu ve 10.000 adres benchmark adımı tamamlandı.

## Kapanması gereken gerçek teslim adımları

1. Başarılı PR #2'yi `main` dalına birleştirin.
2. Başarılı CI koşusundan `delivery-evidence-python-*` paketini indirin veya
   Docker Desktop açıkken `collect_delivery_evidence.bat` çalıştırın. Gerçek
   MySQL süreleri `outputs/evidence/mysql-benchmark.md` dosyasına yazılır.
3. Sefa ile Görev 1 çözümlerini karşılaştırın ve Görev 2/3'ü birlikte sunun.

Doğukan Bey'in onayladığı mevcut kapsam sahte DNS, resmî test girdileri,
JSON/veritabanı bildirimi ve SORBS için kullanılamıyor raporudur. Gerçek müşteri
verisi, canlı veritabanı/SES, gerçek bildirim kanalı veya ana uygulama entegrasyonu
bu teslim için gerekli değildir.
