"""
encryption.py - Modul kriptografi untuk Secure Digital Wallet
Mengimplementasikan AES-256 untuk enkripsi data dan RSA untuk pengamanan AES key.
"""

import os
import base64
import json
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


# ─────────────────────────────────────────────
#  RSA Key Management
# ─────────────────────────────────────────────

RSA_KEY_FILE = "assets/rsa_keys.json"

def generate_rsa_keys():
    """
    Generate pasangan RSA key (public + private) 2048-bit.
    Key disimpan ke file JSON agar persisten antar sesi.
    """
    key = RSA.generate(2048)
    private_key = key.export_key().decode()
    public_key = key.publickey().export_key().decode()

    os.makedirs("assets", exist_ok=True)
    with open(RSA_KEY_FILE, "w") as f:
        json.dump({"private": private_key, "public": public_key}, f)

    return public_key, private_key


def load_rsa_keys():
    """
    Memuat RSA key dari file. Jika belum ada, generate key baru.
    Returns: (public_key_str, private_key_str)
    """
    if not os.path.exists(RSA_KEY_FILE):
        return generate_rsa_keys()

    with open(RSA_KEY_FILE, "r") as f:
        keys = json.load(f)
    return keys["public"], keys["private"]


def rsa_encrypt_aes_key(aes_key: bytes, public_key_str: str) -> str:
    """
    Mengenkripsi AES key menggunakan RSA public key (OAEP padding).
    Returns: base64-encoded encrypted AES key
    """
    public_key = RSA.import_key(public_key_str)
    cipher_rsa = PKCS1_OAEP.new(public_key)
    encrypted_key = cipher_rsa.encrypt(aes_key)
    return base64.b64encode(encrypted_key).decode()


def rsa_decrypt_aes_key(encrypted_key_b64: str, private_key_str: str) -> bytes:
    """
    Mendekripsi AES key menggunakan RSA private key.
    Returns: bytes AES key
    """
    private_key = RSA.import_key(private_key_str)
    cipher_rsa = PKCS1_OAEP.new(private_key)
    encrypted_key = base64.b64decode(encrypted_key_b64)
    return cipher_rsa.decrypt(encrypted_key)


# ─────────────────────────────────────────────
#  AES Encryption / Decryption
# ─────────────────────────────────────────────

def generate_aes_key() -> bytes:
    """Generate random 256-bit (32 byte) AES key."""
    return get_random_bytes(32)


def aes_encrypt(plaintext: str, aes_key: bytes) -> str:
    """
    Mengenkripsi string plaintext dengan AES-256 CBC.
    IV acak di-prefix ke ciphertext.
    Returns: base64-encoded (IV + ciphertext)
    """
    iv = get_random_bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode()


def aes_decrypt(encrypted_b64: str, aes_key: bytes) -> str:
    """
    Mendekripsi data yang dienkripsi dengan aes_encrypt().
    Returns: plaintext string
    """
    raw = base64.b64decode(encrypted_b64)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode()


# ─────────────────────────────────────────────
#  Wallet-level AES key (satu kunci global)
# ─────────────────────────────────────────────

AES_KEY_FILE = "assets/aes_key.enc"

def get_or_create_wallet_aes_key() -> bytes:
    """
    Mengambil atau membuat AES key global untuk wallet.
    AES key dienkripsi dengan RSA public key sebelum disimpan.
    Returns: raw bytes AES key
    """
    public_key, private_key = load_rsa_keys()
    os.makedirs("assets", exist_ok=True)

    if not os.path.exists(AES_KEY_FILE):
        # Buat AES key baru dan enkripsi dengan RSA
        aes_key = generate_aes_key()
        encrypted = rsa_encrypt_aes_key(aes_key, public_key)
        with open(AES_KEY_FILE, "w") as f:
            f.write(encrypted)
        return aes_key

    # Baca dan dekripsi AES key yang tersimpan
    with open(AES_KEY_FILE, "r") as f:
        encrypted = f.read()
    return rsa_decrypt_aes_key(encrypted, private_key)


def encrypt_value(value: str) -> str:
    """Helper: enkripsi nilai (saldo / data transaksi) menggunakan AES wallet key."""
    aes_key = get_or_create_wallet_aes_key()
    return aes_encrypt(value, aes_key)


def decrypt_value(encrypted: str) -> str:
    """Helper: dekripsi nilai yang dienkripsi dengan encrypt_value()."""
    aes_key = get_or_create_wallet_aes_key()
    return aes_decrypt(encrypted, aes_key)
