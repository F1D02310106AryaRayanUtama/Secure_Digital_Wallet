"""
database.py - Manajemen database SQLite untuk Secure Digital Wallet
Semua data sensitif (saldo, transaksi) disimpan dalam bentuk terenkripsi.
"""

import sqlite3
import os
from encryption import encrypt_value, decrypt_value

DB_PATH = "assets/wallet.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = None  # Di-set oleh auth.py saat init


def get_connection():
    """Membuka koneksi ke database SQLite."""
    os.makedirs("assets", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Inisialisasi skema database.
    Membuat tabel users dan transactions jika belum ada.
    Setelah tabel dibuat, pastikan akun admin tersedia.
    """
    conn = get_connection()
    c = conn.cursor()

    # Tabel pengguna
    # role: 'admin' atau 'user'
    # pin_hash: SHA-256 hash PIN transaksi (NULL = belum set)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            pin_hash      TEXT,
            balance_enc   TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'user',
            created_at    TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    # Tabel transaksi: amount & memo dienkripsi AES
    # tx_type: 'transfer' atau 'topup'
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender      TEXT    NOT NULL,
            receiver    TEXT    NOT NULL,
            amount_enc  TEXT    NOT NULL,
            memo_enc    TEXT,
            tx_type     TEXT    NOT NULL DEFAULT 'transfer',
            timestamp   TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()

    # Pastikan akun admin sudah ada
    _ensure_admin()


def _ensure_admin():
    """
    Membuat akun admin bawaan jika belum ada.
    Username: admin | Password: admin123
    Admin tidak perlu PIN dan tidak memiliki saldo sendiri.
    """
    import hashlib
    salt = "secure_wallet_salt_v1"
    pwd_hash = hashlib.sha256((salt + "admin123").encode()).hexdigest()
    balance_enc = encrypt_value("0")

    conn = get_connection()
    c = conn.cursor()
    # INSERT OR IGNORE: hanya buat jika belum ada
    c.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, balance_enc, role)
        VALUES (?, ?, ?, 'admin')
    """, (ADMIN_USERNAME, pwd_hash, balance_enc))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  User Operations
# ─────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> bool:
    """
    Mendaftarkan user baru dengan saldo 0.
    PIN belum di-set (NULL) — akan di-set di halaman setup PIN pasca register.
    Returns True jika berhasil, False jika username sudah ada.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        balance_enc = encrypt_value("0")
        c.execute(
            "INSERT INTO users (username, password_hash, balance_enc, role) VALUES (?, ?, ?, 'user')",
            (username, password_hash, balance_enc)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user(username: str):
    """Mengambil data user berdasarkan username. Returns Row atau None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_role(username: str) -> str:
    """Mengembalikan role user: 'admin' atau 'user'."""
    user = get_user(username)
    if user is None:
        return "user"
    return user["role"]


def get_balance(username: str) -> float:
    """Mengambil saldo user (dekripsi AES secara otomatis)."""
    user = get_user(username)
    if user is None:
        return 0.0
    return float(decrypt_value(user["balance_enc"]))


def update_balance(username: str, new_balance: float):
    """Memperbarui saldo user (enkripsi AES otomatis sebelum simpan)."""
    conn = get_connection()
    c = conn.cursor()
    balance_enc = encrypt_value(str(new_balance))
    c.execute(
        "UPDATE users SET balance_enc = ? WHERE username = ?",
        (balance_enc, username)
    )
    conn.commit()
    conn.close()


def set_pin(username: str, pin_hash: str):
    """Menyimpan hash PIN transaksi user."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET pin_hash = ? WHERE username = ?",
              (pin_hash, username))
    conn.commit()
    conn.close()


def get_pin_hash(username: str):
    """Mengambil pin_hash user. Returns None jika belum di-set."""
    user = get_user(username)
    if user is None:
        return None
    return user["pin_hash"]


def has_pin(username: str) -> bool:
    """Cek apakah user sudah memiliki PIN."""
    ph = get_pin_hash(username)
    return ph is not None and ph != ""


def get_all_usernames() -> list:
    """Mengambil daftar semua username terdaftar (termasuk admin)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    rows = c.fetchall()
    conn.close()
    return [r["username"] for r in rows]


def get_all_regular_users() -> list:
    """Mengambil daftar username dengan role 'user' saja."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE role = 'user'")
    rows = c.fetchall()
    conn.close()
    return [r["username"] for r in rows]


# ─────────────────────────────────────────────
#  Transaction Operations
# ─────────────────────────────────────────────

def record_transaction(sender: str, receiver: str, amount: float,
                       memo: str = "", tx_type: str = "transfer"):
    """
    Menyimpan catatan transaksi ke database.
    Amount dan memo dienkripsi AES.
    tx_type: 'transfer' atau 'topup'
    """
    conn = get_connection()
    c = conn.cursor()
    amount_enc = encrypt_value(str(amount))
    memo_enc   = encrypt_value(memo) if memo else encrypt_value("-")
    c.execute(
        """INSERT INTO transactions
           (sender, receiver, amount_enc, memo_enc, tx_type)
           VALUES (?, ?, ?, ?, ?)""",
        (sender, receiver, amount_enc, memo_enc, tx_type)
    )
    conn.commit()
    conn.close()


def get_transactions(username: str) -> list:
    """
    Mengambil semua transaksi yang melibatkan username tertentu.
    Dekripsi amount dan memo secara otomatis.
    Returns: list of dict
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM transactions
        WHERE sender = ? OR receiver = ?
        ORDER BY timestamp DESC
        """,
        (username, username)
    )
    rows = c.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id":        row["id"],
            "sender":    row["sender"],
            "receiver":  row["receiver"],
            "amount":    float(decrypt_value(row["amount_enc"])),
            "memo":      decrypt_value(row["memo_enc"]),
            "tx_type":   row["tx_type"],
            "timestamp": row["timestamp"],
        })
    return result


def get_all_transactions() -> list:
    """Mengambil SEMUA transaksi (dipakai oleh admin)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id":        row["id"],
            "sender":    row["sender"],
            "receiver":  row["receiver"],
            "amount":    float(decrypt_value(row["amount_enc"])),
            "memo":      decrypt_value(row["memo_enc"]),
            "tx_type":   row["tx_type"],
            "timestamp": row["timestamp"],
        })
    return result
