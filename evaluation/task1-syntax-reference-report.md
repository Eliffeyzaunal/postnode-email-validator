# Görev 1 Bağımsız Syntax Referans Karşılaştırması

Referans: `python-email-validator==2.3.0` (Unlicense). Bu ölçüm yalnız syntax karar uyumudur;
genel adres doğruluğu veya teslim edilebilirlik oranı değildir.

- Corpus: 473 görülmemiş/deterministik örnek
- Syntax agreement: %89.43
- Belgelenmiş politika farkları hariç uyum: %100.00 (403 örnek)
- Geçerli precision: %89.27
- Geçerli recall: %89.27
- Geçerli F1: %89.27
- Politika/uygulama farkı: 50
- Corpus SHA-256: `d7fba06c4ef11c2bfbdee8c02fe3bdc3e4ed04fb2e746b951d5cab6b0fbd5c01`

## İkili confusion matrix

| Referans \ Proje | Geçerli | Geçersiz |
|---|---:|---:|
| Geçerli | 208 | 25 |
| Geçersiz | 25 | 215 |

## Kategori uyumu

| Kategori | Uyum/Toplam | Oran |
|---|---:|---:|
| `invalid_alabel` | 5/5 | %100.00 |
| `invalid_domain` | 55/55 | %100.00 |
| `invalid_local` | 75/75 | %100.00 |
| `length_boundary` | 25/25 | %100.00 |
| `missing_or_extra_at` | 50/50 | %100.00 |
| `policy_outer_space` | 0/20 | %0.00 |
| `policy_quoted_local` | 20/20 | %100.00 |
| `policy_single_char_tld` | 0/20 | %0.00 |
| `policy_smtputf8_octet_limit` | 0/5 | %0.00 |
| `policy_trailing_root_dot` | 0/5 | %0.00 |
| `valid_ascii` | 105/105 | %100.00 |
| `valid_idn` | 40/40 | %100.00 |
| `valid_smtputf8` | 48/48 | %100.00 |

## İlk fark örnekleri

| Kategori | Adres | Referans | Proje |
|---|---|---:|---:|
| `policy_trailing_root_dot` | `domaincase3-0@trailing.example.` | False | True |
| `policy_trailing_root_dot` | `domaincase3-1@trailing.example.` | False | True |
| `policy_trailing_root_dot` | `domaincase3-2@trailing.example.` | False | True |
| `policy_trailing_root_dot` | `domaincase3-3@trailing.example.` | False | True |
| `policy_trailing_root_dot` | `domaincase3-4@trailing.example.` | False | True |
| `policy_outer_space` | `  spaced0@example.com  ` | False | True |
| `policy_single_char_tld` | `single0@example.c` | True | False |
| `policy_outer_space` | `  spaced1@example.com  ` | False | True |
| `policy_single_char_tld` | `single1@example.c` | True | False |
| `policy_outer_space` | `  spaced2@example.com  ` | False | True |
| `policy_single_char_tld` | `single2@example.c` | True | False |
| `policy_outer_space` | `  spaced3@example.com  ` | False | True |
| `policy_single_char_tld` | `single3@example.c` | True | False |
| `policy_outer_space` | `  spaced4@example.com  ` | False | True |
| `policy_single_char_tld` | `single4@example.c` | True | False |
| `policy_outer_space` | `  spaced5@example.com  ` | False | True |
| `policy_single_char_tld` | `single5@example.c` | True | False |
| `policy_outer_space` | `  spaced6@example.com  ` | False | True |
| `policy_single_char_tld` | `single6@example.c` | True | False |
| `policy_outer_space` | `  spaced7@example.com  ` | False | True |

Ham sonuçtan hiçbir fark silinmez. Politika uyumlu ikinci oran yalnız `policy_*` olarak
önceden tanımlanmış dış boşluk, DNS kök noktası ve tek karakterli TLD farklarını dışarıda tutar.
İlk çalıştırma ayrıca geçersiz bir Punycode A-label kabulünü ortaya çıkarmış; bu hata
`idna` ile açık IDNA 2008/UTS 46 doğrulaması eklenerek düzeltilmiştir.
Bu corpus mevcut kuralları değiştirmek için kullanılmaz; sonuç bir sonraki sürümle yeniden ölçülür.
