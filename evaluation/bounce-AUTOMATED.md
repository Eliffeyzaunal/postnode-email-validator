# Görev 4 Otomatik Değerlendirme

Bu proje Görev 4'ü manuel etiket girişi gerektirmeden, tekrar üretilebilir bir
otomatik doğrulama hattıyla kontrol eder.

Otomatik değerlendirme iki kanıtı birlikte kullanır:

1. `evaluation/bounce-evaluation.jsonl` içindeki 360 anonim sentetik SES-benzeri
   olay, beklenen kategori ve kalıcılık etiketleriyle sınıflandırıcı sonucunu
   karşılaştırır.
2. `config/bounce_rules.json` içindeki her kuralın `trigger_example` ve
   `counter_example` fixture'larını otomatik doğrular. Olumlu örnek kendi kuralını
   tetiklemeli, karşı örnek aynı kuralı tetiklememelidir.

Çalıştırma:

```bash
python scripts/evaluate_bounce_automated.py --require-acceptance
```

Otomatik kabul için:

- veri kümesi en az 300 olay içermeli,
- sentetik şartname uyumu en az %90 olmalı,
- dokuz beklenen kategori veri kümesinde bulunmalı,
- açık e-posta adresi bulunmamalı,
- tüm kural olumlu ve karşı örnekleri geçmeli,
- geçici bir olay kalıcı olarak sınıflandırılmamalıdır.

GitHub Actions aynı kontrolü Python 3.11 ve 3.12 üzerinde çalıştırır ve sonuçları
`outputs/evidence/` altında artifact olarak saklar.

Bu ölçüm gerçek müşteri veya üretim doğruluğu iddiası değildir. Sentetik veri ve
kural fixture'larına göre tekrar üretilebilir otomatik doğrulamadır. İnsan etiket
incelemesi otomatik CI kabulünün parçası değildir; ancak PDF'deki bağımsız insan
etiketli kabul maddesi veya üretim doğruluğu iddiası için `bounce-REVIEW.md` akışı
ayrıca tamamlanmalıdır.
