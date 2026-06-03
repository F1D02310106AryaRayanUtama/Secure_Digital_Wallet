"""
transaction.py - Logika transaksi transfer dan top up saldo
"""

from database import (get_balance, update_balance, record_transaction,
                      get_user, get_user_role)


def transfer(sender: str, receiver: str, amount: float,
             memo: str = "") -> tuple:
    """
    Transfer saldo dari sender ke receiver.
    PIN sudah diverifikasi di layer GUI sebelum memanggil ini.
    Returns: (success: bool, message: str)
    """
    if sender == receiver:
        return False, "Tidak dapat mengirim ke diri sendiri."
    if get_user(receiver) is None:
        return False, f"Pengguna '{receiver}' tidak ditemukan."
    if get_user_role(receiver) == "admin":
        return False, "Tidak dapat transfer ke akun admin."
    if amount <= 0:
        return False, "Jumlah transfer harus lebih dari 0."
    if amount > 1_000_000_000:
        return False, "Jumlah transfer melebihi batas maksimum (Rp 1 Miliar)."

    sender_balance = get_balance(sender)
    if sender_balance < amount:
        return False, f"Saldo tidak cukup. Saldo Anda: Rp {sender_balance:,.0f}"

    receiver_balance = get_balance(receiver)
    update_balance(sender,   sender_balance - amount)
    update_balance(receiver, receiver_balance + amount)
    record_transaction(sender, receiver, amount,
                       memo or "Transfer", tx_type="transfer")

    return True, f"Transfer Rp {amount:,.0f} ke '@{receiver}' berhasil!"


def topup(admin_username: str, target_user: str,
          amount: float, memo: str = "") -> tuple:
    """
    Admin men-top-up saldo user tertentu.
    Returns: (success: bool, message: str)
    """
    if get_user_role(admin_username) != "admin":
        return False, "Hanya admin yang dapat melakukan top up."
    if get_user(target_user) is None:
        return False, f"Pengguna '{target_user}' tidak ditemukan."
    if get_user_role(target_user) == "admin":
        return False, "Tidak dapat top up ke akun admin."
    if amount <= 0:
        return False, "Jumlah top up harus lebih dari 0."
    if amount > 100_000_000_000:
        return False, "Jumlah top up melebihi batas maksimum."

    current = get_balance(target_user)
    update_balance(target_user, current + amount)
    record_transaction(admin_username, target_user, amount,
                       memo or "Top Up oleh Admin", tx_type="topup")

    return True, f"Top up Rp {amount:,.0f} ke '@{target_user}' berhasil!"
