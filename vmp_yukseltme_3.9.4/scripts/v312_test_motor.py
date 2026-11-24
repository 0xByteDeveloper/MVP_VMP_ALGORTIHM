#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312 ölçüm düzeneği: bir VMProtect konsol motorunu (taban 3.5.1 ya da yamalı) aynı
proje matrisiyle çalıştırır, çıktı PE'yi kendi ayrıştırıcısıyla inceler ve wine altında
çalıştırıp çıktıyı korumamasız exe'nin çıktısıyla karşılaştırır.

Proje XML'i iki motora da AYNI verilir (yamalı özellikler XML özniteliği olarak taşınır);
taban 3.5.1 bilinmeyen öznitelikleri yok sayar — böylece "aynı proje, farklı motor" farkı ölçülür.

Kullanım:
    v312_test_motor.py --bin work/v312/build_base/bin/VMProtectCon --tag taban
                       [--only fn1-virt,fn1-virt-c100] [--wine-siz]
Çıktı:
    work/v312/test/<tag>/<varyasyon>/{proje.vmp, cikti.exe, motor.log, wine.log}
    work/v312/test/<tag>/results.json
"""
import argparse, hashlib, json, os, re, struct, subprocess, sys, time

import numpy as np

KOK = "/home/z/my-project"
GIRDI = "upload/Test_64.exe"
TEST = f"{KOK}/work/v312/test"
KOMUTLAR = f"{TEST}/komutlar.txt"
WINE = f"{KOK}/scripts/v312_wine.sh"

# ---------------------------------------------------------------- proje sabitleri
# core.h enum ProjectOption (3.5.1 kaynağı) — proje XML 'Options' bit maskesi
SECENEK = {"Pack": 0x100, "ImportProtection": 0x200, "CheckDebugger": 0x400,
           "CheckVirtualMachine": 0x800, "MemoryProtection": 0x1000, "StripFixups": 0x8000,
           "ResourceProtection": 0x10000, "CheckKernelDebugger": 0x20000, "StripDebugInfo": 0x40000}
# files.h enum CompilationType: 0 = Virtualization, 1 = Mutation, 2 = Ultra
SANAL, MUTASYON, ULTRA = 0, 1, 2
TIP_AD = {SANAL: "Virtualization", MUTASYON: "Mutation", ULTRA: "Ultra"}
MOVEPLAYER = 0x1400014C0
F6 = [0x140001020, 0x140001470, 0x1400014C0, 0x140001560, 0x140001630, 0x140001680]


def V(ad, fonks, **p):
    """fonks: [(adres, derleme_tipi, fonksiyon_complexity|None), ...]; p: proje öznitelikleri"""
    return {"ad": ad, "fonks": fonks, "proje": p}


def matris():
    m = []
    # --- 3.5.1'de zaten var olan ayarlar
    m.append(V("fn0-none", []))
    m.append(V("fn1-virt", [(MOVEPLAYER, SANAL, None)]))
    m.append(V("fn1-mutation", [(MOVEPLAYER, MUTASYON, None)]))
    m.append(V("fn1-ultra", [(MOVEPLAYER, ULTRA, None)]))
    m.append(V("fn6-virt", [(a, SANAL, None) for a in F6]))
    m.append(V("fn6-mutation", [(a, MUTASYON, None) for a in F6]))
    m.append(V("fn6-ultra", [(a, ULTRA, None) for a in F6]))
    # --- yamalı özellikler (taban bunları yok saymalı; farkı görmek için tabanda da koşulur)
    for c in (0, 25, 50, 75, 100):
        m.append(V(f"fn1-virt-c{c}", [(MOVEPLAYER, SANAL, None)], VMComplexity=c))
    for c in (0, 50, 100):
        m.append(V(f"fn1-mutation-c{c}", [(MOVEPLAYER, MUTASYON, None)], VMComplexity=c))
        m.append(V(f"fn1-ultra-c{c}", [(MOVEPLAYER, ULTRA, None)], VMComplexity=c))
        m.append(V(f"fn1-virt-fc{c}", [(MOVEPLAYER, SANAL, c)]))      # fonksiyona özel complexity
    for i in (1, 2, 5, 10):
        m.append(V(f"fn1-virt-i{i}", [(MOVEPLAYER, SANAL, None)], VMInstances=i))
    m.append(V("fn1-virt-vm2x", [(MOVEPLAYER, SANAL, None)], VMVersion=1))
    m.append(V("fn1-virt-vm2x-c100", [(MOVEPLAYER, SANAL, None)], VMVersion=1, VMComplexity=100))
    m.append(V("fn1-virt-mask-nokta3soru", [(MOVEPLAYER, SANAL, None)], VMCodeSectionName=".???"))
    m.append(V("fn1-virt-mask-vmpsoru", [(MOVEPLAYER, SANAL, None)], VMCodeSectionName="vmp?"))
    m.append(V("fn1-virt-seed12345", [(MOVEPLAYER, SANAL, None)], RandomSeed=12345))
    m.append(V("fn1-virt-seed12345-tekrar", [(MOVEPLAYER, SANAL, None)], RandomSeed=12345))
    m.append(V("fn1-virt-seed777", [(MOVEPLAYER, SANAL, None)], RandomSeed=777))
    m.append(V("fn1-virt-tekrar", [(MOVEPLAYER, SANAL, None)]))
    m.append(V("fn6-virt-c100", [(a, SANAL, None) for a in F6], VMComplexity=100))
    m.append(V("fn6-ultra-fc100", [(a, ULTRA, 100) for a in F6], VMInstances=10, VMCodeSectionName=".???"))
    m.append(V("fn1-virt-tespit", [(MOVEPLAYER, SANAL, None)],
               Options=["MemoryProtection", "ImportProtection", "StripDebugInfo"]))
    m.append(V("hepsi-max", [(a, ULTRA, 100) for a in F6], VMComplexity=100, VMInstances=10,
               VMCodeSectionName=".???", RandomSeed=20261124,
               Options=["MemoryProtection", "ImportProtection", "StripDebugInfo"]))
    return m


def proje_xml(v, cikti):
    p = dict(v["proje"])
    attrs = {
        "InputFileName": f"{KOK}/{GIRDI}",
        "OutputFileName": cikti,
        "Options": str(sum(SECENEK[s] for s in p.get("Options", []))),
        "VMCodeSectionName": p.get("VMCodeSectionName", ".vmp0"),
    }
    for k in ("VMVersion", "VMInstances", "VMComplexity", "RandomSeed"):
        if k in p:
            attrs[k] = p[k]
    satir = ['<?xml version="1.0" encoding="UTF-8" ?>', '<Document Version="2">']
    satir.append("    <Protection " + " ".join(f'{k}="{val}"' for k, val in attrs.items()) + ">")
    satir += ["        <Folders />", "        <Procedures>"]
    for adres, tip, c in v["fonks"]:
        a = f'Address="0x{adres:X}" CompilationType="{tip}" IncludedInCompilation="true"'
        if c is not None:
            a += f' Complexity="{c}"'
        satir.append(f"            <Procedure {a} />")
    satir += ["        </Procedures>", "        <Messages />", "    </Protection>", "    <DLLBox />", "</Document>", ""]
    return "\n".join(satir)


# ---------------------------------------------------------------- PE ayrıştırıcı
STANDART = {".text", ".rdata", ".data", ".pdata", ".tls", ".rsrc", ".reloc", ".edata", ".idata", ".bss",
            ".gfids", ".qtmetad", "_RDATA", ".didat", ".xc", ".clr", ".sdata", ".00cfg", ".textbss"}
DLL_OZELLIK = [(0x0020, "HighEntropyVA"), (0x0040, "DynamicBase"), (0x0080, "ForceIntegrity"),
               (0x0100, "NXCompat"), (0x0200, "NoIsolation"), (0x0400, "NoSEH"), (0x0800, "NoBind"),
               (0x1000, "AppContainer"), (0x2000, "WdmDriver"), (0x4000, "GuardCF"), (0x8000, "TerminalServerAware")]


def shannon(ham):
    say = np.bincount(np.frombuffer(ham, dtype=np.uint8), minlength=256).astype(np.float64)
    p = say[say > 0] / len(ham)
    return round(float(-(p * np.log2(p)).sum()), 3)


def rva_ofset(rva, bl):
    for b in bl:
        if b["va"] <= rva < b["va"] + max(b["vboy"], b["ham_boy"]):
            return b["ham_ofset"] + (rva - b["va"])
    return None


def pe_ayrastir(yol):
    d = open(yol, "rb").read()
    r = {"boyut": len(d), "sha256": hashlib.sha256(d).hexdigest(), "upx": (b"UPX!" in d)}
    e = struct.unpack_from("<I", d, 0x3C)[0]
    if d[e:e + 4] != b"PE\0\0":
        r["hata"] = "PE imzası yok"
        return r
    makine, n, zaman, _, _, opt_boyut, ozellik = struct.unpack_from("<HHIIIHH", d, e + 4)
    opt = e + 24
    sihir = struct.unpack_from("<H", d, opt)[0]
    r.update(makine=hex(makine), bolum_sayisi=n, zaman_damgasi=zaman, ozellikler=hex(ozellik))
    if sihir == 0x20B:
        taban = struct.unpack_from("<Q", d, opt + 24)[0]
        nd = struct.unpack_from("<I", d, opt + 108)[0]
        dd = opt + 112
    else:
        taban = struct.unpack_from("<I", d, opt + 28)[0]
        nd = struct.unpack_from("<I", d, opt + 92)[0]
        dd = opt + 96
    giris = struct.unpack_from("<I", d, opt + 16)[0]
    dll_oz = struct.unpack_from("<H", d, opt + 70)[0]
    r["giris_rva"] = hex(giris)
    r["dll_ozellikleri"] = [ad for m, ad in DLL_OZELLIK if dll_oz & m]
    dizin = [struct.unpack_from("<II", d, dd + 8 * i) for i in range(min(nd, 16))]
    bl = []
    for i in range(n):
        o = opt + opt_boyut + 40 * i
        ad = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vboy, va, ham_boy, ham_ofset = struct.unpack_from("<IIII", d, o + 8)
        oz = struct.unpack_from("<I", d, o + 36)[0]
        b = {"ad": ad, "vboy": vboy, "va": va, "ham_boy": ham_boy, "ham_ofset": ham_ofset,
             "ozellikler": hex(oz), "standart": ad in STANDART}
        if ham_boy:
            b["entropy"] = shannon(d[ham_ofset:ham_ofset + ham_boy])
        bl.append(b)
    r["bolumler"] = bl
    r["giris_bolumu"] = next((b["ad"] for b in bl if b["va"] <= giris < b["va"] + max(b["vboy"], b["ham_boy"])), None)
    son = max((b["ham_ofset"] + b["ham_boy"] for b in bl), default=0)
    r["art_veri"] = max(0, len(d) - son)
    r["upx"] = r["upx"] or any(b["ad"].upper().startswith("UPX") for b in bl)
    # import tablosu
    imp = []
    if len(dizin) > 1 and dizin[1][0]:
        of = rva_ofset(dizin[1][0], bl)
        if of is not None:
            for i in range(512):
                oft, _, _, ad_rva, ft = struct.unpack_from("<IIIII", d, of + 20 * i)
                if not (oft or ad_rva or ft):
                    break
                no = rva_ofset(ad_rva, bl)
                ad = d[no:d.index(b"\0", no)].decode("latin1") if no is not None else "?"
                say, t = 0, rva_ofset(oft or ft, bl)
                if t is not None:
                    while say < 4096 and struct.unpack_from("<Q", d, t + 8 * say)[0]:
                        say += 1
                imp.append({"dll": ad, "sayi": say})
    r["importlar"] = imp
    # TLS geri çağırmaları
    r["tls"] = None
    if len(dizin) > 9 and dizin[9][0]:
        of = rva_ofset(dizin[9][0], bl)
        if of is not None:
            _, _, _, cb_va, _, _ = struct.unpack_from("<QQQQII", d, of)
            cbs, co = [], rva_ofset(cb_va - taban, bl) if cb_va else None
            if co is not None:
                for i in range(64):
                    val = struct.unpack_from("<Q", d, co + 8 * i)[0]
                    if not val:
                        break
                    cbs.append(hex(val - taban))
            r["tls"] = {"geri_cagirma_sayisi": len(cbs), "geri_cagrimalar": cbs}
    # yükleme yapılandırması (GuardFlags)
    r["yukleme_ayar"] = None
    if len(dizin) > 10 and dizin[10][0]:
        of = rva_ofset(dizin[10][0], bl)
        if of is not None:
            boyut = struct.unpack_from("<I", d, of)[0]
            r["yukleme_ayar"] = {"boyut": boyut,
                                 "guard_bayraklari": hex(struct.unpack_from("<I", d, of + 144)[0]) if boyut >= 148 else None}
    return r


def koruyucu_ozet(pe):
    k = [b for b in pe.get("bolumler", []) if not b["standart"]]
    return [{"ad": b["ad"], "vboy": b["vboy"], "ham_boy": b["ham_boy"], "entropy": b.get("entropy")} for b in k]


# ---------------------------------------------------------------- koşu
def motor_kos(motor_yolu, v, dizin, yetki):
    vmp, cikti = f"{dizin}/proje.vmp", f"{dizin}/cikti.exe"
    with open(vmp, "w", encoding="utf-8") as f:
        f.write(proje_xml(v, cikti))
    if os.path.exists(cikti):
        os.remove(cikti)
    t0 = time.time()
    try:
        r = subprocess.run([motor_yolu, f"{KOK}/{GIRDI}", cikti, "-pf", vmp], cwd=KOK, capture_output=True,
                           text=True, errors="replace", timeout=yetki, stdin=subprocess.DEVNULL)
        rc, log = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, log = -99, "TIMEOUT"
    sn = time.time() - t0
    with open(f"{dizin}/motor.log", "w", encoding="utf-8") as f:
        f.write(log + f"\n[motor rc={rc} sure={sn:.1f}s]\n")
    boy = re.search(r"Output file size is (\d+) bytes \((\d+)%\)", log)
    return {"rc": rc, "sure_sn": round(sn, 1), "cikti_boyutu": int(boy.group(1)) if boy else None,
            "log_son": log.strip().splitlines()[-1][:200] if log.strip() else ""}, cikti


SATIR_SIYAH = re.compile(r"^[0-9a-f]{2,4}:(trace|warn|err|fixme):")


def normalise(b):
    s = b.decode("utf-8", errors="replace").replace("\r", "")
    return [l for l in s.split("\n") if l and not SATIR_SIYAH.match(l) and not l.startswith("wine:")]


def wine_kos(exe, dizin, yetki):
    t0 = time.time()
    try:
        with open(KOMUTLAR, "rb") as g:
            r = subprocess.run([WINE, exe], cwd=KOK, stdin=g, capture_output=True, timeout=yetki)
        ham, rc = r.stdout + b"\n" + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        ham, rc = (e.stdout or b"") + b"\nTIMEOUT", -99
        subprocess.run(["pkill", "-f", "wine_root/usr/lib/wine/wineserver64"], capture_output=True)
    sn = time.time() - t0
    with open(f"{dizin}/wine.log", "wb") as ham_f:
        ham_f.write(ham)
    return {"rc": rc, "sure_sn": round(sn, 1)}, normalise(ham)


def ilk_fark(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return {"satir": i + 1, "beklenen": x[:160], "bulunan": y[:160]}
    if len(a) != len(b):
        return {"satir": min(len(a), len(b)) + 1, "beklenen": (a + [""] * 99)[min(len(a), len(b))][:160],
                "bulunan": (b + [""] * 99)[min(len(a), len(b))][:160]}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--wine-siz", action="store_true")
    ap.add_argument("--yetki", type=int, default=2400, help="motor koşusu başına saniye")
    ap.add_argument("--wine-yetki", type=int, default=420)
    a = ap.parse_args()
    motor = os.path.abspath(a.bin)
    kok = f"{TEST}/{a.tag}"
    os.makedirs(kok, exist_ok=True)
    secili = set(x for x in a.only.split(",") if x)

    referans, wref = None, None
    if not a.wine_siz:
        wref, referans = wine_kos(f"{KOK}/{GIRDI}", TEST, a.wine_yetki)
        print(f"referans (korunmayan {GIRDI}): wine rc={wref['rc']} satir={len(referans)} "
              f"md5={hashlib.md5('\n'.join(referans).encode()).hexdigest()[:12]}", flush=True)

    sonuc_yolu = f"{kok}/results.json"
    eski = {}
    if os.path.exists(sonuc_yolu):
        eski = {s["ad"]: s for s in json.load(open(sonuc_yolu, encoding="utf-8"))["sonuclar"]}
    sonuclar = []
    for v in matris():
        if secili and v["ad"] not in secili:
            continue
        dizin = f"{kok}/{v['ad']}"
        os.makedirs(dizin, exist_ok=True)
        motor_s, cikti = motor_kos(motor, v, dizin, a.yetki)
        kayit = {"ad": v["ad"], "motor": motor_s,
                 "proje": {"bolum_adi": v["proje"].get("VMCodeSectionName", ".vmp0"),
                           "secenekler": v["proje"].get("Options", []),
                           **{k: val for k, val in v["proje"].items() if k in
                              ("VMVersion", "VMInstances", "VMComplexity", "RandomSeed")},
                           "fonksiyonlar": [{"adres": hex(ad), "tip": TIP_AD[tip], "complexity": c}
                                            for ad, tip, c in v["fonks"]]}}

        if not motor_s["rc"] and os.path.exists(cikti):
            pe = pe_ayrastir(cikti)
            kayit["pe"] = {"boyut": pe["boyut"], "sha256": pe["sha256"], "upx": pe["upx"],
                           "giris_bolumu": pe.get("giris_bolumu"), "dll_ozellikleri": pe.get("dll_ozellikleri"),
                           "art_veri": pe.get("art_veri"), "koruyucu_bolumler": koruyucu_ozet(pe),
                           "bolum_adlari": [b["ad"] for b in pe.get("bolumler", [])],
                           "importlar": pe.get("importlar"), "tls": pe.get("tls"),
                           "yukleme_ayar": pe.get("yukleme_ayar")}
            if not a.wine_siz and motor_s["rc"] == 0:
                w, satirlar = wine_kos(cikti, dizin, a.wine_yetki)
                fark = ilk_fark(referans, satirlar)
                kayit["wine"] = {**w, "eslesti": fark is None, "satir": len(satirlar), "fark": fark}
        k_ozet = ",".join(k["ad"] for k in kayit.get("pe", {}).get("koruyucu_bolumler", []))
        print(f"{v['ad']:<28} rc={motor_s['rc']!s:>3} {motor_s['sure_sn']:>6.1f}s boyut={motor_s['cikti_boyutu']!s:>10} "
              f"wine={kayit.get('wine', {}).get('eslesti', '-')!s:>5} {k_ozet[:60]}", flush=True)
        sonuclar.append(kayit)
    if secili:
        yeni = {s["ad"]: s for s in sonuclar}
        sonuclar = [yeni.pop(s["ad"], s) for s in eski.values()] + list(yeni.values())
        siralama = [x["ad"] for x in matris()]
        sonuclar.sort(key=lambda s: siralama.index(s["ad"]) if s["ad"] in siralama else 999)
    json.dump({"tag": a.tag, "motor": motor, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
               "referans": {"wine_rc": wref["rc"] if wref else None, "satir": len(referans) if referans else None,
                            "md5": hashlib.md5("\n".join(referans).encode()).hexdigest() if referans else None},
               "sonuclar": sonuclar}, open(sonuc_yolu, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"yazıldı: {sonuc_yolu} ({len(sonuclar)} kayıt)")


if __name__ == "__main__":
    main()
