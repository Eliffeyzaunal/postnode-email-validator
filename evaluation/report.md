# Değerlendirme Raporu

Bu ölçüm sentetik veri ve sabit DNS cevaplarıyla üretilmiştir. Gerçek müşteri doğruluğu iddiası değildir.

- Adres örneği: 258
- Taslak etiketlere göre doğruluk: %100.00
- Macro precision: %100.00
- Macro recall: %100.00
- Macro F1: %100.00
- Geçerli → geçersiz: 0/99
- Geçerli → geçersiz yanlış pozitif oranı: %0.00
- Liste senaryoları: 7/7 başarılı
- İnsan tarafından doğrulanmış etiket: 258
- İnsan incelemesi bekleyen: 0
- En az 200 insan onaylı etiket şartı: sağlandı

## Sınıf metrikleri

| Sınıf | Precision | Recall | F1 | Destek |
|---|---:|---:|---:|---:|
| `gecerli` | %100.00 | %100.00 | %100.00 | 99 |
| `supheli` | %100.00 | %100.00 | %100.00 | 76 |
| `gecersiz` | %100.00 | %100.00 | %100.00 | 83 |

## Confusion matrix

| Beklenen \ Üretilen | `gecerli` | `supheli` | `gecersiz` |
|---|---:|---:|---:|
| `gecerli` | 99 | 0 | 0 |
| `supheli` | 0 | 76 | 0 |
| `gecersiz` | 0 | 0 | 83 |

## Kategori bazlı başarı

| Kategori | Doğru/Toplam | Başarı |
|---|---:|---:|
| `combined` | 3/3 | %100.00 |
| `disposable` | 3/3 | %100.00 |
| `dns` | 4/4 | %100.00 |
| `domain` | 8/8 | %100.00 |
| `false_positive` | 4/4 | %100.00 |
| `legacy_generated` | 200/200 | %100.00 |
| `length_boundary` | 6/6 | %100.00 |
| `local_part` | 11/11 | %100.00 |
| `normalization` | 4/4 | %100.00 |
| `role` | 5/5 | %100.00 |
| `syntax` | 6/6 | %100.00 |
| `typo` | 4/4 | %100.00 |

Eski 200 üretilmiş örneğe farklı yazım, normalizasyon, DNS, rol, disposable ve uzunluk sınırı örnekleri eklenmiştir.
Adresler tek tek ölçülür; yinelenme, ardışık üretim ve yoğunluk senaryoları ayrıca varsayılan eşiklerle ölçülür.
SMTPUTF8 yerel bölüm desteği ayrıca birim testlerle doğrulanır; bu 258 satırlık ölçüme dahil değildir. Tırnaklı posta kutusu/dot-atom dışı biçimler destek kapsamı dışındadır.

İnsan incelemesi: `evaluation/human-review.csv` içindeki reviewed_status, reviewer ve reviewed_at alanlarını gerçek inceleyen doldurur.
Çelişen veya değişmiş örneğe ait incelemeler otomatik onay sayılmaz. Ayrıntılar `evaluation/results.json` dosyasındadır.

Yeniden üretim: `python scripts/evaluate.py --output evaluation/results.json --markdown evaluation/report.md`
