# Postnode E-posta Güvenliği Servisleri

[![Testler](https://github.com/Eliffeyzaunal/postnode-email-validator/actions/workflows/tests.yml/badge.svg)](https://github.com/Eliffeyzaunal/postnode-email-validator/actions/workflows/tests.yml)

Görev 1'in şartname, kod, test ve ölçüm eşlemesi: [`TASK1-REPORT.md`](TASK1-REPORT.md).

PDF'deki Görev 1 için liste hijyeni/adres doğrulama, Görev 2 için periyodik kara liste izleme ve Görev 4 için SES bounce/şikâyet sınıflandırması sağlayan bağımsız FastAPI/CLI servisidir. Üretimde MySQL, otomatik birim testlerinde aynı SQLAlchemy repository kodu üzerinden geçici SQLite kullanılır.

## Özellikler

- Sözdizimi, uzunluk, yerel bölüm ve alan adı kontrolleri
- MX sorgusu; MX yoksa A/AAAA geri dönüşünün ayrı sınıflandırılması
- Kalıcı MySQL DNS önbelleği ve toplu işlemde alan adı tekilleştirme
- Kaynak/lisans bilgili 8.746 disposable-domain snapshot'ı ve aylık güncelleme scripti
- 55 role-account terimi ve yanlış pozitifi sınırlayan yapılandırılmış varyasyonlar
- 30 kesin typo eşlemesi + 27 güvenilir sağlayıcıyla kontrollü fuzzy öneri
- IDN/Punycode ve kontrollü SMTPUTF8 yerel bölüm desteği
- Yazım hatası için düzeltme önerisi
- Yinelenen adres, ardışık üretilmiş yerel bölüm ve alan adı yoğunluğu analizi
- Toplam/karar dağılımı, ilk 10 alan adı ve tahmini bounce oranı
- FastAPI, CLI ve doğrudan Python kütüphane kullanımı
- Açık e-posta adresi DB'ye, CSV çıktısına veya API cevabına yazılmaz
- Spamhaus, SpamCop, Barracuda ve SURBL için resmî test girdileriyle kara liste kontrolü
- Ağdan bağımsız, tekrar üretilebilir sahte DNS cevapları
- Listeye giriş/çıkış durum değişikliklerini MySQL/JSON olarak kaydetme
- SORBS hizmetini `unavailable` olarak ayrıca raporlama
- Varsayılan saatlik izleme, kalıcı kalp atışı ve kaçırılan tur tespiti
- 90 gün saklanan geçmişten 30 günlük özet rapor
- Test için belirleyici sahte DNS, açıkça etkinleştirildiğinde canlı DNSBL istemcisi
- SES, SMTP ve RFC 3463 alanlarını kullanan kural tabanlı bounce/şikâyet sınıflandırması
- Kod değişmeden genişletilebilen kaynaklı kural tablosu ve bilinmeyen örüntü raporu
- Kalıcı/geçici hata güvenlik ölçümü ve 360 anonim sentetik değerlendirme olayı

SMTP `RCPT TO`, catch-all tespiti ve ücretli doğrulama servisi özellikle kullanılmaz.

## Kurulum ve çalıştırma

Python 3.11+ ve MySQL 8 gerekir. En kolay kurulum Docker iledir:

```bash
docker compose up --build
```

Tarayıcı: `http://127.0.0.1:8000/docs`

Uygulamayı VS Code terminalinde çalıştırmak için önce yalnızca MySQL'i başlatın:

```bash
docker compose up -d mysql
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
cp .env.example .env              # Windows CMD: copy .env.example .env
uvicorn app.main:app --reload
```

Windows'ta hızlı başlatmak için `run_windows.bat` dosyasına çift tıklanabilir; Docker'daki MySQL'i, sanal ortamı, bağımlılıkları, saatlik blocklist izleyicisini, API'yi ve Swagger ekranını sırayla başlatır. Bu yol izleyiciyi de çalıştırdığı için `BLOCKLIST_MONITOR_REQUIRED=true` ayarını API'ye aktarır; başlamamış veya durmuş izleyici sağlık kontrolünü başarısız yapar.

## API

| Yöntem | Yol | Amaç |
|---|---|---|
| GET | `/health` | Veritabanı, blocklist modu ve zamanlayıcı sağlık kontrolü |
| GET | `/api/v1/reason-codes` | Sabit sebep kodu sözlüğü |
| POST | `/api/v1/validate` | Tek adres doğrulama |
| POST | `/api/v1/validate/batch` | JSON listesi doğrulama |
| POST | `/api/v1/validate/file` | CSV/TXT yükleme, en fazla 10.000 adres |
| GET | `/api/v1/batches/{id}` | Yükleme özeti |
| GET | `/api/v1/batches/{id}/results` | Sayfalı sonuçlar |
| GET | `/api/v1/batches/{id}/export` | Maskeli CSV dışa aktarma |
| GET | `/api/v1/blocklists/providers` | Sağlayıcı ve kullanılabilirlik listesi |
| POST | `/api/v1/blocklists/check` | Tek seferlik IP/alan adı kara liste kontrolü |
| GET | `/api/v1/blocklists/runs/{id}` | Kontrol geçmişi ve sonuçları |
| GET | `/api/v1/blocklists/runs/{id}/notifications` | Durum değişikliği bildirimleri |
| GET | `/api/v1/blocklists/monitor/status` | Zamanlayıcı sağlığı ve kaçırılan tur bilgisi |
| GET | `/api/v1/blocklists/reports/history?days=30` | Geçmiş/sağlayıcı bulunabilirlik raporu |
| POST | `/api/v1/events/classify` | Tek SES-benzeri olayı sınıflandırma |
| POST | `/api/v1/events/classify/batch` | En fazla 1.000 olayı toplu sınıflandırma |
| GET | `/api/v1/events/rules` | Etkin kurallar, aksiyonlar ve kaynaklar |

Tek adres örneği:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"email":"test@gmial.com"}'
```

Dosya örneği:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate/file \
  -F "file=@samples/sample_emails.csv"
```

Örnek cevapta adres maskelenir:

```json
{
  "status": "supheli",
  "reason_codes": ["DOMAIN_TYPO"],
  "reason_details": [{
    "code": "DOMAIN_TYPO",
    "description": "Alan adı yaygın bir yazım hatasıyla eşleşiyor."
  }],
  "masked_email": "t***t@gmial.com",
  "suggestion": "t***t@gmail.com"
}
```

## CLI

```bash
python -m app.cli samples/sample_emails.csv --output outputs/results.csv
```

CLI, `.env` içindeki MySQL bağlantısını kullanır; özeti terminale JSON yazar ve satır sonuçlarını maskeli CSV'ye kaydeder. Farklı bir sunucu için `--database-url` verilebilir.

Görev 2'nin örnek IP/alan adlarını kara listelerde kontrol etmek için:

```bash
python -m app.blocklist.cli --output outputs/blocklist-report.json
```

Komut `config/monitored-assets.example.json` girdilerini okur, belirleyici sonuçları terminale ve JSON dosyasına yazar, aynı koşuyu MySQL'e kaydeder. FastAPI'de boş gövdeyle `POST /api/v1/blocklists/check` aynı örnekleri kullanır; istenirse gövdede özel `assets` listesi verilebilir. API yanıtındaki `dns_mode` alanı sonucun `fake` veya `live` DNS ile üretildiğini açıkça gösterir.

Saatlik izleyiciyi başlatmak için:

```bash
python -m app.blocklist.scheduler_cli
```

Bir zamanlayıcı turunu elle doğrulamak ve çıkmak için:

```bash
python -m app.blocklist.scheduler_cli --once
```

Son 30 günün JSON raporunu üretmek için:

```bash
python -m app.blocklist.report_cli --days 30
```

Görev 4 örnek olaylarını sınıflandırmak için:

```bash
python -m app.bounce_classifier.cli samples/ses-events-task4.jsonl \
  --output outputs/bounce-classifications.jsonl \
  --report outputs/bounce-summary.json
```

CLI, düz JSON/JSONL ile Amazon SES'in `notificationType/eventType`, `bounce`,
`complaint` ve alıcı nesnelerini; ayrıca SNS `Notification` zarfındaki SES JSON'unu
kabul eder. Çok alıcılı bildirimler CLI ve toplu API'de alıcı başına ayrılır; tek olay
API'si bu girdiyi açıklayıcı bir `422` yanıtıyla toplu uca yönlendirir. Çıktıya açık
e-posta veya tanı metni yazılmaz; anahtarlı alıcı özeti, doğrulanmış alan adı, karar,
aksiyon, güven ve kural kimliği yazılır.

Docker ile `docker compose up --build` çalıştırıldığında API'den ayrı `blocklist-monitor` servisi de başlar. Böylece birden fazla API worker'ının aynı kontrolü tetiklemesi engellenir.

## Görev 2 - kara liste izleme

Varsayılan `BLOCKLIST_DNS_MODE=fake` ayarında sağlayıcıların resmî pozitif test girdileri ve `data/blocklist_fake_dns.json` içindeki sahte cevaplar kullanılır. Böylece testler erişim kotası, DNS çözücü politikası veya internet bağlantısından etkilenmez ve aynı girdi aynı kararı üretir. Uygulama şu dört sonucu birbirinden ayırır:

- `listed`: Belgelenmiş pozitif dönüş kodu alındı.
- `not_listed`: Sahte DNS cevabı `NXDOMAIN` oldu.
- `query_error`: Timeout/SERVFAIL/erişim/kota hatası oluştu; temiz sonuç sayılmaz.
- `unavailable`: Sağlayıcı kullanılamıyor; SORBS EOL durumu bu şekilde tutulur.

İlk kontrolde listelenmiş bir kayıt için `listed`, sonraki kontrolde temizlenirse `delisted` bildirimi üretilir. Aynı durum değişmeden devam ediyorsa tekrar bildirim üretilmez. Bildirimler şimdilik JSON ve `blocklist_notifications` tablosuna yazılır; e-posta/webhook entegrasyonu yapılmaz.

Sağlayıcı tanımları `config/blocklists.json`, örnek varlıklar `config/monitored-assets.example.json`, dönüş kodlarının açıklamalı tablosu ise [`docs/blocklist-code-table.md`](docs/blocklist-code-table.md) içindedir. Örnek giriş/çıkış bildirimleri `samples/blocklist-notification-listed.json` ve `samples/blocklist-notification-delisted.json` dosyalarında bulunur.

Zamanlayıcı her turun başlangıç, başarı ve hata zamanını kalıcı olarak kaydeder. Sonraki turun zamanı `BLOCKLIST_INTERVAL_SECONDS` ile hesaplanır; bu zaman `BLOCKLIST_MISSED_GRACE_SECONDS` kadar aşılırsa `/monitor/status` cevabı `missed` olur. Böylece süreç aniden çöktüğünde eski kalp atışı üzerinden gecikme fark edilir. Geçmiş varsayılan 90 gün tutulur; 30 günden daha kısa saklama ayarı kabul edilmez.

30 günlük rapordaki `availability_rate`, ilgili sağlayıcı için başarılı `listed + not_listed` cevaplarının tüm kontrollere oranıdır. `query_error` ve `unavailable` cevapları başarılı kabul edilmez. Örnek teslim çıktısı `samples/blocklist-30-day-report.json` dosyasındadır. Bu örnek hızlandırılmış 720 saatlik **simülasyondan** üretilir; gerçek 30 günlük işletim geçmişi değildir. Yeniden üretim ve kaynak bilgisi [`samples/README.md`](samples/README.md) dosyasındadır.

### DNS modu, eski kayıtlar ve sağlık kontrolü

- Yeni koşuların DNS modu `blocklist_run_modes` tablosunda kalıcı tutulur.
  `blocklist_scoped_states` durumları `(asset_id, provider_id, dns_mode)` anahtarıyla
  ayırır; zamanlayıcı kalp atışları da moda göre ayrılır. Aynı veritabanında `fake`
  ve `live` kullanıldığında raporlar, durum geçişleri ve bildirimler birbirini etkilemez.
- Geçmiş raporu varsayılan olarak etkin `BLOCKLIST_DNS_MODE` değerini kullanır.
  `GET /api/v1/blocklists/reports/history?days=30&dns_mode=live` veya rapor CLI'ındaki
  `--dns-mode live` seçeneğiyle belirli bir mod okunabilir. Koşu ve bildirim
  ayrıntıları da kalıcı `dns_mode` bilgisi döndürür.
- Güncellemeden önceki kayıtların modu bilinmediği için `legacy` olarak gösterilir.
  Eski tablolar ve kayıtlar silinmez veya mevcut ayara bakılarak yeniden etiketlenmez.
  Bunları `GET /api/v1/blocklists/reports/history?days=30&dns_mode=legacy` ya da
  `python -m app.blocklist.report_cli --dns-mode legacy` ile okuyabilirsiniz.
  Eski durumlar bu raporda arşiv anlık görüntüsüdür; güncel DNS doğrulaması değildir.
  Yeni sürümde her modun ilk kontrolü yeni bir durum başlangıcı oluşturur; halen
  listelenmiş varlıklar için bir kez yeni `listed` bildirimi üretilebilir.
  Otomatik saklama temizliği yalnızca çalıştığı modun yeni geçmişine uygulanır;
  `legacy` geçmişe dokunmaz.
- Güncelleme sırasında API ve izleyiciyi birlikte durdurup birlikte yeni sürüme
  geçirin; eski ve yeni sürümü aynı veritabanına eşzamanlı yazdırmayın. Compose
  için `docker compose stop validator blocklist-monitor` ardından
  `docker compose up -d --build` kullanın. Veritabanı hacmini silmek gerekmez.
- `current_listings` son sorguda doğrulanmış listelenmeleri içerir.
  `unresolved_listings`, daha önce listelenmiş ancak son sorgusu `query_error`
  veya `unavailable` olan kayıtları; son bilinen durum, ilk tespit zamanı ve neden
  bilgisiyle korur. Kesin `not_listed` sonucu gelmeden bunlar temizlenmiş sayılmaz.
- Yalnız API/tek seferlik CLI kullanımında `BLOCKLIST_MONITOR_REQUIRED=false`
  varsayılandır. Periyodik izleme bekleniyorsa `true` yapın: başlamamış, durmuş
  veya gecikmiş izleyici `/health` üzerinden HTTP 503 üretir. Compose izleyiciyi
  de başlattığı için API konteynerinde bu ayarı `true` tutar. Sağlıklı bir izleyici
  kalp atışı, tüm DNS sağlayıcılarının erişilebilir olduğunu garanti etmez;
  sağlayıcı hataları ayrıca raporda görünür.

Dosya doğrulamasındaki ayrıştırma, DNS/veritabanı işlemleri ve yanıt hazırlama
iş parçacığı havuzunda çalışır; büyük bir yükleme API olay döngüsünü bloke etmez.
Dosya ve satır sınırları geçerliliğini korur.

Canlı DNSBL sorgusu yalnızca sağlayıcının kullanım şartları ve uygun DNS çözümleyicisi doğrulandıktan sonra açılmalıdır:

```env
BLOCKLIST_DNS_MODE=live
BLOCKLIST_NAMESERVERS=192.0.2.53
```

Spamhaus için sıradan bir genel çözümleyici sürekli temiz sonuç varsayımına yol açabilir. Uygulama erişim ve kota dönüş kodlarını `query_error` olarak raporlar; bunları `not_listed` saymaz.

Canlı moda geçiş öncesi uygulanacak güvenli doğrulama sırası ve başarı ölçütleri [`docs/live-dns-readiness.md`](docs/live-dns-readiness.md) dosyasında belgelenmiştir. Uygun resolver bilgisi sağlanana kadar canlı ön kontrol tamamlanmış sayılmaz ve sahte DNS varsayılanı korunur.

### Sorgu kullanım şartları

| Sağlayıcı | Ücretsiz kullanım/limit notu | Bu projedeki karar |
|---|---|---|
| Spamhaus | Genel aynalar küçük/orta ölçekli ticari olmayan kullanımda makul hacim için ücretsizdir; sorgu kaynağı kendi recursive resolver'ı veya ECS destekli çözümleyiciyle tanımlanabilir olmalıdır. Ticari/yüksek hacim DQS gerektirir. | Sahte DNS varsayılan; canlı modda uygun resolver zorunlu. |
| SURBL | FQS, 1.000'den az kullanıcısı olan veya günde 250.000'den az mesaj tarayan uygun küçük kuruluşlar için ücretsizdir; ücretli ürüne gömme kapsam dışıdır. | Sahte DNS varsayılan; üretim öncesi kullanım uygunluğu kontrol edilir. |
| SpamCop | Resmî sayfa sayısal bir DNS sorgu kotası yayımlamaz ve SCBL'nin agresif olabileceğini, tek başına engelleme yerine puanlamada kullanılmasını önerir. | `medium` önem; kesin engelleme kararı verilmez. |
| Barracuda | Resmî lookup/removal sayfalarında sayısal ücretsiz kota belirtilmez; canlı DNS erişimi ve kayıt gereksinimi dağıtım öncesi doğrulanmalıdır. | Sahte DNS varsayılan; doğrulanmamış erişim temiz sonuç sayılmaz. |
| SORBS | Proofpoint hizmet için EOL süreci ilan etmiştir. | Sorgulanmaz, `unavailable` raporlanır. |

Kaynaklar: [Spamhaus Fair Use](https://www.spamhaus.org/blocklists/dnsbl-fair-use-policy/), [SURBL Usage Policy](https://surbl.org/usage-policy), [SpamCop SCBL açıklaması](https://www.spamcop.net/fom-serve/cache/297.html), [Barracuda lookup](https://www.barracudacentral.org/lookups), [SORBS EOL](https://proofpoint.my.site.com/community/s/article/End-of-Life-EOL-process-for-the-Spam-and-Open-Relay-Blocking-System-SORBS-service).

## Görev 4 - bounce ve şikâyet sınıflandırma

`app/bounce_classifier` kütüphanesi olayları yalnızca açıklanabilir kurallarla dokuz
ana kategoriye ayırır: kalıcı geçersiz adres, kutu dolu, geçici sunucu hatası,
içerik/politika reddi, blocklist reddi, itibar/oran sınırı, otomatik yanıt, şikâyet
ve bilinmeyen. Her sonuç alt sebep, önerilen aksiyon, güven düzeyi, kalıcılık ve
eşleşen kural kimliğini içerir.

Kural öncelikleri ve kaynakları [`docs/bounce-rule-table.md`](docs/bounce-rule-table.md),
makinece okunan asıl tanımlar `config/bounce_rules.json` içindedir. Her tanımda
sağlayıcı kapsamı, resmî kaynak, olumlu örnek ve karşı örnek zorunludur. SES
`not-spam` ve `auth-failure` geri bildirimleri kalıcı spam baskılamasından önce
ayrı değerlendirilir. Yeni bir tanı metni kuralı JSON'a eklenebilir; Python kodu değişmez.

360 anonim sentetik olayın taslak ölçümünü yeniden üretmek için:

```bash
python scripts/generate_bounce_evaluation.py
python scripts/evaluate_bounce_classifier.py
```

Rapor kategori doğruluğunu, bilinmeyen oranını, en sık 20 güvenli bilinmeyen
örüntüyü ve kalıcı/geçici ayrımını ayrı gösterir. Özellikle geçici bir olayı kalıcı
sayma oranı ölçülür. Mevcut taslak değerlendirme %100 şartname uyumu ve sıfır
geçici→kalıcı hata göstermektedir; bu gerçek müşteri doğruluğu iddiası değildir.
Görev kabulü için en az 300 satırlık bağımsız insan kontrolü hâlâ gereklidir;
akış [`evaluation/bounce-REVIEW.md`](evaluation/bounce-REVIEW.md) içinde açıklanır.

## Süreç ve demo belgeleri

- Günlük 3-5 satırlık çalışma kayıtları: [`docs/progress-notes.md`](docs/progress-notes.md)
- Hafta sonu 15 dakikalık anlatım ve komut sırası: [`docs/demo-plan.md`](docs/demo-plan.md)
- Canlı DNSBL geçiş kontrol listesi: [`docs/live-dns-readiness.md`](docs/live-dns-readiness.md)

## Kütüphane kullanımı

```python
from app.config import Settings
from app.validator import EmailValidatorService

service = EmailValidatorService(Settings())
batch_id, summary, results = service.validate_many(["user@gmail.com"])
```

## Veritabanı

`dns_cache` alan adı sonucunu TTL ile saklar. `batches` işlem özetini, `validation_results` ise satır numarası, maskeli adres, SHA-256 özet, alan adı, karar ve sebep kodlarını saklar. Açık e-posta adresi saklanmaz.

Üretim ve normal geliştirme çalışması `.env` içindeki `DATABASE_URL` üzerinden MySQL kullanır. Repository SQLAlchemy ile yazılmıştır; testler aynı tablo ve sorgu kodunu geçici SQLite veritabanlarında hızlı ve izole biçimde çalıştırır. GitHub Actions ayrıca MySQL 8.4 üzerinde gerçek repository entegrasyonunu doğrular.

Görev 2 için `blocklist_runs` koşu bilgisini, `blocklist_results` her sağlayıcı sonucunu, `blocklist_states` son bilinen durumu ve ilk görülme zamanını, `blocklist_notifications` yalnızca durum değişikliği olaylarını, `blocklist_monitor_status` son kalp atışını, `blocklist_monitor_events` ise zamanlayıcı başlangıç/başarı/hata geçmişini saklar.

## Karar mantığı

1. Syntax veya alan adı kesin hatalıysa `gecersiz`.
2. DNS sorgusu NXDOMAIN ya da MX/A/AAAA yok sonucu verirse `gecersiz`.
3. DNS teknik hata verirse `supheli`; hiçbir zaman `gecersiz` değildir.
4. A/AAAA fallback, disposable, rol hesabı, typo veya liste anomalisi varsa `supheli`.
5. Hiçbir bulgu yoksa `gecerli`.

Geçerli adresi yanlışlıkla geçersiz saymamak için belirsiz bütün durumlar `supheli` sınıfına gider.

Tahmini bounce oranı gerçek teslimat ölçümü değildir; `invalid + 0.25 × suspicious` sayısının toplama oranı olan açıkça belgelenmiş bir risk göstergesidir.

## Sebep kodları

| Kod | Açıklama |
|---|---|
| VALID | Tüm etkin kontrollerden geçti. |
| EMPTY_EMAIL | Alan boş. |
| INVALID_SYNTAX | Temel sözdizimi hatalı. |
| EMAIL_TOO_LONG | Toplam uzunluk 254'ü aşıyor. |
| LOCAL_PART_TOO_LONG | Yerel bölüm 64'ü aşıyor. |
| INVALID_LOCAL_PART | Yerel bölüm karakter/nokta kuralı hatalı. |
| INVALID_DOMAIN | Alan adı etiketi veya uzunluğu hatalı. |
| SMTPUTF8_REQUIRED | Unicode yerel bölüm geçerli; gönderim altyapısının SMTPUTF8 desteği doğrulanmalı. |
| DOMAIN_NXDOMAIN | Alan adı DNS'te yok. |
| DOMAIN_NO_MAIL_HOST | MX/A/AAAA yok. |
| DOMAIN_A_FALLBACK | MX yok ama A/AAAA var. |
| DNS_LOOKUP_ERROR | DNS sorgusu teknik/geçici hata verdi. |
| DISPOSABLE_DOMAIN | Tek kullanımlık alan adı listesinde. |
| ROLE_ACCOUNT | Rol hesabı yerel bölümü. |
| DOMAIN_TYPO | Bilinen alan adı yazım hatası. |
| DUPLICATE_ADDRESS | Liste içinde yinelenen adres. |
| GENERATED_SEQUENCE | Ardışık üretilmiş yerel bölüm örüntüsü. |
| DOMAIN_CONCENTRATION | Tek alan adı oranı anomali eşiğini aşıyor. |

## Test, değerlendirme ve benchmark

```bash
pytest
python scripts/evaluate.py
python scripts/evaluate_bounce_classifier.py
python scripts/benchmark.py
```

`evaluation/evaluation.csv` içindeki 200 sentetik örnek ve `evaluation/edge-cases.json`
ile toplam 258 adres ölçülür; ayrıca 7 liste senaryosu varsayılan eşiklerle çalışır.
Etiketler önce taslak olarak hazırlanmış, ardından 258 örneğin tamamı Elif Feyza
Ünal tarafından 10 Eylül 2026 tarihinde kontrol edilerek `evaluation/human-review.csv`
dosyasına kaydedilmiştir.
`python scripts/evaluate.py --require-human-review` komutu en az 200 onaylanmış
etiket ve çözümlenmemiş uyuşmazlık olmamasını denetler. Ayrıntılar
[`evaluation/REVIEW.md`](evaluation/REVIEW.md) dosyasındadır. Sabit DNS kullanılır;
taslak etiketlerle uyum, gerçek müşteri doğruluğu iddiası değildir.

Görev 1 raporu accuracy, üç sınıf için precision/recall/F1, macro ortalamalar,
confusion matrix, kategori bazlı başarı ve geçerli→geçersiz yanlış pozitif oranını
ayrı gösterir. Güncel sentetik/sabit-DNS sonucu `%100` accuracy, precision,
recall ve macro F1 ile `%0` geçerli→geçersiz FPR'dır. Ayrıntılar
[`evaluation/report.md`](evaluation/report.md) ve [`TASK1-REPORT.md`](TASK1-REPORT.md)
içindedir; bu sayılar üretim doğruluğu olarak sunulmaz.

`benchmark/emails-10000.csv` tam 10.000 satırdır. Benchmark, üretimde kullanılan MySQL kayıt yoluyla hem boş DNS cache ile ilk koşuyu hem de dolu cache ile ikinci koşuyu ölçer. Ağ değişkenliğini ortadan kaldırmak için DNS cevabı sabittir; ilk koşuda dört tekil alan adı için dört sorgu, ikinci koşuda ise kalıcı cache sayesinde sıfır sorgu beklenir. İki koşuda toplam 20.000 sonuç satırının MySQL'e yazıldığı doğrulanır ve benchmark kendi oluşturduğu satırları bitişte temizler.

GitHub Actions, her `main` push ve pull request işleminde Python 3.11 ve 3.12 üzerinde SQLite birim testlerini, gerçek MySQL 8.4 entegrasyon testini, değerlendirmeyi ve MySQL benchmark'ını otomatik çalıştırır.

Ayrı Görev 1 coverage adımı yalnızca adres doğrulama modüllerini ölçer, XML/JSON
kanıtı üretir ve toplam kapsam `%85` altına düşerse CI'ı başarısız yapar. Güncel
yerel ölçüm `%86,35`'tir.

Gerçek DNS gecikmesini ölçmek için `python scripts/benchmark_live_dns.py
--acknowledge-live-dns` kullanılabilir. Bu ölçüm herkese açık 20 alan adıyla,
müşteri verisi olmadan çalışır ve tüm cevaplar teknik hata ise geçersiz sayılır.
Gerçek DNS sonucu, deterministik 10.000 adres/MySQL benchmark'ıyla hız üstünlüğü
iddiası amacıyla karşılaştırılmaz.

CI, ölçülmüş süreleri `delivery-evidence-python-*` adlı indirilebilir dosya
paketlerinde saklar. Windows'ta `collect_delivery_evidence.bat` aynı ölçümleri
yerel geliştirme MySQL'i üzerinde çalıştırıp `outputs/evidence/` klasörüne yazar.
MySQL bulunmazsa işlem başarısız olur; SQLite sonucu MySQL ölçümü gibi sunulmaz.
İnsan etiket incelemesi ve CI sonuçları ayrı kanıtlar olarak raporlanır.

Kara liste testleri IP ters çevirme sorgusunu, SURBL bit maskesini, Spamhaus hata kodlarını, SORBS `unavailable` sonucunu, mükerrer bildirim engelini, `listed → not_listed` geçişini, canlı DNS hata ayrımını, zamanlayıcı kalp atışını, kaçırılan turu, 30 günlük raporu, API geçmişini ve MySQL kayıt yolunu kapsar.

Görev 4 testleri 22 kuralın olumlu ve karşı örneğini, kural önceliğini, düz ve
yerel SES olaylarını, API/CLI çıktısındaki gizliliği, JSON üzerinden kod değişmeden
kural eklenmesini, 360 satırlık veri bütünlüğünü ve kalıcı/geçici hata metriklerini kapsar.

## Liste kaynakları ve güncelleme

`data/disposable_domains.txt`, açık kaynak [disposable_email_blocklist.conf](https://github.com/disposable-email-domains/disposable-email-domains/blob/main/disposable_email_blocklist.conf) dosyasının 8.746 alan adlı, kaynak commit'i ve SHA-256 özeti kaydedilmiş snapshot'ıdır. `scripts/update_disposable_domains.py` ile ayda bir güncellenir; değişiklik test ve kod incelemesinden geçer. Uygulama çalışırken internetten otomatik indirme yapmaz. Kaynak, lisans ve bakım adımları [`docs/disposable-domain-maintenance.md`](docs/disposable-domain-maintenance.md) içindedir.

`role_accounts.txt`, `role_variant_suffixes.txt`, `domain_typos.json` ve `popular_email_domains.txt` kod değişmeden güncellenebilir. Role varyasyonu yalnızca gözden geçirilmiş son eklerle; fuzzy typo ise aynı TLD'de, benzersiz en yakın sonuçla ve güvenilir sağlayıcı allowlist'iyle çalışır. Fuzzy bulgu kesin ret üretmez.

## Güvenlik ve gizlilik

- Gerçek müşteri listelerini repoya koymayın.
- Uygulama açık adresi loglamaz ve kalıcı depoya yazmaz.
- API/CLI çıktısı satır numarası, maskeli adres ve hash ile eşlenir.
- E-posta özeti anahtarlı HMAC-SHA256 ile üretilir; `EMAIL_HASH_SECRET` üretimde güçlü ve benzersiz bir değerle değiştirilmelidir.
- MySQL parolaları yalnızca ortam değişkenlerinde tutulmalı; `.env` repoya eklenmemelidir. Docker Compose içindeki geliştirme parolaları üretimde kullanılmamalıdır.
- Dosya boyutu ve satır sayısı sınırlandırılmıştır.
- SMTP mailbox doğrulaması yapılmaz.
- API, görev kapsamı gereği kimlik doğrulama içermez; internete doğrudan açılmamalı, güvenilir ağ veya kimlik doğrulayan bir ağ geçidi arkasında çalıştırılmalıdır.

## Sınırlamalar

MX kaydı mailbox'ın gerçekten var olduğunu kanıtlamaz. Disposable listesi güncelliği kadar güçlüdür. Rol hesapları ve liste anomalileri risk sinyalidir; kesin geçersizlik değildir. DNS çıktısı TTL süresince önbellekten gelir.

Görev 2 sahte DNS modunda gerçek DNSBL ağına sorgu göndermez. Canlı mod dış ağ durumuna ve sağlayıcı politikasına bağlı olduğu için belirleyici değildir; yalnızca bilinçli olarak etkinleştirilir. Zamanlayıcı tek ayrı süreç olarak çalıştırılmalıdır. Bildirimler JSON/veritabanı kaydıdır; e-posta ve webhook kanalları kapsam dışıdır. SORBS hizmet sonlandırma nedeniyle sorgulanamaz ve `unavailable` raporlanır.

Görev 4 değerlendirmesi anonim sentetik olaylardan oluşur. Gerçek `ses_events`
dışa aktarımı sağlanmadan sağlayıcı dağılımı ve üretim doğruluğu ölçülemez; gerçek
veri geldiğinde önce anonimleştirilmeli, ardından aynı CLI ve insan inceleme akışında çalıştırılmalıdır.
