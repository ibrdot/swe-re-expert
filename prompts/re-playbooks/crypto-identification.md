# Cryptographic Primitive Identification — Detecting Crypto in Binaries

How to identify which cryptographic algorithm a binary uses, based on constants, structure shape, and call patterns — without needing source code or symbols. The goal is to take an opaque binary that "does crypto stuff" and produce a verifiable claim: "this uses AES-128 in CBC mode with the key derived via PBKDF2-HMAC-SHA256 (10000 iterations) and an IV concatenated to the ciphertext".

This playbook covers symmetric ciphers (AES, DES, 3DES, Blowfish, RC4, RC5, RC6, ChaCha20, Salsa20, XTEA, TEA, Serpent, Camellia, SM4), hashes (MD5, SHA-1, SHA-2, SHA-3, BLAKE2, BLAKE3, RIPEMD-160, Whirlpool, SM3), KDFs (PBKDF2, scrypt, Argon2, bcrypt), MACs (HMAC, Poly1305, CMAC), and asymmetric (RSA, DH, ECDH, ECDSA, EdDSA, Curve25519, Curve448, secp256k1, NIST P-256/P-384/P-521).

If the crypto is constant-less (custom hand-rolled cipher), this playbook helps rule out known primitives — the binary then falls into the "custom crypto" bucket where you must recover the algorithm by reading the disasm.

---

## 1. The 4 detection axes

Every crypto primitive in a binary can be identified by one or more of:

1. **Constants** — magic numbers, S-boxes, round constants, irreducible polynomials
2. **Structure shape** — function shape, loop counts, table accesses, key schedule patterns
3. **Library signatures** — FLIRT signatures, library function names (if not stripped), known OpenSSL/libsodium/mbedTLS exports
4. **Side-channel patterns** — how the algorithm uses memory, how many rounds it does, what its input/output sizes are

Strong identification requires at least two of these. Constants alone are usually enough for a HYPOTHESIS; constants + structure shape yields CONFIRMED.

---

## 2. Symmetric cipher constants — the lookup table

### 2.1 AES (Rijndael)

AES has the most recognizable constants of any cipher.

| Constant | Value | Where | Purpose |
|---|---|---|---|
| Forward S-box (first 16 bytes) | `63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76` | `.rodata` | SubBytes |
| Inverse S-box (first 16 bytes) | `52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb` | `.rodata` | InvSubBytes |
| Rcon (round constants) | `01 02 04 08 10 20 40 80 1b 36` (first 10) | `.rodata` | KeyExpansion |
| GF(2^8) multiplication constant | `0x1b` (used in `xtime`) | `.text` | MixColumns |
| T-tables (T0/T1/T2/T3) | 4 × 256-entry × 4-byte tables | `.rodata` (4 KB total) | Optimization for SubBytes+ShiftRows+MixColumns combined |
| Td0 (inverse T-table, first entry) | `51 f4 a7 51 53 65 41 7e 96 5a 35 38 14 12 06 a1` (rearranged) | `.rodata` | InvMixColumns optimization |

**Detection heuristics**:

- Find the forward S-box (`63 7c 77 7b...`) → AES is being used. HYPOTHESIS.
- Find both S-boxes → confirms AES. CONFIRMED.
- Find 4 KB of T-tables alongside the S-box → optimized AES (OpenSSL, mbedTLS, BoringSSL). The T-tables can be reconstructed by their unique first row.
- The Rcon table `01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6 97 35 67 5e` (first 29 bytes for AES-256) confirms the key schedule.

**Key length detection**: AES-128 has 10 rounds, AES-192 has 12 rounds, AES-256 has 14 rounds. Look for the round-count constant in the cipher's main loop:
- `cmp ecx, 10` → AES-128
- `cmp ecx, 12` → AES-192
- `cmp ecx, 14` → AES-256

**Mode detection**: look at what's done to the IV between blocks:
- IV XOR with plaintext before encryption, then IV = ciphertext → **CBC**
- IV XOR with the counter (`inc` instruction on counter), counter encrypted → **CTR**
- 16-byte nonce + counter, IV never chained → **GCM** (look for the GHASH multiply in GF(2^128) which has the polynomial `0x87` shifted)
- IV simply XORed with output (no chaining) → **OFB**
- Plaintext XORed directly with keystream, no feedback → **CFB**
- Each block encrypted standalone with no chaining → **ECB** (insecure mode, worth flagging in a security review)

### 2.2 DES / 3DES

| Constant | Value | Where | Purpose |
|---|---|---|---|
| Initial Permutation (IP) table | bytes `58, 50, 42, 34, 26, 18, 10, 2, 60, 52, ...` | `.rodata` | Initial bit permutation |
| Final Permutation (FP) table | bytes `40, 8, 48, 16, 56, 24, 64, 32, ...` | `.rodata` | Final bit permutation |
| S-boxes 1-8 (each 64 bytes) | 8×64 byte tables; S-box 1 starts `14, 4, 13, 1, 2, 15, 11, 8, 3, 10, ...` | `.rodata` (512 bytes total) | 6-bit-to-4-bit substitution |
| P-box permutation | bytes `16, 7, 20, 21, 29, 12, 28, 17, 1, 15, ...` | `.rodata` | Permutation of S-box output |
| PC1 (Permuted Choice 1) | bytes `57, 49, 41, 33, 25, 17, 9, 1, ...` | `.rodata` | Key schedule |
| PC2 (Permuted Choice 2) | bytes `14, 17, 11, 24, 1, 5, 3, 28, ...` | `.rodata` | Key schedule |
| Shift schedule | bytes `1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1` | `.rodata` | Key schedule rotations |

**Detection**: any one of these tables is essentially unique to DES. The S-box set is the most distinctive — S-box 1's first bytes (`14, 4, 13, 1`) are a strong signature.

**3DES detection**: look for the cipher being called 3 times (encrypt → decrypt → encrypt), with three 8-byte subkeys. The middle "decrypt" call uses the same code path with `1` for the direction flag where encrypt uses `0`. Often the function name (if present) is `DES_ede3_cbc_encrypt` or similar OpenSSL-style.

### 2.3 Blowfish

| Constant | Value | Purpose |
|---|---|---|
| P-array (18 entries) | First few digits of `π`: `0x243F6A88`, `0x85A308D3`, `0x13198A2E`, `0x03707344`, ... | Initial P-array |
| S-boxes (4×256 entries) | Digits of `π` continuing after P-array | Initial S-boxes |

**Detection**: the P-array starting with `0x243F6A88, 0x85A308D3, 0x13198A2E` is a near-unique signature. Look for it in `.rodata` as a 72-byte (`18*4`) sequence followed immediately by 4×1024-byte S-boxes.

### 2.4 Twofish

| Constant | Value | Purpose |
|---|---|---|
| Q0 and Q1 (two 4-bit S-boxes) | `0xA9, 0x67, 0xB3, 0xE8, 0x04, 0xFD, 0xA3, 0x76, ...` (Q0 starts) | Key-dependent S-box derivation |
| MDS matrix coefficients | specific to Twofish | Key-dependent S-box MDS |
| `0x4A818C5B` (round constant) | magic round value | Round function |

### 2.5 RC4 (ARCFOUR)

RC4 has **no constants in `.rodata`**. The S-box (256-byte array) is initialized at runtime from the key. Detection is by **structure**:

- A 256-byte array initialized with `0, 1, 2, ..., 255` (visible as a `mov [rdi+rax], al; inc al; cmp al, 0; jne init_loop` pattern)
- A swap loop: two pointers, a swap of two bytes, then `cmp ecx, 256; jne swap_loop`
- The KSA is `for i in 0..256: j = (j + S[i] + key[i % keylen]) % 256; swap(S[i], S[j])`
- The PRGA is `i++; j += S[i]; swap(S[i], S[j]); output S[(S[i]+S[j]) % 256]`

**Detection signature**: a 256-byte array init loop + the swap-based KSA pattern. The presence of these two loops near each other (one runs once, one runs per byte of output) is a strong RC4 signature.

### 2.6 ChaCha20 / Salsa20

| Constant | Value | Purpose |
|---|---|---|
| Sigma constants (ChaCha20) | `0x61707865, 0x3320646E, 0x79622D32, 0x6B206574` (ASCII: `"expand 32-byte k"`) | Initial state words 0-3 |
| Tau constants (ChaCha20 with 8-byte key) | `0x61707865, 0x3120646E, 0x79622D36, 0x6B206574` (ASCII: `"expand 16-byte k"`) | Initial state words 0-3 for 8-byte key |
| Salsa20 constants | `0x61707865, 0x64207361, 0x79622D32, 0x6B206574` (ASCII: `"expand 32-byte k"` variants) | Initial state words |

**Detection**: search for the 4-constant block `65 78 70 61 6E 64 20 33 32 2D 62 79 74 65 20 6B` (ASCII `"expand 32-byte k"`) in `.rodata`. If present, ChaCha20 or Salsa20 is being used.

**ChaCha20 vs Salsa20 distinction**: look at the round function. ChaCha20's `QR(a,b,c,d)` does `a+=b; d^=a; d<<<=16; c+=d; b^=c; b<<<=12; a+=b; d^=a; d<<<=8; c+=d; b^=c; b<<<=7`. Salsa20's `QR(a,b,c,d)` does `b ^= (a + d) <<< 7; c ^= (b + a) <<< 9; d ^= (c + b) <<< 13; a ^= (d + c) <<< 18`. The rotation constants (`16, 12, 8, 7` for ChaCha; `7, 9, 13, 18` for Salsa) are unique fingerprints.

### 2.7 TEA / XTEA / XXTEA

| Constant | Value | Purpose |
|---|---|---|
| TEA delta | `0x9E3779B9` (golden ratio fractional) | Per-round constant |
| XTEA delta | same `0x9E3779B9` | Per-round constant |

**Detection**: the constant `0x9E3779B9` (or its byte form `B9 79 37 9E` little-endian) appearing in a function with 32-cycle Feistel structure (`sum += delta; v0 += ((v1<<4) + k0) ^ (v1 + sum) ^ ((v1>>5) + k1)`) is a definitive TEA/XTEA signature. TEA does 32 rounds; XTEA does 64 rounds.

### 2.8 Serpent

Serpent uses 8 4-bit S-boxes, applied in parallel 4 at a time per round. The S-boxes are:
- S0: `3 0 6 13 B 5 8 E C F 7 A 9 1 2 4`
- S1: `E D B 4 1 2 9 6 7 A 5 0 8 C 3 F`
- ...

Detection: the S0 byte sequence `03 00 06 0D 0B 05 08 0E 0C 0F 07 0A 09 01 02 04` is essentially unique to Serpent.

### 2.9 Camellia

Camellia uses 4 S-boxes (`s1`, `s2`, `s3`, `s4`); `s2`, `s3`, `s4` are derived from `s1`. `s1` starts with `112 130 156 162  ...`. The constants `SIGMA1-6` (Camellia's key schedule) are:
- `Σ1 = 0xA09E667F3BCC908B` (used to derive subkeys)
- `Σ2 = 0xB67AE8584CAA73B2`
- `Σ3 = 0xC6EF372FE94F82BE`
- `Σ4 = 0x54FF53A5F1D36F1C`
- `Σ5 = 0x10EC5F9C5ED1F8E4`
- `Σ6 = 0xB056882C0B9D0B5C`

**Detection**: any of the `Σ` constants in `.rodata` is a unique Camellia signature.

### 2.10 SM4 (Chinese national standard)

SM4 has a 256-byte S-box (first 16 bytes: `D6 90 E9 FE CC E1 3D B7 16 B6 14 C2 28 FB 2C 05`) and uses FK constants `0xA3B1BAC6` and `0x56AA3350` plus CK constants (`0x00070E15, 0x1C232A31, 0x383F464D, ...`).

**Detection**: the SM4 S-box first 16 bytes are unique to SM4.

### 2.11 ARIA (Korean standard)

ARIA uses two 256-byte S-boxes derived from S1 (AES forward S-box) and S2 (AES inverse S-box), with a specific mixing layer. Detection is by recognizing the cipher has 12-14 rounds (depending on key size) and uses both AES S-boxes.

---

## 3. Hash function constants

### 3.1 MD5

| Constant | Value | Purpose |
|---|---|---|
| IV | `0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476` | Initial state |
| Sin constants table | 64 floating-point values approximated as integers | Per-round values |
| Per-round shift amounts | specific 4×16 tables | Per-round rotations |

**Detection**: the IV `01 23 45 67 89 AB CD EF FE DC BA 98 76 54 32 10` in little-endian (as bytes) is the MD5 signature. The 64-entry table of pre-computed sines (in the form of `T[i] = floor(2^32 × abs(sin(i+1))))` is a 256-byte block whose first entries are `D7 6A A4 78 9C B8 6B 99 ...` (little-endian) — a secondary signature.

### 3.2 SHA-1

| Constant | Value | Purpose |
|---|---|---|
| IV | `0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0` | Initial state |
| Round constants | `0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xCA62C1D6` | Per-20-round-block constants |

**Detection**: the first 4 IVs match MD5's first 4 (because SHA-1 derives from MD4 too), but the 5th IV (`0xC3D2E1F0`) and the 4 round constants are unique to SHA-1. Look for both IVs and round constants present.

### 3.3 SHA-2 (SHA-256, SHA-384, SHA-512, SHA-224)

| Constant | Value | Purpose |
|---|---|---|
| SHA-256 IV | `0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19` | Initial state |
| SHA-256 round constants (K) | 64 entries; first: `0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, ...` | Per-round constants |
| SHA-512 IV | `0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1, ...` (64-bit) | Initial state |
| SHA-512 round constants (K) | 80 entries; first: `0x428a2f98d728ae22, 0x7137449123ef65cd, ...` (64-bit) | Per-round constants |
| SHA-224 IV | 8 32-bit values derived from SHA-256 primes | Initial state |
| SHA-384 IV | 8 64-bit values derived from SHA-512 primes | Initial state |

**Detection**: the SHA-256 K-table first entry `0x428a2f98` (as bytes: `98 2f 8a 42` little-endian) is a unique signature. For SHA-512, the K-table starts with `0x428a2f98d728ae22` (as bytes: `22 ae 28 d7 98 2f 8a 42`).

### 3.4 SHA-3 (Keccak)

SHA-3 uses 24 round constants (64-bit each). The first few are:
- `0x0000000000000001`
- `0x0000000000008082`
- `0x800000000000808A`
- `0x8000000080008000`
- ...

The 24 round constants are unique to Keccak. Their 64-bit byte representation appears as `01 00 00 00 00 00 00 00 82 80 00 00 00 00 00 00 8A 80 00 00 00 00 00 80 ...` (little-endian, 24 8-byte values = 192 bytes).

SHA-3 also has the 5×5 permutation state and 24-round structure.

### 3.5 BLAKE2 / BLAKE3

BLAKE2 uses round constants derived from SHA-2's IV. BLAKE3 uses the same as BLAKE2s with a tree mode. The tree mode parameters appear as constants in the binary.

### 3.6 MD4 (legacy)

IV is the same first 4 values as MD5/SHA-1 (`0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476`). Distinguished from MD5 by absence of sine constants and only 3 rounds vs MD5's 4. Used in NTLM password hashes (Microsoft).

### 3.7 RIPEMD-160

Uses IV `0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0` (same as SHA-1, but the algorithm differs). Detection: 5 32-bit IVs + 5 left-line and 5 right-line constants. The constants `0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E` (left line) and `0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000` (right line) are unique to RIPEMD-160.

### 3.8 SM3 (Chinese standard)

SM3 uses IV `0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600, 0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E` and constants `0x73383316, 0x80018000` (T-j constants).

**Detection**: the SM3 IV is unique.

### 3.9 Whirlpool

Whirlpool uses a 256-byte S-box derived from a specific construction, plus a 10-entry round constant table. The S-box first byte is `0x18` followed by `0x23, 0xC6, 0xE8, 0x87, 0xB8, 0x01, 0x4F, ...`. Detection is by recognizing the Whirlpool S-box.

---

## 4. KDF and MAC constants

### 4.1 PBKDF2

PBKDF2 has **no constants of its own** — it's a wrapper around a PRF (HMAC-SHA1, HMAC-SHA256, etc.). Detection is by structure:
- Loop runs N iterations (often 10000, 100000, or 1000000)
- Each iteration calls HMAC
- Output is XORed together

The iteration count is often a magic number in the binary (`10000 = 0x2710`, `100000 = 0x186A0`, `1000000 = 0xF4240`). Search for these constants and confirm PBKDF2 is in use.

### 4.2 scrypt

scrypt has parameters N (CPU/memory cost), r (block size), p (parallelism). The values are typically powers of 2 for N (e.g., `0x4000` = 16384, `0x8000` = 32768). It uses Salsa20/8 internally (not Salsa20/X). The combination of "memory-hard allocation pattern" (`mmap` of N×128×r bytes) plus a Salsa20/8 core call is the scrypt signature.

### 4.3 Argon2

Argon2 has its own magic constants for the type (Argon2d, Argon2i, Argon2id) and uses Blake2b as the underlying primitive. The Argon2 version byte (`0x13`) and the type bytes (`0x00`, `0x01`, `0x02`) are present in the encoded hash string.

### 4.4 bcrypt

bcrypt uses the Blowfish key schedule (the 72-byte P-array + 4 KB S-boxes). The cost factor (`4..31`) appears as a single byte. The base64 variant (`./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789`) is unique to bcrypt.

### 4.5 HMAC

HMAC has **no constants of its own** — it's a wrapper around a hash. Detection:
- Inner pad: `0x36` repeated (block_size times)
- Outer pad: `0x5c` repeated
- Two hash calls with the same key (one before main data, one after)

Look for the constants `0x36` and `0x5c` near each other in code.

### 4.6 Poly1305

Poly1305 uses the prime `2^130 - 5` (not directly visible as a constant, but the modular reduction pattern is recognizable). The key is 32 bytes (16 for `r`, 16 for `s`). Often paired with ChaCha20 in `crypto_secretbox` (libsodium's authenticated encryption).

### 4.7 AES-CMAC

Uses AES as a block cipher plus the constants `K1` and `K2` derived from the L value (a constant computed by encrypting a zero block). The subkey generation pattern is distinctive: `encrypt zero block, then shift+XOR` based on the MSB of the result.

---

## 5. Asymmetric crypto constants

### 5.1 RSA

RSA itself has no fixed constants. The big-integer arithmetic (`bn_mul_add_words`, `bn_mul_words`, etc.) is recognizable. OpenSSL's BN functions are well-known by name. If stripped, look for:
- Big-integer multiplication patterns (schoolbook or Karatsuba)
- Montgomery reduction (the constant `0xXX_XXXX_XXXX_XXXX` for modular multiplication — Montgomery's R value)
- Sliding-window exponentiation (loop with `1 << i` shifts and conditional multiplies)

**Key detection**: RSA public key has `n` (modulus) and `e` (exponent). Common `e` values are `3`, `17`, `0x10001` (65537). Search for these in `.rodata` near the BN code.

### 5.2 Diffie-Hellman

DH uses prime groups. Common DH group primes:
- Group 14 (RFC 3526): `0xFFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1 29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD EF9519B3 CD3A431B 302B0A6D F25EE143 7C0A0E7F ...`
- Group 1, 2, 5 are shorter (legacy, weak)

The hex pattern `FF FF FF FF FF FF FF FF C9 0F DA A2 ...` is a unique signature for DH-14.

### 5.3 Curve25519 / Curve448

Curve25519 has the prime `2^255 - 19` (= `0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFED`). The scalar multiplication uses the constant `121665/1664563` represented as a 32-byte little-endian constant. The byte sequence `ED FF FF FF ...` (255 - 19 = the prime, little-endian) is unique.

Curve448 uses `2^448 - 2^224 - 2^96 + 2^64 - 1`.

### 5.4 NIST P-256 / P-384 / P-521

The P-256 prime is `0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF`. Detection: search for `FF FF FF FF 00 00 00 01 00 00 00 00 ...` (the unique middle bytes).

P-384 prime: `0xFFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFE FFFFFFFF 00000000 00000000 FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF`.

P-521 prime: `0x01FFFFFFFFFFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF`.

### 5.5 secp256k1 (Bitcoin)

The secp256k1 curve has the prime `0xFFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFC2F` (note the last bytes `FC 2F`). Detection: search for `FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF ... FF FF FF FF FF FF FC 2F`. Unique signature.

### 5.6 EdDSA (Ed25519 / Ed448)

Ed25519 uses the prime `2^255 - 19` (same as Curve25519). It also has a curve order `2^252 + 27742317777372353535851937790883648493`. The Ed25519 basepoint is `5866666666666666666666666666666666666666666666666666666666666666` (hex), unique signature.

---

## 6. Library signatures — FLIRT and named exports

If the binary is **not** stripped of library symbols, you can identify the crypto by function name alone:

### 6.1 OpenSSL / BoringSSL

Common exports:
- `AES_set_encrypt_key`, `AES_set_decrypt_key`, `AES_encrypt`, `AES_decrypt`, `AES_cbc_encrypt`, `AES_ctr128_encrypt`, `AES_cbc_decrypt`, `AES_gcm_encrypt`, `AES_gcm_decrypt`
- `RSA_new`, `RSA_generate_key`, `RSA_public_encrypt`, `RSA_private_decrypt`, `RSA_sign`, `RSA_verify`
- `EVP_CIPHER_CTX_new`, `EVP_EncryptInit_ex`, `EVP_EncryptUpdate`, `EVP_EncryptFinal_ex`
- `SHA1`, `SHA256`, `SHA512`, `EVP_DigestInit_ex`
- `HMAC`, `HMAC_Init_ex`, `HMAC_Update`, `HMAC_Final`
- `DH_new`, `DH_generate_parameters`, `DH_generate_key`

### 6.2 libsodium

Common exports:
- `crypto_secretbox_easy`, `crypto_secretbox_open_easy`
- `crypto_box_easy`, `crypto_box_open_easy`
- `crypto_sign_detached`, `crypto_sign_verify_detached`
- `crypto_aead_chacha20poly1305_encrypt`, `crypto_aead_chacha20poly1305_decrypt`
- `crypto_generichash` (BLAKE2b)
- `crypto_pwhash` (Argon2 family)

### 6.3 mbedTLS (formerly PolarSSL)

Common exports:
- `mbedtls_aes_setkey_enc`, `mbedtls_aes_crypt_cbc`, `mbedtls_aes_crypt_cfb128`
- `mbedtls_rsa_init`, `mbedtls_rsa_pkcs1_encrypt`, `mbedtls_rsa_pkcs1_decrypt`
- `mbedtls_sha1_ret`, `mbedtls_sha256_ret`, `mbedtls_sha512_ret`
- `mbedtls_md_hmac`, `mbedtls_md_hmac_starts`
- `mbedtls_x509_crt_parse`, `mbedtls_ssl_setup`

### 6.4 libgcrypt (GnuTLS, GnuPG)

- `gcry_cipher_open`, `gcry_cipher_setkey`, `gcry_cipher_encrypt`, `gcry_cipher_decrypt`
- `gcry_md_open`, `gcry_md_write`, `gcry_md_final`
- `gcry_mpi_new`, `gcry_mpi_mul`, `gcry_mpi_mod`

### 6.5 Windows CryptoAPI / CNG

- `CryptAcquireContext`, `CryptCreateHash`, `CryptHashData`, `CryptDeriveKey`, `CryptEncrypt`, `CryptDecrypt` (legacy CryptoAPI)
- `BCryptOpenAlgorithmProvider`, `BCryptGenerateSymmetricKey`, `BCryptEncrypt`, `BCryptDecrypt`, `BCryptHashData`, `BCryptFinishHash` (CNG)

### 6.6 FLIRT signatures (IDA Pro)

IDA Pro ships FLIRT signatures for OpenSSL, BoringSSL, mbedTLS, etc. When loaded, IDA matches known library function bytes and restores the function names. Ghidra has similar `Function ID` scripts.

If FLIRT recovers names like `AES_encrypt` or `SHA256_Update`, you have direct identification.

---

## 7. Custom / hand-rolled crypto — the red flag

When the crypto has **no identifiable constants**, no library signatures, and no recognizable structure, you are looking at hand-rolled crypto. **This is almost always a security defect** — the algorithm is likely weak even if the author intended to implement a known cipher.

Report it as `SUSPECTED custom crypto` and flag for security review. Common patterns:
- XOR loops with a fixed key (cipher is `ciphertext = plaintext XOR key` — trivially broken if you can get one plaintext/ciphertext pair)
- Custom Feistel networks with wrong constants
- Substitution-permutation networks with wrong S-box sizes
- Modified AES with weakened rounds (e.g., 5 rounds instead of 10)

---

## 8. Mode-of-operation identification

Even after identifying the cipher, you need to identify the mode to assess security:

| Mode | Detection | Security notes |
|---|---|---|
| ECB | Each block encrypted independently, no IV, no chaining | **INSECURE** — leaks patterns. Flag P0 in any security review. |
| CBC | IV XORed with plaintext before encryption, ciphertext of block N becomes IV for block N+1 | OK if IV is unpredictable; weak if IV is fixed/countered |
| CTR | Counter encrypted, output XORed with plaintext | OK; nonce must be unique per key |
| GCM | CTR mode + GHASH polynomial multiplication in GF(2^128) | AEAD; provides authentication |
| CCM | CTR encryption + CBC-MAC | AEAD; used in 802.11i |
| OFB | Output of one block is the IV for the next | OK but slower than CTR |
| CFB | Ciphertext of one block is the IV for the next | OK |
| XTS | Tweakable block cipher; uses 2 keys, sector-based | Disk encryption only (AES-XTS for BitLocker, FileVault) |

**Detection of mode**:

- **No IV argument** → ECB (P0 finding)
- **IV chained as `(prev_ciphertext, current_plaintext)` XOR before encrypt** → CBC
- **Counter incremented between blocks, encrypted, XORed with plaintext** → CTR
- **Two output streams: ciphertext + tag (16 bytes)** → AEAD (GCM, CCM, OCB, or ChaCha20-Poly1305)
- **GF(2^128) multiply** (constant `0x87`, special 128-bit shifts) → GCM

---

## 9. The detection workflow

Run this sequence:

1. **Run entropy check on `.rodata`**: high-entropy `.rodata` (>7.5) over a >1KB range suggests encrypted key material or precomputed tables (S-boxes, etc.). Pick the high-entropy ranges for closer inspection.

2. **Scan `.rodata` for known constants**: write a Python script that searches the binary for the byte signatures of common ciphers' constants:

```python
SIGNATURES = {
    "AES_forward_sbox": bytes.fromhex("637c777bf26b6fc53001672bfed7ab76")[:16],
    "AES_inverse_sbox": bytes.fromhex("52096ad530653538bf40a39e81f3d7fb")[:16],
    "DES_sbox1_first":  bytes.fromhex("0e040d0110020f08"),  # 14 4 13 1 2 15 11 8
    "Blowfish_p_array": bytes.fromhex("886a3f24d308a3852e8a1913"),
    "ChaCha20_sigma":   b"expand 32-byte k",
    "Salsa20_sigma":    b"expand 32-byte k",  # variant
    "TEA_delta":        bytes.fromhex("b979379e"),
    "MD5_IV":           bytes.fromhex("0123456789abcdeffedcba9876543210"),
    "SHA1_IV":          bytes.fromhex("0123456789abcdeffedcba9876543210c3d2e1f0"),
    "SHA256_K_first":   bytes.fromhex("982f8a42"),
    "SHA512_K_first":   bytes.fromhex("22ae28d7982f8a42"),
    "SM3_IV":           bytes.fromhex("6f168073b9b21449d7422417000a08da"),
    "Camellia_Sigma1":  bytes.fromhex("8b90cc3b7f6609eab2"),
    "secp256k1_prime_tail": bytes.fromhex("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffc2f"),
    "Curve25519_prime":  bytes.fromhex("edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f"),
}
for name, sig in SIGNATURES.items():
    if sig in binary_bytes:
        print(f"MATCH: {name}")
```

3. **If constant match is found, verify with structure**: does the function calling the constant match the cipher's shape?
   - AES: 10/12/14 rounds with the `sub_bytes` + `shift_rows` + `mix_columns` + `add_round_key` pattern
   - SHA-256: 64-round compression function with `rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)` and similar
   - RC4: 256-byte array + swap loop

4. **If no constant match, check for library signatures**: if the binary has imports, check for OpenSSL/mbedTLS/libsodium/CNG exports. Use FLIRT/Function ID for stripped libraries.

5. **If still no match, the crypto is custom**: flag as `SUSPECTED custom crypto` for security review. Even if it implements a known algorithm, the lack of constants suggests it was implemented from scratch — review the algorithm by reading the disasm.

---

## 10. Reporting

The crypto identification section of the report should include:

1. **Algorithm(s) detected** with confidence (CONFIRMED if 2+ signals match; SUSPECTED if only one signal; HYPOTHESIS if pattern match only)
2. **Constants / signatures that matched** — list the specific byte sequence and offset in the binary
3. **Mode of operation** if applicable
4. **Key length inference** (e.g., AES-128 from round count)
5. **Library identification** if known (OpenSSL version, mbedTLS version, etc.)
6. **Security assessment** if applicable (e.g., ECB mode is P0, MD5 for security is P0, custom crypto is P0)
7. **Limitations** — couldn't verify mode statically, key not recovered, etc.
8. **Recommended next step** — typically dynamic capture of the key material via debugger, or submission of the binary to FLIRT signature matching

Example finding:

```
CONFIRMED: AES-128 in CBC mode.
Evidence:
- .rodata:0x4040 contains the AES forward S-box (verified bytes 63 7c 77 7b f2 6b 6f c5 ...)
- .rodata:0x4440 contains the AES inverse S-box (verified bytes 52 09 6a d5 30 36 a5 38 ...)
- .rodata:0x4840 contains the Rcon table (01 02 04 08 10 20 40 80 1b 36)
- .text:0x401000 calls sub_401200 (sub_bytes) 10 times in a loop → AES-128 round count
- .text:0x401050 contains the IV load: mov rax, [rbp+0x18] (the IV is the 2nd arg)
- .text:0x401080 does XOR before the AES_encrypt call: CBC mode

Mode: CBC with IV passed as 2nd argument (16 bytes).
Key length: 128 bits (10 rounds in cipher main loop).
Key not recovered statically — passed at runtime from caller.

To confirm: set a breakpoint at the AES_encrypt call at .text:0x401090; capture the key from the stack (typically arg 1) and the IV from arg 2; verify by encrypting a known plaintext with the captured key+IV using OpenSSL and comparing to the captured ciphertext.
```

That's the gold standard: cipher identified, mode identified, key length inferred, evidence cited, recommended dynamic capture described.
