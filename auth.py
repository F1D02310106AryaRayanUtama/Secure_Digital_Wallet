"""
auth.py - Autentikasi pengguna untuk Secure Digital Wallet
Menggunakan SHA-256 untuk hashing password dan PIN.
"""

import hashlib
from database import create_user, get_user, set_pin, get_pin_hash


def hash_password(password: str) -> str:
    """
    SHA-256 hash dari password dengan salt tetap.
    """
    salt = "secure_wallet_salt_v1"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def hash_pin(pin: str) -> str:
    """
    SHA-256 hash dari PIN dengan salt berbeda dari password.
    """
    salt = "secure_wallet_pin_salt_v1"
    return hashlib.sha256((salt + pin).encode()).hexdigest()


def register(username: str, password: str) -> tuple:
    """
    Mendaftarkan pengguna baru (tanpa saldo awal, tanpa PIN dulu).
    PIN di-set terpisah setelah register berhasil.
    Returns: (success: bool, message: str)
    """
    if len(username) < 3:
        return False, "Username minimal 3 karakter."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    if not username.isalnum():
        return False, "Username hanya boleh berisi huruf dan angka."
    if username.lower() == "admin":
        return False, "Username 'admin' sudah digunakan sistem."

    password_hash = hash_password(password)
    success = create_user(username, password_hash)

    if success:
        return True, f"Akun '{username}' berhasil dibuat!"
    else:
        return False, f"Username '{username}' sudah digunakan."


def setup_pin(username: str, pin: str, pin_confirm: str) -> tuple:
    """
    Menyimpan PIN baru untuk user.
    Returns: (success: bool, message: str)
    """
    if len(pin) < 4:
        return False, "PIN minimal 4 digit."
    if not pin.isdigit():
        return False, "PIN hanya boleh berisi angka."
    if pin != pin_confirm:
        return False, "Konfirmasi PIN tidak cocok."

    pin_hash = hash_pin(pin)
    set_pin(username, pin_hash)
    return True, "PIN berhasil disimpan."


def verify_pin(username: str, pin: str) -> bool:
    """
    Memverifikasi PIN transaksi.
    Returns True jika PIN benar.
    """
    stored = get_pin_hash(username)
    if stored is None:
        return False
    return stored == hash_pin(pin)


def login(username: str, password: str) -> tuple:
    """
    Memverifikasi kredensial login.
    Returns: (success: bool, message: str)
    """
    if not username or not password:
        return False, "Username dan password tidak boleh kosong."

    user = get_user(username)
    if user is None:
        return False, "Username tidak ditemukan."

    if user["password_hash"] != hash_password(password):
        return False, "Password salah."

    return True, "Login berhasil!"
