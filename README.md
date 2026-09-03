# Postnode Liste Hijyeni ve Adres Doğrulama Servisi

PDF'deki Görev 1 için hazırlanmış, ana uygulamadan bağımsız FastAPI servisidir. CSV/TXT listesini `gecerli`, `supheli` veya `gecersiz` olarak sınıflandırır; sabit sebep kodları üretir, liste özeti çıkarır ve gizlilik güvenli geçmişi SQLite'ta saklar.

## Özellikler

- Sözdizimi, uzunluk, yerel bölüm ve alan adı kontrolleri
- MX sorgusu; MX yoksa A/AAAA geri dönüşünün ayrı sınıflandırılması
- Kalıcı SQLite DNS önbelleği ve toplu işlemde alan adı tekilleştirme
- Güncellenebilir disposable-domain, rol hesabı ve typo veri dosyaları
- Yazım hatası için düzeltme önerisi
- Yinelenen adres, ardışık üretilmiş yerel bölüm ve alan adı yoğunluğu analizi
- Toplam/karar dağılımı, ilk 10 alan adı ve tahmini bounce oranı
- FastAPI, CLI ve doğrudan Python kütüphane kullanımı
- Açık e-posta adresi DB'ye, CSV çıktısına veya API cevabına yazılmaz

SMTP `RCPT TO`, catch-all tespiti ve ücretli doğrulama servisi özellikle kullanılmaz.

## Kurulum ve çalıştırma

Python 3.11+ gerekir.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Tarayıcı: `http://127.0.0.1:8000/docs`

Windows'ta hızlı başlatmak için `run_windows.bat` dosyasına çift tıklanabilir; sanal ortamı kurar, bağımlılıkları yükler, servisi açar ve Swagger ekranını tarayıcıda başlatır.

Docker seçeneği:

```bash
docker compose up --build
```

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

CLI özeti terminale JSON yazar; satır sonuçlarını maskeli CSV'ye kaydeder.

## Kütüphane kullanımı

```python
from app.config import Settings
from app.validator import EmailValidatorService

service = EmailValidatorService(Settings())
batch_id, summary, results = service.validate_many(["user@gmail.com"])
```

## Veritabanı

`dns_cache` alan adı sonucunu TTL ile saklar. `batches` işlem özetini, `validation_results` ise satır numarası, maskeli adres, SHA-256 özet, alan adı, karar ve sebep kodlarını saklar. Açık e-posta adresi saklanmaz. SQLite dosyası varsayılan olarak `data/validator.db` konumundadır; `.env` ile değiştirilebilir.

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

`benchmark/emails-10000.csv` tam 10.000 satırdır. Benchmark, gerçek SQLite kayıt yolunu kullanarak hem boş DNS cache ile ilk koşuyu hem de dolu cache ile ikinci koşuyu ölçer. Ağ değişkenliğini ortadan kaldırmak için DNS cevabı sabittir; ilk koşuda dört tekil alan adı için dört sorgu, ikinci koşuda ise kalıcı cache sayesinde sıfır sorgu beklenir. İki koşuda toplam 20.000 sonuç satırının SQLite'a yazıldığı da doğrulanır.

GitHub Actions, her `main` push ve pull request işleminde Python 3.11 ve 3.12 üzerinde testleri, değerlendirmeyi ve benchmark'ı otomatik çalıştırır.

## Liste kaynakları ve güncelleme

`data/disposable_domains.txt` küçük başlangıç listesidir. Üretim öncesinde açık kaynak [disposable_email_blocklist.conf](https://github.com/disposable-email-domains/disposable-email-domains/blob/main/disposable_email_blocklist.conf) dosyasıyla ayda bir güncellenmeli; değişiklik test ve kod incelemesinden geçmelidir. Uygulama çalışırken internetten otomatik indirme yapmaz; bu, sonucun denetlenebilir ve belirleyici kalmasını sağlar.

`role_accounts.txt` ve `domain_typos.json` da kod değişmeden güncellenebilir veri dosyalarıdır. Typo tespiti yalnızca açık eşleme kullanır; bulanık benzerlik kullanılmaması yanlış pozitif riskini azaltır.

## Güvenlik ve gizlilik

- Gerçek müşteri listelerini repoya koymayın.
- Uygulama açık adresi loglamaz ve kalıcı depoya yazmaz.
- API/CLI çıktısı satır numarası, maskeli adres ve hash ile eşlenir.
- SQLite, yetkili olmayan kullanıcıların erişemeyeceği dizinde tutulmalıdır.
- Dosya boyutu ve satır sayısı sınırlandırılmıştır.
- SMTP mailbox doğrulaması yapılmaz.

## Sınırlamalar

MX kaydı mailbox'ın gerçekten var olduğunu kanıtlamaz. Disposable listesi güncelliği kadar güçlüdür. Rol hesapları ve liste anomalileri risk sinyalidir; kesin geçersizlik değildir. DNS çıktısı TTL süresince önbellekten gelir.
