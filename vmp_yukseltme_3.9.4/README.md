# VMProtect 3.5.1 → 3.9.4 yükseltme yaması (V312, 2026-11-24)

- `YAMA_RAPORU.md` — yama raporu (özellik farkı tablosu, ölçümler, yama noktaları, yapılmayanlar)
- `patch/10_yukseltme_3.9.4.diff` — yama (9 dosya, 21 nokta) · `patch/00_gcc_uyumluluk.diff` — yalnız g++ için
- `patch/yama_kayitlari.json` — yama noktaları listesi
- `scripts/` — uygulama / derleme / ölçüm / wine betikleri
- `olcum/` — iki motorun ölçüm sonuçları (JSON) · `rea/` — rea çıktıları (4 dosya)

Kullanım: `python3 scripts/v312_prep_trees.py --yeni && python3 scripts/v312_apply_yukseltme.py && python3 scripts/v312_build_linux.py --src work/v312/src_patched --out work/v312/build_patched`
Lisans kapılı kod değiştirilmedi. Kaynak ağacı (3.5.1) bu pakette YOK, yalnız diff vardır.
