#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312 yama yardımcıları: kaynak dosyalar CRLF satır sonlu olduğu için
değişiklikler bayt düzeyinde, satır-sonu otomatik dönüştürmeli uygulanır.

replace_in_file(dosya, eski, yeni, adet=1)
    eski/yeni metinleri '\n' satır sonlu yazılır; dosya CRLF ise otomatik çevrilir.
    'eski' tam olarak `adet` kez bulunmazsa betik durur (yanlış yere yama engeli).
    Uygulanan her değişiklik KAYIT listesine (dosya, etiket) olarak eklenir.
"""
import os

KAYIT = []


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def read_text(p):
    return _read(p).decode("utf-8", errors="surrogateescape")


def replace_in_file(path, old, new, adet=1, etiket=None):
    data = _read(path)
    o, n = old.encode("utf-8"), new.encode("utf-8")
    # dosyanın çoğu CRLF olsa da eski yamalarla karışan (yalnız LF) bölgeler olabilir:
    # önce CRLF, istenen sayı çıkmazsa LF biçimi denenir; eklenen metin eşleşen biçimi izler
    o_crlf, n_crlf = o.replace(b"\n", b"\r\n"), n.replace(b"\n", b"\r\n")
    c = data.count(o_crlf)
    if c == adet:
        o, n = o_crlf, n_crlf
    else:
        c = data.count(o)
    if c != adet:
        if os.environ.get("V312_KONTROL"):
            print(f"[YAMA-EKSIK] {path}: {etiket or old[:60]!r} {c} kez bulundu (beklenen {adet})")
            return False
        raise SystemExit(f"[YAMA] {path}: {etiket or old[:60]!r} {c} kez bulundu (beklenen {adet})")
    if os.environ.get("V312_KONTROL"):
        KAYIT.append((path, etiket or old.strip().splitlines()[0][:60], c))
        return True
    with open(path, "wb") as f:
        f.write(data.replace(o, n))
    KAYIT.append((path.replace("/home/z/my-project/work/v312/src_patched/", ""), etiket or old.strip().splitlines()[0][:60], adet))
    return True


def say(text, etiket, kaliplar):
    """Metin içinde kalıpların kaçar kez geçtiğini yazdırır (doğrulama için)."""
    for k in kaliplar:
        print(f"   {etiket}: {k!r} -> {text.count(k)}")
