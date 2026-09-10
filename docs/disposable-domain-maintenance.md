# Disposable-domain listesi bakım politikası

## Kaynak ve lisans

- Kaynak: `disposable-email-domains/disposable-email-domains`
- Dosya: `disposable_email_blocklist.conf`
- Lisans: Public Domain dedication; tam metin
  `docs/licenses/disposable-email-domains-LICENSE.txt` içindedir.
- Kullanılan snapshot commit'i ve SHA-256 özeti
  `data/disposable_domains.meta.json` içinde tutulur.

Kaynak, listedeki alan adlarının geçmişte disposable olduğunu ancak güncel
durumlarının garanti edilemeyeceğini açıklar. Bu nedenle eşleşme kesin ret değil,
yalnızca `DISPOSABLE_DOMAIN` şüphesi üretir.

## Güncelleme sıklığı ve süreç

Liste ayda bir kez, uygulama dışında ve kod incelemesiyle güncellenir:

```bash
python scripts/update_disposable_domains.py --source-commit UPSTREAM_COMMIT
python -m pytest tests/test_task1_address_rules.py tests/test_validator.py
git diff -- data/disposable_domains.txt data/disposable_domains.meta.json
```

Script IDNA normalizasyonu, küçük harf, sıralama ve tekilleştirme uygular. Kaynak
1.000 kaydın altına düşerse olası kesik/bozuk indirmeyi kabul etmez. Uygulama
başlarken yalnızca repodaki gözden geçirilmiş snapshot'ı okur; runtime ağ
bağımlılığı ve sessiz liste değişikliği yoktur.

Güncellemede büyük silinmeler, bilinen kurumsal/kalıcı sağlayıcılarla çakışmalar
ve testlerdeki yanlış pozitif örnekleri ayrıca incelenmelidir.
