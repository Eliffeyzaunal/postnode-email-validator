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
