# Görev 1–2 teslim durumu (güncel)

## Hazırlananlar

- Windows başlatıcısı, başlattığı izleyicinin çalışmasını sağlık şartı yapar.
- Değerlendirme 258 sentetik adres ve 7 liste senaryosu içerir; otomatik
  kontroller taslak beklentilerle uyumludur. 258 etiket Elif Feyza Ünal tarafından
  kontrol edilmiş, 0 uyuşmazlıkla insan incelemesi şartı sağlanmıştır.
- Güncel şemayla 720 saatlik simülasyon, giriş/çıkış bildirimleri ve kaynak notu üretildi.
- Test, değerlendirme ve gerçek MySQL ölçümünü dosyalara kaydeden CI ve Windows
  akışları hazırlandı.
- PR #1, #2, #5 ve #6 `main` dalına birleştirildi.
- Son başarılı GitHub Actions koşusunda Python 3.11 ve 3.12 üzerinde tam test
  paketi geçti; Python 3.12 işi `284 passed` sonucu verdi.
- Aynı CI koşusunda gerçek MySQL 8.4 entegrasyonu ve 10.000 adres benchmark adımı
  tamamlandı.
- Coverage sonuçları: Görev 1 `%98,44`, Görev 2 `%96,64`, Görev 4 `%98,69`.
- Görev 1'in 200 adreslik canlı karşılaştırması 200/200 puanlanmış ve geçerli
  ölçüm üretmiştir: accuracy `%95,00`, macro F1 `%94,31`, geçerli→geçerli olmayan
  FPR `%0,00`.

## Teslimde gösterilecek kanıtlar

1. Başarılı CI koşusundan `delivery-evidence-python-*` paketini indirin veya
   Docker Desktop açıkken `collect_delivery_evidence.bat` çalıştırın. Gerçek
   MySQL süreleri `outputs/evidence/mysql-benchmark.md` dosyasına yazılır.
2. Görev 1 için `TASK1-REPORT.md`, canlı değerlendirme raporu ve coverage artifact'ını sunun.
3. Görev 2 için sahte DNS raporu, 720 saatlik simülasyon ve durum geçişi
   bildirimlerini gösterin.

Doğukan Bey'in onayladığı mevcut kapsam sahte DNS, resmî test girdileri,
JSON/veritabanı bildirimi ve SORBS için kullanılamıyor raporudur. Gerçek müşteri
verisi, canlı veritabanı/SES, gerçek bildirim kanalı veya ana uygulama entegrasyonu
bu teslim için gerekli değildir.

Görev 1 ve Görev 2 açısından açık bir kod kabul engeli bulunmamaktadır. Canlı
DNSBL üretim geçişi istenirse sağlayıcı erişimi, izinli resolver ve gerçek çalışma
ortamında zamanlayıcı gözlemi ayrıca doğrulanmalıdır.
