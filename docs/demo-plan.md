# 15 Dakikalık Demo Planı

## Demo öncesi hazırlık

```bat
.venv\Scripts\activate
docker compose up -d mysql
set TEST_MYSQL_DATABASE_URL=mysql+pymysql://postnode:postnode_dev_password@127.0.0.1:3306/postnode_validator?charset=utf8mb4
```

Gerçek müşteri adresi veya üretim IP'si kullanılmaz. Demo, `config/monitored-assets.example.json` ve belirleyici sahte DNS cevaplarıyla yapılır.

## 0:00-1:30 - Amaç ve kapsam

- Görev 1'in gönderim öncesi adres riskini, Görev 2'nin ise gönderim altyapısının blocklist durumunu izlediğini anlat.
- Çıktının ana uygulamaya bağlı olmayan FastAPI/CLI servisi olduğunu belirt.
- Canlı sorgunun sağlayıcı şartları ve uygun resolver doğrulanana kadar kapalı olduğunu söyle.

## 1:30-3:00 - Yapılandırma

- `config/monitored-assets.example.json` içinde IP ve domain örneklerini göster.
- `config/blocklists.json` içinde sağlayıcı zone, varlık tipi, önem seviyesi ve dönüş kodu tablolarını göster.
- SORBS'un sorgulanmadığını ve `unavailable` olarak raporlandığını açıkla.

## 3:00-6:00 - Tek seferlik kontrol

```bat
python -m app.blocklist.cli --output outputs\blocklist-report.json
```

Çıktıda şu dört durumun ayrımını göster: `listed`, `not_listed`, `query_error`, `unavailable`. Bir Spamhaus veya SURBL sonucunda dönüş kodunu, sebebi ve kaldırma bağlantısını göster.

## 6:00-8:00 - Durum değişikliği bildirimi

- İlk listelenmede `listed` bildirimi oluştuğunu anlat.
- Aynı sonuç tekrarlandığında yeni bildirim üretilmediğini göster.
- `samples/blocklist-notification-listed.json` ve `samples/blocklist-notification-delisted.json` dosyalarıyla giriş/çıkış örneğini göster.

## 8:00-10:00 - Saatlik izleme ve sağlık

```bat
python -m app.blocklist.scheduler_cli --once
```

- Normal kullanımda `python -m app.blocklist.scheduler_cli` komutunun varsayılan saatlik çalıştığını belirt.
- `/api/v1/blocklists/monitor/status` çıktısındaki son başarı, sonraki tur ve `missed` alanlarını göster.

## 10:00-12:00 - 30 günlük rapor

```bat
python -m app.blocklist.report_cli --days 30
```

- Toplam koşu/kontrol sayısı, sağlayıcı bulunabilirliği, olay sayıları ve güncel listelenmeleri göster.
- Geçmişin varsayılan 90 gün tutulduğunu ve 30 günden kısa saklama ayarının reddedildiğini belirt.

## 12:00-14:00 - Test ve otomasyon

```bat
python -m pytest
```

- 45 testin geçtiğini söyle.
- GitHub Actions'ta Python 3.11/3.12 ile MySQL entegrasyonu, değerlendirme ve benchmark adımlarını göster.
- DNS hatasının temiz cevap sayılmadığını ve durum geçişlerinin test edildiğini vurgula.

## 14:00-15:00 - Sınırlamalar ve sonraki adım

- Varsayılan modun kasıtlı olarak sahte DNS olduğunu belirt.
- Gerçek sorguya geçiş için uygun resolver, sağlayıcı kullanım izni ve sorgu limitlerinin doğrulanması gerektiğini söyle.
- Bildirimin şu anda JSON/MySQL olduğunu; gerekirse sonraki aşamada webhook/e-posta kanalı eklenebileceğini belirt.

## Demo sırasında sorun olursa

- MySQL başlamazsa `docker compose ps` ile durumu kontrol et.
- Ağ erişimi kullanma; `BLOCKLIST_DNS_MODE=fake` ayarını koru.
- Terminal çıktısı gecikirse repodaki örnek JSON dosyalarını göster.
- Gerçek müşteri verisi veya canlı gönderim altyapısı ile deneme yapma.
