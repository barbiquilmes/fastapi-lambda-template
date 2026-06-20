# 07 — How HTTPS / TLS Works

## The handshake

```
Browser                                        Server
   │                                              │
   │  1. "Hello"                                  │
   │     + algorithms I support:                  │
   │       [RSA, ECDHE, AES-256, ...]             │
   │ ─────────────────────────────────────────►   │
   │                                              │
   │  2. "We'll use ECDHE + AES-256"              │
   │     + certificate (proof I am who I say)     │
   │     + public key                             │
   │ ◄─────────────────────────────────────────   │
   │                                              │
   [Browser has: public key]      [Server has: public key + private key]
   │                                              │
   │  3. Browser verifies the certificate         │
   │     (signed by a trusted third party? ✓)    │
   │                                              │
   │  4. Browser generates session key "abc123"   │
   │     encrypts it with public key → "£$@#*&"  │
   │     sends "£$@#*&"                           │
   │ ─────────────────────────────────────────►   │
   │                                              │
   [Browser has: "abc123"]        [Server decrypts "£$@#*&" with private key]
                                  [Server now has: "abc123"]
   │                                              │
   │  === BOTH HAVE "abc123" ===                  │
   │                                              │
   │  5. "Ready" (encrypted with "abc123")        │
   │ ◄─────────────────────────────────────────   │
   │                                              │
   │  === all traffic encrypted ===               │
   │                                              │
   │  Browser encrypts with "abc123" → "£$@#*&"  │
   │ ─────────────────────────────────────────►   │
   │                          decrypts with "abc123"
   │                                              │
   │  Server encrypts with "abc123" → "*&^%£@!"  │
   │ ◄─────────────────────────────────────────   │
   │  decrypts with "abc123"                      │
```

## Key concepts

- **Asymmetric encryption** (public/private key): used only during the handshake to securely share the session key
  - Public key → encrypts only
  - Private key → decrypts only
  - They are mathematical opposites

- **Symmetric encryption** (session key): used for all traffic after the handshake
  - Both sides have the same key
  - Both can encrypt and decrypt

- **Certificate**: signed by a trusted third party (Let's Encrypt, DigiCert) — proves the public key genuinely belongs to the domain

- **Cipher suite negotiation**: the browser sends the algorithms it supports, the server picks the best one they have in common

## Why the attacker can't intercept the session key

The browser never sends "abc123" directly — it sends it encrypted with the public key. Only the server can decrypt it (it has the private key). The private key never travels over the network.

---

## How the certificate works in detail

### Step 1 — CloudFront requests its certificate from Let's Encrypt (once, not on each connection)

```
CloudFront → Let's Encrypt:
  "I want a certificate for cloudfront.net"
  "here is my public key CF"

Let's Encrypt:
  verifies that CloudFront controls cloudfront.net
  (asks it to place a file on the domain to prove it)

  signs: encrypt("cloudfront.net has public key CF", private key LE)
  → result: certificate

  sends the certificate to CloudFront
```

### What CloudFront has afterwards

```
  private key CF  (it generated itself, never shares it)
  certificate     (given by Let's Encrypt)
```

### Step 2 — Every time a browser connects

```
CloudFront → Browser:
  sends the certificate:
    "cloudfront.net has public key CF" + signature(private key LE)

Browser:
  verifies the signature with public key LE (pre-installed in the OS)
  → confirms that public key CF genuinely belongs to cloudfront.net
  → uses public key CF to encrypt the session key
```

### Is the LE public key tied to the CF public key?

Not directly. What connects them is the certificate:

```
certificate = "cloudfront.net has public key CF" + signature(private key LE)
```

Let's Encrypt is saying: "I guarantee that this public key CF belongs to cloudfront.net".
That guarantee is signed with its private key LE. The browser verifies it with the public key LE.

```
public key LE → verifies the signature → confirms public key CF is legitimate
public key CF → encrypts the session key → only CloudFront can decrypt it
```

They are two independent pairs, but the certificate connects them.

### Why the attacker can't do anything at each step

```
  private key LE  → never leaves Let's Encrypt → cannot forge certificates
  private key CF  → never leaves CloudFront    → cannot decrypt the session key
  session key     → never travels in plaintext → cannot read traffic
```

The security of the entire system depends on private keys never leaving the server that generated them.

---

## What an attacker can and cannot do — step by step

```
STEP 1 — Browser says "hello, I want to connect"

  Browser → Server: "hello" + algorithms I support

  ATTACKER: ✓ can intercept and read this message
            ✗ useless — no sensitive information here
```

```
STEP 2 — Server sends certificate + public key CF

  Server → Browser: certificate + public key CF

  ATTACKER: ✓ can intercept and read the certificate (travels in plaintext)
            ✓ can see the public key CF
            ✗ cannot modify the certificate → would break LE's signature
            ✗ cannot create a fake certificate for cloudfront.net
              → would need private key LE, which never leaves Let's Encrypt
```

```
STEP 3 — Browser verifies the certificate

  Browser: decrypts signature with public key LE (pre-installed)
           match? ✓ → trusts public key CF

  ATTACKER: not involved in this step
            ✗ cannot trick the browser with a fake certificate
              → browser would detect it and show ⚠️
```

```
STEP 4 — Browser encrypts and sends the session key

  Browser: generates "abc123"
           encrypts with public key CF → "£$@#*&"
           sends "£$@#*&"

  ATTACKER: ✓ can intercept "£$@#*&"
            ✗ cannot decrypt it → would need private key CF
              which never leaves CloudFront
            ✗ never learns "abc123"
```

```
STEP 5 — Server decrypts the session key

  Server: decrypts "£$@#*&" with private key CF → "abc123"

  ATTACKER: not involved
            ✗ doesn't have private key CF → cannot do the same
```

```
STEP 6 — All subsequent traffic (login, items, etc)

  Browser ↔ Server: all encrypted with "abc123"

  ATTACKER: ✓ can intercept all packets
            ✓ sees: "£$@#*&^%!£$@#*&^%!£$@#*&^%!"
            ✗ without "abc123" it's useless gibberish
            ✗ cannot read username, password, tokens, anything
```

```
FINAL SUMMARY:

  To break the system the attacker would need:
    private key CF  → never leaves CloudFront      ✗
    private key LE  → never leaves Let's Encrypt   ✗

  Without those two keys → completely blocked at every step.
```
