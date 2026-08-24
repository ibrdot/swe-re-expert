#!/usr/bin/env python3
"""
swe_audit.py — Multi-language codebase audit.

Deterministic. Scans for: complexity hotspots, dead code candidates, dependency
direction anomalies, refactor priorities. Supports Python, Go, Rust, C/C++.

Usage:
    python scripts/swe_audit.py --root <root> --triage          # One-page map
    python scripts/swe_audit.py --root <root> --complexity      # Top complexity hotspots
    python scripts/swe_audit.py --root <root> --dead-code       # Dead code candidates
    python scripts/swe_audit.py --root <root> --deps            # Dependency direction analysis
    python scripts/swe_audit.py --root <root> --all
    python scripts/swe_audit.py --root <root> --out audit.json

Output (JSON):
{
    "root": "/path",
    "languages": {"python": 12, "go": 5, "rust": 3, "c": 8, "cpp": 2, "headers": 20},
    "total_files": 50,
    "total_loc": 12000,
    "complexity_hotspots": [{"file": "...", "function": "...", "score": 25}],
    "dead_code_candidates": [{"file": "...", "symbol": "...", "reason": "..."}],
    "dependency_issues": [{"from": "domain", "to": "controller", "evidence": "..."}],
    "refactor_priorities": [{"priority": "P1", "area": "...", "finding": "...", "evidence": "..."}],
    "summary": "One-line audit summary"
}
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path


# ---------- File inventory ----------

LANG_BY_EXT = {
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".zig": "zig",
}


def inventory(root: Path) -> dict:
    files_by_lang = {v: [] for v in LANG_BY_EXT.values()}
    headers = []
    total_loc = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in {"node_modules", ".git", "vendor", "target", "build",
                        "dist", "__pycache__", ".venv", "venv", ".tox",
                        ".pytest_cache", ".mypy_cache", ".ruff_cache",
                        "Pods", ".next", ".cache"} for part in p.parts):
            continue
        ext = p.suffix.lower()
        lang = LANG_BY_EXT.get(ext)
        if lang:
            try:
                loc = sum(1 for _ in p.open("rb"))
                total_loc += loc
                files_by_lang[lang].append({"path": str(p.relative_to(root)), "loc": loc})
            except (UnicodeDecodeError, PermissionError):
                pass
        elif ext in (".h", ".hpp"):
            headers.append(str(p.relative_to(root)))
    files_by_lang["headers"] = [{"path": h, "loc": 0} for h in headers]
    counts = {k: len(v) for k, v in files_by_lang.items()}
    counts = {k: v for k, v in counts.items() if v > 0}
    return {
        "languages": counts,
        "files_by_lang": files_by_lang,
        "total_files": sum(counts.values()),
        "total_loc": total_loc,
    }


# ---------- Complexity (Python via AST; others via heuristics) ----------

def python_complexity(path: Path) -> list:
    """Use AST to count branches per function. Cyclomatic complexity = branches + 1."""
    out = []
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            branches = 0
            for n in ast.walk(node):
                if isinstance(n, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                    branches += 1
                elif isinstance(n, ast.BoolOp):
                    branches += len(n.values) - 1
                elif isinstance(n, (ast.ExceptHandler,)):
                    branches += 1
                elif isinstance(n, ast.comprehension):
                    branches += 1
            cc = branches + 1
            out.append({
                "file": str(path),
                "function": node.name,
                "line": node.lineno,
                "complexity": cc,
            })
    return out


def generic_complexity(path: Path) -> list:
    """Heuristic: count if/for/while/switch/match per function-block via regex."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, PermissionError):
        return []
    out = []
    # Split by function defs (very loose — language-agnostic)
    func_re = re.compile(
        r"(?:func|fn|def|function|void|int|public|private|static|inline)\s+"
        r"(\w+)\s*[\(\{]",
        re.MULTILINE
    )
    matches = list(func_re.finditer(text))
    if not matches:
        # No functions detected — count file-level complexity
        branches = len(re.findall(r"\b(?:if|for|while|switch|match|case)\b", text))
        if branches > 0:
            out.append({
                "file": str(path),
                "function": "<file-level>",
                "line": 1,
                "complexity": branches + 1,
            })
        return out
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        body = text[start:end]
        branches = len(re.findall(r"\b(?:if|for|while|switch|match|case)\b", body))
        # Don't report zero-complexity trivial wrappers
        if branches > 3:
            out.append({
                "file": str(path),
                "function": m.group(1) if m.group(1) else "<anonymous>",
                "line": text[:m.start()].count("\n") + 1,
                "complexity": branches + 1,
            })
    return out


def collect_complexity(files_by_lang: dict) -> list:
    hotspots = []
    for lang, files in files_by_lang.items():
        if lang == "headers":
            continue
        for f in files:
            path = Path(f["path"])
            if lang == "python":
                hotspots.extend(python_complexity(path))
            else:
                hotspots.extend(generic_complexity(path))
    hotspots.sort(key=lambda x: x.get("complexity", 0), reverse=True)
    return hotspots[:50]


# ---------- Dead code candidates ----------

def python_dead_code(path: Path) -> list:
    """Find functions/classes never called within the codebase (very heuristic)."""
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return []
    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if name.startswith("_") and not name.startswith("__"):
                continue  # private, often called via dunder methods
            if name.startswith("__") and name.endswith("__"):
                continue  # dunder methods, called by Python internals
            candidates.append({"file": str(path), "symbol": name, "line": node.lineno})
    return candidates


def generic_dead_code(path: Path) -> list:
    """Heuristic: find declared but possibly-unused functions."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, PermissionError):
        return []
    # Public-looking function defs
    func_re = re.compile(
        r"^(?:pub\s+)?(?:fn|func|def|function)\s+(\w+)\s*[\(\{]",
        re.MULTILINE
    )
    candidates = []
    for m in func_re.finditer(text):
        name = m.group(1)
        # Skip main, init, test_*, etc.
        if name in ("main", "init", "TestMain", "New") or name.startswith(("Test", "Benchmark", "Example")):
            continue
        candidates.append({
            "file": str(path),
            "symbol": name,
            "line": text[:m.start()].count("\n") + 1,
        })
    return candidates


def find_dead_code(files_by_lang: dict) -> list:
    """Mark symbols that are defined but never referenced outside their definition file."""
    # First, collect all defined symbols
    definitions = []
    for lang, files in files_by_lang.items():
        if lang == "headers":
            continue
        for f in files:
            path = Path(f["path"])
            if lang == "python":
                definitions.extend(python_dead_code(path))
            else:
                definitions.extend(generic_dead_code(path))

    # Build a corpus of all text content
    corpus_text = ""
    for lang, files in files_by_lang.items():
        if lang == "headers":
            continue
        for f in files:
            try:
                corpus_text += Path(f["path"]).read_text() + "\n"
            except (UnicodeDecodeError, PermissionError):
                continue

    # A symbol is "dead" if it appears in the corpus only once (its definition site)
    # Or twice (definition + import statement) — both are weak evidence.
    dead = []
    for d in definitions[:200]:  # cap for performance
        sym = d["symbol"]
        occurrences = corpus_text.count(r"\b" + re.escape(sym) + r"\b")
        if occurrences <= 2:
            dead.append({**d, "occurrences": occurrences, "reason": "low reference count"})
    return dead[:30]


# ---------- Dependency direction ----------

def python_imports(path: Path) -> list:
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            out.append(node.module or "")
    return out


def generic_imports(path: Path) -> list:
    try:
        text = path.read_text()
    except (UnicodeDecodeError, PermissionError):
        return []
    out = []
    # C/C++ #include "foo.h" / <foo.h>
    for m in re.finditer(r'#include\s+[<"]([^>"]+)[>"]', text):
        out.append(m.group(1))
    # Go: import "foo/bar" or import ( "a"; "b" )
    for m in re.finditer(r'^\s*"([^"]+)"\s*$', text, re.MULTILINE):
        if "/" in m.group(1):
            out.append(m.group(1))
    # Rust: use foo::bar;
    for m in re.finditer(r'use\s+([\w:]+)\s*;', text):
        out.append(m.group(1))
    return out


def analyze_deps(files_by_lang: dict, root: Path) -> list:
    """Look for dependency direction anomalies — domain importing from controller/views, etc."""
    issues = []
    # Map files to "layer" by path
    def layer_of(p: str) -> str:
        p_lower = p.lower()
        if any(x in p_lower for x in ["/controller", "/controllers", "/views", "/routes", "/api/"]):
            return "presentation"
        if any(x in p_lower for x in ["/domain", "/model", "/entity", "/entities"]):
            return "domain"
        if any(x in p_lower for x in ["/service", "/services", "/usecase", "/usecases", "/application"]):
            return "application"
        if any(x in p_lower for x in ["/infra", "/infrastructure", "/persistence", "/repository", "/db"]):
            return "infrastructure"
        return "other"

    for lang, files in files_by_lang.items():
        if lang == "headers":
            continue
        for f in files:
            src_path = Path(f["path"])
            try:
                src_layer = layer_of(f["path"])
                if src_layer == "other":
                    continue
                imports = python_imports(src_path) if lang == "python" else generic_imports(src_path)
                for imp in imports:
                    # Resolve import to a path
                    target = None
                    if lang == "python":
                        target = imp.replace(".", "/")
                    else:
                        target = imp.replace("::", "/").replace(".", "/").split("/")[-1]
                    # Check if target is in a lower layer (presentation → domain is bad direction)
                    target_layer = layer_of(target)
                    if target_layer == "other":
                        continue
                    if src_layer == "domain" and target_layer in ("presentation", "application"):
                        issues.append({
                            "from": "domain",
                            "to": target_layer,
                            "evidence": f"{f['path']} imports {imp}",
                        })
                    if src_layer == "infrastructure" and target_layer == "presentation":
                        issues.append({
                            "from": "infrastructure",
                            "to": "presentation",
                            "evidence": f"{f['path']} imports {imp}",
                        })
            except Exception:
                continue
    return issues[:50]


# ---------- Triage summary ----------

def triage_summary(root: Path, inv: dict, complexity: list, dead: list, deps: list) -> dict:
    summary_parts = []
    summary_parts.append(f"{inv['total_files']} files / {inv['total_loc']} LOC")
    if inv['languages']:
        top_lang = max(inv['languages'], key=inv['languages'].get)
        summary_parts.append(f"primary: {top_lang}")
    if complexity:
        top_hotspot = complexity[0]
        summary_parts.append(f"top complexity: {top_hotspot['function']} ({top_hotspot['complexity']})")
    if dead:
        summary_parts.append(f"{len(dead)} dead-code candidates")
    if deps:
        summary_parts.append(f"{len(deps)} dep-direction issues")
    return " | ".join(summary_parts)


def build_refactor_priorities(complexity: list, dead: list, deps: list) -> list:
    out = []
    # P1: complexity > 20 in non-test code
    for c in complexity:
        if c["complexity"] >= 20:
            out.append({
                "priority": "P1",
                "area": "complexity",
                "finding": f"{c['function']} has CC={c['complexity']}",
                "evidence": f"{c['file']}:{c['line']}",
            })
    # P2: dead code with very low reference count
    for d in dead[:10]:
        out.append({
            "priority": "P2",
            "area": "dead_code",
            "finding": f"{d['symbol']} appears {d['occurrences']} time(s) in codebase",
            "evidence": f"{d['file']}:{d['line']}",
        })
    # P2: dependency direction anomalies
    for dep in deps[:10]:
        out.append({
            "priority": "P2",
            "area": "architecture",
            "finding": f"{dep['from']} layer imports from {dep['to']}",
            "evidence": dep["evidence"],
        })
    return out


# ---------- Main ----------

def main():
    p = argparse.ArgumentParser(description="Multi-language codebase audit")
    p.add_argument("--root", required=True, help="Project root")
    p.add_argument("--triage", action="store_true", help="One-page map")
    p.add_argument("--complexity", action="store_true", help="Top complexity hotspots")
    p.add_argument("--dead-code", action="store_true", help="Dead code candidates")
    p.add_argument("--deps", action="store_true", help="Dependency direction analysis")
    p.add_argument("--all", action="store_true")
    p.add_argument("--out", help="Write JSON to file")
    args = p.parse_args()

    if not any([args.triage, args.complexity, args.dead_code, args.deps, args.all]):
        args.all = True

    root = Path(args.root)
    if not root.is_dir():
        print(json.dumps({"error": f"Not a directory: {args.root}"}))
        sys.exit(1)

    inv = inventory(root)
    result = {
        "root": str(root),
        "languages": inv["languages"],
        "total_files": inv["total_files"],
        "total_loc": inv["total_loc"],
    }

    complexity = collect_complexity(inv["files_by_lang"]) if (args.all or args.complexity) else []
    dead = find_dead_code(inv["files_by_lang"]) if (args.all or args.dead_code) else []
    deps = analyze_deps(inv["files_by_lang"], root) if (args.all or args.deps) else []

    if args.all or args.complexity:
        result["complexity_hotspots"] = complexity
    if args.all or args.dead_code:
        result["dead_code_candidates"] = dead
    if args.all or args.deps:
        result["dependency_issues"] = deps
    if args.all or args.triage:
        result["refactor_priorities"] = build_refactor_priorities(complexity, dead, deps)
        result["summary"] = triage_summary(root, inv, complexity, dead, deps)

    out = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(out)
        print(f"Audit written to {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
