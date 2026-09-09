# Değerlendirme Raporu

Bu ölçüm sentetik veri ve sabit DNS cevaplarıyla üretilmiştir. Gerçek müşteri doğruluğu iddiası değildir.

- Adres örneği: 258
- Taslak etiketlere göre doğruluk: %100.00
- Geçerli → geçersiz: 0/99
- Liste senaryoları: 7/7 başarılı
- İnsan tarafından doğrulanmış etiket: 0
- İnsan incelemesi bekleyen: 258
- En az 200 insan onaylı etiket şartı: henüz sağlanmadı

Eski 200 üretilmiş örneğe farklı yazım, normalizasyon, DNS, rol, disposable ve uzunluk sınırı örnekleri eklenmiştir.
Adresler tek tek ölçülür; yinelenme, ardışık üretim ve yoğunluk senaryoları ayrıca varsayılan eşiklerle ölçülür.
Unicode/SMTPUTF8 yerel bölüm ve tırnaklı posta kutusu gibi destek kapsamı dışındaki biçimler bu ölçüme dahil değildir.

İnsan incelemesi: `evaluation/human-review.csv` içindeki reviewed_status, reviewer ve reviewed_at alanlarını gerçek inceleyen doldurur.
Çelişen veya değişmiş örneğe ait incelemeler otomatik onay sayılmaz. Ayrıntılar `evaluation/results.json` dosyasındadır.

Yeniden üretim: `python scripts/evaluate.py --output evaluation/results.json --markdown evaluation/report.md`
