# Bounce ve Şikâyet Kural Tablosu

Kurallar `config/bounce_rules.json` dosyasından öncelik sırasıyla okunur. İlk eşleşme
kararı verir; hiçbir eşleşme yoksa olay bilerek `unknown` sınıfına alınır. Her kural
için sağlayıcı kapsamı, resmî kaynak, olumlu test örneği ve karşı örnek JSON dosyasında
birlikte tutulur. Böylece yeni kural Python kodu değiştirilmeden eklenebilir.

| Öncelik | Kural | Ana kategori | Tetikleyici özeti | Önerilen aksiyon |
|---:|---|---|---|---|
| 5 | `complaint_not_spam` | Şikâyet düzeltmesi | SES `not-spam` geri bildirimi | Baskılama yapma; insan incelemesi |
| 7 | `complaint_auth_failure` | İçerik/politika reddi | SES `auth-failure` geri bildirimi | SPF/DKIM/DMARC incelemesi |
| 10 | `complaint_event` | Şikâyet | SES `Complaint` olayı | Kalıcı baskılama ve kaynak liste incelemesi |
| 20 | `automatic_response_message` | Otomatik yanıt | Out-of-office/auto-reply metni | Yok say |
| 30 | `blocklist_rejection_message` | Blocklist reddi | Spamhaus, RBL, DNSBL vb. | Acil alarm ve gönderimi durdurma |
| 40 | `mailbox_full_subtype` | Kutu dolu | SES `MailboxFull` | Sınırlı gecikmeli tekrar |
| 50 | `mailbox_full_status` | Kutu dolu | RFC 3463 `4.2.2/5.2.2` | Sınırlı gecikmeli tekrar |
| 60 | `mailbox_full_message` | Kutu dolu | Quota/full metni | Sınırlı gecikmeli tekrar |
| 70 | `reputation_rate_limit` | İtibar/oran sınırı | Throttle/rate-limit/çok bağlantı | Gönderim hızını azaltma |
| 80 | `greylisting` | Geçici sunucu hatası | Greylist/try again later | Artan gecikmeyle tekrar |
| 90 | `content_rejected_subtype` | İçerik/politika reddi | SES `ContentRejected` | İnsan/İçerik incelemesi |
| 100 | `attachment_rejected_subtype` | İçerik/politika reddi | SES `AttachmentRejected` | Eki değiştir ve incele |
| 110 | `message_too_large_subtype` | İçerik/politika reddi | SES `MessageTooLarge` | Boyutu azalt |
| 120 | `authentication_policy` | İçerik/politika reddi | SPF/DKIM/DMARC | Kimlik doğrulamayı incele |
| 130 | `content_policy_status` | İçerik/politika reddi | RFC 3463 `4.7.x/5.7.x` | İnsan/politika incelemesi |
| 140 | `invalid_mailbox_message` | Kalıcı geçersiz adres | User/recipient unknown | Kalıcı baskılama |
| 150 | `invalid_mailbox_status` | Kalıcı geçersiz adres | Seçili RFC 3463 `5.1.x` kodları | Kalıcı baskılama |
| 160 | `invalid_domain_status` | Kalıcı geçersiz adres | `5.1.2/5.1.8` | Kalıcı baskılama |
| 170 | `ses_suppression_subtype` | Kalıcı geçersiz adres | SES suppression alt türleri | Gönderimi durdur ve nedeni incele |
| 180 | `temporary_network_status` | Geçici sunucu hatası | RFC 3463 `4.3.x/4.4.x` | Artan gecikmeyle tekrar |
| 190 | `ses_transient_general` | Geçici sunucu hatası | SES `Transient` | Sınırlı gecikmeli tekrar |
| 200 | `ses_permanent_general` | Kalıcı geçersiz adres | SES `Permanent` | Kalıcı baskılama |

## Kaynaklar ve sağlayıcı kapsamı

- SES olay şeması, bounce türleri/alt türleri ve şikâyet alanları:
  [Amazon SES bildirim içeriği](https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html)
- Geliştirilmiş teslim durum kodlarının sınıfları:
  [RFC 3463](https://www.rfc-editor.org/rfc/rfc3463.html)
- Gmail politika, oran ve itibar mesajları:
  [Google Workspace SMTP hata kodları](https://support.google.com/a/answer/3726730)
- Outlook/Exchange NDR alanları ve hata açıklamaları:
  [Microsoft Exchange Online NDR](https://learn.microsoft.com/en-us/troubleshoot/exchange/email-delivery/ndr/non-delivery-reports-in-exchange-online)
- Yahoo oran, itibar ve engelleme mesajları:
  [Yahoo Sender Hub SMTP hata kodları](https://senders.yahooinc.com/error-codes/)

Yandex ve kurumsal sunucularda standart RFC 3463 kodları ile açık tanı metni
örüntüleri kullanılır. Sağlayıcıya özgü doğrulanmış yeni mesajlar geldiğinde ilgili
resmî kaynakla birlikte ayrı ve daha yüksek öncelikli kural eklenmelidir.

## Çakışma ve güvenlik yaklaşımı

Blocklist, otomatik yanıt, kutu dolu ve oran sınırı kuralları genel `5.7.x` veya
SES `Permanent/Transient` kurallarından önce çalışır. Böylece örneğin `5.7.1`
içinde açıkça Spamhaus geçen bir olay yalnızca genel politika reddi sayılmaz.
Çıktıda tanı metni bulunmaz; yalnızca güvenli örüntü (sadece bilinmeyenlerde) ve
SHA-256 mesaj parmak izi bulunur. Açık alıcı adresi varsa çalışma sırasında HMAC
özetine çevrilir ve yanıt dosyasına yazılmaz.
