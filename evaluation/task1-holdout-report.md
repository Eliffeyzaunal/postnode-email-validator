# Görev 1 Dondurulmuş Holdout Raporu

Bu sonuç, 258 satırlık kabul/regresyon setinden ayrı ve sıfır satır örtüşmeli
dondurulmuş challenge setinde ölçülmüştür. Veri müşteri trafiği değildir.

- Örnek: 300 (her sınıfta 100)
- Accuracy: %100.00
- Macro precision: %100.00
- Macro recall: %100.00
- Macro F1: %100.00
- Geçerli → geçerli olmayan FPR: %0.00
- Yanlış sınıflandırma: 0
- Kabul seti örtüşmesi: 0
- Dataset SHA-256: `596bfc798839f00825c1e009b87db9bc188a7b3e327880c4fecdd607e8973b1f`

## Sınıf metrikleri

| Sınıf | Precision | Recall | F1 | Destek |
|---|---:|---:|---:|---:|
| `gecerli` | %100.00 | %100.00 | %100.00 | 100 |
| `supheli` | %100.00 | %100.00 | %100.00 | 100 |
| `gecersiz` | %100.00 | %100.00 | %100.00 | 100 |

## Confusion matrix

| Beklenen \ Üretilen | `gecerli` | `supheli` | `gecersiz` |
|---|---:|---:|---:|
| `gecerli` | 100 | 0 | 0 |
| `supheli` | 0 | 100 | 0 |
| `gecersiz` | 0 | 0 | 100 |

## Kategori bazlı başarı

| Kategori | Doğru/Toplam | Başarı |
|---|---:|---:|
| `ascii_dot_atom` | 15/15 | %100.00 |
| `disposable` | 20/20 | %100.00 |
| `dns_definitive` | 40/40 | %100.00 |
| `dns_uncertain` | 20/20 | %100.00 |
| `domain_false_positive` | 15/15 | %100.00 |
| `domain_typo` | 20/20 | %100.00 |
| `idn_domain` | 20/20 | %100.00 |
| `invalid_domain` | 10/10 | %100.00 |
| `invalid_length` | 5/5 | %100.00 |
| `invalid_local_part` | 25/25 | %100.00 |
| `invalid_syntax` | 20/20 | %100.00 |
| `role_account` | 20/20 | %100.00 |
| `role_false_positive` | 20/20 | %100.00 |
| `smtputf8` | 20/20 | %100.00 |
| `valid_neutral` | 30/30 | %100.00 |

## Sınırlar

- Synthetic/curated addresses are used; there is no customer or SMTP RCPT TO data.
- The balanced class distribution is not an estimate of production prevalence.
- Static DNS scenarios measure decision logic; live DNS performance is reported separately.
- The corpus must remain frozen and must not be used to tune rules after results are recorded.

Bu set kural geliştirmek için kullanılmaz. Bir hata bulunursa önce sonuç kayda alınır;
düzeltmenin başarısı yeni bir holdout sürümüyle ölçülür.

Yeniden üretim: `python scripts/evaluate_task1_holdout.py --output evaluation/task1-holdout-results.json --markdown evaluation/task1-holdout-report.md`
