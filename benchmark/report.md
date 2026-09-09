# 10.000 Adres Benchmark Ölçüm Durumu

Test dosyası dört alan adına dengeli dağıtılmış 10.000 sentetik adres içerir.
Ağ değişkenliğini kaldırmak için DNS cevabı sabittir; üretimde kullanılan
kalıcı MySQL cache ve sonuç kayıt yolu aynen çalıştırılır.

## Kabul ölçümleri

| Ölçüm | Beklenen değer |
|---|---:|
| Her koşudaki adres sayısı | 10.000 |
| İlk koşu DNS sorgusu | 4 |
| İkinci koşu DNS sorgusu | 0 |
| MySQL'e yazılan toplam sonuç | 20.000 |

Bu dosya henüz gerçekleşmemiş bir MySQL süresi içermez. Bu revizyon hazırlanırken
çalışma ortamında MySQL/Docker bulunmadığı için gerçek MySQL ölçümü beklemektedir.
Kabul tablosu beklenen değerlerdir; gerçekleşmiş ölçüm gibi okunmamalıdır.

Güncel süre, adres/saniye, veritabanı sürümü, Python sürümü, commit ve ölçüm tarihi
hedef geliştirme makinesinde şu komutla kaydedilir:

```bash
python scripts/benchmark.py --require-mysql --output outputs/evidence/mysql-benchmark.json --markdown outputs/evidence/mysql-benchmark.md
```

Benchmark benzersiz bir cache alanı kullanır, yazılan satır sayısını doğrular
ve yalnızca kendi oluşturduğu batch/cache kayıtlarını bitişte siler. Böylece
mevcut uygulama verilerine dokunmaz. Süre sonuçları donanım ve MySQL ortamına
göre değişeceği için sabit bir performans iddiası olarak sunulmaz.

Windows'ta Docker Desktop açıkken `collect_delivery_evidence.bat` dosyasını
çalıştırmak testleri, değerlendirmeyi ve bu ölçümü tek sırada yürütür. GitHub PR
kontrolleri de gerçek MySQL 8.4 kullanır ve sonuçları Actions sayfasında
`delivery-evidence-python-3.11` / `delivery-evidence-python-3.12` dosya paketleri
olarak saklar. Teslimde başarılı koşunun `mysql-benchmark.md` dosyasını kullanın;
ölçüm dosyası oluşmadan bu kabul maddesini tamamlanmış işaretlemeyin.
