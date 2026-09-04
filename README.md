# Postnode E-posta Güvenliği Servisleri

PDF'deki Görev 1 için liste hijyeni/adres doğrulama, Görev 2'nin ilk aşaması için kara liste izleme sağlayan bağımsız FastAPI servisidir. Üretimde MySQL, otomatik birim testlerinde aynı SQLAlchemy repository kodu üzerinden geçici SQLite kullanılır.

## Özellikler

- Sözdizimi, uzunluk, yerel bölüm ve alan adı kontrolleri
- MX sorgusu; MX yoksa A/AAAA geri dönüşünün ayrı sınıflandırılması
- Kalıcı MySQL DNS önbelleği ve toplu işlemde alan adı tekilleştirme
- Güncellenebilir disposable-domain, rol hesabı ve typo veri dosyaları
- Yazım hatası için düzeltme önerisi
- Yinelenen adres, ardışık üretilmiş yerel bölüm ve alan adı yoğunluğu analizi
- Toplam/karar dağılımı, ilk 10 alan adı ve tahmini bounce oranı
- FastAPI, CLI ve doğrudan Python kütüphane kullanımı
- Açık e-posta adresi DB'ye, CSV çıktısına veya API cevabına yazılmaz
- Spamhaus, SpamCop, Barracuda ve SURBL için resmî test girdileriyle kara liste kontrolü
- Ağdan bağımsız, tekrar üretilebilir sahte DNS cevapları
- Listeye giriş/çıkış durum değişikliklerini MySQL/JSON olarak kaydetme
- SORBS hizmetini `unavailable` olarak ayrıca raporlama

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

Windows'ta hızlı başlatmak için `run_windows.bat` dosyasına çift tıklanabilir; Docker'daki MySQL'i, sanal ortamı, bağımlılıkları, API'yi ve Swagger ekranını sırayla başlatır.

## API

| Yöntem | Yol | Amaç |
|---|---|---|
| GET | `/health` | Sağlık kontrolü |
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

Komut `config/monitored-assets.example.json` girdilerini okur, belirleyici sonuçları terminale ve JSON dosyasına yazar, aynı koşuyu MySQL'e kaydeder. FastAPI'de boş gövdeyle `POST /api/v1/blocklists/check` aynı örnekleri kullanır; istenirse gövdede özel `assets` listesi verilebilir.

## Görev 2 — kara liste izleme (ilk aşama)

Bu aşamada canlı DNSBL sorgusu yerine sağlayıcıların resmî pozitif test girdileri ve `data/blocklist_fake_dns.json` içindeki sahte cevaplar kullanılır. Böylece testler erişim kotası, DNS çözücü politikası veya internet bağlantısından etkilenmez. Uygulama şu dört sonucu birbirinden ayırır:

- `listed`: Belgelenmiş pozitif dönüş kodu alındı.
- `not_listed`: Sahte DNS cevabı `NXDOMAIN` oldu.
- `query_error`: Timeout/SERVFAIL/erişim/kota hatası oluştu; temiz sonuç sayılmaz.
- `unavailable`: Sağlayıcı kullanılamıyor; SORBS EOL durumu bu şekilde tutulur.

İlk kontrolde listelenmiş bir kayıt için `listed`, sonraki kontrolde temizlenirse `delisted` bildirimi üretilir. Aynı durum değişmeden devam ediyorsa tekrar bildirim üretilmez. Bildirimler şimdilik JSON ve `blocklist_notifications` tablosuna yazılır; e-posta/webhook entegrasyonu yapılmaz.

Sağlayıcı tanımları `config/blocklists.json`, örnek varlıklar `config/monitored-assets.example.json`, dönüş kodlarının açıklamalı tablosu ise [`docs/blocklist-code-table.md`](docs/blocklist-code-table.md) içindedir. Örnek giriş/çıkış bildirimleri `samples/blocklist-notification-listed.json` ve `samples/blocklist-notification-delisted.json` dosyalarında bulunur.

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

Görev 2 için `blocklist_runs` koşu bilgisini, `blocklist_results` her sağlayıcı sonucunu, `blocklist_states` son bilinen durumu ve ilk görülme zamanını, `blocklist_notifications` ise yalnızca durum değişikliği olaylarını saklar.

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
python scripts/benchmark.py
```

`evaluation/evaluation.csv` 200 sentetik ve elle gözden geçirilmiş etiket içerir. Değerlendirme gerçek DNS değişimlerinden etkilenmemek için aynı dosyadaki sabit DNS durumlarını kullanır. Bu sonuç bir kural-kapsam kontrolüdür; gerçek müşteri doğruluğu iddiası değildir.

`benchmark/emails-10000.csv` tam 10.000 satırdır. Benchmark, üretimde kullanılan MySQL kayıt yoluyla hem boş DNS cache ile ilk koşuyu hem de dolu cache ile ikinci koşuyu ölçer. Ağ değişkenliğini ortadan kaldırmak için DNS cevabı sabittir; ilk koşuda dört tekil alan adı için dört sorgu, ikinci koşuda ise kalıcı cache sayesinde sıfır sorgu beklenir. İki koşuda toplam 20.000 sonuç satırının MySQL'e yazıldığı doğrulanır ve benchmark kendi oluşturduğu satırları bitişte temizler.

GitHub Actions, her `main` push ve pull request işleminde Python 3.11 ve 3.12 üzerinde SQLite birim testlerini, gerçek MySQL 8.4 entegrasyon testini, değerlendirmeyi ve MySQL benchmark'ını otomatik çalıştırır.

Kara liste testleri IP ters çevirme sorgusunu, SURBL bit maskesini, Spamhaus hata kodlarını, SORBS `unavailable` sonucunu, mükerrer bildirim engelini, `listed → not_listed` geçişini, API geçmişini ve MySQL kayıt yolunu kapsar.

## Liste kaynakları ve güncelleme

`data/disposable_domains.txt` küçük başlangıç listesidir. Üretim öncesinde açık kaynak [disposable_email_blocklist.conf](https://github.com/disposable-email-domains/disposable-email-domains/blob/main/disposable_email_blocklist.conf) dosyasıyla ayda bir güncellenmeli; değişiklik test ve kod incelemesinden geçmelidir. Uygulama çalışırken internetten otomatik indirme yapmaz; bu, sonucun denetlenebilir ve belirleyici kalmasını sağlar.

`role_accounts.txt` ve `domain_typos.json` da kod değişmeden güncellenebilir veri dosyalarıdır. Typo tespiti yalnızca açık eşleme kullanır; bulanık benzerlik kullanılmaması yanlış pozitif riskini azaltır.

## Güvenlik ve gizlilik

- Gerçek müşteri listelerini repoya koymayın.
- Uygulama açık adresi loglamaz ve kalıcı depoya yazmaz.
- API/CLI çıktısı satır numarası, maskeli adres ve hash ile eşlenir.
- MySQL parolaları yalnızca ortam değişkenlerinde tutulmalı; `.env` repoya eklenmemelidir.
- Dosya boyutu ve satır sayısı sınırlandırılmıştır.
- SMTP mailbox doğrulaması yapılmaz.

## Sınırlamalar

MX kaydı mailbox'ın gerçekten var olduğunu kanıtlamaz. Disposable listesi güncelliği kadar güçlüdür. Rol hesapları ve liste anomalileri risk sinyalidir; kesin geçersizlik değildir. DNS çıktısı TTL süresince önbellekten gelir.

Görev 2'nin bu ilk aşaması gerçek DNSBL ağına sorgu göndermez. Saatlik otomatik zamanlayıcı, 30 günlük bulunabilirlik raporu ve gerçek bildirim kanalları sonraki aşamaya bırakılmıştır. SORBS hizmet sonlandırma nedeniyle sorgulanamaz ve `unavailable` raporlanır.
