# 10.000 Adres Benchmark Raporu

Test dosyası dört alan adına dengeli dağıtılmış 10.000 sentetik adres içerir. Ağ değişkenliğini kaldırmak için DNS cevabı sabittir; ancak üretimde kullanılan kalıcı SQLite cache ve sonuç kayıt yolu aynen çalıştırılır.

## Sonuç

| Ölçüm | Değer |
|---|---:|
| Her koşudaki adres sayısı | 10.000 |
| Soğuk cache süresi | 0,2941 saniye |
| Soğuk cache hızı | 34.000 adres/saniye |
| İlk koşu DNS sorgusu | 4 |
| Sıcak cache süresi | 0,1905 saniye |
| Sıcak cache hızı | 52.480 adres/saniye |
| İkinci koşu DNS sorgusu | 0 |
| SQLite'a yazılan toplam sonuç | 20.000 |

Sonuç, teslim ortamındaki tek bir yerel koşunun ölçümüdür. Canlı DNS kullanılan ilk koşuda süre ağ gecikmesine göre değişir; kalıcı önbellek sonrası aynı alan adları yeniden sorgulanmaz. Benchmark her çalıştırmada geçici ve temiz bir SQLite veritabanı oluşturur.
