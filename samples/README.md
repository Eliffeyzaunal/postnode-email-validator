# Görev 2 örnek teslim çıktıları

Bu klasördeki 30 günlük rapor **simülasyondur**. Servisin 30 gün canlı çalıştığını
veya gerçek varlıkların kara listede olduğunu göstermez.

`python scripts/generate_blocklist_samples.py` komutu:

- Geçici SQLite veritabanı ve resmi test girdileri için sahte DNS kullanır.
- Sabit, hızlandırılmış saatle 720 saatlik kontrolü gerçek kayıt/durum geçişi kodundan geçirir.
- Listelenme, çıkış, DNS hatası ve doğrulanamayan son listelenme senaryolarını üretir.
- Güncel modellerle doğrulanan JSON'ları ve `generation-manifest.json` kaynak notunu yazar.
- Mevcut uygulama veritabanına veya dış DNS ağına bağlanmaz.

`dns_mode` tüm çıktılarda `fake` değerindedir. `unresolved_listings`, daha önce
listelenmiş olup son sorgusu başarısız olan kaydı içerir. Sayılar elle yazılmamıştır;
senaryo değişirse komutla yeniden üretilir. Tekrarlanan listelenme ve çıkış
bildirim örnekleri aynı 720 saatlik senaryodan alınır.

## Görev 4 örnekleri

`ses-events-task4.jsonl`, dokuz ana kategorinin her biri için açık adres içermeyen
bir SES-benzeri örnek barındırır. `bounce-classifications-task4.jsonl` güvenli
çıktıyı, `bounce-summary-task4.json` ise kategori dağılımı ile bilinmeyen oranını
gösterir. Yeniden üretmek için:

```bash
python -m app.bounce_classifier.cli samples/ses-events-task4.jsonl \
  --output samples/bounce-classifications-task4.jsonl \
  --report samples/bounce-summary-task4.json
```
