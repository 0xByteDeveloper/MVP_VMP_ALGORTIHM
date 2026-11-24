#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312: çalışma kopyalarını hazırlar (kaynak ağaç A'ya ASLA yazılmaz).

    A (salt okunur)  : work/src/a_kaynak_kod/universalObfusPublicSrc   (3.5.1 + _YAMALAR)
    BASE             : work/v312/src_base        = A + yalnız g++ uyumluluk düzeltmesi
    PATCHED          : work/v312/src_patched     = BASE + 3.9.4 yükseltme yaması
                       (yama scripts/v312_apply_yukseltme.py ile uygulanır)

g++ uyumluluk düzeltmesi (tek dosya, core/pe.h):
    Ağaçtaki eski uyumluluk yaması pe.h'e
        #ifndef COMIMAGE_FLAGS_NATIVE_ENTRYPOINT
        #define COMIMAGE_FLAGS_NATIVE_ENTRYPOINT 0x00000010
        #endif
    eklemiş. clang altında bu satırlar sorunsuz; g++ altında pe.h, dotnet.h'ten ÖNCE
    include edildiği için makro tanımlanıyor ve dotnet.h:45'teki
        COMIMAGE_FLAGS_NATIVE_ENTRYPOINT =0x00000010
    enum girdisi "0x00000010 =0x00000010" e dönüşüyor (derleme hatası).
    Sembol yalnız dotnetfile.cc'de kullanılıyor ve dotnetfile.cc dotnet.h'i kendi include
    ediyor; bu yüzden makro bloğu kaldırılır, enum olduğu gibi kalır.

Kullanım: v312_prep_trees.py [--yeni]     (--yeni: BASE ve PATCHED'i silip yeniden kurar)
Çıktı   : work/v312/out/patch/00_gcc_uyumluluk.diff
"""
import argparse, filecmp, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v312_patchlib as P

A = "/home/z/my-project/work/src/a_kaynak_kod/universalObfusPublicSrc"
BASE = "/home/z/my-project/work/v312/src_base"
PATCHED = "/home/z/my-project/work/v312/src_patched"
OUT = "/home/z/my-project/work/v312/out/patch"

ESKI_BLOK = (
    "#ifndef COMIMAGE_FLAGS_NATIVE_ENTRYPOINT\n"
    "#define COMIMAGE_FLAGS_NATIVE_ENTRYPOINT 0x00000010\n"
    "#endif\n"
)

ap = argparse.ArgumentParser()
ap.add_argument("--yeni", action="store_true")
a = ap.parse_args()

if a.yeni or not os.path.isdir(BASE):
    for d in (BASE, PATCHED):
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    shutil.copytree(A, BASE, symlinks=True)
    print(f"BASE kopyalandı: {A} -> {BASE}")

    P.replace_in_file(f"{BASE}/core/pe.h", ESKI_BLOK, "", 1, "pe.h: COMIMAGE makro bloğu")
    print("BASE/core/pe.h: g++ uyumluluk düzeltmesi uygulandı")

    shutil.copytree(BASE, PATCHED, symlinks=True)
    print(f"PATCHED kopyalandı: {BASE} -> {PATCHED}")
else:
    print("BASE zaten var (--yeni verilmedi): dokunulmadı")

# uyumluluk diff'i (A -> BASE), yalnız farklı dosyalar
os.makedirs(OUT, exist_ok=True)
farkli = []
for kok, _, dosyalar in os.walk(BASE):
    for f in dosyalar:
        pb = os.path.join(kok, f)
        pa = os.path.join(A, os.path.relpath(pb, BASE))
        if not os.path.exists(pa) or not filecmp.cmp(pa, pb, shallow=False):
            farkli.append(os.path.relpath(pb, BASE))
farkli.sort()
diff = ""
for rel in farkli:
    r = subprocess.run(["diff", "-u", "--label", f"a/universalObfusPublicSrc/{rel}",
                        "--label", f"b/universalObfusPublicSrc/{rel}",
                        os.path.join(A, rel), os.path.join(BASE, rel)],
                       capture_output=True, text=True)
    diff += r.stdout
dp = f"{OUT}/00_gcc_uyumluluk.diff"
open(dp, "w", encoding="utf-8").write(diff)
print(f"BASE'de A'dan farklı dosya sayısı: {len(farkli)} -> {farkli}")
print(f"yazıldı: {dp} ({len(diff)} bayt)")
