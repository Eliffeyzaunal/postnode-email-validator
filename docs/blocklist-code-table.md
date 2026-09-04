# Kara Liste DNS Dönüş Kodları

Bu belge Görev 2'de kullanılan dönüş kodlarını ve karar kurallarını kaydeder. Varsayılan sahte DNS modu `data/blocklist_fake_dns.json` içindeki belirleyici cevapları kullanır. `BLOCKLIST_DNS_MODE=live` açıkça seçilirse aynı yorumlama kuralları gerçek DNS cevaplarına uygulanır.

## Genel kararlar

| DNS sonucu | Uygulama durumu | Açıklama |
|---|---|---|
| `NXDOMAIN` | `not_listed` | Sağlayıcı bu varlık için liste kaydı döndürmedi. |
| Belgelenmiş pozitif kod | `listed` | Kod sağlayıcının tablosuna göre yorumlanır. |
| Timeout, SERVFAIL, REFUSED | `query_error` | Teknik hata temiz sonuç sayılmaz. |
| Erişim/kota hata kodu | `query_error` | Hata cevabı liste kaydı olarak yorumlanmaz. |
| SORBS | `unavailable` | Hizmetin EOL durumu ayrıca raporlanır. |

## Spamhaus ZEN

| Kod | Anlam |
|---|---|
| `127.0.0.2` | SBL |
| `127.0.0.3` | CSS |
| `127.0.0.4` | XBL |
| `127.0.0.9` | DROP |
| `127.0.0.10` | PBL (ISP politikası) |
| `127.0.0.11` | PBL (Spamhaus politikası) |
| `127.0.0.30` | BCL |

## Spamhaus DBL

| Kod | Anlam |
|---|---|
| `127.0.1.2` | Düşük itibarlı alan adı |
| `127.0.1.4` | Kimlik avı |
| `127.0.1.5` | Zararlı yazılım |
| `127.0.1.6` | Botnet komuta/kontrol |
| `127.0.1.102` | Kötüye kullanılan meşru alan adı |
| `127.0.1.103` | Kötüye kullanılan yönlendirici |
| `127.0.1.104` | Kötüye kullanılan kimlik avı alan adı |
| `127.0.1.105` | Kötüye kullanılan zararlı yazılım alan adı |
| `127.0.1.106` | Kötüye kullanılan C2 alan adı |

Spamhaus `127.255.255.252`, `127.255.255.254` ve `127.255.255.255` cevapları sırasıyla sorgu adı, genel DNS çözücü erişimi ve kota hatasıdır. DBL için `127.0.1.255`, IP sorgusuna izin verilmediğini belirtir. Bunların tamamı `query_error` olur.

## SpamCop ve Barracuda

| Sağlayıcı | Kod | Anlam |
|---|---|---|
| SpamCop SCBL | `127.0.0.2` | Listelenmiş IP |
| Barracuda BRBL | `127.0.0.2` | Listelenmiş IP |

## SURBL Multi

SURBL son okteti bit maskesi olarak yorumlanır; tek cevap birden fazla bulgu üretebilir.

| Bit | Anlam |
|---|---|
| `4` | Disposable mail |
| `8` | Kimlik avı |
| `16` | Zararlı yazılım |
| `32` | Tıklama izleyici |
| `64` | Kötüye kullanım |
| `128` | Ele geçirilmiş site |

`127.0.0.1`, erişim engeli anlamına gelir ve `query_error` olur. Örnek `127.0.0.80`, `16 + 64` olduğu için `MALWARE` ve `ABUSE` olarak çözülür.

## Kaynaklar

- [Spamhaus zone ve kod belgeleri](https://docs.spamhaus.com/datasets/docs/source/10-data-type-documentation/datasets/040-zones.html)
- [Spamhaus resmî test girdileri](https://docs.spamhaus.com/datasets/docs/source/70-access-methods/data-query-service/060-dqs-testing.html)
- [Spamhaus genel çözücü hata kodları](https://www.spamhaus.org/resource-hub/dnsbl/using-our-public-mirrors-check-your-return-codes-now/)
- [SpamCop DNSBL yapılandırması](https://www.spamcop.net/fom-serve/cache/291.html)
- [SURBL liste ve bit maskeleri](https://www.surbl.org/surbl-analysis/lists/lists)
- [Barracuda Reputation Block List](https://www.barracudacentral.org/lookups)
- [SORBS EOL duyurusu](https://proofpoint.my.site.com/community/s/article/End-of-Life-EOL-process-for-the-Spam-and-Open-Relay-Blocking-System-SORBS-service)
