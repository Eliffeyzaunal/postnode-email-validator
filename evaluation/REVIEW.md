# Etiketlerin bağımsız kontrolü

`evaluation.csv` içindeki önceki 200 sentetik örneğe `edge-cases.json` üzerinden
58 farklı örnek eklenmiştir. Ayrıca 7 liste senaryosu varsayılan eşiklerle ölçülür.
Hiçbir örnek gerçek müşteri verisi değildir. Taslak etiketler kod çıktısından
otomatik kopyalanmaz; ölçüm bu beklentilerle uyuşmazsa hata verir.

PDF en az 200 elle etiketlenmiş örnek ister. Bu dosyaları oluşturmak bu insan
incelemesinin yerine geçmez. Eski rapordaki kanıtlanmamış “elle gözden geçirilmiş”
ifadesi kaldırılmıştır. Güncel rapor onaylanan ve bekleyen sayıları ayrı gösterir.

1. `human-review.csv` dosyasını UTF-8 CSV olarak açın; CSV destekli bir düzenleyici
   kullanın. `email_json` sütunu adresi JSON metni olarak gösterir: dış çift tırnaklar
   gösterim içindir; `\n`, `\r` ve `\t` gerçek girdide satır sonu/sekme demektir.
   Böylece boşluk ve satır sonu sınır örnekleri görünür kalır.
2. Adres ve sabit DNS durumuna bakarak kararı kontrol edin. `proposed_status`
   taslak karardır; sınıflandırıcının tahmini değildir.
3. Gerçekten incelediğiniz satırlarda `reviewed_status` alanına `gecerli`, `supheli`
   veya `gecersiz`; `reviewer` alanına adınızı; `reviewed_at` alanına gerçek inceleme
   tarihini `YYYY-MM-DD` biçiminde yazın. Gerekçeniz farklıysa `notes` alanına ekleyin.
4. `case_id` ve `case_sha256` alanlarını değiştirmeyin. Bunlar hangi örneğin
   incelendiğini korur. Toplu otomatik onay vermeyin ve yapılmayan incelemeyi yazmayın.
5. En az 200 satır tamamlanınca aşağıdaki komutu çalıştırın. Çelişkiler tartışılıp
   çözülmeden veya örnek değiştikten sonra yeniden incelenmeden şart sağlanmış sayılmaz.

```bash
python scripts/evaluate.py --require-human-review --output evaluation/results.json --markdown evaluation/report.md
```

İnceleme tamamlanmadan normal ölçüm yapılabilir; insan incelemesi şartı raporda
ayrıca başarısız/bekliyor kalır. CI teknik davranışı ölçer, insan onayı uydurmaz.
Taslaklara göre %100 sonuç, gerçek dünya veya bağımsız veri doğruluğu değildir.

## Tamamlanma kaydı

258 örneğin tamamı Elif Feyza Ünal tarafından 10 Eylül 2026 tarihinde kontrol
edilmiş ve taslak kararlarla uyuştuğu kaydedilmiştir. Sonuç: 258 onaylı, 0
bekleyen, 0 uyuşmazlık.

Adres örnekleri tek başına çalıştırılır. Liste bağlamına bağlı yinelenme, ardışık
üretim ve alan adı yoğunluğu kuralları ayrı senaryolarda kontrol edilir. Destek
kapsamı dışındaki SMTPUTF8/Unicode yerel bölüm ve tırnaklı adres biçimleri bu
değerlendirmeden kapsamlı standart uyumluluğu sonucu çıkarılmasına izin vermez.
