# Görev 1 - Liste Hijyeni ve Adres Doğrulama Kanıt Raporu

Bu rapor yalnızca Görev 1'i değerlendirir. Görev 2 ve Görev 4 özellikleri,
testleri ve ölçümleri aşağıdaki sonuçlara dahil edilmemiştir.

## Sonuç özeti

| Ölçüm | Sonuç | Sınır / açıklama |
|---|---:|---|
| İnsan tarafından kontrol edilmiş sentetik adres | 258 | Sabit DNS; müşteri verisi değil |
| Accuracy | %100,00 | İncelenmiş sentetik etiketlerle uyum |
| Macro precision | %100,00 | Üç karar sınıfının ortalaması |
| Macro recall | %100,00 | Üç karar sınıfının ortalaması |
| Macro F1 | %100,00 | Üç karar sınıfının ortalaması |
| Geçerli → geçersiz FPR | %0,00 | 0/99 geçerli örnek |
| Liste senaryosu | 7/7 | Duplicate, sequence ve concentration sınırları |
| Görev 1 kod kapsamı | %86,35 | 447 satırdan 386'sı; CI alt sınırı %85 |
| Disposable-domain anlık görüntüsü | 8.746 | Runtime'da ağ erişimi yok |
| Role-account terimi | 55 | Türkçe + İngilizce |
| Kontrollü role varyasyon son eki | 15 | Ör. `ticket`, `eu`, `tr` |
| Açık typo eşlemesi | 30 | Önce kesin eşleme |
| Fuzzy hedef sağlayıcı | 27 | Aynı TLD + benzersiz en yakın eşleşme |

Bu oranlar gerçek müşteri trafiği doğruluğu değildir. Veri kümesi sentetiktir,
DNS cevapları sabittir ve sonuç yalnızca belgelenmiş görev kurallarına uyumu ölçer.

## Şartname - uygulama - test eşlemesi

| Şartname maddesi | Durum | Uygulama | Otomatik kanıt |
|---|---|---|---|
| CSV/TXT girdi ve adres başına karar/sebep | Tamamlandı | `app/parser.py`, `app/cli.py`, `app/main.py` | `tests/test_parser.py`, `tests/test_api.py` |
| Syntax, yerel bölüm, domain ve uzunluk | Tamamlandı | `app/syntax.py` | `tests/test_syntax.py` |
| IDN/Punycode | Tamamlandı | `app/syntax.py` | SMTPUTF8/IDN syntax testi |
| Kontrollü SMTPUTF8 | Tamamlandı | Unicode harf/rakam/işaret alt kümesi; `SMTPUTF8_REQUIRED` | `tests/test_syntax.py`, `tests/test_validator.py` |
| MX ve A/AAAA fallback | Tamamlandı | `app/dns_checker.py` | `tests/test_dns_checker.py` |
| NXDOMAIN ve teknik DNS hata ayrımı | Tamamlandı | `app/dns_checker.py`, `app/validator.py` | DNS ve validator testleri |
| Kalıcı DNS cache | Tamamlandı | `app/repository.py` | `tests/test_dns_cache.py` |
| Disposable-domain tespiti | Tamamlandı | `app/address_rules.py`, `data/disposable_domains.txt` | `tests/test_task1_address_rules.py` |
| Güncellenebilir ve kaynaklı liste | Tamamlandı | `scripts/update_disposable_domains.py` | Snapshot bütünlük/minimum boyut testi |
| Role-account ve varyasyonları | Tamamlandı | Role ve varyasyon veri dosyaları | Pozitif ve yanlış-pozitif testleri |
| Typo ve düzeltme önerisi | Tamamlandı | Kesin eşleme + kontrollü fuzzy öneri | Address-rule ve validator testleri |
| Duplicate, generated sequence, concentration | Tamamlandı | `app/validator.py` | Validator ve değerlendirme senaryoları |
| Bir adres için birden fazla bulgu | Tamamlandı | `reason_codes` listesi | Validator ve API testleri |
| İnsan okunur karar açıklaması | Tamamlandı | API `reason_details` alanı | `tests/test_api.py` |
| Liste özeti ve tahmini bounce oranı | Tamamlandı | `app/validator.py` | Validator ve API testleri |
| 10.000 adres ve süre raporu | Tamamlandı | `scripts/benchmark.py` | CI'da gerçek MySQL kayıt/cache yolu |
| En az 200 elle kontrol edilmiş örnek | Tamamlandı | 258 kayıt | `scripts/evaluate.py --require-human-review` |
| Accuracy ve yanlış pozitif oranı | Tamamlandı | `evaluation/results.json` | Değerlendirme testleri |
| Precision, recall, F1, confusion matrix | Tamamlandı | `evaluation/report.md` | Metrik birim testi |
| Görev 1 coverage kanıtı | Tamamlandı | GitHub Actions XML/JSON artifact | `%85` alt sınırı |
| Gerçek DNS ölçümünün ayrılması | Tamamlandı | `scripts/benchmark_live_dns.py` | Resolver hatası başarı sayılmaz |
| SMTP `RCPT TO`, catch-all ve ücretli servis yok | Tamamlandı | Tasarım kapsamı | README kapsam beyanı |

## Kararların açıklanması

API, sabit `reason_codes` değerlerinin yanında aynı sırada insan okunur
`reason_details` döndürür. Örnek:

```json
{
  "status": "supheli",
  "reason_codes": ["ROLE_ACCOUNT", "DOMAIN_TYPO"],
  "reason_details": [
    {"code": "ROLE_ACCOUNT", "description": "Yerel bölüm info, admin veya destek gibi bir rol hesabı."},
    {"code": "DOMAIN_TYPO", "description": "Alan adı yaygın bir yazım hatasıyla eşleşiyor."}
  ]
}
```

Fuzzy typo yalnızca `data/popular_email_domains.txt` içindeki gözden geçirilmiş
sağlayıcılara, aynı TLD altında ve tek bir en yakın sonuç bulunduğunda uygulanır.
Bu bulgu adresi hiçbir zaman `gecersiz` yapmaz; yalnızca `supheli` ve öneri üretir.

## Yeniden üretme

```bash
python -m pytest
python scripts/evaluate.py --review evaluation/human-review.csv --require-human-review \
  --output evaluation/results.json --markdown evaluation/report.md
```

Görev 1 coverage komutu GitHub Actions içinde sabitlenmiştir; sonuç
`task1-coverage.xml` ve `task1-coverage.json` olarak saklanır.

Gerçek DNS ölçümü otomatik CI'a konmaz; ağ ve resolver koşullarına bağlıdır:

```bash
python scripts/benchmark_live_dns.py --acknowledge-live-dns
```

En az bir gerçek DNS cevabı alınamazsa komut başarısız olur ve raporu geçersiz
olarak işaretler. Bu sonuç, 10.000 adreslik deterministik MySQL benchmark'ıyla
hız üstünlüğü iddiası için karşılaştırılmaz.
