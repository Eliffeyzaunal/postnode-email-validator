# Görev 1 Gerçek DNS Benchmark Sonucu

- Ölçüm zamanı: 2026-09-10T18:03:32.371292+00:00
- Ortam: Windows; Python 3.13.1
- Resolver: 10.157.112.139, 192.168.1.1
- Her turdaki benzersiz, herkese açık alan adı: 20
- Ölçüm geçerliliği: geçerli - en az bir gerçek DNS cevabı alındı
- Müşteri verisi: kullanılmadı

| Ölçüm | Gerçek DNS (soğuk) | Kalıcı cache (sıcak) |
|---|---:|---:|
| Süre (sn) | 2.1438 | 0.0115 |
| Sorgu/sn | 9.33 | 1737.36 |
| Cache hit | 0 | 20 |

DNS durumları: `mx`=15, `no_mail_host`=3, `nxdomain`=2.

Bu ölçüm yalnızca gerçek DNS gecikmesini ve cache davranışını gösterir. 
10.000 adreslik deterministik MySQL benchmark'ıyla hız karşılaştırması yapılamaz; 
alan adı sayısı, ağ, resolver ve donanım koşulları farklıdır.
