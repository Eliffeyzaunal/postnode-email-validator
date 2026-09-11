# Görev 1 — 200 Adreslik Canlı DNS Karşılaştırması

Bu ölçüm, bağımsız strict syntax referansı ve iki tarafa da verilen tek bir
canlı DNS anlık görüntüsüyle proje kararını karşılaştırır. Mailbox varlığını
sınamaz ve müşteri verisi kullanmaz.

- Ölçüm zamanı: 2026-09-11T07:55:13.492181+00:00
- Ortam: Windows; Python 3.13.1
- Resolver: 1.1.1.1, 8.8.8.8, 9.9.9.9
- DNS snapshot: 59 tekil domain; 0 teknik hata
- DNS durumları: `{"a_fallback": 7, "mx": 30, "no_mail_host": 8, "nxdomain": 14}`
- Corpus: 200 adres; SHA-256 `c3cd5673d6cdf29dd2f611cb4f70a17aee52c76d62d268112e06e822cb01939e`
- Puanlanan: 200; teknik nedenle puanlanmayan: 0
- Ölçüm geçerli: evet
- Accuracy: %95.00
- Macro precision: %95.37
- Macro recall: %94.15
- Macro F1: %94.31
- Geçerli → geçerli olmayan FPR: %0.00
- Belgelenmiş trim politikası hariç accuracy: %100.00

## Sınıf metrikleri

| Sınıf | Precision | Recall | F1 | Destek |
|---|---:|---:|---:|---:|
| `gecerli` | %86.11 | %100.00 | %92.54 | 62 |
| `supheli` | %100.00 | %100.00 | %100.00 | 81 |
| `gecersiz` | %100.00 | %82.46 | %90.38 | 57 |

## Confusion matrix

| Beklenen \ Üretilen | `gecerli` | `supheli` | `gecersiz` |
|---|---:|---:|---:|
| `gecerli` | 62 | 0 | 0 |
| `supheli` | 0 | 81 | 0 |
| `gecersiz` | 10 | 0 | 47 |

## Kategori başarısı

| Kategori | Doğru/Toplam | Başarı |
|---|---:|---:|
| `disposable_domain` | 20/20 | %100.00 |
| `invalid_syntax` | 25/25 | %100.00 |
| `neutral_public_domain` | 60/60 | %100.00 |
| `nonexistent_subdomain` | 15/15 | %100.00 |
| `provider_typo` | 20/20 | %100.00 |
| `role_account` | 40/40 | %100.00 |
| `smtputf8` | 10/10 | %100.00 |
| `strict_outer_space` | 0/10 | %0.00 |

## Yanlış sınıflandırmalar

- `live-191` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-192` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-193` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-194` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-195` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-196` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-197` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-198` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-199` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)
- `live-200` / `strict_outer_space`: beklenen `gecersiz`, üretilen `gecerli` (VALID)

## Sınırlar

- No SMTP RCPT TO or mailbox-existence probe is performed.
- Only public domain-level DNS is queried; no customer data is used.
- The shared DNS snapshot prevents transient resolver bias but does not independently validate the project's DNS algorithm.
- Role, disposable, typo and SMTPUTF8 are risk-policy labels, not proof of non-delivery.
- DNS changes over time; the timestamp, resolver and corpus hash must accompany the metric.
- This result is not directly comparable with a different project's differently labeled corpus.
