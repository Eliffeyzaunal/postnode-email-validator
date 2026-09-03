# 10.000 Adres Benchmark Raporu

Test dosyası dört alan adına dengeli dağıtılmış 10.000 sentetik adres içerir; ağ gecikmesini değil liste motorunun kapasitesini ölçmek için sabit DNS sağlayıcısı kullanılır.

## Sonuç

| Ölçüm | Değer |
|---|---:|
| Adres sayısı | 10.000 |
| Süre | 0,0577 saniye |
| Hız | 173.281 adres/saniye |
| Benzersiz alan adı | 4 |
| DNS lookup | 4 |

Sonuç, teslim ortamındaki tek bir yerel koşunun ölçümüdür. Canlı DNS kullanılan ilk koşuda süre ağ gecikmesine göre değişir; kalıcı önbellek sonrası aynı alan adları yeniden sorgulanmaz.
