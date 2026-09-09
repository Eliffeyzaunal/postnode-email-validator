# Görev 1–2 teslim durumu

## Hazırlananlar

- Windows başlatıcısı, başlattığı izleyicinin çalışmasını sağlık şartı yapar.
- Değerlendirme 258 sentetik adres ve 7 liste senaryosu içerir; otomatik
  kontroller taslak beklentilerle uyumludur. Bağımsız insan etiket incelemesi ayrı tutulur.
- Güncel şemayla 720 saatlik simülasyon, giriş/çıkış bildirimleri ve kaynak notu üretildi.
- Test, değerlendirme ve gerçek MySQL ölçümünü dosyalara kaydeden CI ve Windows
  akışları hazırlandı. 76 test geçti; bu ortamda 4 MySQL testi atlandı.

## Kapanması gereken gerçek teslim adımları

1. Değişiklikleri `fix/runtime-monitor-isolation` dalına gönderip bu daldan `main`
   hedefine PR açın. GitHub Actions'ın Python 3.11/3.12 ve MySQL kontrolleri
   başarılı olmadan birleştirmeyin. Bu çalışma ortamında GitHub yazma erişimi
   bulunmadığı için PR/merge işlemi yapılmadı.
2. Başarılı CI koşusundan `delivery-evidence-python-*` paketini indirin veya
   Docker Desktop açıkken `collect_delivery_evidence.bat` çalıştırın. Gerçek
   MySQL süreleri `outputs/evidence/mysql-benchmark.md` dosyasına yazılır.
   Bu ortamda MySQL/Docker bulunmadığından henüz güncel MySQL süresi yoktur.
3. `evaluation/human-review.csv` dosyasındaki en az 200 etiketi Elif veya Sefa
   bağımsız inceleyerek doldurmalı. Yönerge `evaluation/REVIEW.md` içindedir.
   İnceleme yapılmadan etiketleri topluca onaylı işaretlemeyin.
4. Sefa ile Görev 1 çözümlerini karşılaştırın ve Görev 2/3'ü birlikte sunun.

Doğukan Bey'in onayladığı mevcut kapsam sahte DNS, resmî test girdileri,
JSON/veritabanı bildirimi ve SORBS için kullanılamıyor raporudur. Gerçek müşteri
verisi, canlı veritabanı/SES, gerçek bildirim kanalı veya ana uygulama entegrasyonu
bu teslim için gerekli değildir.
