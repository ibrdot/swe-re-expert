# RE Thinking — How a Senior Reverse Engineer Approaches a Binary

## The mindset

A senior RE doesn't start by reading every byte. They start by asking: **what is this thing, and what do I need to know about it?** Then they pick the cheapest signal that answers the question, and only escalate to expensive techniques when cheap ones run out.

## The hierarchy of questions

In order, ask:

1. **What is it?** (file type, arch, format, language, toolchain)
2. **What does it claim to be?** (entry point, main function, declared imports)
3. **What does it actually do?** (strings, calls, behavior — work backward from imports)
4. **What's unusual?** (high entropy, anti-debug, missing strings, odd section layout)
5. **What's the story?** (one-sentence summary of behavior)
6. **What's the proof?** (offsets, instructions, call targets that support the story)
7. **What's missing?** (what couldn't be confirmed statically, what needs dynamic)

## The cheap-signals-first principle

Always exhaust cheap signals before expensive ones:

| Cost | Signal | What it tells you |
|------|--------|---------------------|
| Free | `file`, size, magic bytes | Format, arch, toolchain |
| Free | Hashes (MD5/SHA256) | Threat intel lookup, identity |
| Cheap | `strings -a` | C2 endpoints, paths, mutexes, error messages |
| Cheap | Section entropy | Packing, encryption, suspicious regions |
| Cheap | Import table | Behavior categories (injection, persistence, network) |
| Cheap | Symbol table (if not stripped) | Function names → behavior |
| Medium | Disassembly of `main` + entry | Control flow, idioms |
| Medium | Cross-references from suspicious imports | Behavior confirmation |
| Expensive | Full disassembly + analysis | Function-by-function semantics |
| Expensive | Dynamic execution | Confirms behavior, captures runtime-only state |

A senior RE gets 80% of the understanding from the first 4 rows. Dynamic analysis is reserved for confirming hypotheses, not forming them.

## The backward-from-imports trick

The single most powerful RE technique: **don't start at `main`, start at suspicious imports**.

1. Pick a high-signal import (e.g. `CreateRemoteThread`, `socket`, `RegSetValueEx`)
2. Find all call sites that target it (`objdump -d | grep "call.*CreateRemoteThread"`)
3. Walk backward from each call to find the enclosing function prologue
4. Trace what prepares the args — that's the actual behavior

This works because imports are stable anchors. Stripped binaries still expose imports (PE IAT, ELF DT_NEEDED). Anti-debugging might hide strings, but it can't hide that the binary calls `socket()`.

## The "one-sentence story" rule

Before writing the report, force yourself to summarize the binary's behavior in **one sentence**. If you can't, you don't understand it yet — go back to the cheap signals.

Bad: "The binary does various things including network communication and file operations."
Good: "Lumma stealer variant that enumerates browser profiles, exfils to a hardcoded C2 via HTTP POST with base64-encoded body, and uses process hollowing to persist in `explorer.exe`."

The good version has: family, target, exfil method, persistence. That's the minimum bar.

## The "show me the bytes" rule

Every claim in the report must point to a byte. If you say "the binary uses AES", point to the S-box in `.rodata` at offset `0x4040`. If you say "it calls socket", point to the `call socket@plt` instruction at `0x401234`. If you say "the C2 is 1.2.3.4", point to the string at `0x4080F0`.

No bytes → not a finding. It's a hypothesis. Mark it as such.

## When to give up and escalate

Static analysis has limits. Recognize them:

- **Packed binary** — static sees the packer's stub, not the payload. Need to unpack (run + memory dump) before the analysis becomes useful.
- **VM-protected binary** — disassembly shows the VM dispatcher, not the original logic. Need handler-by-handler analysis (days of work) or symbolic execution.
- **Encrypted strings** — strings extraction returns nothing useful. Need to find the decryption routine and emulate it (Unicorn / Qiling).
- **Reflective loading** — the binary is just a loader; the real payload is in a resource or registry blob. Need to extract the payload first.
- **Stripped Go binary** — surprisingly analyzable (gopclntab); use Ghidra Go analyzer
- **Stripped Rust binary** — harder; panic strings are the main hook
- **Stripped C++ binary** — vtables in `.rodata` are the main hook

When you hit a wall, say so. The report should mark `BLOCKED` and explain what would unblock it, not pretend you understood what you didn't.

## The "two-pass" pattern

First pass: skim. Identify format, arch, key imports, suspicious strings. Form a one-paragraph hypothesis.

Second pass: verify. Pick the 3-5 most suspicious functions and disassemble them carefully. Confirm or refute the hypothesis. If refuted, form a new hypothesis and do another pass.

Most RE work is 2-3 passes. Trying to deep-dive on the first pass is a classic beginner mistake — you spend 30 minutes on a function that turns out to be the C runtime startup, not the actual behavior.

## Final mental hook

> "I have X bytes. I want to know Y. What's the cheapest signal that tells me Y?"

If you can answer that question repeatedly, you're doing RE. If you can't, you're reading bytes — and reading bytes is not analysis.
