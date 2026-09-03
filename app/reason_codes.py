from enum import StrEnum


class ReasonCode(StrEnum):
    VALID = "VALID"
    EMPTY_EMAIL = "EMPTY_EMAIL"
    INVALID_SYNTAX = "INVALID_SYNTAX"
    EMAIL_TOO_LONG = "EMAIL_TOO_LONG"
    LOCAL_PART_TOO_LONG = "LOCAL_PART_TOO_LONG"
    INVALID_LOCAL_PART = "INVALID_LOCAL_PART"
    INVALID_DOMAIN = "INVALID_DOMAIN"
    DOMAIN_NXDOMAIN = "DOMAIN_NXDOMAIN"
    DOMAIN_NO_MAIL_HOST = "DOMAIN_NO_MAIL_HOST"
    DOMAIN_A_FALLBACK = "DOMAIN_A_FALLBACK"
    DNS_LOOKUP_ERROR = "DNS_LOOKUP_ERROR"
    DISPOSABLE_DOMAIN = "DISPOSABLE_DOMAIN"
    ROLE_ACCOUNT = "ROLE_ACCOUNT"
    DOMAIN_TYPO = "DOMAIN_TYPO"
    DUPLICATE_ADDRESS = "DUPLICATE_ADDRESS"
    GENERATED_SEQUENCE = "GENERATED_SEQUENCE"
    DOMAIN_CONCENTRATION = "DOMAIN_CONCENTRATION"


REASON_DESCRIPTIONS: dict[ReasonCode, str] = {
    ReasonCode.VALID: "Adres bütün etkin kontrollerden geçti.",
    ReasonCode.EMPTY_EMAIL: "E-posta alanı boş.",
    ReasonCode.INVALID_SYNTAX: "Adres temel e-posta sözdizimine uymuyor.",
    ReasonCode.EMAIL_TOO_LONG: "Adres 254 karakterlik toplam uzunluk sınırını aşıyor.",
    ReasonCode.LOCAL_PART_TOO_LONG: "@ işaretinden önceki bölüm 64 karakteri aşıyor.",
    ReasonCode.INVALID_LOCAL_PART: "Yerel bölümde geçersiz karakter veya nokta kullanımı var.",
    ReasonCode.INVALID_DOMAIN: "Alan adı geçerli etiket ve uzunluk kurallarına uymuyor.",
    ReasonCode.DOMAIN_NXDOMAIN: "Alan adı DNS'te bulunamadı.",
    ReasonCode.DOMAIN_NO_MAIL_HOST: "Alan adında MX, A veya AAAA kaydı bulunamadı.",
    ReasonCode.DOMAIN_A_FALLBACK: "MX yok; RFC uyumlu A/AAAA geri dönüşü bulundu ve adres şüpheli sayıldı.",
    ReasonCode.DNS_LOOKUP_ERROR: "DNS sorgusu geçici veya teknik bir hatayla tamamlanamadı; adres geçersiz sayılmadı.",
    ReasonCode.DISPOSABLE_DOMAIN: "Alan adı bilinen tek kullanımlık e-posta listesinde.",
    ReasonCode.ROLE_ACCOUNT: "Yerel bölüm info, admin veya destek gibi bir rol hesabı.",
    ReasonCode.DOMAIN_TYPO: "Alan adı yaygın bir yazım hatasıyla eşleşiyor.",
    ReasonCode.DUPLICATE_ADDRESS: "Adres aynı yükleme içinde daha önce görüldü.",
    ReasonCode.GENERATED_SEQUENCE: "Yerel bölüm aynı kökten türetilmiş ardışık sayı örüntüsüne dahil.",
    ReasonCode.DOMAIN_CONCENTRATION: "Bir alan adının listedeki oranı yapılandırılmış anomali eşiğini aşıyor.",
}

