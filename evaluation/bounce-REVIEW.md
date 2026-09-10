# Görev 4 İnsan Etiket İncelemesi

`bounce-evaluation.jsonl` dosyası 360 anonim ve sentetik SES-benzeri olay içerir.
Üretim verisi veya gerçek e-posta adresi içermez. `expected_category` alanları
test senaryosunun taslak şartname etiketidir; insan etiketi değildir.

İnceleme için `bounce-human-review.csv` dosyasında en az 300 satırda:

1. Olayı `bounce-evaluation.jsonl` içindeki aynı `event_id` ile bulun.
2. `human_category` alanına bağımsız kararınızı yazın.
3. `review_status` değerini `confirmed` yapın.
4. `reviewer` ve ISO tarih biçimindeki `reviewed_at` alanlarını doldurun.
5. Taslakla uyuşmuyorsa gerekçeyi `note` alanına yazın; taslağı körlemesine kopyalamayın.

Geçerli etiketler:

`permanent_invalid_address`, `mailbox_full`, `temporary_server_error`,
`content_policy_rejection`, `blocklist_rejection`, `reputation_rate_limit`,
`automatic_response`, `complaint`, `unknown`.

Kontrol komutu:

```bash
python scripts/evaluate_bounce_classifier.py --require-human-review
```

Komut, 300'den az doğrulanmış satır varsa veya insan etiketlerine göre doğruluk
%90'ın altındaysa başarısız olur. İnsan incelemesi tamamlanana kadar
`evaluation/bounce-report.md` içindeki %100 değer yalnızca sentetik şartname
etiketleriyle uyum olarak okunmalıdır.
