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
| Ayrı dondurulmuş holdout | 300 örnekte %100,00 | Kabul setiyle 0 satır örtüşme; statik senaryolar |
| Bağımsız syntax referans uyumu | Ham %89,43 | 473 örnek; politika farkları hariç %100,00 |
| Canlı DNS karşılaştırması | 200 adres | Bağımsız strict syntax + paylaşılan canlı DNS snapshot; yalnız 200/200 sonuç geçerli |
| Liste senaryosu | 7/7 | Duplicate, sequence ve concentration sınırları |
| Görev 1 kod kapsamı | %88,39 | 448 satırdan 396'sı; CI alt sınırı %85 |
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
| Kabul setinden ayrı holdout | Tamamlandı | `evaluation/task1-holdout.csv` | Hash, denge ve 0 örtüşme testi |
| Bağımsız syntax referansı | Tamamlandı | `scripts/evaluate_task1_syntax_reference.py` | Ham ve politika uyumlu oran birlikte |
| 200 adreslik canlı DNS karşılaştırması | Tamamlandı | `scripts/evaluate_task1_live_challenge.py` | Harici strict syntax, tekilleştirilmiş/tekrar denemeli canlı DNS snapshot, corpus hash'i ve 200/200 geçerlilik kontrolü |
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

## Bağımsız değerlendirme katmanları

258 satırlık `%100` sonuç kabul/regresyon setidir. Buna ek olarak kabul setiyle
sıfır adres örtüşmeli, sınıf başına 100 örnek içeren 300 satırlık dondurulmuş
holdout seti çalıştırılır; güncel sonuç `%100` ve geçerli→geçerli olmayan FPR `%0`'dır.

Syntax katmanı ayrıca Unlicense lisanslı `python-email-validator==2.3.0` ile 473
deterministik örnekte karşılaştırılır. Ham uyum `%89,43`; açıkça belgelenmiş girdi
normalizasyonu, TLD ve RFC 5321 SMTPUTF8 oktet politikaları hariç uyum `%100`'dür.
İlk ham ölçüm `%87,32` iken geçersiz Punycode A-label kabulü bulunmuş ve açık
IDNA doğrulamasıyla düzeltilmiştir. Bu sayılar diğer projelerin farklı veri seti
sonuçlarıyla doğrudan karşılaştırılmaz. Metodoloji:
`docs/task1-holdout-methodology.md`.

Karşılaştırılabilir tek bir canlı ölçüm için ayrıca 200 adreslik dondurulmuş corpus,
harici strict syntax/DNS referansı ve proje resolver'ı birlikte çalıştırılır. Corpus;
tarafsız adres, rol hesabı, disposable domain, sağlayıcı typo'su, SMTPUTF8, geçersiz
syntax, bulunmayan alt alan adı ve gerçek hayattaki dış boşluk vakalarını içerir.
Resolver timeout/NoNameservers veya proje `DNS_LOOKUP_ERROR` sonucu puana katılmaz;
bu nedenle 200 örneğin tamamı puanlanmadıkça ölçüm geçerli sayılmaz. Sonuç dosyaları:
`evaluation/task1-live-challenge-results.json` ve
`evaluation/task1-live-challenge-report.md`.

## Yeniden üretme

```bash
python -m pytest
python scripts/evaluate.py --review evaluation/human-review.csv --require-human-review \
  --output evaluation/results.json --markdown evaluation/report.md
python scripts/evaluate_task1_holdout.py \
  --output evaluation/task1-holdout-results.json --markdown evaluation/task1-holdout-report.md
python scripts/evaluate_task1_syntax_reference.py \
  --output evaluation/task1-syntax-reference-results.json --markdown evaluation/task1-syntax-reference-report.md
python scripts/evaluate_task1_live_challenge.py --acknowledge-live-dns
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

200 adreslik canlı değerlendirme de ağ bağımlılığı nedeniyle CI'a konmaz. Sonuç ancak
`measurement_valid=true`, `scored_cases=200` ve corpus SHA-256 değeri raporda birlikte
bulunduğunda paylaşılır.
