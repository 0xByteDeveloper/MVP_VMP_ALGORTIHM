# MVP_VMP_ALGORTIHM — VMProtect UI Yapısı (11 Sürüm)

VMProtect arayüz yapısının (Tab Liste: Project / Functions / Details; Project →
Functions for protection, Licenses, Files, Options; Options → Virtual Machine,
File, Detection, Additional, Messages, Licensing Parameters; ADD Function →
MovePlayer → Protection/Details) 11 sürüm için çıkarılmış envanteri.

## Dosyalar
- `VMProtect_UI_yapisi_v311.html` — tek dosya: exe ekleme ekranı → sürüm listesi → seçilen sürümün UI ağacı
- `vmp_ui_json/VMProtect_<Edition>_<ver>.json` — 11 sürüm, her biri: canlıTarama + ui ağacı + kanıtlar

## Yöntem (ekran görüntüsü YOK)
- **Canlı tarama:** UniversalMVPUIAlgorithm_QT (umvpqt_cli, V307-3 statik-Qt tespit yaması) —
  V307'de 11/11 sürümde Qt5 (static) tespit edildi (QObject 3–317; metaobject verisi
  self-protect tarafından bellekte bile şifreli).
- **RAM menü taraması:** /proc/PID/mem üzerinde CE-tarzı UTF-8 + UTF-16LE string taraması
  (sürüm başına tablo JSON'a gömülü).
- **UI yapısı:** 3.5.1 kaynak kodu (ProjectOption bitleri, NodeType ağacı, diyaloglar),
  V308 en.lng eşik ölçümleri (Virtual Machine grubu ilk kez 3.8.0; Shadow Stack 3.8.3) ve
  V309 gerçek .vmp proje derlemesi (MovePlayer @ 0x1400014C0 — Virtualization/Mutation/Ultra).
- UPX kaldırılmadı: .UPX0/.UPX1 bölüm adları kamuflaj (upx -d: "not packed by UPX").

## Sürüm kapıları
- Virtual Machine grubu (Version/Instances/Complexity): **3.8.0+**
- Shadow Stack Compatible: **3.8.3+** · .NET VM ayarları: **3.8.6+**
- Licenses / Files / Licensing Parameters / Lock to Serial: **yalnız Ultimate**
- Watermark / Script / Console: Professional +
