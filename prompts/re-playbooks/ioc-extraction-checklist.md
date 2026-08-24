# IOC Extraction Checklist

For every suspicious sample, extract indicators across all six categories. Each IOC should be: specific, contextualized, actionable.

## The 6 categories

1. Network IOCs — IPs, domains, URLs, UAs, SNI
2. Host IOCs — file paths, registry keys, services, mutexes, scheduled tasks
3. Process IOCs — spawned processes, command lines, parent-child pairs
4. Crypto IOCs — public keys, symmetric keys, KDF parameters
5. Target data — browser paths, wallet paths, FTP/SSH configs
6. Behavioral signatures — patterns for YARA / Sigma / EDR

## Network IOCs

### IPs

For each IP found in strings or observed during dynamic execution:

```
| IP | Port | Context | Source |
|----|------|---------|--------|
| 1.2.3.4 | 443 | C2 endpoint (HTTPS beacon) | strings:0x4080F0 + confirmed dynamic |
| 5.6.7.8 | 80 | Secondary C2 (HTTP POST exfil) | dynamic: HTTP request observed at T+15s |
```

Source tells the reader where you found it (offset in strings, dynamic observation, etc.).

Extract IPs from:
- ASCII strings matching `^[0-9]{1,3}(\.[0-9]{1,3}){3}$`
- UTF-16LE strings (Windows-heavy binaries)
- Dynamic pcap

### Domains

```
| Domain | Context | Source |
|--------|---------|--------|
| c2.evil.com | C2 domain (resolved to 1.2.3.4) | strings:0x4080F0 + DNS dynamic |
| update.evil.com | Update check domain | strings:0x408110 |
```

Watch for:
- DGA patterns (random-looking subdomains)
- Fast-flux (rapidly changing IPs for same domain)
- Subdomain滥用 (legit domain + malicious subdomain, e.g., `evil.github.io`)

### URLs

```
| URL | Method | Body | UA | Context |
|-----|--------|-------|-----|---------|
| https://c2.evil.com/gate.php?id=123 | POST | base64(infosteal_data) | Mozilla/5.0... | Beacon + exfil |
| http://update.evil.com/payload.bin | GET | - | Mozilla/5.0... | Payload download |
```

For each URL, capture:
- Full URL (path included)
- HTTP method
- POST body format (base64 / JSON / form / custom)
- User-Agent string
- Frequency (beacon interval + jitter)

### TLS SNIs

From dynamic pcap, the SNI in TLS Client Hello tells you which host the malware thinks it's connecting to. Often more reliable than DNS (DNS may be cached, redirected, etc.).

### Beacon intervals

If you captured multiple beacons, compute:
- Mean inter-arrival time
- Stddev (low stddev = beacon; high = burst)
- Jitter pattern (often ±10–20% of base)

Useful for EDR rules — "process making HTTPS requests to X at 60s ± 10% intervals" is a detection.

## Host IOCs

### File paths

For each path created/written/read:

```
| Path | Operation | Context |
|------|-----------|---------|
| C:\Users\Public\svchost.exe | create, write | Dropped payload |
| C:\ProgramData\Update\config.bin | create, write | Encrypted config |
| %TEMP%\~tmpXXXX.tmp | create, write, delete | Staging + cleanup |
| C:\Windows\System32\drivers\evil.sys | create | Kernel driver install |
```

Watch for:
- File names mimicking system binaries (`svchost.exe`, `csrss.exe` in user dirs)
- Use of `ProgramData` / `Public` for write access without elevation
- Use of `%TEMP%` for staging / cleanup
- `.bin`, `.dat`, `.tmp` extensions (often encrypted payloads)
- Driver files in user directories (kernel mode installation attempt)

### Registry keys

```
| Key | Operation | Context |
|-----|-----------|---------|
| HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\Updater | set | Persistence (Run key) |
| HKLM\SYSTEM\CurrentControlSet\Services\WinUpdateHelper | set | Service persistence |
| HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\... | set | Add/Remove entry disguise |
| HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run | set | Startup folder persistence |
```

The big 4 persistence locations:
1. `HKCU\...\Run` and `HKLM\...\Run` — Run keys (very common)
2. `HKLM\SYSTEM\CurrentControlSet\Services\` — Service install
3. `HKCU\...\StartupApproved\StartupFolder` — Startup folder
4. `HKLM\...\Winlogon\Userinit` / `Shell` — Winlogon hijack

### Services

```
| Service name | Display name | Binary path | Start type |
|--------------|---------------|--------------|------------|
| WinUpdateHelper | Windows Update Helper Service | C:\ProgramData\Update\helper.exe | auto_start |
```

### Mutex / event names

```
| Name | Type | Context |
|------|------|---------|
| Global\MutexFamily_v1 | mutex | Single-instance check |
| Global\WinStartupEvent | event | Sync signal to child process |
```

Mutex names are often family-specific. They're great for YARA strings too (single-instance mutex is a strong family signature).

### Scheduled tasks

```
| Task path | Trigger | Action |
|-----------|---------|--------|
| \Microsoft\Windows\Update\UpdateTask | ONSTART, every 30 min | powershell -nop -w hidden -enc ... |
```

Common persistence via:
- `schtasks /create` (direct command)
- COM interface `ITaskScheduler` / `IRegisteredTask` (programmatic)
- XML task definition dropped into `C:\Windows\System32\Tasks\`

## Process IOCs

### Spawned processes

```
| PID | Name | Parent PID | Parent name | Command line |
|-----|------|------------|-------------|--------------|
| 1234 | powershell.exe | 1200 | winword.exe | powershell -nop -w hidden -enc <base64> |
| 1250 | cmd.exe | 1234 | powershell.exe | cmd /c vssadmin delete shadows /all /quiet |
```

Suspicious parent-child patterns:
- `winword.exe` → `powershell.exe` → `cmd.exe` (classic macro dropper)
- `excel.exe` → `wscript.exe` (XLS macro)
- `outlook.exe` → `cmd.exe` (email-borne)
- `mshta.exe` → `powershell.exe` (HTA dropper)
- `rundll32.exe <weird.dll>,<weird_func>` (DLL execution)
- `regsvr32.exe /s /n /u /i:http://... scrobj.dll` (squiblydoo)
- `msbuild.exe <file>` (LOLBins — code execution via build)

### Command lines

Flag unusual flags:
- `powershell -nop -w hidden -enc` (no profile, hidden window, base64)
- `powershell -nop -w hidden -c IEX (New-Object ...)` (download cradle)
- `cmd /c <vssadmin|wbadmin|bcdedit> ...` (ransomware prep)
- `mshta javascript:...` (HTA inline)
- `rundll32 <strange>,<strange_func>` (DLL exec)

### Process injection targets

Common injection targets:
- `explorer.exe` (long-running, legit-looking)
- `svchost.exe` (multiple instances, blends in)
- `firefox.exe` / `chrome.exe` (browser context, network access)
- `lsass.exe` (credential theft target — actually a sign of Mimikatz)

## Crypto IOCs

### Public keys

For asymmetric crypto used by the malware (RSA, ECC):

```
| Key | Type | Where found | Use |
|-----|------|--------------|-----|
| MIICI...goB5AAAA... | RSA-2048 public | strings:0x4090A0 | Encrypts symmetric key for exfil |
```

These are embedded in the binary; extract from strings or from `.rodata`.

### Symmetric keys

For symmetric crypto (AES, RC4, ChaCha20):

```
| Key | Algorithm | Where found | Use |
|-----|------------|--------------|-----|
| 0x12 0x34 0x56 ... (16 bytes) | AES-128 | .rodata:0x404020 | Decrypts C2 response |
| 0xAA 0xBB ... (32 bytes) | AES-256 | stack (built at runtime) | Encrypts exfil data |
```

If keys are built at runtime (stack strings), you'll need dynamic dump.

### KDF parameters

For derived keys (PBKDF2, scrypt):

```
| Algorithm | Iterations | Salt | Output length |
|-----------|------------|------|---------------|
| PBKDF2-HMAC-SHA256 | 10000 | 0x... (16 bytes) | 32 |
```

Useful for forensic reconstruction (you can re-derive the key if you know the password).

## Target data (exfil targets)

What does the sample look for / exfiltrate?

### Browser data

```
| Browser | Path checked | Data extracted |
|---------|--------------|----------------|
| Chrome | %LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data | Login credentials (URL, username, password) |
| Chrome | %LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies | Session cookies |
| Chrome | %LOCALAPPDATA%\Google\Chrome\User Data\Default\Web Data | Autofill data |
| Edge | %LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Login Data | Same as Chrome (Chromium-based) |
| Firefox | %APPDATA%\Mozilla\Firefox\Profiles\*\logins.json | Login credentials |
| Firefox | %APPDATA%\Mozilla\Firefox\Profiles\*\key4.db | Encryption key |
```

### Crypto wallets

```
| Wallet | Path checked | Data extracted |
|--------|--------------|----------------|
| Bitcoin Core | %APPDATA%\Bitcoin\wallet.dat | Wallet file |
| Electrum | %APPDATA%\Electrum\wallets\ | Seed, keys |
| MetaMask | %APPDATA%\MetaMask\Local Extension Settings\ | Vault (encrypted) |
| Exodus | %APPDATA%\Exodus\ | Wallet seed |
| Monero GUI | %USERPROFILE%\Documents\Monero\wallets\ | Wallet file |
```

### Other credential stores

```
| Target | Path | Data extracted |
|--------|------|----------------|
| FileZilla | %APPDATA%\FileZilla\sitemanager.xml | FTP server credentials |
| WinSCP | HKCU\SOFTWARE\Martin Prikryl\WinSCP 2\Sessions | SFTP credentials |
| OpenSSH | %USERPROFILE%\.ssh\known_hosts | Known hosts |
| OpenSSH | %USERPROFILE%\.ssh\id_* | Private keys |
| Windows Vault | Vault API | Generic credential store |
| Outlook | %APPDATA%\Microsoft\Outlook\*.ost | Email cache |
| Telegram | %APPDATA%\Telegr Desktop\ | Session data |
| Discord | %APPDATA%\Discord\Local Storage\ | Tokens |
| Signal | %APPDATA%\Signal\ | Session data |
```

## Behavioral signatures

For each behavior, write a YARA rule, Sigma rule, or EDR query:

### YARA (file-based)

For static patterns that identify the family. See `yara-rule-design.md` for the playbook.

### Sigma (log-based)

For Windows Event Log patterns:

```yaml
title: FamilyName Persistence via Run Key
status: experimental
logsource:
    product: windows
    category: registry_event
detection:
    selection:
        EventType: SetValue
        TargetObject|contains:
            - '\Software\Microsoft\Windows\CurrentVersion\Run\Updater'
            - '\Software\Microsoft\Windows\CurrentVersion\Run\WinUpdateHelper'
    condition: selection
level: high
```

### Sysmon (process-based)

For Sysmon Event ID 1 (process create) detection:

```
ProcessCreation events where:
    (ParentImage = "winword.exe" AND Image = "powershell.exe" AND CommandLine contains "-enc")
    OR (ParentImage = "excel.exe" AND Image = "wscript.exe")
```

### Network detection (Suricata/Snort)

For C2 beacon detection:

```
alert http any any -> $HOME_NET any (msg:"FamilyName C2 beacon"; \
    content:"/gate.php?id="; http_uri; \
    content:"Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1)"; http_header; \
    flow:to_server,established; threshold:type both, track by_src, count 5, seconds 60;
    sid:1000001; rev:1;)
```

## Extraction methodology

For each IOC:
1. Find the IOC (in strings, dynamic pcap, log, etc.)
2. Verify it's actually used (not a leftover / dead code string)
3. Record the context (what behavior it supports)
4. Record the source (offset / log line / etc.) for evidence
5. Test in detection rule (does the rule fire on this sample? on clean files?)

Without context and source, IOCs are noise. With them, they're actionable intelligence.

## Output

The IOC section of the malware triage report should have 6 tables (one per category). Each IOC should be specific, sourced, and contextualized.

Avoid the temptation to dump "every IP in the strings file" — many are bogus (strings from imported libs, error messages, etc.). Filter for IOCs that actually support the behavioral narrative in the report.
