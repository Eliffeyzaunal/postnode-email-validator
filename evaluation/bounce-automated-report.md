# Gorev 4 Otomatik Degerlendirme Raporu

- Veri kumesi: **360** anonim sentetik SES-benzeri olay
- Sentetik sartname uyumu: **%100.00**
- Kural fixture sayisi: **22**
- Geciciyi kalici sayma: **0**
- Otomatik kabul: **GECTI**

> Bu otomatik sentetik/fixture degerlendirmesidir. Gercek musteri veya uretim dogrulugu iddiasi degildir.

## Otomatik kabul kontrolleri

| Kontrol | Sonuc |
|---|---|
| `dataset_size_at_least_300` | PASS |
| `specification_accuracy_at_least_90_percent` | PASS |
| `all_required_categories_present` | PASS |
| `no_clear_email_in_dataset` | PASS |
| `all_rule_trigger_examples_pass` | PASS |
| `all_rule_counter_examples_pass` | PASS |
| `no_transient_event_classified_as_permanent` | PASS |

## Kategori sonuclari

| Kategori | Ornek | Dogru | Recall |
|---|---:|---:|---:|
| `automatic_response` | 40 | 40 | %100.00 |
| `blocklist_rejection` | 40 | 40 | %100.00 |
| `complaint` | 40 | 40 | %100.00 |
| `content_policy_rejection` | 40 | 40 | %100.00 |
| `mailbox_full` | 40 | 40 | %100.00 |
| `permanent_invalid_address` | 40 | 40 | %100.00 |
| `reputation_rate_limit` | 40 | 40 | %100.00 |
| `temporary_server_error` | 40 | 40 | %100.00 |
| `unknown` | 40 | 40 | %100.00 |
