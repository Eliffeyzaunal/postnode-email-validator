# Görev 1 bağımsız değerlendirme metodolojisi

Görev 1 için üç ölçüm birbirinden ayrılır; hiçbir sayı gerçek müşteri trafiğinin
teslim edilebilirlik doğruluğu olarak sunulmaz.

## 1. Kabul/regresyon seti

`evaluation/evaluation.csv` ve `evaluation/edge-cases.json` toplam 258 sentetik
örnek içerir. Bu set belgelenmiş proje kurallarının değişikliklerden sonra aynı
sonucu vermesini denetler. `%100` sonucu yalnız bu sözleşmeyle uyumu gösterir.

## 2. Dondurulmuş challenge holdout

`evaluation/task1-holdout.csv`, kabul setiyle adres bazında sıfır örtüşmeye sahip
300 örnektir. Her karar sınıfında 100 kayıt vardır. Syntax, IDN, SMTPUTF8,
disposable, role-account, typo, yanlış-pozitif tuzakları ve sabit DNS senaryoları
ayrı kategorilerde tutulur.

Dosya SHA-256 ile dondurulmuştur. Hash hesabı Windows `CRLF` ve POSIX `LF` satır
sonlarını aynı kanonik metne dönüştürür; içerik değişiklikleri yine reddedilir.
Değerlendirme kodu bu özeti ve sınıf dengesini
doğrular. Sonuç görüldükten sonra kural ayarlamak için bu dosya değiştirilmez;
yeni bir değerlendirme gerektiğinde yeni sürüm ve yeni hash oluşturulur.

Bu setin bir bölümü `python-email-validator` syntax testlerinden uyarlanmış,
bir bölümü RFC sınırlarından ve proje politikasından bağımsız olarak derlenmiştir.
Disposable örnekleri kaynaklı listenin, eski sekiz domainlik değerlendirmede
bulunmayan kayıtlarıdır. Bu bölüm bir genelleme ölçümü değil, geniş snapshot'ın
çalıştığına dair kapsam kontrolüdür.

## 3. Bağımsız syntax referans uyumu

`scripts/evaluate_task1_syntax_reference.py`, 473 deterministik örneği projenin
kural kodundan bağımsız `python-email-validator==2.3.0` uygulamasıyla karşılaştırır.
Bu yalnız ikili syntax kabul/ret uyumudur; DNS veya mailbox varlığını ölçmez.

Ham oran bütün farkları korur. `policy_aligned_agreement`, yalnız adı önceden
`policy_*` olarak belirlenmiş şu açık politika farklarını dışarıda tutar:

- girdi çevresindeki boşlukların temizlenmesi,
- DNS kök noktasının normalleştirilmesi,
- tek karakterli son domain etiketinin reddi,
- SMTPUTF8 yerel bölümünde RFC 5321'in 64 oktet sınırının uygulanması.

İlk çapraz çalıştırmada `%87,32` ham uyum ölçülmüş ve geçersiz `xn--` A-label
değerlerinin standart kütüphane codec'i tarafından geçirilebildiği bulunmuştur.
Uygulama açık `idna` doğrulamasına geçirilmiş; hata kaydı sonuç dosyasında
korunmuştur. Son ölçüm ham `%89,43`, belgelenmiş politika farkları hariç `%100`
uyumdur. Ham oranın daha düşük olması gizlenmez.

## 4. 200 adreslik bağımsız canlı DNS değerlendirmesi

`evaluation/task1-live-challenge.csv`, tam 200 benzersiz adres içerir: 60 tarafsız
public-domain, 40 rol hesabı, 20 disposable, 20 sağlayıcı typo'su, 25 bozuk syntax,
15 bulunmayan public alt alan adı, 10 SMTPUTF8 ve 10 dış boşluk vakası.

Bağımsız `python-email-validator` strict syntax kararı alınır. Corpus'taki geçerli
adreslerin domainleri tekilleştirilir; yapılandırılmış DNS sunucuları yoklanır ve
her domain tek bir canlı DNS anlık görüntüsüne alınır. Teknik hatalar sınırlı sayıda
yeniden denenir. Aynı anlık görüntü hem beklenen karar hem proje çalıştırması için
kullanılır; böylece iki ardışık sorgu arasındaki geçici resolver farkı taraflardan
birini kayırmaz. Syntax veya domain mail kabulü başarısızsa beklenen sınıf
`gecersiz`; domain mail kabul ediyor ve önceden belirlenmiş risk kategorisi varsa
`supheli`; aksi durumda `gecerli` olur.

Timeout, NoNameservers veya `DNS_LOOKUP_ERROR` sonucu başarı/başarısızlık gibi
puanlanmaz. Tek bir örnek dahi teknik nedenle puanlanamazsa `measurement_valid=false`
olur ve komut hata koduyla biter. Böylece ağ arızası yapay doğruluk sayısına dönüşmez.
Ham oran dış boşluk konusundaki strict referans/ürün trim farkını korur; ayrıca bu
önceden belgelenmiş politika farkı hariç ikinci oran gösterilir.

Bu ölçüm SMTP `RCPT TO` yapmaz, mailbox varlığını kanıtlamaz ve gerçek kullanıcı
adresleri içermez. Bağımsız strict syntax referansı sağlar; paylaşılan snapshot
tasarımı projenin DNS algoritmasını bağımsız bir DNS uygulamasıyla doğrulamaz.
DNS zamana bağlı olduğundan rapor ancak ölçüm zamanı, resolver,
corpus SHA-256, `scored_cases=200` ve `measurement_valid=true` ile birlikte paylaşılır.

## Kaynaklar ve lisans

- `python-email-validator` test yaklaşımı ve seçili/adapte örnekler:
  <https://github.com/JoshData/python-email-validator/tree/main/tests>
- Kaynak lisansı: Unlicense; kopyası
  `docs/licenses/python-email-validator-UNLICENSE.txt`
- SMTP yerel bölüm uzunluğu: RFC 5321 §4.5.3.1.1
- SMTPUTF8: RFC 6531
- IDNA kavramları: RFC 5890 ve RFC 5891

## Tekrar üretme

```bash
python scripts/evaluate_task1_holdout.py \
  --output evaluation/task1-holdout-results.json \
  --markdown evaluation/task1-holdout-report.md

python scripts/evaluate_task1_syntax_reference.py \
  --output evaluation/task1-syntax-reference-results.json \
  --markdown evaluation/task1-syntax-reference-report.md

python scripts/evaluate_task1_live_challenge.py --acknowledge-live-dns
```

İki ayrı proje ancak aynı corpus, aynı sürüm, aynı politika ve aynı DNS koşuluyla
çalıştırıldığında sayısal olarak karşılaştırılabilir.

### Canli corpus DNS kararliligi notu (2026-09-11)

`throwawaymail.com` canli DNS karsilastirmasinda Cloudflare, Google ve Quad9 resolver'larinin tamaminda teknik `NoNameservers` sonucu verdigi icin iki ornek puanlanamiyordu. Canli corpusun disposable-domain kapsamini korumak icin bu iki ornek, ayni risk kategorisindeki ve canli MX cevabi alinabilen `yopmail.fr` ile degistirildi. Bu degisiklik urun karar mantigini degistirmez; corpus SHA-256 degeri yeniden dondurulmustur.

Canli corpus kararlilik notu: `throwawaymail.com` tum secili resolver'larda `NoNameservers` urettigi icin, ayni disposable kategorisinde canli DNS'i kararli olan `yopmail.fr` kullanildi. Ayni domainin iki cift ornegi oldugundan e-posta benzersizligini korumak icin ikinci ciftte `challenge.gamma` / `challenge.delta` local-part'lari kullanilir.
