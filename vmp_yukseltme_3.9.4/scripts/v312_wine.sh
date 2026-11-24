#!/usr/bin/env bash
# V312: sandbox'ta root olmadan çıkarılan Debian wine 10.0 ile Windows exe çalıştırma sarmalayıcısı.
# Kurulum (root YOK, sistem dizinine yazılmaz):
#   apt-get download libwine wine64 libz-mingw-w64   -> work/tools/wine_deb/
#   dpkg -x *.deb work/tools/wine_root (zlib1.dll x86_64-windows/ altına kopyalanır)
#   /usr/lib/wine/wineserver sarmalayıcındaki sabit /usr/lib/wine yolları betiğin kendi dizinine çevrilir
# Kullanım: v312_wine.sh <exe> [args...]      (stdin/stdout aynen geçer)
# Önek: work/tools/wine_prefix (kaynak ağacına ve sistem dizinlerine dokunulmaz).
R="${V312_WINE_ROOT:-/home/z/my-project/work/tools/wine_root}"
export WINEPREFIX="${WINEPREFIX:-/home/z/my-project/work/tools/wine_prefix}"
export WINEDEBUG="${WINEDEBUG:-fixme-all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"
export LD_LIBRARY_PATH="$R/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export WINEDLLDIR="$R/usr/lib/x86_64-linux-gnu/wine/x86_64-unix"
export WINEDLLPATH="$R/usr/lib/x86_64-linux-gnu/wine/x86_64-windows"
mkdir -p "$WINEPREFIX"
exec "$R/usr/lib/wine/wine64" "$@"
