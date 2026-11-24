#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V312: VMProtect 3.5.1 -> 3.9.4 yükseltme yaması.

src_base'in TAZE kopyası src_patched'e yazılır (her çalıştırmada sıfırdan), yamalar bayt düzeyinde
ve CRLF/LF duyarlı uygulanır (v312_patchlib). Kaynak ağaç A'ya ve src_base'e dokunulmaz.

Yamalar:
  1. Rastgele bölüm adları (maske): CompileOptions + NextSectionName (files.h/files.cc) ve 13 adlandırma noktası
  2. Proje seçenekleri: VMVersion / VMInstances / VMComplexity / RandomSeed (core.h, core.cc XML oku/yaz, Compile)
  3. Fonksiyona özel Complexity: <Procedure Complexity="0..100"> (adres -> % tablosu, Core içinde)
  4. Motor tüketimi: IntelFunction::Mutate çöp komut üst sınırı, Sanallaştırma + complexity -> önce mutasyon
  5. Varsayılan şablon bölüm adı: ".???" maskesi (3.5.1'de başlangıçta bir kez üretilen sabit ad yerine)

Lisans kapılı kod (cpEncryptBytecode / VMProtectGetSerialNumberState bloğu) DEĞİŞTİRİLMEDİ.

Kullanım: v312_apply_yukseltme.py        (V312_KONTROL=1: yalnız denetler, yazmaz)
Çıktı   : work/v312/src_patched/*, work/v312/out/patch/10_yukseltme_3.9.4.diff, yama_kayitlari.json
"""
import filecmp, json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v312_patchlib as P

BASE = "/home/z/my-project/work/v312/src_base"
PATCHED = "/home/z/my-project/work/v312/src_patched"
OUT = "/home/z/my-project/work/v312/out/patch"
KONTROL = bool(os.environ.get("V312_KONTROL"))

if not KONTROL:
    if os.path.isdir(PATCHED):
        shutil.rmtree(PATCHED)
    shutil.copytree(BASE, PATCHED, symlinks=True)
os.makedirs(OUT, exist_ok=True)


def R(rel, eski, yeni, adet, etiket):
    P.replace_in_file(f"{PATCHED}/core/{rel}", eski, yeni, adet, etiket)


# ---------------------------------------------------------------- 1+2+3: files.h
R("files.h",
  "struct CompileOptions {\n"
  "\tuint32_t flags;\n"
  "\tuint32_t vm_flags;\n"
  "\tuint32_t sdk_flags;\n"
  "\tsize_t vm_count;\n"
  "\tstd::string section_name;\n",
  "#include <map>\n"
  "#define VMP_COMPLEXITY_DEFAULT 0xFF\n"
  "\n"
  "struct CompileOptions {\n"
  "\tuint32_t flags;\n"
  "\tuint32_t vm_flags;\n"
  "\tuint32_t sdk_flags;\n"
  "\tsize_t vm_count;\n"
  "\tstd::string section_name;\n"
  "\t// 3.9.4 upgrade: project VM complexity (0..100 %) and per-function complexity (address -> %)\n"
  "\tuint8_t vm_complexity;\n"
  "\tconst std::map<uint64_t, uint8_t> *function_complexity;\n",
  1, "files.h: CompileOptions alanlari")

R("files.h", "vm_count(1), watermark(NULL), script(NULL), architecture(NULL)",
  "vm_count(1), vm_complexity(0), function_complexity(NULL), watermark(NULL), script(NULL), architecture(NULL)",
  1, "files.h: CompileOptions kurucusu")

R("files.h",
  "\t{}\n"
  "};\n"
  "\n"
  "class Folder : public ObjectList<Folder>\n",
  "\t{}\n"
  "};\n"
  "\n"
  "// 3.9.4 upgrade: section name mask. Every '?' becomes a random printable symbol; without '?'\n"
  "// the 3.5.1 behaviour (name + running index) is kept. max_len: PE 8, Mach-O 16, ELF 0 (unlimited).\n"
  "std::string NextSectionName(const CompileOptions &options, uint32_t index, size_t max_len);\n"
  "\n"
  "class Folder : public ObjectList<Folder>\n",
  1, "files.h: NextSectionName bildirimi")

# ---------------------------------------------------------------- 1: files.cc (uygulama)
UYGULAMA = (
    "// 3.9.4 upgrade: random section names (VMProtect 3.6+ \"mask\" feature)\n"
    "std::string NextSectionName(const CompileOptions &options, uint32_t index, size_t max_len)\n"
    "{\n"
    "\tstd::string mask = options.section_name;\n"
    "\tif (mask.find('?') == std::string::npos) {\n"
    "\t\t// 3.5.1 behaviour: fixed name + running index\n"
    "\t\tstd::string res = string_format(\"%s%d\", mask.c_str(), index);\n"
    "\t\tif (max_len && res.size() > max_len)\n"
    "\t\t\tres.resize(max_len);\n"
    "\t\treturn res;\n"
    "\t}\n"
    "\tstatic const char symbols[] = \"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&'()*+,-.@^_`{}~\";\n"
    "\tstd::string res;\n"
    "\tfor (size_t i = 0; i < mask.size(); i++) {\n"
    "\t\tif (max_len && res.size() >= max_len)\n"
    "\t\t\tbreak;\n"
    "\t\tres += (mask[i] == '?') ? symbols[rand() % (sizeof(symbols) - 1)] : mask[i];\n"
    "\t}\n"
    "\treturn res;\n"
    "}\n"
    "\n")
R("files.cc", "CompilationType FunctionBundle::compilation_type() const\n",
  UYGULAMA + "CompilationType FunctionBundle::compilation_type() const\n",
  1, "files.cc: NextSectionName uygulaması")

ESKI_AD = 'string_format("%s%d", ctx.options.section_name.c_str(), vmp_index++)'
for rel, sinir in (("pefile.cc", 8), ("dotnetfile.cc", 8), ("elffile.cc", 0), ("macfile.cc", 16)):
    yol = f"{PATCHED}/core/{rel}"
    adet = open(yol, "rb").read().count(ESKI_AD.encode())
    P.replace_in_file(yol, ESKI_AD, f"NextSectionName(ctx.options, vmp_index++, {sinir})", adet,
                      f"{rel}: bolum adi uretme ({adet} nokta)")

# ---------------------------------------------------------------- 2: core.h
R("core.h",
  "\tuint32_t options() const { return options_; }\n"
  "\tstd::string vm_section_name() const { return vm_section_name_; }\n"
  "\tstd::string watermark_name() const { return watermark_name_; }\n",
  "\tuint32_t options() const { return options_; }\n"
  "\tstd::string vm_section_name() const { return vm_section_name_; }\n"
  "\t// 3.9.4 upgrade: project options (Project -> Options -> Virtual Machine)\n"
  "\tuint32_t vm_version() const { return vm_version_; }        // 0 = Default (advanced VM), 1 = VMProtect 2.X (classic VM)\n"
  "\tuint32_t vm_instances() const { return vm_instances_; }    // 0 = Default (10), 1..10\n"
  "\tuint32_t vm_complexity() const { return vm_complexity_; }  // 0..100 (%)\n"
  "\tuint32_t random_seed() const { return random_seed_; }      // 0 = new seed on every build\n"
  "\tvoid set_vm_version(uint32_t v) { vm_version_ = v; }\n"
  "\tvoid set_vm_instances(uint32_t v) { vm_instances_ = v; }\n"
  "\tvoid set_vm_complexity(uint32_t v) { vm_complexity_ = v; }\n"
  "\tvoid set_random_seed(uint32_t v) { random_seed_ = v; }\n"
  "\tstd::string watermark_name() const { return watermark_name_; }\n",
  1, "core.h: Core erişimcileri")

R("core.h",
  "\tuint32_t vm_options_;\n"
  "\tstd::string vm_section_name_;\n"
  "\tProjectTemplateManager *template_manager_;\n",
  "\tuint32_t vm_options_;\n"
  "\tuint32_t vm_version_, vm_instances_, vm_complexity_, random_seed_;\n"
  "\tstd::map<uint64_t, uint8_t> function_complexity_;\n"
  "\tstd::string vm_section_name_;\n"
  "\tProjectTemplateManager *template_manager_;\n",
  1, "core.h: Core üyeleri")

R("core.h", "class Core : public IObject\n{\n", "#include <map>\n\nclass Core : public IObject\n{\n",
  1, "core.h: <map> include")

# ---------------------------------------------------------------- 2+3: core.cc
R("core.cc",
  "\tvm_options_ = 0;\n"
  "\tvm_section_name_ = default_template->vm_section_name();\n",
  "\tvm_options_ = 0;\n"
  "\t// 3.9.4 upgrade: project option defaults\n"
  "\tvm_version_ = 0;\n"
  "\tvm_instances_ = 0;\n"
  "\tvm_complexity_ = 0;\n"
  "\trandom_seed_ = 0;\n"
  "\tfunction_complexity_.clear();\n"
  "\tvm_section_name_ = default_template->vm_section_name();\n",
  1, "core.cc: Open varsayılanları")

R("core.cc",
  "\t\t\tprotection_node->QueryStringAttribute(\"VMCodeSectionName\", &vm_section_name_);\n"
  "\t\t\tprotection_node->QueryStringAttribute(\"OutputFileName\", &output_file_name_);\n",
  "\t\t\tprotection_node->QueryStringAttribute(\"VMCodeSectionName\", &vm_section_name_);\n"
  "\t\t\t// 3.9.4 upgrade: Project -> Options -> Virtual Machine\n"
  "\t\t\tu = vm_version_;\n"
  "\t\t\tprotection_node->QueryUnsignedAttribute(\"VMVersion\", &u);\n"
  "\t\t\tvm_version_ = (u > 1) ? 0 : u;\n"
  "\t\t\tu = vm_instances_;\n"
  "\t\t\tprotection_node->QueryUnsignedAttribute(\"VMInstances\", &u);\n"
  "\t\t\tvm_instances_ = (u > 10) ? 10 : u;\n"
  "\t\t\tu = vm_complexity_;\n"
  "\t\t\tprotection_node->QueryUnsignedAttribute(\"VMComplexity\", &u);\n"
  "\t\t\tvm_complexity_ = (u > 100) ? 100 : u;\n"
  "\t\t\tu = random_seed_;\n"
  "\t\t\tprotection_node->QueryUnsignedAttribute(\"RandomSeed\", &u);\n"
  "\t\t\trandom_seed_ = u;\n"
  "\t\t\tprotection_node->QueryStringAttribute(\"OutputFileName\", &output_file_name_);\n",
  1, "core.cc: XML okuma (VMVersion/VMInstances/VMComplexity/RandomSeed)")

R("core.cc",
  "\t\t\t\t\t\t\tif (function) {\n"
  "\t\t\t\t\t\t\t\tu = 0;\n"
  "\t\t\t\t\t\t\t\tprocedure_node->QueryUnsignedAttribute(\"BreakOffset\", &u);\n",
  "\t\t\t\t\t\t\tif (function) {\n"
  "\t\t\t\t\t\t\t\t// 3.9.4 upgrade: per-function complexity (Functions for protection -> Protection -> Complexity)\n"
  "\t\t\t\t\t\t\t\tu = VMP_COMPLEXITY_DEFAULT;\n"
  "\t\t\t\t\t\t\t\tprocedure_node->QueryUnsignedAttribute(\"Complexity\", &u);\n"
  "\t\t\t\t\t\t\t\tfunction_complexity_[address] = (uint8_t)((u > 100) ? VMP_COMPLEXITY_DEFAULT : u);\n"
  "\t\t\t\t\t\t\t\tu = 0;\n"
  "\t\t\t\t\t\t\t\tprocedure_node->QueryUnsignedAttribute(\"BreakOffset\", &u);\n",
  1, "core.cc: XML okuma (Procedure Complexity)")

R("core.cc",
  "\t\t\t\tprocedure_node->SetAttribute(\"Options\", function->compilation_options());\n",
  "\t\t\t\tprocedure_node->SetAttribute(\"Options\", function->compilation_options());\n"
  "\n"
  "\t\t\t\t{\n"
  "\t\t\t\t\t// 3.9.4 upgrade: store per-function complexity when it differs from the project value\n"
  "\t\t\t\t\tstd::map<uint64_t, uint8_t>::const_iterator fc = function_complexity_.find(function->address());\n"
  "\t\t\t\t\tif (fc != function_complexity_.end() && fc->second != VMP_COMPLEXITY_DEFAULT)\n"
  "\t\t\t\t\t\tprocedure_node->SetAttribute(\"Complexity\", (int)fc->second);\n"
  "\t\t\t\t}\n",
  1, "core.cc: XML yazma (Procedure Complexity)")

R("core.cc",
  "\t\t? 1 : 10;\n"
  "\tfor (size_t i = 0; i < _countof(options.messages); i++) {\n",
  "\t\t? 1 : 10;\n"
  "\t// 3.9.4 upgrade: VM version / instances / complexity (values are passed to the engine)\n"
  "\tif (vm_version_ == 1)\n"
  "\t\toptions.vm_flags |= 1; // \"VMProtect 2.X\": classic virtual machine\n"
  "\tif (vm_instances_ >= 1 && vm_instances_ <= 10)\n"
  "\t\toptions.vm_count = vm_instances_;\n"
  "\toptions.vm_complexity = (uint8_t)vm_complexity_;\n"
  "\toptions.function_complexity = &function_complexity_;\n"
  "\tfor (size_t i = 0; i < _countof(options.messages); i++) {\n",
  1, "core.cc: Compile seçenek aktarımı")

R("core.cc",
  "\trand_seed = 0;\n",
  "\t// 3.9.4 upgrade: RandomSeed project option (0 = new seed on every build)\n"
  "\tif (random_seed_ == 0)\n"
  "\t\trand_seed = os::GetTickCount();\n"
  "\telse\n"
  "\t\trand_seed = random_seed_;\n",
  1, "core.cc: Compile rastgele tohum")

R("core.cc",
  "\t// create random section name\n"
  "\tvm_section_name_ = \".\";\n"
  "\tsize_t i;\n"
  "\tstatic const char alphanum[] =\n"
  "\t\t\"0123456789\"\n"
  "\t\t\"ABCDEFGHIJKLMNOPQRSTUVWXYZ\"\n"
  "\t\t\"abcdefghijklmnopqrstuvwxyz\";\n"
  "\tsrand(os::GetTickCount());\n"
  "\tfor (i = 0; i < 3; i++) {\n"
  "\t\tvm_section_name_ += alphanum[rand() % (sizeof(alphanum) - 1)];\n"
  "\t}\n",
  "\t// 3.9.4 upgrade: default template uses a name mask instead of one fixed random name\n"
  "\tvm_section_name_ = \".???\";\n"
  "\tsize_t i;\n",
  1, "core.cc: varsayılan şablon bölüm adı maskesi")

# ---------------------------------------------------------------- 4: intel.cc
R("intel.cc",
  "void IntelFunction::Mutate(const CompileContext &ctx, bool for_virtualization, int /*index*/)\n"
  "{\n",
  "// 3.9.4 upgrade: effective complexity (%) of a function: own value, else project value\n"
  "static uint32_t VMP_Complexity(const CompileContext &ctx, uint64_t address)\n"
  "{\n"
  "\tif (ctx.options.function_complexity) {\n"
  "\t\tstd::map<uint64_t, uint8_t>::const_iterator it = ctx.options.function_complexity->find(address);\n"
  "\t\tif (it != ctx.options.function_complexity->end() && it->second != VMP_COMPLEXITY_DEFAULT)\n"
  "\t\t\treturn it->second;\n"
  "\t}\n"
  "\treturn ctx.options.vm_complexity;\n"
  "}\n"
  "\n"
  "void IntelFunction::Mutate(const CompileContext &ctx, bool for_virtualization, int /*index*/)\n"
  "{\n",
  1, "intel.cc: VMP_Complexity yardımcısı")

R("intel.cc",
  "\t\t\tsize_t c = rand() % 4;\n"
  "\t\t\tfor (size_t m = 0; m < c && !garbage_command_list.empty(); m++) {\n",
  "\t\t\t// 3.9.4 upgrade: complexity raises the upper bound of garbage commands per insertion point\n"
  "\t\t\tsize_t c = rand() % (4 + VMP_Complexity(ctx, address()) * 12 / 100);\n"
  "\t\t\tfor (size_t m = 0; m < c && !garbage_command_list.empty(); m++) {\n",
  1, "intel.cc: Mutate çöp komut sınırı")

R("intel.cc",
  "\tcase ctVirtualization: //xu ni hua\n"
  "\t\tCompileToVM(ctx);\n"
  "\t\tbreak;\n",
  "\tcase ctVirtualization: //xu ni hua\n"
  "\t\t// 3.9.4 upgrade: complexity > 0 mutates the code before virtualization (more bytecode)\n"
  "\t\tif (VMP_Complexity(ctx, address()) > 0)\n"
  "\t\t\tMutate(ctx, true);\n"
  "\t\tCompileToVM(ctx);\n"
  "\t\tbreak;\n",
  1, "intel.cc: Sanallaştırma + complexity")

# ---------------------------------------------------------------- diff + kayıt
if KONTROL:
    print(f"KONTROL: {len(P.KAYIT)}/{len(P.KAYIT) + sum(1 for _ in [])} yama noktası eşleşti (yazılmadı)")
    sys.exit(0)

farkli = []
for kok, _, fs in os.walk(PATCHED):
    for f in fs:
        pp = os.path.join(kok, f)
        rel = os.path.relpath(pp, PATCHED)
        pb = os.path.join(BASE, rel)
        if not os.path.exists(pb) or not filecmp.cmp(pb, pp, shallow=False):
            farkli.append(rel)
farkli.sort()
diff = ""
for rel in farkli:
    r = subprocess.run(["diff", "-u", "--label", f"a/universalObfusPublicSrc/{rel}",
                        "--label", f"b/universalObfusPublicSrc/{rel}",
                        os.path.join(BASE, rel), os.path.join(PATCHED, rel)], capture_output=True)
    diff += r.stdout.decode("utf-8", "surrogateescape")
dp = f"{OUT}/10_yukseltme_3.9.4.diff"
with open(dp, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
    f.write(diff)
with open(f"{OUT}/yama_kayitlari.json", "w", encoding="utf-8") as f:
    json.dump([{"dosya": d, "etiket": e, "adet": n} for d, e, n in P.KAYIT], f, ensure_ascii=False, indent=1)
print(f"yama noktası: {len(P.KAYIT)}  değişen dosya: {farkli}")
print(f"yazıldı: {dp} ({os.path.getsize(dp)} bayt)  +/− satır: "
      f"{sum(1 for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++'))}/"
      f"{sum(1 for l in diff.splitlines() if l.startswith('-') and not l.startswith('---'))}")
