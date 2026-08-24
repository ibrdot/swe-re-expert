#!/usr/bin/env python3
"""
re_disasm.py — Capstone-based function-level disasm summary.

Deterministic static disassembler. Uses capstone for disasm;
pyelftools/pefile for ELF/PE parsing to find functions and entry points.

Usage:
    python scripts/re_disasm.py --file <target>                          # Disasm entry function
    python scripts/re_disasm.py --file <target> --entry                  # Disasm entry point only
    python scripts/re_disasm.py --file <target> --functions              # List functions
    python scripts/re_disasm.py --file <target> --disasm 0x401234        # Disasm specific addr
    python scripts/re_disasm.py --file <target> --function main          # Disasm named function
    python scripts/re_disasm.py --file <target> --all                    # Full per-function summary

Output (JSON):
{
    "file": "...",
    "arch": "x86_64",
    "entry_point": "0x...",
    "functions": [
        {"name": "main", "start": "0x401234", "end": "0x401290", "size": 92,
         "basic_blocks": 4, "calls": ["printf@plt", "exit@plt"],
         "jumps": [{"from": "0x401240", "to": "0x401260", "type": "jcc"}],
         "suspicious_patterns": ["xor_loop", "crypto_constant"]}
    ]
}
"""

import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

# Optional deps — fall back gracefully
try:
    from capstone import Cs, CS_ARCH_X86, CS_ARCH_ARM64, CS_ARCH_ARM, CS_ARCH_MIPS, CS_MODE_64, CS_MODE_32, CS_MODE_ARM, CS_MODE_THUMB, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN, CS_MODE_BIG_ENDIAN
    HAS_CAPSTONE = True
except ImportError:
    HAS_CAPSTONE = False

try:
    from elftools.elf.elffile import ELFFile
    from elftools.elf.sections import SymbolTableSection
    HAS_ELF = True
except ImportError:
    HAS_ELF = False

try:
    import pefile
    HAS_PE = True
except ImportError:
    HAS_PE = False


# Suspicious instruction patterns to flag
SUSPICIOUS_PATTERNS = {
    # XOR decryption loops
    "xor_loop": [
        # x86: xor [mem], reg; add reg, 1; cmp reg, len; jl loop
        (["xor", "add", "cmp", "jl"], "Possible XOR string decryption"),
    ],
    # Inline crypto constants (AES S-box first byte)
    "aes_sbox": (b"\x63\x7c\x77\x7b\xf2\x6b\x6f\xc5", "AES S-box detected"),
    "aes_inv_sbox": (b"\x52\x09\x6a\xd5\x30\x36\xa5\x38", "AES inverse S-box"),
    "sha256_k": (b"\x42\x8a\x2f\x98\x71\x37\x44\x91", "SHA-256 round constants"),
    # Stack strings
    "stack_string": (["mov byte ptr [rbp", "0x"], "Stack string construction"),
    # Anti-debug
    "anti_debug": (["IsDebuggerPresent", "CheckRemoteDebuggerPresent",
                     "NtQueryInformationProcess"], "Anti-debug API"),
    # Direct syscall
    "direct_syscall": (["syscall"], "Direct syscall"),
    # API hashing
    "api_hashing": (["ror", "cmp", "0x"], "Possible API hash resolution"),
}


def detect_format(path: Path):
    data = path.read_bytes()[:8]
    if data[:4] == b"\x7fELF": return "ELF"
    if data[:2] == b"MZ":     return "PE"
    if data[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                    b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"):
        return "Mach-O"
    return "unknown"


def get_arch_mode(fmt, path):
    """Return (arch, mode, bits) for capstone."""
    if fmt == "ELF" and HAS_ELF:
        with path.open("rb") as f:
            elf = ELFFile(f)
            m = elf.header.e_machine
            bits = elf.elfclass
            endian = elf.little_endian
            if m == "EM_X86_64":
                return CS_ARCH_X86, CS_MODE_64, 64
            if m == "EM_386":
                return CS_ARCH_X86, CS_MODE_32, 32
            if m == "EM_AARCH64":
                return CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN if endian else CS_MODE_BIG_ENDIAN, 64
            if m == "EM_ARM":
                return CS_ARCH_ARM, CS_MODE_ARM, 32
            if m == "EM_MIPS":
                return CS_ARCH_MIPS, CS_MODE_MIPS32 | (CS_MODE_LITTLE_ENDIAN if endian else CS_MODE_BIG_ENDIAN), 32
    if fmt == "PE" and HAS_PE:
        pe = pefile.PE(str(path), fast_load=True)
        m = pe.FILE_HEADER.Machine
        if m == 0x8664: return CS_ARCH_X86, CS_MODE_64, 64
        if m == 0x14c:  return CS_ARCH_X86, CS_MODE_32, 32
        if m == 0xaa64: return CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, 64
        if m == 0x1c0:  return CS_ARCH_ARM, CS_MODE_THUMB, 32
    return None, None, None


def find_elf_functions(path: Path):
    """Return list of (name, start_addr, end_or_size) for ELF."""
    if not HAS_ELF:
        return []
    out = []
    with path.open("rb") as f:
        elf = ELFFile(f)
        for sec in elf.iter_sections():
            if isinstance(sec, SymbolTableSection):
                for sym in sec.iter_symbols():
                    if sym["st_info"]["type"] == "STT_FUNC" and sym["st_size"] > 0 and sym["st_value"]:
                        out.append((sym.name, sym["st_value"], sym["st_size"]))
    return out


def find_pe_functions(path: Path):
    """Return list of (name, rva, size) for PE — from exports + .text prologue scan."""
    if not HAS_PE:
        return []
    pe = pefile.PE(str(path))
    out = []
    # 1. Exports
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if exp.name:
                out.append((exp.name.decode(errors="replace"), exp.address, 0))
    # 2. Prologue scan in .text
    text_sec = None
    for sec in pe.sections:
        if b".text" in sec.Name:
            text_sec = sec
            break
    if text_sec:
        data = text_sec.get_data()
        # Common x64 prologue: 48 89 5c 24 ?? (mov [rsp+N], rbx)  or  48 83 ec ?? (sub rsp, N)  or  40 53 (push rbx)
        for off in range(0, len(data) - 16):
            if data[off] == 0x48 and data[off+1] in (0x89, 0x83) and data[off+2] in (0x5c, 0xec, 0x6c, 0x7c):
                addr = text_sec.VirtualAddress + off
                out.append((f"sub_%08x" % addr, addr, 0))
            elif data[off:off+2] == b"\x40\x53":  # push rbx (REX prefix)
                addr = text_sec.VirtualAddress + off
                out.append((f"sub_%08x" % addr, addr, 0))
    # Dedup by start
    seen = set()
    deduped = []
    for name, addr, sz in out:
        if addr in seen:
            continue
        seen.add(addr)
        deduped.append((name, addr, sz))
    return deduped


def get_section_data_for_addr(path: Path, fmt, addr):
    """Return (data_bytes, file_offset_of_addr) for the given virtual addr."""
    if fmt == "ELF" and HAS_ELF:
        with path.open("rb") as f:
            elf = ELFFile(f)
            for seg in elf.iter_segments():
                if seg.header.p_type == "PT_LOAD":
                    start = seg.header.p_vaddr
                    end = start + seg.header.p_memsz
                    if start <= addr < end:
                        offset_in_seg = addr - start
                        # Cap at file size — some addrs are in .bss (zero-init)
                        file_size = seg.header.p_filesz
                        if offset_in_seg < file_size:
                            return seg.data()[offset_in_seg:offset_in_seg+0x10000], offset_in_seg
    if fmt == "PE" and HAS_PE:
        pe = pefile.PE(str(path), fast_load=True)
        for sec in pe.sections:
            start = sec.VirtualAddress
            end = start + sec.Misc_VirtualSize
            if start <= addr < end:
                offset_in_sec = addr - start
                data = sec.get_data()
                return data[offset_in_sec:offset_in_sec+0x10000], offset_in_sec
    return None, None


def disasm_function(path: Path, fmt: str, addr: int, size: int = 0, max_insns: int = 2000):
    """Disasm starting at addr for `size` bytes (or until ret/jmp if size=0)."""
    if not HAS_CAPSTONE:
        return None
    arch, mode, bits = get_arch_mode(fmt, path)
    if arch is None:
        return None

    md = Cs(arch, mode)
    md.detail = True

    data, _ = get_section_data_for_addr(path, fmt, addr)
    if not data:
        return None

    if size > 0:
        data = data[:size]

    instructions = []
    basic_blocks = 1
    calls = []
    jumps = []
    suspicious = []
    end_addr = addr

    for ins in md.disasm(data, addr):
        if len(instructions) >= max_insns:
            break
        instructions.append({
            "addr": hex(ins.address),
            "mnemonic": ins.mnemonic,
            "op_str": ins.op_str,
        })
        end_addr = ins.address + ins.size
        # Track calls
        if ins.mnemonic.startswith("call"):
            # Resolve target if symbolic
            target = None
            try:
                # Try to parse operand as immediate
                if ins.op_str and not ins.op_str.startswith("["):
                    target = ins.op_str
            except Exception:
                pass
            calls.append(target or ins.op_str)
        # Track jumps (control flow)
        if ins.mnemonic.startswith("j") or ins.mnemonic in ("jmp", "ret"):
            try:
                if ins.op_str and not ins.op_str.startswith("["):
                    target_addr = int(ins.op_str, 16) if ins.op_str.startswith("0x") else None
                    if target_addr:
                        jumps.append({
                            "from": hex(ins.address),
                            "to": hex(target_addr),
                            "type": "jcc" if ins.mnemonic != "jmp" and ins.mnemonic != "ret" else ("jmp" if ins.mnemonic == "jmp" else "ret"),
                        })
            except (ValueError, AttributeError):
                pass
        if ins.mnemonic == "ret":
            if size == 0:
                break
    return {
        "instructions": instructions,
        "instruction_count": len(instructions),
        "basic_blocks": basic_blocks,
        "calls": calls,
        "jumps": jumps,
        "suspicious_patterns": suspicious,
        "end": hex(end_addr),
    }


def detect_suspicious_in_func(path: Path, fmt: str, addr: int, size: int = 0):
    """Quick pattern scan in a function's bytes."""
    data, _ = get_section_data_for_addr(path, fmt, addr)
    if not data:
        return []
    if size > 0:
        data = data[:size]
    else:
        data = data[:0x1000]
    hits = []
    # AES S-box
    if b"\x63\x7c\x77\x7b\xf2\x6b\x6f\xc5" in data:
        hits.append("aes_sbox")
    if b"\x52\x09\x6a\xd5\x30\x36\xa5\x38" in data:
        hits.append("aes_inv_sbox")
    if b"\x42\x8a\x2f\x98\x71\x37\x44\x91" in data:
        hits.append("sha256_k")
    # XOR loop heuristic
    has_xor = b"\x30" in data or b"\x31" in data or b"\x32" in data or b"\x33" in data
    has_loop = b"\xfe\x01" in data or b"\x48\xff\xc0" in data or b"\x48\xff\xc1" in data
    if has_xor and has_loop:
        hits.append("xor_loop_suspicious")
    # syscall
    if b"\x0f\x05" in data and bits_get(path, fmt) == 64:  # syscall on x64
        hits.append("direct_syscall")
    # Stack strings (mov byte ptr [rbp-N], imm)
    if b"\xc6\x45" in data:
        hits.append("stack_string_construction")
    return hits


def bits_get(path: Path, fmt: str):
    if fmt == "ELF" and HAS_ELF:
        with path.open("rb") as f:
            return ELFFile(f).elfclass
    if fmt == "PE" and HAS_PE:
        pe = pefile.PE(str(path), fast_load=True)
        return 64 if pe.FILE_HEADER.Machine == 0x8664 else 32
    return 0


def main():
    p = argparse.ArgumentParser(description="Capstone-based disasm summary")
    p.add_argument("--file", required=True)
    p.add_argument("--entry", action="store_true", help="Disasm entry point")
    p.add_argument("--functions", action="store_true", help="List functions")
    p.add_argument("--disasm", help="Disasm at specific address (hex)")
    p.add_argument("--function", help="Disasm named function")
    p.add_argument("--all", action="store_true", help="Full per-function summary (expensive)")
    p.add_argument("--out", help="Write JSON to file")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(json.dumps({"error": f"File not found: {args.file}"}))
        sys.exit(1)

    fmt = detect_format(path)

    if not HAS_CAPSTONE:
        print(json.dumps({
            "error": "capstone not installed. Install with: pip install capstone",
            "fallback": "Use objdump -d -M intel <file> instead",
            "file": args.file,
        }, indent=2))
        sys.exit(1)

    result = {"file": str(path), "format": fmt}

    # Find functions
    if fmt == "ELF":
        funcs = find_elf_functions(path)
    elif fmt == "PE":
        funcs = find_pe_functions(path)
    else:
        funcs = []
    result["function_count"] = len(funcs)

    # Entry point
    entry = None
    if fmt == "ELF" and HAS_ELF:
        with path.open("rb") as f:
            entry = ELFFile(f).header.e_entry
    elif fmt == "PE" and HAS_PE:
        pe = pefile.PE(str(path), fast_load=True)
        entry = pe.OPTIONAL_HEADER.AddressOfEntryPoint
    result["entry_point"] = hex(entry) if entry else "unknown"

    if args.functions:
        result["functions"] = [{"name": n, "start": hex(a), "size": s} for n, a, s in funcs[:500]]
    elif args.entry:
        if entry:
            result["entry_disasm"] = disasm_function(path, fmt, entry, max_insns=200)
    elif args.disasm:
        addr = int(args.disasm, 16) if args.disasm.startswith("0x") else int(args.disasm, 16)
        result["disasm"] = disasm_function(path, fmt, addr, max_insns=500)
    elif args.function:
        name = args.function
        match = [(n, a, s) for n, a, s in funcs if n == name]
        if match:
            n, a, s = match[0]
            result["function_disasm"] = {
                "name": n,
                "start": hex(a),
                "size": s,
                **(disasm_function(path, fmt, a, s, max_insns=2000) or {}),
            }
        else:
            result["error"] = f"Function {name} not found"
    elif args.all:
        out_funcs = []
        for name, addr, size in funcs[:200]:
            d = disasm_function(path, fmt, addr, size, max_insns=500)
            if d:
                out_funcs.append({
                    "name": name,
                    "start": hex(addr),
                    "end": d.get("end", hex(addr)),
                    "size": size,
                    "instruction_count": d.get("instruction_count", 0),
                    "basic_blocks": d.get("basic_blocks", 0),
                    "calls": d.get("calls", [])[:20],
                    "jump_count": len(d.get("jumps", [])),
                    "suspicious_patterns": detect_suspicious_in_func(path, fmt, addr, size),
                })
        result["functions_summary"] = out_funcs
    else:
        # Default: print entry point disasm
        if entry:
            result["entry_disasm"] = disasm_function(path, fmt, entry, max_insns=100)

    out = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(out)
        print(f"Disasm summary written to {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
