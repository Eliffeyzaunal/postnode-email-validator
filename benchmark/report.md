# 10.000 Adres Benchmark Raporu

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

Güncel süre ve adres/saniye değerleri hedef makinede şu komutla ölçülür:

```bash
python scripts/benchmark.py
```

Benchmark benzersiz bir cache alanı kullanır, yazılan satır sayısını doğrular
ve yalnızca kendi oluşturduğu batch/cache kayıtlarını bitişte siler. Böylece
mevcut uygulama verilerine dokunmaz. Süre sonuçları donanım ve MySQL ortamına
göre değişeceği için sabit bir performans iddiası olarak sunulmaz.
