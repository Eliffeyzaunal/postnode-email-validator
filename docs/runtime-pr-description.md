# DNS modları, izleme sağlığı ve teslim kanıtları

Dosya doğrulaması diğer API isteklerini bekletebiliyor, deneme/canlı DNS durumları
birbirini etkileyebiliyor ve DNS hatası sonrası son bilinen listelenme rapordan
kaybolabiliyordu. Bu değişiklik bu davranışları düzeltir ve görev tesliminin
ölçümlerini tekrar üretilebilir hale getirir.

- Dosya işlemleri iş parçacığı havuzuna taşındı.
- DNS koşuları, durum geçişleri ve kalp atışları moda göre ayrıldı; eski kayıtlar
  silinmeden `legacy` olarak korunuyor.
- İzleyiciyi çalıştıran Compose ve Windows başlatıcıları sağlık kontrolünde
  izleyici çalışmasını zorunlu tutuyor.
- Doğrulanamayan listelenmeler `unresolved_listings` içinde korunuyor.
- 258 sentetik adres, 7 liste senaryosu ve bağımsız insan etiket inceleme dosyası eklendi.
- Örnek JSON'lar güncel kodla 720 saatlik simülasyondan üretildi; simülasyon olduğu açıkça belirtildi.
- CI test/değerlendirme/MySQL benchmark çıktılarını indirilebilir dosya paketi olarak saklıyor.

Yerel doğrulama: 76 test başarılı, 4 MySQL testi ortam eksikliğinden atlandı.
MySQL entegrasyonu ve süre ölçümü bu PR'ın CI kontrolünde doğrulanmalı.
258 sentetik adresin tamamı Elif Feyza Ünal tarafından kontrol edildi; inceleme
sonucu 258 onaylı, 0 bekleyen ve 0 uyuşmazlıktır.
Windows başlatıcısı burada Windows üzerinde çalıştırılmadı; değişiklik metin düzeyinde kontrol edildi.

Güncellemede API ve izleyiciyi birlikte yeni sürüme geçirin. Eski durumlardan
mod tahmin edilmediği için her modun ilk yeni kontrolünde bir kez yeni listed
bildirimleri oluşabilir. Veritabanı hacmini silmek gerekmez.
