"""Encrypt or decrypt the book's exercise code for the website.

The published files in book/enc/ are AES-256-GCM ciphertexts; the key is derived from the
password with PBKDF2-HMAC-SHA256. The page decrypts them in the reader's browser.

  python3 tools/book_crypt.py encrypt SRC_DIR      # SRC_DIR holds py/ and matlab/
  python3 tools/book_crypt.py decrypt OUT_DIR      # recover the plain files
The password is read from the BOOK_PASSWORD environment variable or asked for.
"""
import base64, getpass, json, os, sys
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ENC = Path(__file__).resolve().parent.parent / "book" / "enc"
ITER = 310_000
CHECK = b"heavy-tails-book-ok"

def key(password, salt, it=ITER):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(password.encode("utf-8"))

def password():
    return os.environ.get("BOOK_PASSWORD") or getpass.getpass("Book password: ")

def seal(k, data):
    iv = os.urandom(12)
    return iv + AESGCM(k).encrypt(iv, data, None)

def encrypt(src):
    src = Path(src); pw = password(); salt = os.urandom(16); k = key(pw, salt)
    ENC.mkdir(parents=True, exist_ok=True)
    for old in ENC.glob("*.bin"): old.unlink()
    files = []
    for sub in ("py", "matlab"):
        for f in sorted((src / sub).iterdir()):
            if f.suffix not in (".py", ".m"): continue
            name = f"{sub}__{f.name}.bin"
            (ENC / name).write_bytes(seal(k, f.read_bytes()))
            files.append(f"{sub}/{f.name}")
    manifest = {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "cipher": "AES-256-GCM",
                "salt": base64.b64encode(salt).decode(), "check": base64.b64encode(seal(k, CHECK)).decode(), "files": files}
    (ENC / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"encrypted {len(files)} files into {ENC}")

def decrypt(out):
    m = json.loads((ENC / "manifest.json").read_text()); k = key(password(), base64.b64decode(m["salt"]), m["iter"])
    def opn(b): return AESGCM(k).decrypt(b[:12], b[12:], None)
    opn(base64.b64decode(m["check"]))  # raises if the password is wrong
    out = Path(out)
    for rel in m["files"]:
        sub, name = rel.split("/")
        (out / sub).mkdir(parents=True, exist_ok=True)
        (out / sub / name).write_bytes(opn((ENC / f"{sub}__{name}.bin").read_bytes()))
    print(f"decrypted {len(m['files'])} files into {out}")

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("encrypt", "decrypt"): sys.exit(__doc__)
    (encrypt if sys.argv[1] == "encrypt" else decrypt)(sys.argv[2])
