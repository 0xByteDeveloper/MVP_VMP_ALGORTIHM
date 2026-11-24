#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312: VMProtect 3.5.1 kaynak ağacı — Linux (g++) derleme sürücüsü.

Zincir (orijinal lin_*.mak dosyalarındaki kaynak listeleriyle birebir):
    invar -> core -> sdk -> con -> link
  invar : third-party (tinyxml, demangle, lzma, lua)   [scintilla yalnız GUI — atlanır]
  core  : core/*.cc (18) + runtime/crypto.cc           [-DULTIMATE -DTIXML_USE_STL -DSPV_LIBRARY -DFFI_BUILDING]
  sdk   : sdk/sdk.cc
  con   : VMProtectCon/console.cc + main.cc            -> bin/VMProtectCon

Çalışma-zamanı modülleri (win_runtime*.dll.inc, lin_runtime*.so.inc, mac_runtime*.dylib.inc)
kaynak ağacında zaten gömülü — ayrı runtime derlemesi GEREKMEZ.

Kullanım:
    v312_build_linux.py --src <ağaç> --out <derleme dizini> [--opt -O1] [-j N] [--step core]
Nesneler mtime ile önbelleklenir; yalnız değişen kaynaklar yeniden derlenir.
Kaynak ağacına YAZILMAZ ( Salt okunur kaynak, çıktı --out altına).
"""
import argparse, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

TINYXML = ["tinyxml", "tinyxmlparser", "tinyxmlerr"]
DEMANGLE = ["cp-demangle", "undname", "unmangle"]
LZMA = ["Alloc", "LzFind", "LzmaEnc"]
LUA = ["lapi", "lauxlib", "lstate", "ldebug", "lzio", "llex", "lctype", "lvm", "ldump", "ltm",
       "lstring", "lundump", "lobject", "lparser", "lcode", "lmem", "ltable", "ldo", "lgc", "lfunc",
       "linit", "lopcodes", "loadlib", "ltablib", "lstrlib", "liolib", "lmathlib", "loslib",
       "lbaselib", "lbitlib", "lcorolib", "ldblib"]
CORE = ["core", "files", "inifile", "dotnetfile", "dwarf", "elffile", "intel", "il", "lang",
        "objc", "macfile", "objects", "osutils", "packer", "pefile", "processors", "script", "streams"]
CON = ["console", "main"]

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--cxx", default="g++")
ap.add_argument("--cc", default="gcc")
ap.add_argument("--opt", default="-O1")
ap.add_argument("-j", type=int, default=max(1, os.cpu_count() or 1))
ap.add_argument("--step", default="all", choices=["all", "invar", "core", "sdk", "con"])
ap.add_argument("--extra-core-flags", default="", help="core/con derlemesine ek bayraklar")
a = ap.parse_args()

SRC = os.path.abspath(a.src)
OUT = os.path.abspath(a.out)
for d in ("obj", "bin", "log"):
    os.makedirs(f"{OUT}/{d}", exist_ok=True)
# önceki koşulardan kalan eski hata günlükleri silinir (yenileri hata olursa yazılır)
for f in os.listdir(f"{OUT}/log"):
    os.remove(os.path.join(OUT, "log", f))

# lin_common.mak: -DNDEBUG -fno-stack-protector -fno-builtin -fPIC ; C++: -std=c++11 -fvisibility-inlines-hidden
# (-w: uyarılar kapatıldı; -gdwarf-2 atlandı — hata ayıklama bilgisi gerekmediği için)
BASE = [a.opt, "-fPIC", "-DNDEBUG", "-fno-stack-protector", "-fno-builtin", "-w"]
BASE_CXX = BASE + ["-std=c++11", "-fvisibility-inlines-hidden"]

def job(cmd, cwd, obj, src, pch=None):
    """(cmd, cwd, obj, src) — taze nesneler atlanır; src, cwd'ye göreli verilir, mutlakaştırılır"""
    src = os.path.normpath(os.path.join(cwd, src))
    if os.path.exists(obj) and os.path.getmtime(obj) >= os.path.getmtime(src):
        return None
    os.makedirs(os.path.dirname(obj), exist_ok=True)
    c = list(cmd) + ["-c", "-o", obj, src]
    if pch:
        c += ["-include", pch]
    return (c, cwd, obj, src)

def run_jobs(jobs, tag):
    jobs = [j for j in jobs if j]
    if not jobs:
        print(f"  [{tag}] tüm nesneler taze", flush=True)
        return []
    print(f"  [{tag}] {len(jobs)} dosya derleniyor...", flush=True)
    fails, t0 = [], time.time()
    def work(j):
        c, cwd, obj, src = j
        try:
            r = subprocess.run(c, cwd=cwd, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=3600)
            return (r.returncode, c, src, (r.stderr or r.stdout))
        except subprocess.TimeoutExpired:
            return (-99, c, src, "TIMEOUT")
        except OSError as e:
            return (-98, c, src, f"CALISTIRILAMADI: {e}")
    with ThreadPoolExecutor(max_workers=a.j) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            rc, c, src, err = f.result()
            if rc != 0:
                fails.append((src, err))
            print(f"      {i}/{len(jobs)} {'ERR ' if rc else 'ok  '}{os.path.basename(src)}", flush=True)
    if fails:
        for src, err in fails:
            lp = f"{OUT}/log/{os.path.basename(src)}.log"
            open(lp, "w").write(err)
            print(f"  HATA {src}\n    " + "\n    ".join(err.strip().splitlines()[:12]), flush=True)
        sys.exit(f"[{tag}] {len(fails)} derleme hatası")
    print(f"  [{tag}] bitti ({time.time() - t0:.0f} sn)", flush=True)
    return [j[2] for j in jobs]

def collect(step_dir, cwd, names, ext, cmd, pch=None):
    return [job(cmd, cwd, f"{OUT}/obj/{step_dir}/{n}.o", os.path.join(cwd, f"{n}{ext}"), pch) for n in names]

ORDER = ["invar", "core", "sdk", "con"]
STEPS = set(ORDER) if a.step == "all" else [a.step]
objs = {}

# ---------------------------------------------------------------- invar
if "invar" in STEPS:
    inv = os.path.join(SRC, "core", "invariant")
    # lin_invariant_core.mak DEFINES (C ve C++ için ortak):
    INV_DEFINES = ["-DSCI_NAMESPACE", "-DTIXML_USE_STL", "-DSPV_LIBRARY", "-DSCI_LEXER", "-D_7ZIP_ST",
                   "-DLUA_USE_MKSTEMP", "-DFFI_BUILDING", "-DLUA_USE_POSIX"]
    d_cxx = [a.cxx] + BASE_CXX + INV_DEFINES + ["-I", "."]
    d_c = [a.cc] + BASE + INV_DEFINES + ["-I", "."]
    js = []
    for n in TINYXML:
        js.append(job(d_cxx, inv, f"{OUT}/obj/invar/{n}.o", f"../../third-party/tinyxml/{n}.cpp", "precompiled.h"))
    for grp, lib in ((DEMANGLE, "demangle"), (LZMA, "lzma"), (LUA, "lua")):
        for n in grp:
            js.append(job(d_c, inv, f"{OUT}/obj/invar/{lib}_{n}.o",
                          f"../../third-party/{lib}/{n}.c", "precompiled_c.h"))
    objs["invar"] = run_jobs(js, "invar")

# ---------------------------------------------------------------- core
if "core" in STEPS:
    core = os.path.join(SRC, "core")
    d = [a.cxx] + BASE_CXX + ["-DULTIMATE", "-DTIXML_USE_STL", "-DSPV_LIBRARY", "-DFFI_BUILDING",
                              "-I", ".", "-I", "../third-party/lua"] + a.extra_core_flags.split()
    js = collect("core", core, CORE, ".cc", d, "precompiled.h")
    js.append(job(d, core, f"{OUT}/obj/core/runtime_crypto.o", "../runtime/crypto.cc", "precompiled.h"))
    objs["core"] = run_jobs(js, "core")

# ---------------------------------------------------------------- sdk
if "sdk" in STEPS:
    sdk = os.path.join(SRC, "sdk")
    objs["sdk"] = run_jobs([job([a.cxx] + BASE_CXX + ["-I", "."], sdk, f"{OUT}/obj/sdk/sdk.o", "sdk.cc", "precompiled.h")], "sdk")

# ---------------------------------------------------------------- con
if "con" in STEPS:
    con = os.path.join(SRC, "VMProtectCon")
    d = [a.cxx] + BASE_CXX + ["-DULTIMATE", "-DTIXML_USE_STL", "-I", "."] + a.extra_core_flags.split()
    objs["con"] = run_jobs(collect("con", con, CON, ".cc", d, "precompiled.h"), "con")

# ---------------------------------------------------------------- link
def allof(step_dir, names, ext=".o"):
    return [f"{OUT}/obj/{step_dir}/{n}{ext}" for n in names]

invar_objs = (allof("invar", TINYXML) + allof("invar", [f"demangle_{n}" for n in DEMANGLE])
              + allof("invar", [f"lzma_{n}" for n in LZMA]) + allof("invar", [f"lua_{n}" for n in LUA]))
core_objs = allof("core", CORE) + [f"{OUT}/obj/core/runtime_crypto.o"]
need = invar_objs + core_objs + [f"{OUT}/obj/sdk/sdk.o"] + allof("con", CON)
missing = [p for p in need if not os.path.exists(p)]
if missing:
    msg = f"link atlandı: {len(missing)} nesne eksik, örnek {missing[0]}"
    if a.step == "all":
        sys.exit(msg)
    print(msg)
    sys.exit(0)

binp = f"{OUT}/bin/VMProtectCon"
newest = max(os.path.getmtime(p) for p in need)
if os.path.exists(binp) and os.path.getmtime(binp) >= newest:
    print(f"  [link] {binp} taze")
else:
    cmd = [a.cxx, "-no-pie", "-o", binp] + allof("con", CON) + core_objs + invar_objs + [f"{OUT}/obj/sdk/sdk.o",
           f"{SRC}/third-party/libffi/libffi64.a", "-Wl,-Bstatic", "-lcrypto", "-lzstd", "-lz", "-Wl,-Bdynamic",
           "-ldl", "-lpthread", "-lrt"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(f"{OUT}/log/link.log", "w").write(r.stderr + "\n" + r.stdout)
    if r.returncode != 0:
        sys.exit("[link] HATA:\n" + "\n".join(r.stderr.strip().splitlines()[:25]))
    print(f"  [link] {binp} ({os.path.getsize(binp) / 1e6:.1f} MB)", flush=True)

print("TAMAM", binp)
