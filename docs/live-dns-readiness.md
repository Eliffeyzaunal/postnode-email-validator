# Canlı DNSBL Geçiş Hazırlığı

## Mevcut karar

Proje varsayılan olarak `BLOCKLIST_DNS_MODE=fake` kullanır. Bu seçim, resmî test girdileri ve sahte DNS cevaplarıyla belirleyici sonuç alınmasını sağlar. Canlı mod kodu ve birim testleri hazırdır; ancak uygun DNS çözümleyicisi ve sağlayıcı kullanım koşulları doğrulanmadan üretim sorgusu açılmaz.

## Canlıya geçmeden önce zorunlu kontroller

- İzlenecek IP ve domainlerin test/anonimleştirilmiş varlıklar olduğu doğrulanır.
- Spamhaus tarafından kabul edilen kendi recursive resolver'ı veya izinli erişim yöntemi belirlenir.
- Her sağlayıcının ücretsiz/ticari kullanım şartları ve sorgu limiti yazılı olarak onaylanır.
- Yalnızca sağlayıcıların resmî pozitif test girdileriyle kontrollü doğrulama yapılır.
- `NXDOMAIN`, timeout, SERVFAIL, REFUSED, erişim engeli ve kota hatalarının ayrı sonuç verdiği kontrol edilir.
- A ve TXT cevaplarının birlikte okunabildiği; TXT sebebinin bildirimde saklandığı doğrulanır.
- Bilinmeyen `127.0.0.x` kodları temiz sonuç olarak yorumlanmaz.
- Sorgu sıklığı saatlik ve izlenen varlık sayısıyla sınırlı tutulur.

## Güvenli doğrulama sırası

Önce ağsız testler çalıştırılır:

```bat
set BLOCKLIST_DNS_MODE=fake
python -m pytest tests\test_blocklist_checker.py tests\test_blocklist_dns_live.py
python -m app.blocklist.cli --output outputs\blocklist-report.json
```

Yetkili resolver bilgisi sağlandıktan sonra yalnızca resmî test girdileriyle canlı ön kontrol yapılır:

```bat
set BLOCKLIST_DNS_MODE=live
set BLOCKLIST_NAMESERVERS=YETKILI_RESOLVER_IP
python -m app.blocklist.cli --output outputs\blocklist-live-preflight.json
```

`YETKILI_RESOLVER_IP` gerçek ve onaylı bir recursive resolver adresiyle değiştirilmeden komut çalıştırılmaz.

## Başarı ölçütleri

- Resmî pozitif girdiler beklenen `listed` sonucunu ve belgelenmiş dönüş kodunu üretir.
- Temiz test sonucu yalnızca gerçek `NXDOMAIN` cevabında `not_listed` olur.
- Erişim, kota ve DNS teknik sorunları `query_error` olur; sessizce temiz kabul edilmez.
- Aynı durumun ikinci kontrolünde yeni bildirim oluşmaz.
- Listeden çıkış geçişi `delisted` bildirimi oluşturur.
- Kontrol turu ve sonuçları MySQL'de kalıcı olarak görünür.

## Sağlayıcı durumu

| Sağlayıcı | Durum | Canlıya geçiş notu |
|---|---|---|
| Spamhaus ZEN/DBL | Hazır, varsayılan kapalı | Uygun resolver veya izinli erişim yöntemi zorunlu |
| SpamCop | Hazır, varsayılan kapalı | Agresif liste olduğundan `medium` önemle raporlanır |
| Barracuda | Hazır, varsayılan kapalı | DNS erişim/kayıt gereksinimi önceden doğrulanır |
| SURBL | Hazır, varsayılan kapalı | Kullanım uygunluğu ve sorgu hacmi doğrulanır |
| SORBS | Kullanılamıyor | EOL nedeniyle sorgu yapılmaz, `unavailable` döner |

UCEPROTECT mevcut zorunlu sağlayıcı listesinde değildir ve yüksek yanlış pozitif riski nedeniyle bu sürüme eklenmemiştir. İleride eklenirse ayrı düşük güven/önem seviyesinde değerlendirilir; tek başına engelleme kararı üretmez.

## Geri dönüş

Canlı ön kontrolde beklenmeyen kod, erişim sorunu veya sağlayıcı şartı belirsizliği görülürse `BLOCKLIST_DNS_MODE=fake` ayarına dönülür. Sorun belgelenmeden ve onay alınmadan canlı mod varsayılan yapılmaz.
