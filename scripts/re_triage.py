#!/usr/bin/env python3
"""
re_triage.py — PE/ELF/Mach-O triage wrapper.

Deterministic static analyzer — reads the binary and produces structured
triage JSON for the agent to reason over.

Usage:
    python scripts/re_triage.py --file <target> --all
    python scripts/re_triage.py --file <target> --imports --strings --entropy
    python scripts/re_triage.py --file <target> --out triage.json

Output (JSON):
{
    "file": "path",
    "size": N,
    "hashes": {"md5":..., "sha1":..., "sha256":..., "ssdeep":...},
    "type": "ELF 64-bit LSB executable, x86-64, dynamically linked",
    "format": "ELF" | "PE" | "Mach-O" | "unknown",
    "arch": "x86_64" | "x86" | "ARM" | "ARM64" | "MIPS" | ...,
    "endianness": "little" | "big",
    "linking": "static" | "dynamic",
    "security_features": {"nx": true, "pie": true, "relro": "full"|"partial"|"none", "canary": true, "fortify": true},
    "sections": [{"name":..., "vaddr":..., "size":..., "entropy":...}],
    "imports": ["func1", "func2", ...],
    "exports": [...],
    "entry_point": "0x...",
    "suspicious_imports": {"injection": [...], "persistence": [...], "anti_analysis": [...], "network": [...], ...},
    "suspicious_strings": {"network": [...], "paths": [...], "cred_hints": [...], "vm_check": [...]},
    "packer_hints": ["UPX"] | [],
    "compiler_hints": ["GCC 11.4.0"] | ["Go"] | ["Rust"] | [],
    "summary": "One-line triage verdict"
}
"""

import argparse
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


# ---------- Hashes ----------

def compute_hashes(path: Path) -> dict:
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha256 = hashlib.sha256()
    data = path.read_bytes()
    h_md5.update(data); h_sha1.update(data); h_sha256.update(data)
    out = {
        "md5": h_md5.hexdigest(),
        "sha1": h_sha1.hexdigest(),
        "sha256": h_sha256.hexdigest(),
        "size": len(data),
    }
    try:
        import ssdeep  # pyssdeep
        out["ssdeep"] = ssdeep.hash(data)
    except ImportError:
        out["ssdeep"] = None
    return out


# ---------- Entropy ----------

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freqs = [0] * 256
    for b in data:
        freqs[b] += 1
    n = len(data)
    h = 0.0
    for f in freqs:
        if f:
            p = f / n
            h -= p * math.log2(p)
    return h


def section_entropy(path: Path, fmt: str) -> list:
    """Extract per-section entropy. Falls back gracefully if format-specific libs missing."""
    sections = []
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            with path.open("rb") as f:
                elf = ELFFile(f)
                for sec in elf.iter_sections():
                    data = sec.data()
                    if not data:
                        continue
                    sections.append({
                        "name": sec.name,
                        "vaddr": hex(sec["sh_addr"]) if sec["sh_addr"] else "0x0",
                        "size": sec["sh_size"],
                        "entropy": round(shannon_entropy(data), 3),
                    })
        except ImportError:
            # Fallback: parse with readelf if available
            try:
                out = subprocess.check_output(["readelf", "-S", "-W", str(path)], text=True)
                for line in out.splitlines():
                    m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\d+)", line)
                    if m and m.group(2) != "NOBITS":
                        offset = int(m.group(5), 16)
                        size = int(m.group(6))
                        with open(path, "rb") as f:
                            f.seek(offset)
                            data = f.read(size)
                        sections.append({
                            "name": m.group(1),
                            "vaddr": "0x" + m.group(3),
                            "size": size,
                            "entropy": round(shannon_entropy(data), 3),
                        })
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path))
            for sec in pe.sections:
                sections.append({
                    "name": sec.Name.rstrip(b"\x00").decode(errors="replace"),
                    "vaddr": hex(sec.VirtualAddress),
                    "size": sec.SizeOfRawData,
                    "entropy": round(shannon_entropy(sec.get_data()), 3),
                })
        except ImportError:
            pass
    elif fmt == "Mach-O":
        # Best-effort: parse with otool if available
        try:
            out = subprocess.check_output(["otool", "-l", str(path)], text=True)
            # Parse sections — otool output varies; simple best-effort
            current_sect = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("sectname"):
                    current_sect = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ""
                elif line.startswith("size") and current_sect:
                    size = int(line.split()[1])
                    sections.append({"name": current_sect, "vaddr": "0x0", "size": size, "entropy": None})
                    current_sect = None
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return sections


# ---------- File type detection ----------

def detect_format(path: Path) -> tuple:
    """Returns (format, type_string). format in {ELF, PE, Mach-O, Java, unknown}."""
    data = path.read_bytes()[:64]
    if len(data) < 4:
        return "unknown", "file too small"
    magic4 = data[:4]
    if magic4 == b"\x7fELF":
        return "ELF", "ELF"
    if magic4[:2] == b"MZ":
        return "PE", "PE (Windows executable)"
    if magic4 in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                  b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"):
        return "Mach-O", "Mach-O"
    if magic4 == b"\xca\xfe\xba\xbe":
        return "Java", "Java class / fat Mach-O"
    # try `file` command for richer string
    try:
        out = subprocess.check_output(["file", "-b", str(path)], text=True).strip()
        return "unknown", out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"


def detect_arch(path: Path, fmt: str) -> str:
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            with path.open("rb") as f:
                elf = ELFFile(f)
                machine = elf.header["e_machine"]
                ei_class = elf.elfclass
                if machine == "EM_X86_64": return "x86_64"
                if machine == "EM_386": return "x86"
                if machine == "EM_AARCH64": return "ARM64"
                if machine == "EM_ARM": return "ARM"
                if machine == "EM_MIPS": return "MIPS"
                if machine == "EM_RISCV": return "RISC-V"
                return machine
        except ImportError:
            pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path), fast_load=True)
            m = pe.FILE_HEADER.Machine
            if m == 0x8664: return "x86_64"
            if m == 0x14c:  return "x86"
            if m == 0xaa64: return "ARM64"
            if m == 0x1c0:  return "ARM"
            return hex(m)
        except ImportError:
            pass
    elif fmt == "Mach-O":
        try:
            out = subprocess.check_output(["file", "-b", str(path)], text=True).strip()
            return out
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"
    return "unknown"


# ---------- Security features ----------

def detect_security_features(path: Path, fmt: str) -> dict:
    feats = {"nx": None, "pie": None, "relro": None, "canary": None, "fortify": None}
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            from elftools.elf.dynamic import DynamicSection
            from elftools.elf.sections import SymbolTableSection
            with path.open("rb") as f:
                elf = ELFFile(f)
                # NX: check GNU_STACK
                for seg in elf.iter_segments():
                    if seg.header.p_type == "PT_GNU_STACK":
                        feats["nx"] = not (seg.header.p_flags & 0x1)  # PF_X bit
                # PIE
                feats["pie"] = elf.header.e_type == "ET_DYN"
                # RELRO
                relro_seg = False
                for seg in elf.iter_segments():
                    if seg.header.p_type == "PT_GNU_RELRO":
                        relro_seg = True
                        break
                dynsec = None
                for sec in elf.iter_sections():
                    if isinstance(sec, DynamicSection):
                        dynsec = sec
                        break
                bind_now = False
                if dynsec:
                    for tag in dynsec.iter_tags():
                        if tag.entry.d_tag in ("DT_BIND_NOW", "DT_FLAGS"):
                            if tag.entry.d_tag == "DT_BIND_NOW":
                                bind_now = True
                            elif tag.entry.d_tag == "DT_FLAGS" and (tag.entry.d_val & 0x8):  # DF_BIND_NOW
                                bind_now = True
                if relro_seg and bind_now:
                    feats["relro"] = "full"
                elif relro_seg:
                    feats["relro"] = "partial"
                else:
                    feats["relro"] = "none"
                # Canary + Fortify — check dynamic symbol table for __stack_chk_fail / *_chk
                for sec in elf.iter_sections():
                    if isinstance(sec, SymbolTableSection):
                        for sym in sec.iter_symbols():
                            name = sym.name if isinstance(sym.name, str) else (sym.name.decode(errors="replace") if sym.name else "")
                            if name == "__stack_chk_fail":
                                feats["canary"] = True
                            elif name.endswith("_chk") and name.startswith("__"):
                                feats["fortify"] = True
        except ImportError:
            pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories()
            dc = pe.OPTIONAL_HEADER.DllCharacteristics
            feats["nx"] = bool(dc & 0x100)        # NX_COMPAT
            feats["pie"] = bool(dc & 0x40)         # DYNAMIC_BASE
            feats["canary"] = False
            feats["relro"] = "n/a"
            feats["fortify"] = False
            # CFG
            feats["cfg"] = bool(dc & 0x4000)
        except ImportError:
            pass
    return feats


# ---------- Imports & suspicious ----------

SUSPICIOUS_IMPORT_CATEGORIES = {
    "injection":     ["CreateRemoteThread", "WriteProcessMemory", "VirtualAllocEx",
                       "NtMapViewOfSection", "QueueUserAPC", "RtlCreateUserThread",
                       "SetThreadContext", "VirtualProtectEx", "ReadProcessMemory"],
    "persistence":   ["RegSetValueEx", "RegSetValueExA", "RegSetValueExW",
                       "CreateService", "WinExec", "ShellExecute", "ShellExecuteA",
                       "ShellExecuteW", "ITaskScheduler", "SchRpcRegisterTask"],
    "anti_analysis": ["IsDebuggerPresent", "CheckRemoteDebuggerPresent",
                       "NtQueryInformationProcess", "GetTickCount", "QueryPerformanceCounter",
                       "GetSystemInfo", "rdtsc"],
    "network":       ["WSAStartup", "socket", "connect", "send", "recv",
                       "InternetOpenUrl", "InternetOpenUrlA", "InternetOpenUrlW",
                       "HttpSendRequest", "HttpSendRequestA", "HttpSendRequestW",
                       "WinHttpOpen", "WinHttpSendRequest",
                       "URLDownloadToFile", "URLDownloadToFileA", "URLDownloadToFileW"],
    "credential":    ["LsaOpenPolicy", "SamConnect", "SamOpenDatabase",
                       "LogonUser", "LogonUserA", "LogonUserW",
                       "RegOpenCurrentUser", "CredEnumerate", "CryptUnprotectData"],
    "keylogging":    ["SetWindowsHookEx", "SetWindowsHookExA", "SetWindowsHookExW",
                       "GetAsyncKeyState", "GetKeyState", "GetForegroundWindow"],
    "evasion":       ["VirtualProtect", "NtProtectVirtualMemory",
                       "Wow64DisableWow64FsRedirection", "NtSetInformationThread"],
    "crypto":        ["CryptEncrypt", "CryptDecrypt", "CryptHashData",
                       "BCryptEncrypt", "BCryptDecrypt", "EVP_EncryptInit_ex"],
}


def categorize_suspicious_imports(imports: list) -> dict:
    out = {}
    for cat, names in SUSPICIOUS_IMPORT_CATEGORIES.items():
        hits = [n for n in imports if any(p.lower() in (n.lower() if n else "") for p in names)]
        if hits:
            out[cat] = hits
    return out


def extract_pe_imports(path: Path) -> list:
    try:
        import pefile
        pe = pefile.PE(str(path))
        imports = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                for imp in entry.imports:
                    if imp.name:
                        imports.append(imp.name.decode(errors="replace"))
                    elif imp.ordinal is not None:
                        imports.append(f"#{imp.ordinal}")
        return imports
    except ImportError:
        return []


def extract_elf_imports(path: Path) -> list:
    """ELF doesn't have 'imports' in the PE sense — uses dynamic symbols / NEEDED libs."""
    try:
        from elftools.elf.elffile import ELFFile
        from elftools.elf.dynamic import DynamicSection
        out = []
        with path.open("rb") as f:
            elf = ELFFile(f)
            for sec in elf.iter_sections():
                if isinstance(sec, DynamicSection):
                    for tag in sec.iter_tags():
                        if tag.entry.d_tag == "DT_NEEDED":
                            val = tag.needed
                            if isinstance(val, bytes):
                                val = val.decode(errors="replace")
                            out.append(val)
        return out
    except ImportError:
        # Fallback: readelf -d
        try:
            out = subprocess.check_output(["readelf", "-d", str(path)], text=True)
            libs = []
            for line in out.splitlines():
                m = re.search(r"NEEDED\s+Shared library:\s+\[(.+?)\]", line)
                if m:
                    libs.append(m.group(1))
            return libs
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []


# ---------- Strings ----------

SUSPICIOUS_STRING_PATTERNS = {
    "network":   re.compile(r"https?://[a-zA-Z0-9./?=_-]+|^[0-9]{1,3}(\.[0-9]{1,3}){3}(:[0-9]+)?$", re.I),
    "win_paths": re.compile(r"^[A-Za-z]:\\"),
    "nix_paths": re.compile(r"^/(etc|usr|var|tmp|root|home|proc|sys)/"),
    "cred_hints":re.compile(r"(password|passwd|secret|api[_-]?key|token|bearer)", re.I),
    "vm_check":  re.compile(r"(vmware|virtualbox|vbox|qemu|xen|hyper[\-]?v|sandboxie)", re.I),
    "reg_keys":  re.compile(r"(HKEY_|HKLM\\|HKCU\\|Software\\\\Microsoft)", re.I),
    "base64":    re.compile(r"^[A-Za-z0-9+/]{20,}={0,2}$"),
    "hex_blob":  re.compile(r"^[A-Fa-f0-9]{32,}$"),
}


def extract_strings(path: Path, min_len: int = 4, max_strings: int = 50000) -> list:
    """Extract ASCII strings — equivalent to `strings -a -n 4`."""
    strings = []
    current = bytearray()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            for b in chunk:
                if 32 <= b < 127 or b == 9:  # printable ASCII + tab
                    current.append(b)
                else:
                    if len(current) >= min_len:
                        s = current.decode("ascii", errors="replace")
                        if len(strings) < max_strings:
                            strings.append(s)
                        else:
                            return strings
                    current = bytearray()
    if len(current) >= min_len:
        strings.append(current.decode("ascii", errors="replace"))
    return strings


def categorize_strings(strings: list) -> dict:
    out = {k: [] for k in SUSPICIOUS_STRING_PATTERNS}
    for s in strings:
        for cat, pat in SUSPICIOUS_STRING_PATTERNS.items():
            if pat.search(s):
                out[cat].append(s)
                break
    # Dedupe and limit
    for k in out:
        out[k] = sorted(set(out[k]))[:100]
    return out


# ---------- Packer & compiler detection ----------

PACKER_SIGNATURES = {
    "UPX":          [b"UPX!", b"UPX0", b"UPX1"],
    "Themida":      [b".themida", b"Themida"],
    "VMProtect":    [b".vmp0", b".vmp1", b"VMProtect"],
    "Enigma":       [b".enigma1", b".enigma2", b"Enigma"],
    "MPRESS":       [b"MPRESS1", b"MPRESS2"],
    "ASPack":       [b".aspack", b"ASPack"],
    "MPack":        [b"MPack"],
    "Petite":       [b".petite", b"Petite"],
}

COMPILER_SIGNATURES = {
    "GCC":         b"GCC: (GNU)",
    "Clang":       b"clang version",
    "MSVC":        b"Microsoft (R)",
    "Go":          b"go:build",
    "Rust":        b"rustc/",
    "TinyCC":      b"TCC ",
    "Intel":       b"Intel(R)",
}


def detect_packers(path: Path, fmt: str) -> list:
    hits = []
    data = path.read_bytes()
    # .comment section for ELF
    section_data = b""
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            with path.open("rb") as f:
                elf = ELFFile(f)
                for sec in elf.iter_sections():
                    if sec.name in (".comment",):
                        section_data += sec.data()
        except ImportError:
            pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path))
            for sec in pe.sections:
                section_data += sec.get_data()
        except ImportError:
            pass

    search_data = data[:1 << 20]  # First 1MB
    if section_data:
        search_data = section_data + search_data

    for packer, sigs in PACKER_SIGNATURES.items():
        for sig in sigs:
            if sig in search_data:
                hits.append(packer)
                break

    return hits


def detect_compilers(path: Path, fmt: str) -> list:
    hits = []
    section_data = b""
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            with path.open("rb") as f:
                elf = ELFFile(f)
                for sec in elf.iter_sections():
                    if sec.name in (".comment",):
                        section_data += sec.data()
        except ImportError:
            pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path))
            for sec in pe.sections:
                section_data += sec.get_data() if hasattr(sec, "get_data") else b""
        except ImportError:
            pass

    for compiler, sig in COMPILER_SIGNATURES.items():
        if sig in section_data:
            hits.append(compiler)

    # Fallback: if .comment is stripped (common on distro binaries), infer from dynsym
    if not hits:
        try:
            if fmt == "ELF":
                from elftools.elf.elffile import ELFFile
                from elftools.elf.dynamic import DynamicSection
                with path.open("rb") as f:
                    elf = ELFFile(f)
                    dynsyms = set()
                    for sec in elf.iter_sections():
                        if isinstance(sec, DynamicSection):
                            for tag in sec.iter_tags():
                                if tag.entry.d_tag == "DT_NEEDED":
                                    val = tag.needed
                                    if isinstance(val, bytes):
                                        val = val.decode(errors="replace")
                                    dynsyms.add(val)
                    if "libc.so.6" in dynsyms:
                        hits.append("glibc-linked")
                    if any("libstdc++" in s for s in dynsyms):
                        hits.append("libstdc++")
            elif fmt == "PE":
                import pefile
                pe = pefile.PE(str(path))
                if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                    imported_dlls = set()
                    for entry in pe.DIRECTORY_ENTRY_IMPORT:
                        if entry.dll:
                            imported_dlls.add(entry.dll.decode(errors="replace").lower())
                    if "msvcr140.dll" in imported_dlls or "vcruntime140.dll" in imported_dlls:
                        hits.append("MSVC-redist")
                    if "mscoree.dll" in imported_dlls:
                        hits.append(".NET")
        except (ImportError, Exception):
            pass

    return hits


# ---------- Entry point ----------

def detect_entry_point(path: Path, fmt: str) -> str:
    if fmt == "ELF":
        try:
            from elftools.elf.elffile import ELFFile
            with path.open("rb") as f:
                elf = ELFFile(f)
                return hex(elf.header.e_entry)
        except ImportError:
            pass
    elif fmt == "PE":
        try:
            import pefile
            pe = pefile.PE(str(path), fast_load=True)
            return hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        except ImportError:
            pass
    return "unknown"


# ---------- Main ----------

def triage(path: Path, args) -> dict:
    result = {}
    fmt, type_str = detect_format(path)
    result["file"] = str(path)
    result["format"] = fmt
    result["type"] = type_str
    result["size"] = path.stat().st_size

    if args.all or args.hashes:
        result["hashes"] = compute_hashes(path)

    if args.all or args.arch:
        result["arch"] = detect_arch(path, fmt)
        result["endianness"] = "little" if fmt == "PE" or (fmt == "ELF" and result.get("arch")) else "unknown"

    if args.all or args.security:
        result["security_features"] = detect_security_features(path, fmt)

    if args.all or args.entropy:
        result["sections"] = section_entropy(path, fmt)

    if args.all or args.imports:
        if fmt == "PE":
            imps = extract_pe_imports(path)
        elif fmt == "ELF":
            imps = extract_elf_imports(path)
        else:
            imps = []
        result["imports"] = imps
        result["suspicious_imports"] = categorize_suspicious_imports(imps)

    if args.all or args.strings:
        strings = extract_strings(path)
        result["string_count"] = len(strings)
        result["suspicious_strings"] = categorize_strings(strings)

    if args.all or args.packers:
        result["packer_hints"] = detect_packers(path, fmt)

    if args.all or args.packers:
        result["compiler_hints"] = detect_compilers(path, fmt)

    if args.all or args.entry:
        result["entry_point"] = detect_entry_point(path, fmt)

    # Build summary — verbose to surface fast verdict hint
    summary_parts = [fmt]
    if result.get("arch"):
        summary_parts.append(result["arch"])
    if result.get("packer_hints"):
        summary_parts.append(f"packed[{','.join(result['packer_hints'])}]")
    elif result.get("sections"):
        # Surface high-entropy sections if no packer matched but entropy is suspicious
        high_entropy = [s["name"] for s in result["sections"]
                        if isinstance(s.get("entropy"), (int, float)) and s.get("entropy", 0) >= 7.5]
        if high_entropy:
            summary_parts.append(f"high_entropy_sections[{','.join(high_entropy[:3])}]")
        else:
            summary_parts.append("no_packed_sections")
    if result.get("compiler_hints"):
        summary_parts.append(f"compiler[{','.join(result['compiler_hints'])}]")
    if result.get("suspicious_imports"):
        cats = list(result["suspicious_imports"].keys())
        summary_parts.append(f"suspicious_imports[{','.join(cats)}]")
    else:
        summary_parts.append("0_suspicious_import_cats")
    if result.get("suspicious_strings", {}).get("vm_check"):
        summary_parts.append("vm_check_strings")
    result["summary"] = " | ".join(summary_parts)

    return result


def main():
    p = argparse.ArgumentParser(description="Binary triage wrapper — static analysis only")
    p.add_argument("--file", required=True, help="Path to target binary")
    p.add_argument("--all", action="store_true", help="Run all checks")
    p.add_argument("--hashes", action="store_true")
    p.add_argument("--arch", action="store_true")
    p.add_argument("--security", action="store_true")
    p.add_argument("--imports", action="store_true")
    p.add_argument("--strings", action="store_true")
    p.add_argument("--entropy", action="store_true")
    p.add_argument("--packers", action="store_true")
    p.add_argument("--entry", action="store_true")
    p.add_argument("--out", help="Write JSON to file (default: stdout)")
    args = p.parse_args()

    if not any([args.all, args.hashes, args.arch, args.security, args.imports,
                args.strings, args.entropy, args.packers, args.entry]):
        args.all = True  # Default to all if nothing specified

    path = Path(args.file)
    if not path.exists():
        print(json.dumps({"error": f"File not found: {args.file}"}))
        sys.exit(1)

    try:
        result = triage(path, args)
    except Exception as e:
        result = {"error": str(e), "file": args.file}

    out = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(out)
        print(f"Triage written to {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
