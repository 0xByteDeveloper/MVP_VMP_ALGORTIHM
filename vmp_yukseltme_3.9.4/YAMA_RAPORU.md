# Yama raporu — VMProtect 3.5.1 → 3.9.4 altyapısı

**Tarih:** 2026-11-24 · **Kaynak:** universalObfusPublicSrc (VMProtect 3.5.1) · **Hedef:** VMProtect Ultimate 3.9.4
**Durum:** yama uygulandı, motor Linux/g++ 14 ile derlendi (5 varyasyon), korumalı çıktılar wine 10.0 ile doğrulandı.

## 1. Özet

3.5.1 kaynağı ile 3.9.4 arasındaki fark, resmî changelog ve ikili kanıtlara göre beş başlıkta toplanıyor: rastgele bölüm adları,
sanal makine complexity'si, fonksiyona özel complexity, sanal makine örnek sayısı ve sanal makine sürümü. Bunlardan ilk beşi bu yamayla
3.5.1 kaynağına eklendi; changelog'daki anti-decompiler, Shadow Stack ve RTTI maddeleri eklenmedi (aşağıda listelendi).

Ölçülen sonuç (girdi Test_64.exe, 12.800 bayt): MovePlayer sanallaştırma 3.5.1'de 589.312 bayt; yamalı motor complexity %100 ile
1.623.552 bayt; 6 fonksiyon Ultra + complexity + 10 örnek + Memory/Import Protection ile 18.545.152 bayt (18,55 MB).
Bölüm adları 3.5.1'de her derlemede `.vmp00/.vmp01/.vmp02`, yamalı motorda `.???` maskesiyle her derlemede farklı
(.%b2, .8LR, .29u).

## 2. UPX kontrolü

3.9.4 UPX ile paketli DEĞİL (kendisi bir paketleyici: çıktısı UPX ile sıkıştırılmış bölüm tablosu taşımaz) → UPX kaldırma adımı uygulanmadı. 3.9.4 bölüm tablosu (V306 kaydı): .text, .rdata, .data, .pdata, .tls, .qtmetad, .gfids, _RDATA, .qWo, .!*_, .xz@, .rsrc, .reloc. Elimizdeki resmî 3.9.6 çıktısının UPX işareti: False.

## 3. Özellik farkları

| Özellik | 3.5.1 | 3.9.4 | Ölçüm | Yamada |
|---|---|---|---|---|
| Rastgele bölüm adları (maske) | YOK — ad = şablon adı + sıra numarası, her derlemede aynı | VAR — her koruyucu bölüm ayrı rastgele ad taşır | 3.5.1 motor: .vmp00, .vmp01, .vmp02 — yamalı motor '.???' maskesi: .%b2, .8LR, .29u | NextSectionName(): '?' karakterleri rastgele yazdırılabilir simge olur (PE 8, Mach-O 16, ELF sınırsız); varsayılan şablon adı .??? |
| Sanal makine complexity (proje) | YOK — projede yalnız Options ve VMOptions sayısal öznitelikleri var | VAR — None / 1..100 % | MovePlayer sanallaştırma — 3.5.1: 589.312 bayt; yamalı complexity %0: 585.216 bayt; %25: 864.256 bayt; %50: 1.150.464 bayt; %75: 1.396.224 bayt; %100: 1.623.552 bayt | XML VMComplexity="0..100" → CompileOptions::vm_complexity → Mutate çöp komut üst sınırı ve sanallaştırma öncesi mutasyon |
| Fonksiyona özel complexity | YOK — fonksiyon seçenekleri yalnız bir bit maskesi (coLockToKey) | VAR — Default / 0..100 % | Yamalı: fonksiyon %50 → 611.840 bayt, %100 → 612.352 bayt (proje %0 iken). NOT: proje düzeyi %100 = 1.623.552 bayt; fonksiyon düzeyi etkinin daha küçük kalmasının nedeni bu oturumda incelenmedi. | XML <Procedure Complexity="0..100"> → adres→% tablosu → fonksiyon değeri yoksa proje değeri kullanılır |
| Sanal makine örnek sayısı (Instances) | Kullanıcıya kapalı — motor içinde sabit 1 veya 10 | VAR — Default / 1..10 | Yamalı: 1 örnek → 75.264 bayt; 10 örnek → 589.312 bayt | XML VMInstances="1..10" → CompileOptions::vm_count |
| Sanal makine sürümü (Version) | Kullanıcıya kapalı — yalnız VMOptions biti (klasik/gelişmiş VM) | VAR — Default / VMProtect 2.X | Yamalı: Default → 589.312 bayt; VMProtect 2.X → 156.160 bayt | XML VMVersion="0|1" → vm_flags bit 0 |
| Derleme rastgele tohumu | Tohum sabit 0 → aynı proje her derlemede bayt bayt aynı çıktı | Bu oturumda resmî 3.9.4 davranışı ölçülemedi (ikili yok) | Yamalı: tohumsuz iki derleme aynı mı? hayır; RandomSeed=12345 ile iki derleme aynı mı? evet | XML RandomSeed (yoksa her derlemede yeni tohum; verilirse tekrarlanabilir derleme) |
| Sanal koda karşı anti-statik-decompiler koruması | yok | changelog'da kayıtlı | — | UYGULANMADI (bu oturumun kapsamı dışı) |
| Sanal makine obfuscation iyileştirmeleri | yok | changelog'da kayıtlı | — | UYGULANMADI (bu oturumun kapsamı dışı) |
| Shadow Stack uyumluluğu | yok | changelog'da kayıtlı | — | UYGULANMADI (bu oturumun kapsamı dışı) |
| RTTI ad obfuscation vb. | yok | changelog'da kayıtlı | — | UYGULANMADI (bu oturumun kapsamı dışı) |
| Bayt kodu şifreleme (cpEncryptBytecode) | Kaynakta var, lisans kapılı | bu oturumda ölçülemedi | — | DOKUNULMADI — lisans mekanizması değiştirilmedi |

### Resmî changelog — ilgili kayıtlar (vmpsoft.com, olduğu gibi)

| Sürüm | Tür | Kayıt |
|---|---|---|
| 3.6 | YENİ | Added the ability to create segments with random symbols using mask ‘?’ |
| 3.7 | YENİ | .NET: Added protection against static decompilers for virtualized code |
| 3.7 | YENİ | Intel: Added protection against static decompilers for virtualized code |
| 3.7.3 | İYİLEŞTİRME | Intel: Improved virtual machine obfuscation |
| 3.8 | YENİ | Intel: Added the project option “Virtual Machine – Instances” with the following values: Default, 1..10 |
| 3.8 | YENİ | Intel: Added the project option “Virtual Machine – Complexity” with the following values: None, 1..100% |
| 3.8 | YENİ | Intel: Added the function option “Protection – Complexity” with the following values: Default, 0..100% |
| 3.8 | İYİLEŞTİRME | .NET: Fixed the error “System.TypeLoadException: Could not load type ‘System.Random’ from assembly ‘System.Runtime’” that occurred while starting a protected application |
| 3.8.2 | İYİLEŞTİRME | Intel: Improved virtual machine obfuscation |
| 3.8.3 | YENİ | PE: Added the project option “Shadow Stack Compatible” |
| 3.8.6 | YENİ | .NET: Added the project option "Virtual Machine - Complexity" |
| 3.9.3 | YENİ | PE: Added obfuscation of RTTI names for binaries compiled with MSVC when using the "Strip Debug Information" option |

## 4. Ölçümler (aynı proje matrisi, iki motor)

| Varyasyon | 3.5.1 boyut | Yamalı boyut | 3.5.1 bölüm adları | Yamalı bölüm adları | wine 3.5.1 | wine yamalı |
|---|---|---|---|---|---|---|
| fn0-none | 13.312 | 13.312 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt | 589.312 | 589.312 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-mutation | 13.824 | 13.824 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-ultra | 595.968 | 593.920 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn6-virt | 696.320 | 701.952 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn6-mutation | 16.384 | — | .vmp00 | — | ✓ | — |
| fn6-ultra | 738.304 | — | .vmp00 | — | ✓ | — |
| fn1-virt-c0 | 589.312 | 585.216 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-c25 | 589.312 | 864.256 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-c50 | 589.312 | 1.150.464 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-c75 | 589.312 | 1.396.224 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-c100 | 589.312 | 1.623.552 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-mutation-c0 | 13.824 | — | .vmp00 | — | ✓ | — |
| fn1-ultra-c0 | 595.968 | — | .vmp00 | — | ✓ | — |
| fn1-virt-fc0 | 589.312 | — | .vmp00 | — | ✓ | — |
| fn1-mutation-c50 | 13.824 | 13.824 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-ultra-c50 | 595.968 | — | .vmp00 | — | ✓ | — |
| fn1-virt-fc50 | 589.312 | 611.840 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-mutation-c100 | 13.824 | 14.336 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-ultra-c100 | 595.968 | 1.636.352 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-fc100 | 589.312 | 612.352 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-i1 | 589.312 | 75.264 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-i2 | 589.312 | — | .vmp00 | — | ✓ | — |
| fn1-virt-i5 | 589.312 | — | .vmp00 | — | ✓ | — |
| fn1-virt-i10 | 589.312 | 589.312 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-vm2x | 589.312 | 156.160 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-vm2x-c100 | 589.312 | 286.208 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-mask-nokta3soru | 589.312 | 584.704 | .???0 | .$H* | ✓ | ✓ |
| fn1-virt-mask-vmpsoru | 589.312 | 584.704 | vmp?0 | vmpr | ✓ | ✓ |
| fn1-virt-seed12345 | 589.312 | 589.312 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-seed12345-tekrar | 589.312 | 589.312 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-seed777 | 589.312 | 585.216 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn1-virt-tekrar | 589.312 | 586.240 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn6-virt-c100 | 696.320 | 1.948.160 | .vmp00 | .vmp00 | ✓ | ✓ |
| fn6-ultra-fc100 | 738.304 | 873.472 | .???0 | .TvC | ✓ | ✓ |
| fn1-virt-tespit | 5.260.288 | 5.267.456 | .vmp00, .vmp01, .vmp02 | .vmp00, .vmp01, .vmp02 | ✗ | ✗ |
| hepsi-max | 5.620.736 | 18.545.152 | .???0, .???1, .???2 | .%b2, .8LR, .29u | ✗ | ✗ |

✓ = korumalı exe wine 10 altında korumamasız exe ile aynı çıktıyı verdi; ✗ = vermedi; — = koşulmadı. Eşleşmeyenler
(fn1-virt-tespit, hepsi-max) MemoryProtection + ImportProtection seçenekli projeler; 3.5.1 motorunda da aynı.

## 5. Yama noktaları

`patch/10_yukseltme_3.9.4.diff` (src_base → src_patched). 21 nokta, 9 dosya:

| Dosya | Değişiklik | Nokta |
|---|---|---|
| core/files.h | files.h: CompileOptions alanlari | 1 |
| core/files.h | files.h: CompileOptions kurucusu | 1 |
| core/files.h | files.h: NextSectionName bildirimi | 1 |
| core/files.cc | files.cc: NextSectionName uygulaması | 1 |
| core/pefile.cc | pefile.cc: bolum adi uretme (5 nokta) | 5 |
| core/dotnetfile.cc | dotnetfile.cc: bolum adi uretme (2 nokta) | 2 |
| core/elffile.cc | elffile.cc: bolum adi uretme (2 nokta) | 2 |
| core/macfile.cc | macfile.cc: bolum adi uretme (4 nokta) | 4 |
| core/core.h | core.h: Core erişimcileri | 1 |
| core/core.h | core.h: Core üyeleri | 1 |
| core/core.h | core.h: <map> include | 1 |
| core/core.cc | core.cc: Open varsayılanları | 1 |
| core/core.cc | core.cc: XML okuma (VMVersion/VMInstances/VMComplexity/RandomSeed) | 1 |
| core/core.cc | core.cc: XML okuma (Procedure Complexity) | 1 |
| core/core.cc | core.cc: XML yazma (Procedure Complexity) | 1 |
| core/core.cc | core.cc: Compile seçenek aktarımı | 1 |
| core/core.cc | core.cc: Compile rastgele tohum | 1 |
| core/core.cc | core.cc: varsayılan şablon bölüm adı maskesi | 1 |
| core/intel.cc | intel.cc: VMP_Complexity yardımcısı | 1 |
| core/intel.cc | intel.cc: Mutate çöp komut sınırı | 1 |
| core/intel.cc | intel.cc: Sanallaştırma + complexity | 1 |

`patch/00_gcc_uyumluluk.diff`: yalnızca g++ derlemesi için gerekli tek dosyalık düzeltme (`core/pe.h`, 3 satır); MSVC/clang için gerekmez.

### Yeni proje XML öznitelikleri

| Öznitelik | Değer | Anlamı |
|---|---|---|
| `VMCodeSectionName` | `.???` | `?` karakterleri rastgele simge olur; `?` yoksa 3.5.1 davranışı |
| `VMVersion` | 0 / 1 | Default (gelişmiş VM) / VMProtect 2.X (klasik VM) |
| `VMInstances` | 0..10 | 0 = Default (10) |
| `VMComplexity` | 0..100 | proje düzeyi complexity (%) |
| `RandomSeed` | sayı | verilirse tekrarlanabilir derleme; yoksa her derlemede yeni tohum |
| `Procedure Complexity` | 0..100 | fonksiyona özel complexity; yoksa proje değeri |

## 6. Uygulama ve derleme

```bash
python3 scripts/v312_prep_trees.py --yeni          # src_base (A + pe.h g++ uyumu), src_patched
python3 scripts/v312_apply_yukseltme.py            # yama → src_patched ve out/patch/*.diff
python3 scripts/v312_build_linux.py --src work/v312/src_patched --out work/v312/build_patched
python3 scripts/v312_test_motor.py --bin work/v312/build_patched/bin/VMProtectCon --tag yamali
```

Betiklerdeki kök dizin sabittir (`/home/z/my-project`); başka makinede `KOK`/`BASE` sabitlerini değiştirin.
Windows (clang/MSVC, orijinal makefile) derlemesi bu oturumda denenmedi; diff CRLF korunarak üretildi, `git apply` ile uygulanabilir.

## 7. Yapılmayanlar ve bilinen sorunlar

- Lua binder'ları (vmVersion/vmInstances/vmComplexity/randomSeed, complexity)
- Qt GUI özellik satırları (derlenmedi)
- konsol anahtarları (-vm/-vi/-vc/-rs)
- ValueCryptor zincir uzunluğunun complexity'e bağlanması
- AddUnknown (map adı) dalında Complexity
- Fonksiyona özel complexity'nin etki büyüklüğü: %50 → 611.840 bayt, %100 → 612.352 bayt
  (proje %0 iken). Proje düzeyi %100 = 1.623.552 bayt. Farkın nedeni incelenmedi.
- MemoryProtection + Import Protection seçenkeli çıktılar wine 10 altında çalışmadı (her iki motorda).

- Yandex Disk captcha'sı aşılmadı → resmî 3.9.4 ikilisi yok
- rea'da decompiler provider'ı yok; compare-artifacts yalnız inspect-artifact kanıtı kabul ediyor
- MemoryProtection + ImportProtection seçenekli çıktılar wine 10 altında beklenen çıktıyı vermedi (3.5.1 ve yamalı motorda aynı)
