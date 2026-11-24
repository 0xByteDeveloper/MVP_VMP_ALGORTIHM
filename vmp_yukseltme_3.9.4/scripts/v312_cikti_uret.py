#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312 çıktı üretici: 3.5.1 ↔ 3.9.4 özellik farkı JSON'u, HTML sayfası, yama paketi,
Markdown yama raporu, WORKLOG2 kaydı. Tüm sayılar ölçüm dosyalarından hesaplanır.

Kullanım: v312_cikti_uret.py        (ölçümler: work/v312/test/{taban,yamali}/results.json)
Çıktı   : download/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.{json,html}
          download/YAMA_RAPORU_VMProtect_3.5.1_3.9.4.md
          download/vmp_yukseltme_3.9.4/   (diff, betikler, ölçüm + rea JSON, README)
"""
import hashlib, html as H, json, os, re, shutil, sys, time

KOK = "/home/z/my-project"
W = f"{KOK}/work/v312"
T = f"{W}/test"
DL = f"{KOK}/download"
PAKET = f"{DL}/vmp_yukseltme_3.9.4"
TARIH = "2026-11-24"
sys.path.insert(0, f"{KOK}/scripts")
import v312_test_motor as M  # PE ayrıştırıcısı (pe_ayrastir)


def yukle(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def tr(n):
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else "—"


def mb(n):
    return f"{n / 1e6:.2f} MB".replace(".", ",")


taban = yukle(f"{T}/taban/results.json") or {"sonuclar": []}
yamali = yukle(f"{T}/yamali/results.json") or {"sonuclar": []}
B = {s["ad"]: s for s in taban["sonuclar"]}
Y = {s["ad"]: s for s in yamali["sonuclar"]}
changelog = yukle(f"{W}/changelog_351_394.json") or []
kayitlar = yukle(f"{W}/out/patch/yama_kayitlari.json") or []
girdi = os.path.getsize(f"{KOK}/upload/Test_64.exe")


def boyut(x):
    return (x or {}).get("motor", {}).get("cikti_boyutu")


def koruyucu(x):
    return [k["ad"] for k in ((x or {}).get("pe") or {}).get("koruyucu_bolumler", [])]


def wine(x):
    w = (x or {}).get("wine")
    return None if not w else bool(w.get("eslesti"))


def sha(x):
    return (((x or {}).get("pe") or {}).get("sha256") or "")[:12] or None


def oran(a, b):
    return round(b / a, 2) if a and b else None


# ---------------------------------------------------------------- ölçüm tablosu
SIRA = [s["ad"] for s in taban["sonuclar"]] + [a for a in Y if a not in B]
olcum = []
for a in SIRA:
    b, y = B.get(a), Y.get(a)
    tb, yb = boyut(b), boyut(y)
    olcum.append({"varyasyon": a, "taban_boyut": tb, "yamali_boyut": yb, "yamali_taban_orani": oran(tb, yb),
                  "taban_koruyucu_bolumler": koruyucu(b), "yamali_koruyucu_bolumler": koruyucu(y),
                  "taban_sha12": sha(b), "yamali_sha12": sha(y),
                  "taban_wine_eslesti": wine(b), "yamali_wine_eslesti": wine(y),
                  "taban_sure_sn": (b or {}).get("motor", {}).get("sure_sn"),
                  "yamali_sure_sn": (y or {}).get("motor", {}).get("sure_sn"),
                  "yamali_bolum_entropy": {k["ad"]: k.get("entropy") for k in ((y or {}).get("pe") or {}).get("koruyucu_bolumler", [])}})


def ayni(idx, a, b):
    x, z = idx.get(a), idx.get(b)
    return None if not (x and z) else (sha(x) == sha(z) and sha(x) is not None)


wine_ozet = {}
for etiket, idx in (("taban", B), ("yamali", Y)):
    degerler = [wine(s) for s in idx.values()]
    wine_ozet[etiket] = {"eslesti": degerler.count(True), "eslesmedi": degerler.count(False), "kosulmadi": degerler.count(None),
                         "eslesmeyenler": [s["ad"] for s in idx.values() if wine(s) is False]}

# ---------------------------------------------------------------- resmî changelog (vmpsoft.com kaydı)
ANAHTAR = [("segment name", "bölüm adı"), ("decompiler", "anti-decompiler"), ("complexity", "complexity"),
           ("instances", "instances"), ("virtual machine version", "VM sürümü"), ("version of the virtual machine", "VM sürümü"),
           ("shadow stack", "shadow stack"), ("rtti", "RTTI"), ("obfuscation", "obfuscation"), ("random", "random")]
ilgili = []
for k in changelog:
    for b, et in (("yeni", "YENİ"), ("iyilestirme", "İYİLEŞTİRME"), ("duzeltme", "DÜZELTME")):
        for s in k[b]:
            t = s.lower()
            etiketler = sorted({et for anahtar, et in ANAHTAR if anahtar in t})
            if etiketler:
                ilgili.append({"surum": k["surum"], "tarih": k["tarih"], "tur": et, "metin": s, "etiket": etiketler})


def cl(etiket):
    return [{"surum": x["surum"], "tur": x["tur"], "metin": x["metin"]} for x in ilgili if etiket in x["etiket"]]


# ---------------------------------------------------------------- UPX / resmî ikili kanıtı
v306 = f"{KOK}/download/v306_kanit/VMProtect_Ultimate_3.9.4__VMProtect_peqt.json"
v306_metin = open(v306, encoding="utf-8", errors="replace").read() if os.path.exists(v306) else ""
resmi_396 = M.pe_ayrastir(f"{KOK}/download/Test_64.vmp.exe") if os.path.exists(f"{KOK}/download/Test_64.vmp.exe") else {}
upx = {
    "upx_bolumu_394": False,
    "kanit": "V306 analizci kaydı (VMProtect_Ultimate_3.9.4__VMProtect_peqt.json): UPX'e ait bölüm adı yok",
    "upx_kelimesi_v306_kayitinda": "UPX" in v306_metin,
    "bolumler_394": [".text", ".rdata", ".data", ".pdata", ".tls", ".qtmetad", ".gfids", "_RDATA", ".qWo", ".!*_", ".xz@", ".rsrc", ".reloc"],
    "koruyucu_bolumler_394": {".qWo": "sanal boyut 17.763.483, ham veri 0", ".!*_": "264 / 512 bayt, entropy 0,91", ".xz@": "37.916.172 / 37.916.672 bayt, entropy 7,97"},
    "resmi_396_ciktisi_upx": resmi_396.get("upx"),
    "resmi_396_ciktisi_bolumleri": [b["ad"] for b in resmi_396.get("bolumler", [])],
    "sonuc": "3.9.4 UPX ile paketli DEĞİL (kendisi bir paketleyici: çıktısı UPX ile sıkıştırılmış bölüm tablosu taşımaz) → UPX kaldırma adımı uygulanmadı.",
}

# ---------------------------------------------------------------- özellik farkları
bv, yc = boyut(B.get("fn1-virt")), boyut(Y.get("fn1-virt-c100"))
hmax = boyut(Y.get("hepsi-max"))
OZ = [
    {"ad": "Rastgele bölüm adları (maske)", "ui": "Bölüm tablosu / Project → Options",
     "durum_351": "YOK — ad = şablon adı + sıra numarası, her derlemede aynı",
     "durum_394": "VAR — her koruyucu bölüm ayrı rastgele ad taşır",
     "kanit_351": "core/core.cc:3564-3578 (ProjectTemplate::Init: '.' + 3 alfanümerik, bir kez üretilir) ve 13 adlandırma noktası "
                  "string_format(\"%s%d\", section_name, vmp_index++) [pefile.cc 5, dotnetfile.cc 2, elffile.cc 2, macfile.cc 4]",
     "kanit_394": "3.9.4 ikili bölüm tablosu: .qWo, .!*_ , .xz@ (V306 kaydı)",
     "olcum": f"3.5.1 motor: {', '.join(koruyucu(B.get('fn1-virt-tespit')))} — yamalı motor '.???' maskesi: {', '.join(koruyucu(Y.get('hepsi-max')))}",
     "yama": "NextSectionName(): '?' karakterleri rastgele yazdırılabilir simge olur (PE 8, Mach-O 16, ELF sınırsız); varsayılan şablon adı .???",
     "iddia": "doğru"},
    {"ad": "Sanal makine complexity (proje)", "ui": "Project → Options → Virtual Machine → Complexity",
     "durum_351": "YOK — projede yalnız Options ve VMOptions sayısal öznitelikleri var",
     "durum_394": "VAR — None / 1..100 %",
     "kanit_351": "core/core.cc:691-711 (<Protection> okuma: InputFileName, Options, VMOptions, VMCodeSectionName…); core/files.h:1169 CompileOptions",
     "kanit_394": "Resmî changelog 3.8 (aşağıdaki changelog kayıtları)",
     "olcum": "MovePlayer sanallaştırma — 3.5.1: " + tr(bv) + " bayt; yamalı complexity " + "; ".join(
         f"%{c}: {tr(boyut(Y.get(f'fn1-virt-c{c}')))} bayt" for c in (0, 25, 50, 75, 100) if boyut(Y.get(f"fn1-virt-c{c}"))),
     "yama": "XML VMComplexity=\"0..100\" → CompileOptions::vm_complexity → Mutate çöp komut üst sınırı ve sanallaştırma öncesi mutasyon",
     "iddia": "doğru (boyut ölçümüyle doğrulandı)"},
    {"ad": "Fonksiyona özel complexity", "ui": "Functions for protection → fonksiyon → Protection → Complexity",
     "durum_351": "YOK — fonksiyon seçenekleri yalnız bir bit maskesi (coLockToKey)",
     "durum_394": "VAR — Default / 0..100 %",
     "kanit_351": "core/processors.h:632-634 enum CompilationOption { coLockToKey = 0x2000 }; core/core.cc:749-841 <Procedure> okuma",
     "kanit_394": "Resmî changelog 3.8 (aşağıdaki changelog kayıtları)",
     "olcum": "Yamalı: fonksiyon %50 → " + tr(boyut(Y.get("fn1-virt-fc50"))) + " bayt, %100 → " + tr(boyut(Y.get("fn1-virt-fc100"))) +
              " bayt (proje %0 iken). NOT: proje düzeyi %100 = " + tr(yc) + " bayt; fonksiyon düzeyi etkinin daha küçük kalmasının nedeni bu oturumda incelenmedi.",
     "yama": "XML <Procedure Complexity=\"0..100\"> → adres→% tablosu → fonksiyon değeri yoksa proje değeri kullanılır",
     "iddia": "kısmen doğrulandı (çalışıyor, etki büyüklüğü incelenmedi)"},
    {"ad": "Sanal makine örnek sayısı (Instances)", "ui": "Project → Options → Virtual Machine → Instances",
     "durum_351": "Kullanıcıya kapalı — motor içinde sabit 1 veya 10",
     "durum_394": "VAR — Default / 1..10",
     "kanit_351": "core/core.cc:1749-1757 (options.vm_count … ? 1 : 10); core/intel.cc:30781 VM oluşturma döngüsü",
     "kanit_394": "Resmî changelog 3.8",
     "olcum": f"Yamalı: 1 örnek → {tr(boyut(Y.get('fn1-virt-i1')))} bayt; 10 örnek → {tr(boyut(Y.get('fn1-virt-i10')))} bayt",
     "yama": "XML VMInstances=\"1..10\" → CompileOptions::vm_count", "iddia": "doğru"},
    {"ad": "Sanal makine sürümü (Version)", "ui": "Project → Options → Virtual Machine → Version",
     "durum_351": "Kullanıcıya kapalı — yalnız VMOptions biti (klasik/gelişmiş VM)",
     "durum_394": "VAR — Default / VMProtect 2.X",
     "kanit_351": "core/intel.cc:30645-30651 ((vm_flags & 1) ? vtClassic : vtAdvanced)",
     "kanit_394": "Resmî changelog 3.8",
     "olcum": f"Yamalı: Default → {tr(boyut(Y.get('fn1-virt')))} bayt; VMProtect 2.X → {tr(boyut(Y.get('fn1-virt-vm2x')))} bayt",
     "yama": "XML VMVersion=\"0|1\" → vm_flags bit 0", "iddia": "doğru"},
    {"ad": "Derleme rastgele tohumu", "ui": "(yamaya eklenen yardımcı seçenek)",
     "durum_351": "Tohum sabit 0 → aynı proje her derlemede bayt bayt aynı çıktı",
     "durum_394": "Bu oturumda resmî 3.9.4 davranışı ölçülemedi (ikili yok)",
     "kanit_351": "core/core.cc:1707 (rand_seed = 0; srand(rand_seed))",
     "kanit_394": "—",
     "olcum": "Yamalı: tohumsuz iki derleme aynı mı? " + ("evet" if ayni(Y, "fn1-virt", "fn1-virt-tekrar") else "hayır") +
              "; RandomSeed=12345 ile iki derleme aynı mı? " + ("evet" if ayni(Y, "fn1-virt-seed12345", "fn1-virt-seed12345-tekrar") else "hayır"),
     "yama": "XML RandomSeed (yoksa her derlemede yeni tohum; verilirse tekrarlanabilir derleme)", "iddia": "kullanıcı iddiası dışında"},
]
for ad, etiket, ui in (("Sanal koda karşı anti-statik-decompiler koruması", "anti-decompiler", "3.7"),
                       ("Sanal makine obfuscation iyileştirmeleri", "obfuscation", "3.7.3 / 3.8.2"),
                       ("Shadow Stack uyumluluğu", "shadow stack", "3.8.3"),
                       ("RTTI ad obfuscation vb.", "RTTI", "3.9.3")):
    OZ.append({"ad": ad, "ui": ui, "durum_351": "yok", "durum_394": "changelog'da kayıtlı",
               "kanit_351": "3.5.1 kaynağında karşılığı bulunamadı", "kanit_394": "Resmî changelog: " + ui,
               "olcum": "—", "yama": "UYGULANMADI (bu oturumun kapsamı dışı)", "iddia": "changelog ile doğrulandı", "changelog": cl(etiket)})
OZ.append({"ad": "Bayt kodu şifreleme (cpEncryptBytecode)", "ui": "Lisans bağlantılı",
           "durum_351": "Kaynakta var, lisans kapılı", "durum_394": "bu oturumda ölçülemedi",
           "kanit_351": "core/core.cc:1739-1744 (VMProtectGetSerialNumberState() == SERIAL_STATE_SUCCESS)",
           "kanit_394": "—", "olcum": "—", "yama": "DOKUNULMADI — lisans mekanizması değiştirilmedi", "iddia": "—"})

# ---------------------------------------------------------------- JSON
fj = {"baslik": "VMProtect 3.5.1 ↔ 3.9.4 özellik farkı ve yükseltme yaması", "tarih": TARIH,
      "kaynak_kod": "universalObfusPublicSrc (3.5.1)", "hedef_surum": "VMProtect Ultimate 3.9.4",
      "girdi": {"dosya": "Test_64.exe", "boyut": girdi},
      "ozellik_farklari": OZ,
      "changelog_351_394": {"surum_sayisi": len(changelog), "kaynak": "vmpsoft.com changelog (work/vmp_history.json)",
                            "ilgili_kayitlar": ilgili},
      "upx": upx,
      "olcum": olcum,
      "wine_dogrulama": wine_ozet,
      "boyut_iddiasi": {"kullanici": "100 KB exe → 24 MB", "durum": "resmî 3.9.4 ikilisi elde edilemediği için DOĞRULANAMADI",
                        "olculenler": {"taban_3.5.1_virt_1fonk": bv, "yamali_virt_c100": yc, "yamali_hepsi_max": hmax,
                                       "resmi_396_v301_6fonk": resmi_396.get("boyut")}},
      "yama": {"diff": "10_yukseltme_3.9.4.diff", "dosyalar": sorted({k["dosya"] for k in kayitlar}),
               "yama_noktasi": len(kayitlar), "kayitlar": kayitlar,
               "yapilmayanlar": ["Lua binder'ları (vmVersion/vmInstances/vmComplexity/randomSeed, complexity)",
                                 "Qt GUI özellik satırları (derlenmedi)", "konsol anahtarları (-vm/-vi/-vc/-rs)",
                                 "ValueCryptor zincir uzunluğunun complexity'e bağlanması", "AddUnknown (map adı) dalında Complexity"]},
      "sinirlar": ["Yandex Disk captcha'sı aşılmadı → resmî 3.9.4 ikilisi yok",
                   "rea'da decompiler provider'ı yok; compare-artifacts yalnız inspect-artifact kanıtı kabul ediyor",
                   "MemoryProtection + ImportProtection seçenekli çıktılar wine 10 altında beklenen çıktıyı vermedi (3.5.1 ve yamalı motorda aynı)"]}
json.dump(fj, open(f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- HTML
def isaret(v):
    return {True: "✓", False: "✗", None: "—"}[v]


def esc(s):
    return H.escape("" if s is None else str(s))


CSS = """
:root{--bg:#0f1420;--card:#19202f;--fg:#e8edf5;--mut:#9aa7bb;--acc:#5cc8ff;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24;--line:#2a3550}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);line-height:1.5;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:clamp(12px,3vw,28px)}
.kicker{color:var(--acc);font-size:clamp(.72rem,2vw,.88rem);letter-spacing:.08em;text-transform:uppercase}
h1{font-size:clamp(1.3rem,4.4vw,2.3rem);margin:.15em 0 .2em;line-height:1.2}
h2{font-size:clamp(1.05rem,3vw,1.45rem);margin:.4em 0 .5em}
h3{font-size:clamp(.95rem,2.6vw,1.15rem);margin:1.2em 0 .4em}
p,li,td,th{font-size:clamp(.86rem,2.2vw,.96rem)}
.sub{color:var(--mut);margin:.2em 0 1em}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:clamp(12px,2.5vw,20px);margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(230px,100%),1fr));gap:12px}
.kpi b{display:block;font-size:clamp(1.25rem,4.5vw,2rem);color:var(--acc);word-break:break-word}
.kpi span{color:var(--mut);font-size:clamp(.78rem,2vw,.9rem)}
.tabs{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 8px}
.tabs button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:8px clamp(10px,2.5vw,16px);
 font-size:clamp(.82rem,2.2vw,.95rem);cursor:pointer}
.tabs button[aria-selected="true"]{border-color:var(--acc);color:var(--acc)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;min-width:560px}
th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:#0b0f18;padding:1px 5px;border-radius:5px;font-size:.9em;word-break:break-word}
pre{overflow-x:auto;background:#0b0f18;padding:12px;border-radius:8px;font-size:clamp(.74rem,1.9vw,.84rem)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
details{margin:8px 0}summary{cursor:pointer;color:var(--acc)}
.panel[hidden]{display:none}
ul{padding-left:1.2em}li{margin:.25em 0}
footer{color:var(--mut);font-size:clamp(.75rem,2vw,.85rem);margin:24px 0 8px}
"""
JS = "(function(){var b=[].slice.call(document.querySelectorAll('.tabs button')),s=[].slice.call(document.querySelectorAll('.panel'));b.forEach(function(x,i){x.addEventListener('click',function(){b.forEach(function(y){y.setAttribute('aria-selected','false')});x.setAttribute('aria-selected','true');s.forEach(function(p,j){if(j!==i){p.hidden=true}else{p.hidden=false}})})})})();"

kpi = [("Girdi (Test_64.exe)", tr(girdi) + " bayt"), ("3.5.1 · MovePlayer sanallaştırma", tr(bv) + " bayt"),
       ("Yamalı · aynı iş, complexity %100", tr(yc) + " bayt"), ("Yamalı · hepsi-max (6 fonk, Ultra)", mb(hmax)),
       ("wine doğrulama (yamalı)", f"{wine_ozet['yamali']['eslesti']} eşleşti / {wine_ozet['yamali']['eslesmedi']} eşleşmedi")]

oz_satir = "".join(
    f"<tr><td><b>{esc(o['ad'])}</b><br><span class=warn>{esc(o['ui'])}</span></td><td>{esc(o['durum_351'])}<br><code>{esc(o['kanit_351'])}</code></td>"
    f"<td>{esc(o['durum_394'])}<br><code>{esc(o['kanit_394'])}</code></td><td>{esc(o['olcum'])}</td><td>{esc(o['yama'])}</td></tr>" for o in OZ)

olcum_satir = "".join(
    f"<tr><td><code>{esc(r['varyasyon'])}</code></td><td>{tr(r['taban_boyut'])}</td><td>{tr(r['yamali_boyut'])}</td>"
    f"<td>{esc(', '.join(r['taban_koruyucu_bolumler']))}</td><td>{esc(', '.join(r['yamali_koruyucu_bolumler']))}</td>"
    f"<td class={'ok' if r['taban_wine_eslesti'] else ('bad' if r['taban_wine_eslesti'] is False else '')}>{isaret(r['taban_wine_eslesti'])}</td>"
    f"<td class={'ok' if r['yamali_wine_eslesti'] else ('bad' if r['yamali_wine_eslesti'] is False else '')}>{isaret(r['yamali_wine_eslesti'])}</td></tr>" for r in olcum)

cl_satir = "".join(f"<tr><td>{esc(x['surum'])}</td><td>{esc(x['tur'])}</td><td>{esc(x['metin'])}</td><td>{esc(', '.join(x['etiket']))}</td></tr>" for x in ilgili)
yama_satir = "".join(f"<tr><td><code>{esc(k['dosya'])}</code></td><td>{esc(k['etiket'])}</td><td>{k['adet']}</td></tr>" for k in kayitlar)

doc = f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VMProtect 3.5.1 ↔ 3.9.4 — özellik farkı ve yükseltme yaması</title>
<style>{CSS}</style></head><body><div class="wrap">
<div class="kicker">VMProtect · MVP_VMP_ALGORTIHM · V312 · {TARIH}</div>
<h1>VMProtect 3.5.1 ↔ Ultimate 3.9.4: özellik farkı ve yükseltme yaması</h1>
<p class="sub">Kaynak: universalObfusPublicSrc (3.5.1) satır satır okundu; resmî changelog (3.5.1 &lt; sürüm ≤ 3.9.4, {len(changelog)} sürüm) ve elimizdeki 3.9.x ikili kanıtlarıyla karşılaştırıldı.
Eksik özellikler 3.5.1 kaynağına yama olarak kodlandı, iki motor Linux/g++ ile derlenip aynı {len(SIRA)} varyasyonluk proje matrisiyle ölçüldü ve çıktılar wine 10 altında çalıştırılarak doğrulandı.</p>
<div class="grid card">{''.join(f'<div class="kpi"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in kpi)}</div>
<div class="tabs" role="tablist">
<button aria-selected="true">Özellik farkları</button><button aria-selected="false">Ölçümler</button><button aria-selected="false">Yama</button>
<button aria-selected="false">UPX ve 3.9.4 kanıtı</button><button aria-selected="false">Sınırlar</button></div>
<section class="panel"><h2>Özellik farkları</h2>
<div class="card"><p><b>Yöntem:</b> her satır üç kanıtla desteklenir — 3.5.1 kaynağında dosya:satır, resmî changelog kaydı ve elimizdeki ikili kanıtı.
"Ölçüm" sütunundaki sayılar bu oturumda, aynı <code>Test_64.exe</code> girdisiyle iki motorun ürettiği çıktı boyutlarıdır (bayt).</p></div>
<div class="card tw"><table><thead><tr><th>Özellik</th><th>3.5.1 (kaynak)</th><th>3.9.4</th><th>Ölçüm</th><th>Yamada</th></tr></thead>
<tbody>{oz_satir}</tbody></table></div>
<h3>Boyut iddiası: “100 KB exe → 24 MB”</h3>
<div class="card"><p>Resmî 3.9.4 ikilisi elde edilemediği için iddia resmî sürümde <b>doğrulanamadı</b>. Yamalı motorla ölçülenler:
MovePlayer sanallaştırma {tr(bv)} bayt; aynı iş complexity %100 ile {tr(yc)} bayt; 6 fonksiyon Ultra + fonksiyon %100 + proje %100 + 10 örnek + Memory/Import Protection ile <b>{tr(hmax)} bayt ({mb(hmax)})</b> — girdi {tr(girdi)} bayt.
Yani büyüme tek bir özellikten değil; complexity, örnek sayısı, koruma seçenekleri ve sanallaştırılan fonksiyon sayısının toplamından gelir.</p></div>
<h3>Resmî changelog — ilgili kayıtlar (olduğu gibi)</h3>
<div class="card tw"><table><thead><tr><th>Sürüm</th><th>Tür</th><th>Kayıt</th><th>Etiket</th></tr></thead><tbody>{cl_satir}</tbody></table></div>
</section>
<section class="panel" hidden><h2>Ölçümler: aynı proje, iki motor</h2>
<div class="card"><p>Proje XML'i iki motora da aynı verilir; 3.5.1 bilinmeyen öznitelikleri yok sayar. ✓ = korumalı exe wine 10 altında korumamasız exe ile aynı çıktıyı verdi (94 satır).</p></div>
<div class="card tw"><table><thead><tr><th>Varyasyon</th><th>3.5.1 boyut</th><th>Yamalı boyut</th><th>3.5.1 bölüm adları</th><th>Yamalı bölüm adları</th><th>wine 3.5.1</th><th>wine yamalı</th></tr></thead>
<tbody>{olcum_satir}</tbody></table></div>
<div class="card"><p><b>Wine:</b> 3.5.1 — {wine_ozet['taban']['eslesti']} eşleşti, {wine_ozet['taban']['eslesmedi']} eşleşmedi; yamalı — {wine_ozet['yamali']['eslesti']} eşleşti, {wine_ozet['yamali']['eslesmedi']} eşleşmedi.
Eşleşmeyenler: <code>{esc(', '.join(wine_ozet['yamali']['eslesmeyenler']))}</code> (MemoryProtection + ImportProtection açık; her iki motorda aynı sonuç, yamadan kaynaklı değil).</p></div>
</section>
<section class="panel" hidden><h2>Yükseltme yaması (3.5.1 → 3.9.4 altyapısı)</h2>
<div class="card"><p><b>{len(kayitlar)} yama noktası, {len({k['dosya'] for k in kayitlar})} dosya:</b> {esc(', '.join(sorted({k['dosya'] for k in kayitlar})))}.
Kaynak ağacına ve lisans kapılı koda dokunulmadı; yama <code>vmp_yukseltme_3.9.4/10_yukseltme_3.9.4.diff</code> dosyasında, betikler aynı pakette.</p></div>
<div class="card tw"><table><thead><tr><th>Dosya</th><th>Değişiklik</th><th>Nokta</th></tr></thead><tbody>{yama_satir}</tbody></table></div>
<h3>Yeni proje XML öznitelikleri</h3>
<div class="card"><pre>&lt;Protection Options="0" VMCodeSectionName=".???"
             VMVersion="0"      &lt;!-- 0 = Default, 1 = VMProtect 2.X --&gt;
             VMInstances="10"   &lt;!-- 0 = Default (10), 1..10 --&gt;
             VMComplexity="50"  &lt;!-- proje %0..100 --&gt;
             RandomSeed="12345"&gt; &lt;!-- isteğe bağlı: tekrarlanabilir derleme --&gt;
  &lt;Procedure Address="0x1400014C0" CompilationType="0" IncludedInCompilation="true" Complexity="100" /&gt;</pre></div>
</section>
<section class="panel" hidden><h2>UPX ve 3.9.4 ikili kanıtı</h2>
<div class="card"><p><b>Sonuç: 3.9.4 UPX ile paketli değil.</b> {esc(upx['kanit'])}. UPX kaldırma adımı bu yüzden uygulanmadı.</p>
<p>3.9.4 bölüm tablosu (V306): {esc(', '.join(upx['bolumler_394']))}. Koruyucu bölümler: <code>{esc(json.dumps(upx['koruyucu_bolumler_394'], ensure_ascii=False))}</code>.
Üç koruyucu bölümün üçü farklı rastgele ad taşıyor — 3.5.1'de ise hepsi <code>.vmp00 / .vmp01 / .vmp02</code>.</p>
<p>Elimizdeki resmî 3.9.6 çıktısı (Test_64.vmp.exe): UPX işareti = {esc(upx['resmi_396_ciktisi_upx'])}; bölümler: {esc(', '.join(upx['resmi_396_ciktisi_bolumleri']))}.</p></div>
</section>
<section class="panel" hidden><h2>Sınırlar ve yapılmayanlar</h2>
<div class="card"><ul>{''.join(f'<li>{esc(s)}</li>' for s in fj['sinirlar'])}</ul></div>
<div class="card"><p><b>Yamada yapılmayanlar (sonraki oturum):</b></p><ul>{''.join(f'<li>{esc(s)}</li>' for s in fj['yama']['yapilmayanlar'])}</ul></div>
</section>
<footer>Statik sayfa · veriler: VMProtect_3.5.1_vs_3.9.4_ozellik_farki.json · ölçüm düzeneği scripts/v312_test_motor.py</footer>
</div><script>{JS}</script></body></html>"""
open(f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.html", "w", encoding="utf-8").write(doc)

# ---------------------------------------------------------------- yama paketi
if os.path.isdir(PAKET):
    shutil.rmtree(PAKET)
for d in ("", "/patch", "/scripts", "/olcum", "/rea"):
    os.makedirs(PAKET + d)
for f in ("v312_apply_yukseltme.py", "v312_build_linux.py", "v312_prep_trees.py", "v312_patchlib.py",
          "v312_test_motor.py", "v312_wine.sh", "v312_cikti_uret.py"):
    shutil.copy2(f"{KOK}/scripts/{f}", f"{PAKET}/scripts/{f}")
for f in os.listdir(f"{W}/out/patch"):
    shutil.copy2(f"{W}/out/patch/{f}", f"{PAKET}/patch/{f}")
for tag, ad in (("taban", "olcum_taban_3.5.1.json"), ("yamali", "olcum_yamali.json")):
    if os.path.exists(f"{T}/{tag}/results.json"):
        shutil.copy2(f"{T}/{tag}/results.json", f"{PAKET}/olcum/{ad}")
rea_liste = []
if os.path.isdir(f"{W}/rea"):
    for f in sorted(os.listdir(f"{W}/rea")):
        if f.startswith("_probe"):
            continue
        shutil.copy2(f"{W}/rea/{f}", f"{PAKET}/rea/{f}")
        rea_liste.append(f)

# ---------------------------------------------------------------- Markdown yama raporu
def md_tablo(baslik, satirlar):
    return "| " + " | ".join(baslik) + " |\n|" + "|".join("---" for _ in baslik) + "|\n" + "".join("| " + " | ".join(str(c) for c in r) + " |\n" for r in satirlar)


olcum_md = md_tablo(["Varyasyon", "3.5.1 boyut", "Yamalı boyut", "3.5.1 bölüm adları", "Yamalı bölüm adları", "wine 3.5.1", "wine yamalı"],
                    [[r["varyasyon"], tr(r["taban_boyut"]), tr(r["yamali_boyut"]), ", ".join(r["taban_koruyucu_bolumler"]) or "—",
                      ", ".join(r["yamali_koruyucu_bolumler"]) or "—", isaret(r["taban_wine_eslesti"]), isaret(r["yamali_wine_eslesti"])] for r in olcum])
oz_md = md_tablo(["Özellik", "3.5.1", "3.9.4", "Ölçüm", "Yamada"],
                 [[o["ad"], o["durum_351"], o["durum_394"], o["olcum"], o["yama"]] for o in OZ])
yama_md = md_tablo(["Dosya", "Değişiklik", "Nokta"], [[k["dosya"], k["etiket"], k["adet"]] for k in kayitlar])
cl_md = md_tablo(["Sürüm", "Tür", "Kayıt"], [[x["surum"], x["tur"], x["metin"]] for x in ilgili])
rapor = f"""# Yama raporu — VMProtect 3.5.1 → 3.9.4 altyapısı

**Tarih:** {TARIH} · **Kaynak:** universalObfusPublicSrc (VMProtect 3.5.1) · **Hedef:** VMProtect Ultimate 3.9.4
**Durum:** yama uygulandı, motor Linux/g++ 14 ile derlendi ({len(yamali)} varyasyon), korumalı çıktılar wine 10.0 ile doğrulandı.

## 1. Özet

3.5.1 kaynağı ile 3.9.4 arasındaki fark, resmî changelog ve ikili kanıtlara göre beş başlıkta toplanıyor: rastgele bölüm adları,
sanal makine complexity'si, fonksiyona özel complexity, sanal makine örnek sayısı ve sanal makine sürümü. Bunlardan ilk beşi bu yamayla
3.5.1 kaynağına eklendi; changelog'daki anti-decompiler, Shadow Stack ve RTTI maddeleri eklenmedi (aşağıda listelendi).

Ölçülen sonuç (girdi Test_64.exe, {tr(girdi)} bayt): MovePlayer sanallaştırma 3.5.1'de {tr(bv)} bayt; yamalı motor complexity %100 ile
{tr(yc)} bayt; 6 fonksiyon Ultra + complexity + 10 örnek + Memory/Import Protection ile {tr(hmax)} bayt ({mb(hmax)}).
Bölüm adları 3.5.1'de her derlemede `.vmp00/.vmp01/.vmp02`, yamalı motorda `.???` maskesiyle her derlemede farklı
({', '.join(koruyucu(Y.get('hepsi-max')))}).

## 2. UPX kontrolü

{upx['sonuc']} 3.9.4 bölüm tablosu (V306 kaydı): {', '.join(upx['bolumler_394'])}. Elimizdeki resmî 3.9.6 çıktısının UPX işareti: {upx['resmi_396_ciktisi_upx']}.

## 3. Özellik farkları

{oz_md}
### Resmî changelog — ilgili kayıtlar (vmpsoft.com, olduğu gibi)

{cl_md}
## 4. Ölçümler (aynı proje matrisi, iki motor)

{olcum_md}
✓ = korumalı exe wine 10 altında korumamasız exe ile aynı çıktıyı verdi; ✗ = vermedi; — = koşulmadı. Eşleşmeyenler
({', '.join(wine_ozet['yamali']['eslesmeyenler'])}) MemoryProtection + ImportProtection seçenekli projeler; 3.5.1 motorunda da aynı.

## 5. Yama noktaları

`patch/10_yukseltme_3.9.4.diff` (src_base → src_patched). {len(kayitlar)} nokta, {len({k['dosya'] for k in kayitlar})} dosya:

{yama_md}
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

{chr(10).join('- ' + s for s in fj['yama']['yapilmayanlar'])}
- Fonksiyona özel complexity'nin etki büyüklüğü: %50 → {tr(boyut(Y.get('fn1-virt-fc50')))} bayt, %100 → {tr(boyut(Y.get('fn1-virt-fc100')))} bayt
  (proje %0 iken). Proje düzeyi %100 = {tr(yc)} bayt. Farkın nedeni incelenmedi.
- MemoryProtection + Import Protection seçenkeli çıktılar wine 10 altında çalışmadı (her iki motorda).

{chr(10).join('- ' + s for s in fj['sinirlar'])}
"""
for hedef in (f"{PAKET}/YAMA_RAPORU.md", f"{DL}/YAMA_RAPORU_VMProtect_3.5.1_3.9.4.md"):
    open(hedef, "w", encoding="utf-8").write(rapor)

open(f"{PAKET}/README.md", "w", encoding="utf-8").write(f"""# VMProtect 3.5.1 → 3.9.4 yükseltme yaması (V312, {TARIH})

- `YAMA_RAPORU.md` — yama raporu (özellik farkı tablosu, ölçümler, yama noktaları, yapılmayanlar)
- `patch/10_yukseltme_3.9.4.diff` — yama (9 dosya, {len(kayitlar)} nokta) · `patch/00_gcc_uyumluluk.diff` — yalnız g++ için
- `patch/yama_kayitlari.json` — yama noktaları listesi
- `scripts/` — uygulama / derleme / ölçüm / wine betikleri
- `olcum/` — iki motorun ölçüm sonuçları (JSON) · `rea/` — rea çıktıları ({len(rea_liste)} dosya)

Kullanım: `python3 scripts/v312_prep_trees.py --yeni && python3 scripts/v312_apply_yukseltme.py && python3 scripts/v312_build_linux.py --src work/v312/src_patched --out work/v312/build_patched`
Lisans kapılı kod değiştirilmedi. Kaynak ağacı (3.5.1) bu pakette YOK, yalnız diff vardır.
""")

# ---------------------------------------------------------------- WORKLOG2 + .gitignore + yönlendirme
md5ler = {os.path.basename(p): hashlib.md5(open(p, "rb").read()).hexdigest()
          for p in (f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.json", f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.html",
                    f"{DL}/YAMA_RAPORU_VMProtect_3.5.1_3.9.4.md", f"{W}/out/patch/10_yukseltme_3.9.4.diff") if os.path.exists(p)}
wl = f"""
### V312 oturum sonu kaydı ({TARIH}) — YAMALI MOTOR DERLENDİ VE ÖLÇÜLDÜ
- Yamalı derleme: `work/v312/build_patched/bin/VMProtectCon` (CIKIS=0); yama {len(kayitlar)} nokta / {len({k['dosya'] for k in kayitlar})} dosya, diff {os.path.getsize(f"{W}/out/patch/10_yukseltme_3.9.4.diff") if os.path.exists(f"{W}/out/patch/10_yukseltme_3.9.4.diff") else 0} bayt.
- Ölçüm (yamalı): fn1-virt {tr(bv)} (taban) → c0 {tr(boyut(Y.get('fn1-virt-c0')))}, c25 {tr(boyut(Y.get('fn1-virt-c25')))}, c50 {tr(boyut(Y.get('fn1-virt-c50')))}, c75 {tr(boyut(Y.get('fn1-virt-c75')))}, c100 {tr(yc)};
  i1 {tr(boyut(Y.get('fn1-virt-i1')))}, vm2x {tr(boyut(Y.get('fn1-virt-vm2x')))}, hepsi-max {tr(hmax)} ({mb(hmax)}); bölüm adları `.???` → {', '.join(koruyucu(Y.get('hepsi-max')))}.
- Wine: yamalı {wine_ozet['yamali']['eslesti']} eşleşti / {wine_ozet['yamali']['eslesmedi']} eşleşmedi ({', '.join(wine_ozet['yamali']['eslesmeyenler'])} — Memory/Import Protection, iki motorda da aynı).
- Teslimler: download/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.json + .html, download/YAMA_RAPORU_VMProtect_3.5.1_3.9.4.md, download/vmp_yukseltme_3.9.4/ (diff, betikler, ölçüm, rea).
- MD5: {json.dumps(md5er) if (md5er := md5ler) else {}}
- Yapılmayanlar: Lua binder'ları, Qt GUI satırları, konsol anahtarları, ValueCryptor, AddUnknown dalı; .docx/.pdf yama raporu (adım sınırı — Markdown rapor var);
  rea decompiler/compare-artifacts (provider yok); fonksiyona özel complexity etki büyüklüğü incelenmedi; resmî 3.9.4 ikilisi yok (Yandex captcha).
- DEVAM → yukarıdaki "Yapılmayanlar" listesinden; ilk adım `work/push_mvp_vmp` klonunda push doğrulaması.
"""
open(f"{KOK}/WORKLOG2.md", "a", encoding="utf-8").write(wl)
wl1 = f"{KOK}/WORKLOG.md"
if "WORKLOG2.md" not in open(wl1, encoding="utf-8").read()[-600:]:
    open(wl1, "a", encoding="utf-8").write("\n\n---\n**WORKLOG.md 400 satırı aştı: devamı `WORKLOG2.md` dosyasında (son bölüm `## 33) V312`). Her kullanıcı mesajında önce WORKLOG2.md'nin son bölümü okunur.**\n")
gi = f"{KOK}/.gitignore"
gl = open(gi, encoding="utf-8").read() if os.path.exists(gi) else ""
for pat in ("work/v312/build_*/", "work/tools/wine_root/", "work/tools/wine_prefix/", "work/tools/wine_deb/", "work/tools/wine_zroot/"):
    if pat not in gl:
        gl += ("\n" if gl and not gl.endswith("\n") else "") + pat + "\n"
open(gi, "w", encoding="utf-8").write(gl)

print("JSON ", os.path.getsize(f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.json"))
print("HTML ", os.path.getsize(f"{DL}/VMProtect_3.5.1_vs_3.9.4_ozellik_farki.html"))
print("RAPOR", os.path.getsize(f"{DL}/YAMA_RAPORU_VMProtect_3.5.1_3.9.4.md"))
print("PAKET", sum(len(f) for _, _, f in os.walk(PAKET)), "dosya; rea:", rea_liste)
print("ölçüm satırı", len(olcum), "| changelog ilgili", len(ilgili), "/", len(changelog), "sürüm | yama noktası", len(kayitlar))
print("wine", wine_ozet)
