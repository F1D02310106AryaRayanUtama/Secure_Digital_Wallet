"""
main.py - Secure Digital Wallet
Aplikasi simulasi dompet digital dengan kriptografi AES & RSA.
Jalankan: python main.py

Fitur:
  - Login / Register (2 role: admin & user)
  - Setup PIN pasca register (wajib sebelum transaksi)
  - Dashboard User  : saldo, transfer, riwayat, info kriptografi
  - Dashboard Admin : top up saldo ke user, riwayat semua transaksi
  - Konfirmasi PIN sebelum setiap transaksi / top up
  - Auto-refresh data saat login akun baru (tidak ada data sisa)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import (init_db, get_balance, get_all_usernames,
                      get_all_regular_users, get_user_role, has_pin)
from auth import register, login, setup_pin, verify_pin, hash_password
from transaction import transfer, topup
from database import get_transactions, get_all_transactions
from encryption import load_rsa_keys, get_or_create_wallet_aes_key

# ─────────────────────────────────────────────
#  Palet warna & font
# ─────────────────────────────────────────────
C = {
    "bg":       "#0D1117",
    "panel":    "#161B22",
    "sidebar":  "#0D1117",
    "border":   "#30363D",
    "accent":   "#2563EB",
    "accent2":  "#1D4ED8",
    "success":  "#10B981",
    "danger":   "#EF4444",
    "warning":  "#F59E0B",
    "text":     "#E6EDF3",
    "muted":    "#8B949E",
    "hi":       "#21262D",
    "gold":     "#F0B429",
    "inp":      "#0D1117",
    "admin":    "#7C3AED",   # ungu untuk admin
    "admin2":   "#6D28D9",
}
F = {
    "title": ("Consolas", 22, "bold"),
    "head":  ("Consolas", 14, "bold"),
    "sub":   ("Consolas", 11, "bold"),
    "body":  ("Consolas", 10),
    "small": ("Consolas", 9),
    "mono":  ("Courier New", 9),
    "badge": ("Consolas", 8, "bold"),
}


# ─────────────────────────────────────────────
#  Widget helpers
# ─────────────────────────────────────────────
def entry(parent, show=None, width=30, **kw):
    return tk.Entry(parent, show=show, width=width,
                    bg=C["inp"], fg=C["text"],
                    insertbackground=C["accent"],
                    relief="flat", font=F["body"],
                    highlightthickness=1,
                    highlightcolor=C["accent"],
                    highlightbackground=C["border"], **kw)


def btn(parent, text, cmd, color=None, tc=C["text"], width=18, pady=8):
    bg = color or C["accent"]
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=tc,
                  activebackground=C["accent2"],
                  activeforeground=C["text"],
                  relief="flat", font=F["sub"],
                  width=width, pady=pady,
                  cursor="hand2", bd=0)
    b.bind("<Enter>", lambda e: b.config(bg=_darken(bg)))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def _darken(hex_color):
    """Sedikit menggelapkan warna tombol saat hover."""
    mapping = {
        C["accent"]:  C["accent2"],
        C["accent2"]: C["accent2"],
        C["admin"]:   C["admin2"],
        C["admin2"]:  C["admin2"],
        C["danger"]:  "#DC2626",
        C["success"]: "#059669",
        C["hi"]:      "#2D333B",
    }
    return mapping.get(hex_color, hex_color)


def card(parent, **kw):
    return tk.Frame(parent, bg=C["panel"],
                    highlightthickness=1,
                    highlightbackground=C["border"], **kw)


def sep(parent, bg=None):
    return tk.Frame(parent, height=1, bg=bg or C["border"])


def lbl(parent, text, fg=None, font=None, bg=None, **kw):
    return tk.Label(parent, text=text,
                    fg=fg or C["text"],
                    bg=bg or C["panel"],
                    font=font or F["body"], **kw)


# ─────────────────────────────────────────────
#  Dialog PIN sederhana
# ─────────────────────────────────────────────
class PinDialog(tk.Toplevel):
    """
    Modal dialog untuk memasukkan PIN transaksi.
    Mengembalikan PIN via self.result (None = batal).
    """
    def __init__(self, parent, title="Konfirmasi PIN"):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()

        # Posisi di tengah parent
        self.geometry("340x240")
        self._center(parent)

        tk.Label(self, text="🔒", font=("Segoe UI Emoji", 28),
                 bg=C["bg"]).pack(pady=(20, 4))
        tk.Label(self, text=title,
                 bg=C["bg"], fg=C["text"],
                 font=F["sub"]).pack()
        tk.Label(self, text="Masukkan PIN transaksi Anda",
                 bg=C["bg"], fg=C["muted"],
                 font=F["small"]).pack(pady=(2, 12))

        self._pin_var = tk.StringVar()
        pin_entry = tk.Entry(self, show="●", width=16,
                             textvariable=self._pin_var,
                             bg=C["inp"], fg=C["text"],
                             insertbackground=C["accent"],
                             relief="flat", font=F["sub"],
                             justify="center",
                             highlightthickness=1,
                             highlightcolor=C["accent"],
                             highlightbackground=C["border"])
        pin_entry.pack(ipady=8, padx=40, fill="x")
        pin_entry.focus_set()
        pin_entry.bind("<Return>", lambda e: self._confirm())

        row = tk.Frame(self, bg=C["bg"])
        row.pack(pady=16, fill="x", padx=40)
        btn(row, "Batal", self._cancel,
            color=C["hi"], width=10).pack(side="left")
        btn(row, "Konfirmasi", self._confirm,
            width=12).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _center(self, parent):
        parent.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 170
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 120
        self.geometry(f"+{px}+{py}")

    def _confirm(self):
        self.result = self._pin_var.get()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ─────────────────────────────────────────────
#  Aplikasi utama
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure Digital Wallet")
        self.geometry("1060x700")
        self.minsize(920, 620)
        self.configure(bg=C["bg"])

        self.current_user = None   # username yang sedang login
        self.current_role = None   # 'admin' / 'user'
        self._pages = {}

        init_db()
        get_or_create_wallet_aes_key()

        self._wrap = tk.Frame(self, bg=C["bg"])
        self._wrap.pack(fill="both", expand=True)

        self._build_login()
        self._build_register()
        self._build_setup_pin()       # Halaman setup PIN pasca register
        self._build_user_dashboard()
        self._build_admin_dashboard()

        self._show("login")

    # ── Routing ───────────────────────────────
    def _show(self, page):
        for f in self._pages.values():
            f.pack_forget()
        self._pages[page].pack(fill="both", expand=True)

    # ─────────────────────────────────────────
    #  LOGIN
    # ─────────────────────────────────────────
    def _build_login(self):
        page = tk.Frame(self._wrap, bg=C["bg"])
        self._pages["login"] = page

        # Branding panel kiri
        left = tk.Frame(page, bg=C["accent"], width=360)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(left, bg=C["accent"]).pack(expand=True)
        tk.Label(left, text="🔐", font=("Segoe UI Emoji", 52),
                 bg=C["accent"], fg="white").pack(pady=(0, 10))
        tk.Label(left, text="SECURE\nDIGITAL WALLET",
                 font=("Consolas", 20, "bold"),
                 bg=C["accent"], fg="white",
                 justify="center").pack()
        tk.Label(left,
                 text="Keamanan transaksi Anda\ndengan AES-256 & RSA-2048",
                 font=F["body"], bg=C["accent"],
                 fg="#BFDBFE", justify="center").pack(pady=(6, 0))
        tk.Frame(left, bg=C["accent"]).pack(expand=True)
        bf = tk.Frame(left, bg=C["accent2"], padx=10, pady=6)
        bf.pack(pady=(0, 30))
        for t in ["SHA-256  Password Hashing",
                  "AES-256  Data Encryption",
                  "RSA-2048 Key Protection",
                  "PIN      Transaction Guard"]:
            tk.Label(bf, text=f"✓  {t}",
                     bg=C["accent2"], fg="#DBEAFE",
                     font=F["small"]).pack(anchor="w")

        # Form kanan
        right = tk.Frame(page, bg=C["bg"])
        right.pack(side="right", fill="both", expand=True)
        tk.Frame(right, bg=C["bg"]).pack(expand=True)

        fc = card(right, padx=44, pady=44)
        fc.pack(padx=50)

        lbl(fc, "Selamat Datang",
            fg=C["muted"], font=F["small"]).pack(anchor="w")
        lbl(fc, "Masuk ke Akun Anda",
            fg=C["text"], font=F["head"]).pack(anchor="w", pady=(0, 22))

        lbl(fc, "USERNAME", fg=C["muted"], font=F["badge"]).pack(anchor="w")
        self._lu = entry(fc, width=34)
        self._lu.pack(fill="x", pady=(4, 12), ipady=8, padx=2)

        lbl(fc, "PASSWORD", fg=C["muted"], font=F["badge"]).pack(anchor="w")
        self._lp = entry(fc, show="●", width=34)
        self._lp.pack(fill="x", pady=(4, 20), ipady=8, padx=2)
        self._lp.bind("<Return>", lambda e: self._do_login())

        btn(fc, "  MASUK  →", self._do_login,
            width=34, pady=10).pack(fill="x", padx=2)
        sep(fc).pack(fill="x", pady=18)
        lbl(fc, "Belum punya akun?",
            fg=C["muted"], font=F["small"]).pack()
        tk.Button(fc, text="Daftar Sekarang",
                  command=lambda: self._show("register"),
                  bg=C["panel"], fg=C["accent"],
                  font=F["sub"], relief="flat",
                  cursor="hand2", bd=0).pack(pady=4)

        tk.Frame(right, bg=C["bg"]).pack(expand=True)

    def _do_login(self):
        username = self._lu.get().strip()
        password = self._lp.get()
        ok, msg = login(username, password)
        if not ok:
            messagebox.showerror("Login Gagal", msg)
            return

        self.current_user = username
        self.current_role = get_user_role(username)

        # Bersihkan field
        self._lu.delete(0, "end")
        self._lp.delete(0, "end")

        if self.current_role == "admin":
            self._enter_admin_dashboard()
        else:
            self._enter_user_dashboard()

    # ─────────────────────────────────────────
    #  REGISTER
    # ─────────────────────────────────────────
    def _build_register(self):
        page = tk.Frame(self._wrap, bg=C["bg"])
        self._pages["register"] = page

        tk.Frame(page, bg=C["bg"]).pack(expand=True)
        c = card(page, padx=50, pady=40)
        c.pack()

        # Header
        hf = tk.Frame(c, bg=C["panel"])
        hf.pack(fill="x", pady=(0, 20))
        tk.Label(hf, text="👤", font=("Segoe UI Emoji", 26),
                 bg=C["panel"]).pack(side="left", padx=(0, 10))
        tf = tk.Frame(hf, bg=C["panel"])
        tf.pack(side="left")
        lbl(tf, "Buat Akun Baru",
            fg=C["text"], font=F["head"]).pack(anchor="w")
        lbl(tf, "Saldo awal Rp 0  —  Top up dari Admin",
            fg=C["muted"], font=F["small"]).pack(anchor="w")

        sep(c).pack(fill="x", pady=(0, 18))

        def fld(label, show=None):
            lbl(c, label, fg=C["muted"],
                font=F["badge"]).pack(anchor="w", pady=(8, 2))
            e = entry(c, show=show, width=40)
            e.pack(fill="x", ipady=8, padx=2)
            return e

        self._ru  = fld("USERNAME")
        self._rp  = fld("PASSWORD", show="●")
        self._rp2 = fld("KONFIRMASI PASSWORD", show="●")
        lbl(c, "* Password min. 6 karakter  |  Username hanya huruf & angka",
            fg=C["muted"], font=F["small"]).pack(anchor="w", pady=(6, 0))

        sep(c).pack(fill="x", pady=18)
        row = tk.Frame(c, bg=C["panel"])
        row.pack(fill="x")
        btn(row, "← Kembali",
            lambda: self._show("login"),
            color=C["hi"], width=14).pack(side="left")
        btn(row, "DAFTAR →",
            self._do_register, width=14).pack(side="right")

        tk.Frame(page, bg=C["bg"]).pack(expand=True)

    def _do_register(self):
        u  = self._ru.get().strip()
        p  = self._rp.get()
        p2 = self._rp2.get()

        if p != p2:
            messagebox.showerror("Error", "Konfirmasi password tidak cocok.")
            return

        ok, msg = register(u, p)
        if ok:
            # Simpan username sementara untuk setup PIN
            self._pending_pin_user = u
            messagebox.showinfo("Berhasil", msg + "\n\nSelanjutnya buat PIN transaksi Anda.")
            for e in [self._ru, self._rp, self._rp2]:
                e.delete(0, "end")
            self._show("setup_pin")
        else:
            messagebox.showerror("Gagal", msg)

    # ─────────────────────────────────────────
    #  SETUP PIN (pasca register)
    # ─────────────────────────────────────────
    def _build_setup_pin(self):
        page = tk.Frame(self._wrap, bg=C["bg"])
        self._pages["setup_pin"] = page

        tk.Frame(page, bg=C["bg"]).pack(expand=True)
        c = card(page, padx=50, pady=44)
        c.pack()

        tk.Label(c, text="🔑", font=("Segoe UI Emoji", 36),
                 bg=C["panel"]).pack(pady=(0, 8))
        lbl(c, "Buat PIN Transaksi",
            fg=C["text"], font=F["head"]).pack()
        lbl(c, "PIN digunakan untuk konfirmasi setiap transaksi",
            fg=C["muted"], font=F["small"]).pack(pady=(2, 18))
        sep(c).pack(fill="x", pady=(0, 18))

        def fld(label, show="●"):
            lbl(c, label, fg=C["muted"],
                font=F["badge"]).pack(anchor="w", pady=(8, 2))
            e = entry(c, show=show, width=30)
            e.pack(fill="x", ipady=8, padx=2)
            return e

        self._sp1 = fld("PIN BARU  (min. 4 digit angka)")
        self._sp2 = fld("KONFIRMASI PIN")
        lbl(c, "* Gunakan angka saja, contoh: 1234",
            fg=C["muted"], font=F["small"]).pack(anchor="w", pady=(6, 0))

        sep(c).pack(fill="x", pady=18)
        btn(c, "SIMPAN PIN  →",
            self._do_setup_pin, width=30,
            pady=10).pack(fill="x", padx=2)

        tk.Frame(page, bg=C["bg"]).pack(expand=True)

    def _do_setup_pin(self):
        pin  = self._sp1.get()
        pin2 = self._sp2.get()
        username = getattr(self, "_pending_pin_user", None)

        if not username:
            messagebox.showerror("Error", "Sesi tidak valid, silakan daftar ulang.")
            self._show("login")
            return

        ok, msg = setup_pin(username, pin, pin2)
        if ok:
            messagebox.showinfo("PIN Tersimpan",
                                f"{msg}\n\nSilakan login dengan akun Anda.")
            self._sp1.delete(0, "end")
            self._sp2.delete(0, "end")
            self._pending_pin_user = None
            self._show("login")
        else:
            messagebox.showerror("Gagal", msg)

    # ─────────────────────────────────────────
    #  USER DASHBOARD
    # ─────────────────────────────────────────
    def _build_user_dashboard(self):
        page = tk.Frame(self._wrap, bg=C["bg"])
        self._pages["user_dash"] = page

        # Navbar
        nav = tk.Frame(page, bg=C["panel"], height=52,
                       highlightthickness=1,
                       highlightbackground=C["border"])
        nav.pack(fill="x")
        nav.pack_propagate(False)
        tk.Label(nav, text="🔐  Secure Digital Wallet",
                 bg=C["panel"], fg=C["text"],
                 font=F["head"]).pack(side="left", padx=20)
        btn(nav, "Logout", self._do_logout,
            color=C["danger"], width=8,
            pady=4).pack(side="right", padx=20, pady=10)
        self._u_nav_lbl = tk.Label(nav, text="",
                                    bg=C["panel"], fg=C["accent"],
                                    font=F["sub"])
        self._u_nav_lbl.pack(side="right", padx=(0, 8))
        tk.Label(nav, text="Login sebagai:",
                 bg=C["panel"], fg=C["muted"],
                 font=F["small"]).pack(side="right", padx=(20, 0))

        # Body
        body = tk.Frame(page, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # Sidebar
        self._u_sidebar = tk.Frame(body, bg=C["sidebar"], width=195,
                                    highlightthickness=1,
                                    highlightbackground=C["border"])
        self._u_sidebar.pack(side="left", fill="y")
        self._u_sidebar.pack_propagate(False)
        tk.Label(self._u_sidebar, text="MENU",
                 bg=C["sidebar"], fg=C["muted"],
                 font=F["badge"]).pack(anchor="w", padx=16, pady=(18, 6))

        self._u_tab_btns = {}
        self._u_active   = tk.StringVar(value="")

        for icon, label, key in [
            ("🏠", "Dashboard",   "u_overview"),
            ("💸", "Transfer",    "u_transfer"),
            ("📋", "Riwayat",     "u_history"),
            ("🔑", "Kriptografi", "u_crypto"),
        ]:
            self._make_sidebar_btn(self._u_sidebar,
                                   self._u_tab_btns,
                                   self._u_active,
                                   icon, label, key,
                                   self._u_switch)

        # Content
        self._u_content = tk.Frame(body, bg=C["bg"])
        self._u_content.pack(side="right", fill="both", expand=True)

        self._u_panels = {}
        self._build_u_overview()
        self._build_u_transfer()
        self._build_u_history()
        self._build_u_crypto()

    def _enter_user_dashboard(self):
        """Dipanggil saat user login — reset semua state lalu tampilkan overview."""
        # Paksa switch ke overview agar data langsung refresh
        self._u_active.set("")          # reset tab aktif
        self._u_switch("u_overview")    # masuk overview = auto refresh
        self._u_nav_lbl.config(text=f"@{self.current_user}")
        self._show("user_dash")

    def _u_switch(self, key):
        """Ganti tab user dashboard."""
        for k, (b, ind, fr) in self._u_tab_btns.items():
            b.config(bg=C["sidebar"], fg=C["muted"])
            ind.config(bg=C["sidebar"])
            fr.config(bg=C["sidebar"])
        b, ind, fr = self._u_tab_btns[key]
        b.config(bg="#1C2128", fg=C["text"])
        ind.config(bg=C["accent"])
        fr.config(bg="#1C2128")
        self._u_active.set(key)

        for p in self._u_panels.values():
            p.pack_forget()
        self._u_panels[key].pack(fill="both", expand=True)

        # Refresh konten sesuai tab
        if key == "u_overview":
            self._refresh_u_overview()
        elif key == "u_history":
            self._refresh_u_history()
        elif key == "u_transfer":
            self._refresh_u_transfer_bal()
        elif key == "u_crypto":
            self._refresh_u_crypto()

    # ── Overview ──────────────────────────────
    def _build_u_overview(self):
        panel = tk.Frame(self._u_content, bg=C["bg"])
        self._u_panels["u_overview"] = panel

        cv = tk.Canvas(panel, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(panel, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True)

        inner = tk.Frame(cv, bg=C["bg"])
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",
                lambda e: cv.itemconfig(win, width=e.width))

        p = tk.Frame(inner, bg=C["bg"])
        p.pack(fill="both", padx=28, pady=22)

        # Saldo card
        sc = tk.Frame(p, bg=C["accent"])
        sc.pack(fill="x", pady=(0, 18))
        si = tk.Frame(sc, bg=C["accent"], padx=26, pady=20)
        si.pack(fill="x")
        lbl(si, "TOTAL SALDO",
            fg="#BFDBFE", font=F["badge"], bg=C["accent"]).pack(anchor="w")
        self._u_bal_lbl = tk.Label(si, text="Rp 0",
                                    bg=C["accent"], fg="white",
                                    font=("Consolas", 34, "bold"))
        self._u_bal_lbl.pack(anchor="w", pady=(4, 0))
        self._u_acct_lbl = tk.Label(si, text="",
                                     bg=C["accent"], fg="#BFDBFE",
                                     font=F["body"])
        self._u_acct_lbl.pack(anchor="w", pady=(4, 0))

        # Statistik
        sr = tk.Frame(p, bg=C["bg"])
        sr.pack(fill="x", pady=(0, 18))
        self._u_stat = {}
        for icon, label, key, color in [
            ("📤", "Total Keluar",  "out",   C["danger"]),
            ("📥", "Total Masuk",   "in",    C["success"]),
            ("🔄", "Transaksi",     "count", C["gold"]),
        ]:
            cf = card(sr, padx=16, pady=14)
            cf.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(cf, text=icon, bg=C["panel"],
                     font=("Segoe UI Emoji", 20)).pack(anchor="w")
            v = tk.Label(cf, text="—",
                         bg=C["panel"], fg=color, font=F["head"])
            v.pack(anchor="w")
            tk.Label(cf, text=label,
                     bg=C["panel"], fg=C["muted"],
                     font=F["small"]).pack(anchor="w")
            self._u_stat[key] = v

        # Aksi cepat
        lbl(p, "AKSI CEPAT",
            fg=C["muted"], font=F["badge"], bg=C["bg"]).pack(
            anchor="w", pady=(0, 8))
        ar = tk.Frame(p, bg=C["bg"])
        ar.pack(fill="x", pady=(0, 16))
        btn(ar, "💸 Transfer",
            lambda: self._u_switch("u_transfer"),
            width=16, pady=10).pack(side="left", padx=(0, 10))
        btn(ar, "📋 Riwayat",
            lambda: self._u_switch("u_history"),
            width=16, pady=10).pack(side="left")

        # Transaksi terbaru
        lbl(p, "TRANSAKSI TERBARU",
            fg=C["muted"], font=F["badge"], bg=C["bg"]).pack(
            anchor="w", pady=(0, 8))
        self._u_recent = tk.Frame(p, bg=C["bg"])
        self._u_recent.pack(fill="x")

    def _refresh_u_overview(self):
        if not self.current_user:
            return
        bal = get_balance(self.current_user)
        self._u_bal_lbl.config(text=f"Rp {bal:,.0f}")
        self._u_acct_lbl.config(
            text=f"@{self.current_user}  •  Wallet aktif")
        self._u_nav_lbl.config(text=f"@{self.current_user}")

        txs = get_transactions(self.current_user)
        total_out = sum(t["amount"] for t in txs
                        if t["sender"] == self.current_user
                        and t["tx_type"] == "transfer")
        total_in  = sum(t["amount"] for t in txs
                        if t["receiver"] == self.current_user)
        self._u_stat["out"].config(text=f"Rp {total_out:,.0f}")
        self._u_stat["in"].config(text=f"Rp {total_in:,.0f}")
        self._u_stat["count"].config(text=str(len(txs)))

        for w in self._u_recent.winfo_children():
            w.destroy()
        for t in txs[:5]:
            self._tx_row(self._u_recent, t, self.current_user)
        if not txs:
            lbl(self._u_recent, "Belum ada transaksi.",
                fg=C["muted"], bg=C["bg"]).pack(anchor="w", pady=8)

    def _tx_row(self, parent, t, viewer):
        is_out = (t["sender"] == viewer and t["tx_type"] == "transfer")
        is_topup = t["tx_type"] == "topup"
        row = tk.Frame(parent, bg=C["panel"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        row.pack(fill="x", pady=2)
        inner = tk.Frame(row, bg=C["panel"], padx=14, pady=10)
        inner.pack(fill="x")

        if is_topup:
            icon, color, sign = "💰", C["gold"], "+"
        elif is_out:
            icon, color, sign = "📤", C["danger"], "−"
        else:
            icon, color, sign = "📥", C["success"], "+"

        tk.Label(inner, text=icon, bg=C["panel"],
                 font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 10))
        mid = tk.Frame(inner, bg=C["panel"])
        mid.pack(side="left", fill="x", expand=True)

        if is_topup:
            desc = f"Top Up dari Admin"
        elif is_out:
            desc = f"Ke: @{t['receiver']}"
        else:
            desc = f"Dari: @{t['sender']}"

        tk.Label(mid, text=desc,
                 bg=C["panel"], fg=C["text"],
                 font=F["sub"]).pack(anchor="w")
        tk.Label(mid, text=t["timestamp"],
                 bg=C["panel"], fg=C["muted"],
                 font=F["small"]).pack(anchor="w")
        tk.Label(inner,
                 text=f"{sign}Rp {t['amount']:,.0f}",
                 bg=C["panel"], fg=color,
                 font=F["sub"]).pack(side="right")

    # ── Transfer ──────────────────────────────
    def _build_u_transfer(self):
        panel = tk.Frame(self._u_content, bg=C["bg"])
        self._u_panels["u_transfer"] = panel

        tk.Frame(panel, bg=C["bg"]).pack(expand=True)
        c = card(panel, padx=44, pady=38)
        c.pack(padx=60)

        lbl(c, "💸  Transfer Saldo",
            fg=C["text"], font=F["head"]).pack(anchor="w")
        lbl(c, "Kirim saldo ke pengguna lain — dikonfirmasi dengan PIN",
            fg=C["muted"], font=F["small"]).pack(anchor="w", pady=(2, 14))
        sep(c).pack(fill="x", pady=(0, 16))

        self._u_tf_bal = tk.Label(c, text="",
                                   bg=C["hi"], fg=C["success"],
                                   font=F["sub"], padx=12, pady=6)
        self._u_tf_bal.pack(anchor="w", pady=(0, 14))

        def fld(label):
            lbl(c, label, fg=C["muted"],
                font=F["badge"]).pack(anchor="w", pady=(10, 2))
            e = entry(c, width=42)
            e.pack(fill="x", ipady=8, padx=2)
            return e

        self._u_tf_recv  = fld("PENERIMA (USERNAME)")
        self._u_tf_amt   = fld("JUMLAH (Rp)")
        self._u_tf_memo  = fld("MEMO / KETERANGAN  (opsional)")

        sep(c).pack(fill="x", pady=18)
        row = tk.Frame(c, bg=C["panel"])
        row.pack(fill="x")
        btn(row, "Batal",
            lambda: self._u_switch("u_overview"),
            color=C["hi"], width=14).pack(side="left")
        btn(row, "Kirim  →",
            self._do_transfer, width=14).pack(side="right")

        tk.Frame(panel, bg=C["bg"]).pack(expand=True)

    def _refresh_u_transfer_bal(self):
        if not self.current_user:
            return
        bal = get_balance(self.current_user)
        self._u_tf_bal.config(
            text=f"  Saldo tersedia: Rp {bal:,.0f}  ")

    def _do_transfer(self):
        recv    = self._u_tf_recv.get().strip()
        amt_str = self._u_tf_amt.get().strip()
        memo    = self._u_tf_memo.get().strip()

        if not recv or not amt_str:
            messagebox.showerror("Error",
                                 "Penerima dan jumlah wajib diisi.")
            return
        try:
            amount = float(amt_str.replace(",", "").replace(".", ""))
        except ValueError:
            messagebox.showerror("Error", "Jumlah harus berupa angka.")
            return

        # Konfirmasi PIN
        dlg = PinDialog(self, "Konfirmasi PIN Transfer")
        self.wait_window(dlg)
        if dlg.result is None:
            return
        if not verify_pin(self.current_user, dlg.result):
            messagebox.showerror("PIN Salah",
                                 "PIN yang Anda masukkan salah.")
            return

        ok, msg = transfer(self.current_user, recv, amount, memo)
        if ok:
            messagebox.showinfo("Berhasil", msg)
            self._u_tf_recv.delete(0, "end")
            self._u_tf_amt.delete(0, "end")
            self._u_tf_memo.delete(0, "end")
            self._u_switch("u_overview")
        else:
            messagebox.showerror("Gagal", msg)

    # ── History ───────────────────────────────
    def _build_u_history(self):
        panel = tk.Frame(self._u_content, bg=C["bg"])
        self._u_panels["u_history"] = panel

        hdr = tk.Frame(panel, bg=C["bg"], padx=28, pady=16)
        hdr.pack(fill="x")
        lbl(hdr, "📋  Riwayat Transaksi",
            fg=C["text"], font=F["head"],
            bg=C["bg"]).pack(side="left")

        tf = tk.Frame(panel, bg=C["bg"], padx=28)
        tf.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("U.Treeview",
                         background=C["panel"], foreground=C["text"],
                         rowheight=36, fieldbackground=C["panel"],
                         font=F["body"], borderwidth=0)
        style.configure("U.Treeview.Heading",
                         background=C["hi"], foreground=C["muted"],
                         font=F["badge"], relief="flat")
        style.map("U.Treeview",
                  background=[("selected", C["accent2"])],
                  foreground=[("selected", "white")])

        cols = ("Tipe", "Pengirim", "Penerima",
                "Jumlah", "Memo", "Waktu")
        self._u_tree = ttk.Treeview(tf, columns=cols,
                                     show="headings",
                                     style="U.Treeview")
        ws = {"Tipe": 80, "Pengirim": 110, "Penerima": 110,
              "Jumlah": 140, "Memo": 150, "Waktu": 150}
        for col in cols:
            self._u_tree.heading(col, text=col)
            self._u_tree.column(col, width=ws[col],
                                 anchor="center"
                                 if col in ("Tipe", "Jumlah") else "w")
        self._u_tree.tag_configure("out",
                                    background="#1A0A0A",
                                    foreground="#FCA5A5")
        self._u_tree.tag_configure("in",
                                    background="#0A1A0E",
                                    foreground="#6EE7B7")
        self._u_tree.tag_configure("topup",
                                    background="#1A1500",
                                    foreground="#FDE68A")
        sb2 = ttk.Scrollbar(tf, orient="vertical",
                             command=self._u_tree.yview)
        self._u_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self._u_tree.pack(fill="both", expand=True)

        self._u_hist_sum = tk.Label(panel, text="",
                                     bg=C["hi"], fg=C["muted"],
                                     font=F["small"], padx=28,
                                     pady=8, anchor="w")
        self._u_hist_sum.pack(fill="x")

    def _refresh_u_history(self):
        if not self.current_user:
            return
        for r in self._u_tree.get_children():
            self._u_tree.delete(r)
        txs = get_transactions(self.current_user)
        for t in txs:
            is_topup = t["tx_type"] == "topup"
            is_out   = (t["sender"] == self.current_user
                        and not is_topup)
            if is_topup:
                tag  = "topup"
                tipe = "💰 Top Up"
                amt  = f"+Rp {t['amount']:,.0f}"
            elif is_out:
                tag  = "out"
                tipe = "📤 Keluar"
                amt  = f"−Rp {t['amount']:,.0f}"
            else:
                tag  = "in"
                tipe = "📥 Masuk"
                amt  = f"+Rp {t['amount']:,.0f}"
            self._u_tree.insert("", "end", tags=(tag,),
                                 values=(tipe, t["sender"],
                                         t["receiver"], amt,
                                         t["memo"], t["timestamp"]))
        self._u_hist_sum.config(
            text=f"  Total: {len(txs)} transaksi")

    # ── Crypto ────────────────────────────────
    def _build_u_crypto(self):
        panel = tk.Frame(self._u_content, bg=C["bg"])
        self._u_panels["u_crypto"] = panel

        cv = tk.Canvas(panel, bg=C["bg"], highlightthickness=0)
        sb3 = ttk.Scrollbar(panel, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["bg"])
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",
                lambda e: cv.itemconfig(win, width=e.width))

        p = tk.Frame(inner, bg=C["bg"])
        p.pack(fill="both", padx=28, pady=20)

        lbl(p, "🔑  Informasi Kriptografi",
            fg=C["text"], font=F["head"],
            bg=C["bg"]).pack(anchor="w", pady=(0, 4))
        lbl(p, "Simulasi pengamanan data: RSA-2048 & AES-256",
            fg=C["muted"], font=F["small"],
            bg=C["bg"]).pack(anchor="w", pady=(0, 18))

        def section(title, desc, accent):
            c = card(p, padx=20, pady=16)
            c.pack(fill="x", pady=(0, 14))
            hf = tk.Frame(c, bg=C["panel"])
            hf.pack(fill="x")
            tk.Frame(hf, bg=accent, width=4).pack(side="left", fill="y")
            inf = tk.Frame(hf, bg=C["panel"], padx=12)
            inf.pack(side="left", fill="x", expand=True)
            lbl(inf, title, fg=C["text"], font=F["sub"]).pack(anchor="w")
            lbl(inf, desc, fg=C["muted"], font=F["small"]).pack(anchor="w")
            sep(c).pack(fill="x", pady=10)
            return c

        def key_box(parent, label):
            lbl(parent, label, fg=C["muted"],
                font=F["badge"]).pack(anchor="w")
            v = tk.Text(parent, height=3, wrap="char",
                        bg="#060A0E", fg=C["success"],
                        font=F["mono"], relief="flat",
                        padx=8, pady=6, state="disabled",
                        highlightthickness=1,
                        highlightbackground=C["border"])
            v.pack(fill="x", pady=(4, 10), padx=2)
            return v

        sc = section("SHA-256  —  Password & PIN Hashing",
                     "SHA-256 untuk hash password dan PIN.\n"
                     "Data tidak pernah disimpan plaintext.",
                     C["warning"])
        self._u_sha_v = key_box(sc, "Hash Password Anda:")
        self._u_pin_v = key_box(sc, "Hash PIN Anda:")

        ac = section("AES-256  —  Enkripsi Data",
                     "AES-256 CBC mengenkripsi saldo & transaksi\n"
                     "sebelum disimpan ke database SQLite.",
                     C["success"])
        self._u_aes_v = key_box(ac, "AES Key (hex):")

        rc = section("RSA-2048  —  Key Protection",
                     "RSA melindungi AES key.\n"
                     "Hanya private key yang bisa membuka AES key.",
                     C["accent"])
        self._u_rsa_pub  = key_box(rc, "Public Key:")
        self._u_rsa_priv = key_box(rc, "Private Key:")

    def _set_txt(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _refresh_u_crypto(self):
        if not self.current_user:
            return
        from database import get_user as _gu
        user = _gu(self.current_user)
        self._set_txt(self._u_sha_v,
            f"SHA-256(salt + password) =\n{user['password_hash']}")
        pin_h = user["pin_hash"] or "(belum di-set)"
        self._set_txt(self._u_pin_v,
            f"SHA-256(pin_salt + PIN) =\n{pin_h}")

        aes_key = get_or_create_wallet_aes_key()
        self._set_txt(self._u_aes_v,
            f"AES-256 Key (hex):\n{aes_key.hex()}\n"
            f"Key length: {len(aes_key)*8} bits")

        pub, priv = load_rsa_keys()
        self._set_txt(self._u_rsa_pub,
                      pub[:200] + "\n... (truncated)")
        self._set_txt(self._u_rsa_priv,
                      priv[:200] + "\n... (truncated)")

    # ─────────────────────────────────────────
    #  ADMIN DASHBOARD
    # ─────────────────────────────────────────
    def _build_admin_dashboard(self):
        page = tk.Frame(self._wrap, bg=C["bg"])
        self._pages["admin_dash"] = page

        # Navbar admin (ungu)
        nav = tk.Frame(page, bg=C["admin"], height=52,
                       highlightthickness=0)
        nav.pack(fill="x")
        nav.pack_propagate(False)
        tk.Label(nav, text="⚙️  Secure Wallet  —  ADMIN PANEL",
                 bg=C["admin"], fg="white",
                 font=F["head"]).pack(side="left", padx=20)
        btn(nav, "Logout", self._do_logout,
            color="#991B1B", width=8,
            pady=4).pack(side="right", padx=20, pady=10)
        self._a_nav_lbl = tk.Label(nav, text="",
                                    bg=C["admin"], fg="#DDD6FE",
                                    font=F["sub"])
        self._a_nav_lbl.pack(side="right", padx=(0, 8))
        tk.Label(nav, text="Login sebagai:",
                 bg=C["admin"], fg="#C4B5FD",
                 font=F["small"]).pack(side="right", padx=(20, 0))

        # Body
        body = tk.Frame(page, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # Sidebar admin
        a_side = tk.Frame(body, bg=C["sidebar"], width=195,
                          highlightthickness=1,
                          highlightbackground=C["border"])
        a_side.pack(side="left", fill="y")
        a_side.pack_propagate(False)
        tk.Label(a_side, text="ADMIN MENU",
                 bg=C["sidebar"], fg=C["muted"],
                 font=F["badge"]).pack(anchor="w", padx=16, pady=(18, 6))

        self._a_tab_btns = {}
        self._a_active   = tk.StringVar(value="")

        for icon, label, key in [
            ("🏠", "Ringkasan",        "a_overview"),
            ("💳", "Top Up User",      "a_topup"),
            ("📋", "Semua Transaksi",  "a_all_tx"),
            ("👥", "Daftar User",      "a_users"),
        ]:
            self._make_sidebar_btn(a_side, self._a_tab_btns,
                                   self._a_active,
                                   icon, label, key,
                                   self._a_switch,
                                   accent=C["admin"])

        # Content
        self._a_content = tk.Frame(body, bg=C["bg"])
        self._a_content.pack(side="right", fill="both", expand=True)

        self._a_panels = {}
        self._build_a_overview()
        self._build_a_topup()
        self._build_a_all_tx()
        self._build_a_users()

    def _enter_admin_dashboard(self):
        """Dipanggil saat admin login — reset state lalu masuk overview."""
        self._a_active.set("")
        self._a_switch("a_overview")
        self._a_nav_lbl.config(text=f"@{self.current_user}")
        self._show("admin_dash")

    def _a_switch(self, key):
        """Ganti tab admin dashboard."""
        for k, (b, ind, fr) in self._a_tab_btns.items():
            b.config(bg=C["sidebar"], fg=C["muted"])
            ind.config(bg=C["sidebar"])
            fr.config(bg=C["sidebar"])
        b, ind, fr = self._a_tab_btns[key]
        b.config(bg="#1C2128", fg=C["text"])
        ind.config(bg=C["admin"])
        fr.config(bg="#1C2128")
        self._a_active.set(key)

        for p in self._a_panels.values():
            p.pack_forget()
        self._a_panels[key].pack(fill="both", expand=True)

        if key == "a_overview":
            self._refresh_a_overview()
        elif key == "a_topup":
            self._refresh_a_topup_users()
        elif key == "a_all_tx":
            self._refresh_a_all_tx()
        elif key == "a_users":
            self._refresh_a_users()

    # ── Admin Overview ────────────────────────
    def _build_a_overview(self):
        panel = tk.Frame(self._a_content, bg=C["bg"])
        self._a_panels["a_overview"] = panel

        p = tk.Frame(panel, bg=C["bg"])
        p.pack(fill="both", padx=28, pady=22, expand=True)

        # Admin banner
        banner = tk.Frame(p, bg=C["admin"])
        banner.pack(fill="x", pady=(0, 20))
        bi = tk.Frame(banner, bg=C["admin"], padx=26, pady=20)
        bi.pack(fill="x")
        tk.Label(bi, text="⚙️  Admin Dashboard",
                 bg=C["admin"], fg="white",
                 font=F["head"]).pack(anchor="w")
        self._a_ov_lbl = tk.Label(bi, text="",
                                   bg=C["admin"], fg="#DDD6FE",
                                   font=F["body"])
        self._a_ov_lbl.pack(anchor="w", pady=(4, 0))

        # Statistik
        sr = tk.Frame(p, bg=C["bg"])
        sr.pack(fill="x", pady=(0, 20))
        self._a_stat = {}
        for icon, label, key, color in [
            ("👥", "Total User",     "users",  C["accent"]),
            ("💰", "Total Top Up",   "topup",  C["gold"]),
            ("🔄", "Semua Transaksi","count",  C["success"]),
        ]:
            cf = card(sr, padx=16, pady=14)
            cf.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(cf, text=icon, bg=C["panel"],
                     font=("Segoe UI Emoji", 20)).pack(anchor="w")
            v = tk.Label(cf, text="—",
                         bg=C["panel"], fg=color, font=F["head"])
            v.pack(anchor="w")
            tk.Label(cf, text=label,
                     bg=C["panel"], fg=C["muted"],
                     font=F["small"]).pack(anchor="w")
            self._a_stat[key] = v

        # Aksi cepat
        lbl(p, "AKSI CEPAT",
            fg=C["muted"], font=F["badge"], bg=C["bg"]).pack(
            anchor="w", pady=(0, 8))
        ar = tk.Frame(p, bg=C["bg"])
        ar.pack(fill="x", pady=(0, 16))
        btn(ar, "💳 Top Up User",
            lambda: self._a_switch("a_topup"),
            color=C["admin"], width=16, pady=10).pack(side="left", padx=(0, 10))
        btn(ar, "📋 Semua Transaksi",
            lambda: self._a_switch("a_all_tx"),
            width=18, pady=10).pack(side="left")

        lbl(p, "TRANSAKSI TERBARU",
            fg=C["muted"], font=F["badge"], bg=C["bg"]).pack(
            anchor="w", pady=(0, 8))
        self._a_recent = tk.Frame(p, bg=C["bg"])
        self._a_recent.pack(fill="x")

    def _refresh_a_overview(self):
        users = get_all_regular_users()
        txs   = get_all_transactions()
        topup_total = sum(t["amount"] for t in txs
                          if t["tx_type"] == "topup")
        self._a_stat["users"].config(text=str(len(users)))
        self._a_stat["topup"].config(text=f"Rp {topup_total:,.0f}")
        self._a_stat["count"].config(text=str(len(txs)))
        self._a_ov_lbl.config(
            text=f"Selamat datang, @{self.current_user}")
        self._a_nav_lbl.config(text=f"@{self.current_user}")

        for w in self._a_recent.winfo_children():
            w.destroy()
        for t in txs[:5]:
            self._admin_tx_row(self._a_recent, t)
        if not txs:
            lbl(self._a_recent, "Belum ada transaksi.",
                fg=C["muted"], bg=C["bg"]).pack(anchor="w", pady=8)

    def _admin_tx_row(self, parent, t):
        is_topup = t["tx_type"] == "topup"
        row = tk.Frame(parent, bg=C["panel"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        row.pack(fill="x", pady=2)
        inner = tk.Frame(row, bg=C["panel"], padx=14, pady=10)
        inner.pack(fill="x")
        icon  = "💰" if is_topup else "💸"
        color = C["gold"] if is_topup else C["accent"]
        tk.Label(inner, text=icon, bg=C["panel"],
                 font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 10))
        mid = tk.Frame(inner, bg=C["panel"])
        mid.pack(side="left", fill="x", expand=True)
        tipe = "Top Up" if is_topup else "Transfer"
        tk.Label(mid, text=f"{tipe}: @{t['receiver']}",
                 bg=C["panel"], fg=C["text"],
                 font=F["sub"]).pack(anchor="w")
        tk.Label(mid, text=t["timestamp"],
                 bg=C["panel"], fg=C["muted"],
                 font=F["small"]).pack(anchor="w")
        tk.Label(inner,
                 text=f"+Rp {t['amount']:,.0f}",
                 bg=C["panel"], fg=color,
                 font=F["sub"]).pack(side="right")

    # ── Admin Top Up ──────────────────────────
    def _build_a_topup(self):
        panel = tk.Frame(self._a_content, bg=C["bg"])
        self._a_panels["a_topup"] = panel

        tk.Frame(panel, bg=C["bg"]).pack(expand=True)
        c = card(panel, padx=44, pady=38)
        c.pack(padx=60)

        lbl(c, "💳  Top Up Saldo User",
            fg=C["text"], font=F["head"]).pack(anchor="w")
        lbl(c, "Tambahkan saldo ke akun pengguna yang ditentukan",
            fg=C["muted"], font=F["small"]).pack(anchor="w", pady=(2, 14))
        sep(c).pack(fill="x", pady=(0, 16))

        # Pilih user dari dropdown
        lbl(c, "PILIH USER", fg=C["muted"],
            font=F["badge"]).pack(anchor="w", pady=(0, 4))
        self._a_tu_var = tk.StringVar()
        self._a_tu_combo = ttk.Combobox(c,
                                         textvariable=self._a_tu_var,
                                         state="readonly",
                                         font=F["body"],
                                         width=38)
        self._a_tu_combo.pack(fill="x", ipady=6, padx=2)

        # Saldo user terpilih
        self._a_tu_cur_bal = tk.Label(c, text="",
                                       bg=C["hi"], fg=C["muted"],
                                       font=F["small"], padx=10, pady=4)
        self._a_tu_cur_bal.pack(anchor="w", pady=(6, 0))
        self._a_tu_combo.bind("<<ComboboxSelected>>",
                               self._on_topup_user_select)

        lbl(c, "JUMLAH TOP UP (Rp)",
            fg=C["muted"], font=F["badge"]).pack(anchor="w", pady=(14, 4))
        self._a_tu_amt = entry(c, width=42)
        self._a_tu_amt.pack(fill="x", ipady=8, padx=2)

        lbl(c, "KETERANGAN  (opsional)",
            fg=C["muted"], font=F["badge"]).pack(anchor="w", pady=(10, 4))
        self._a_tu_memo = entry(c, width=42)
        self._a_tu_memo.pack(fill="x", ipady=8, padx=2)

        sep(c).pack(fill="x", pady=18)
        btn(c, "✅  PROSES TOP UP",
            self._do_topup,
            color=C["admin"], width=38,
            pady=10).pack(fill="x", padx=2)

        tk.Frame(panel, bg=C["bg"]).pack(expand=True)

    def _refresh_a_topup_users(self):
        """Perbarui daftar user di combobox."""
        users = get_all_regular_users()
        self._a_tu_combo["values"] = users
        if users:
            self._a_tu_combo.current(0)
            self._on_topup_user_select()
        else:
            self._a_tu_cur_bal.config(text="  Belum ada user terdaftar")

    def _on_topup_user_select(self, event=None):
        u = self._a_tu_var.get()
        if u:
            bal = get_balance(u)
            self._a_tu_cur_bal.config(
                text=f"  Saldo @{u} saat ini: Rp {bal:,.0f}  ")

    def _do_topup(self):
        target  = self._a_tu_var.get().strip()
        amt_str = self._a_tu_amt.get().strip()
        memo    = self._a_tu_memo.get().strip()

        if not target:
            messagebox.showerror("Error", "Pilih user terlebih dahulu.")
            return
        if not amt_str:
            messagebox.showerror("Error", "Jumlah top up wajib diisi.")
            return
        try:
            amount = float(amt_str.replace(",", "").replace(".", ""))
        except ValueError:
            messagebox.showerror("Error", "Jumlah harus berupa angka.")
            return

        confirm = messagebox.askyesno(
            "Konfirmasi Top Up",
            f"Top up Rp {amount:,.0f} ke @{target}?\n"
            f"Keterangan: {memo or '-'}"
        )
        if not confirm:
            return

        ok, msg = topup(self.current_user, target, amount, memo)
        if ok:
            messagebox.showinfo("Berhasil", msg)
            self._a_tu_amt.delete(0, "end")
            self._a_tu_memo.delete(0, "end")
            self._on_topup_user_select()   # Refresh saldo
            self._a_switch("a_overview")
        else:
            messagebox.showerror("Gagal", msg)

    # ── Admin All Transactions ─────────────────
    def _build_a_all_tx(self):
        panel = tk.Frame(self._a_content, bg=C["bg"])
        self._a_panels["a_all_tx"] = panel

        hdr = tk.Frame(panel, bg=C["bg"], padx=28, pady=16)
        hdr.pack(fill="x")
        lbl(hdr, "📋  Semua Transaksi",
            fg=C["text"], font=F["head"],
            bg=C["bg"]).pack(side="left")

        tf = tk.Frame(panel, bg=C["bg"], padx=28)
        tf.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("A.Treeview",
                         background=C["panel"], foreground=C["text"],
                         rowheight=36, fieldbackground=C["panel"],
                         font=F["body"], borderwidth=0)
        style.configure("A.Treeview.Heading",
                         background=C["hi"], foreground=C["muted"],
                         font=F["badge"], relief="flat")
        style.map("A.Treeview",
                  background=[("selected", C["admin2"])],
                  foreground=[("selected", "white")])

        cols = ("Tipe", "Pengirim", "Penerima",
                "Jumlah", "Memo", "Waktu")
        self._a_tree = ttk.Treeview(tf, columns=cols,
                                     show="headings",
                                     style="A.Treeview")
        ws = {"Tipe": 80, "Pengirim": 110, "Penerima": 110,
              "Jumlah": 140, "Memo": 160, "Waktu": 150}
        for col in cols:
            self._a_tree.heading(col, text=col)
            self._a_tree.column(col, width=ws[col],
                                 anchor="center"
                                 if col in ("Tipe", "Jumlah") else "w")
        self._a_tree.tag_configure("topup",
                                    background="#1A1500",
                                    foreground="#FDE68A")
        self._a_tree.tag_configure("transfer",
                                    background="#0A0F1A",
                                    foreground="#93C5FD")
        sb4 = ttk.Scrollbar(tf, orient="vertical",
                             command=self._a_tree.yview)
        self._a_tree.configure(yscrollcommand=sb4.set)
        sb4.pack(side="right", fill="y")
        self._a_tree.pack(fill="both", expand=True)

        self._a_tx_sum = tk.Label(panel, text="",
                                   bg=C["hi"], fg=C["muted"],
                                   font=F["small"], padx=28,
                                   pady=8, anchor="w")
        self._a_tx_sum.pack(fill="x")

    def _refresh_a_all_tx(self):
        for r in self._a_tree.get_children():
            self._a_tree.delete(r)
        txs = get_all_transactions()
        for t in txs:
            tag  = "topup" if t["tx_type"] == "topup" else "transfer"
            tipe = "💰 Top Up" if t["tx_type"] == "topup" else "💸 Transfer"
            amt  = f"Rp {t['amount']:,.0f}"
            self._a_tree.insert("", "end", tags=(tag,),
                                 values=(tipe, t["sender"],
                                         t["receiver"], amt,
                                         t["memo"], t["timestamp"]))
        self._a_tx_sum.config(
            text=f"  Total: {len(txs)} transaksi")

    # ── Admin User List ───────────────────────
    def _build_a_users(self):
        panel = tk.Frame(self._a_content, bg=C["bg"])
        self._a_panels["a_users"] = panel

        hdr = tk.Frame(panel, bg=C["bg"], padx=28, pady=16)
        hdr.pack(fill="x")
        lbl(hdr, "👥  Daftar Pengguna",
            fg=C["text"], font=F["head"],
            bg=C["bg"]).pack(side="left")
        btn(hdr, "🔄 Refresh",
            self._refresh_a_users,
            color=C["hi"], width=10,
            pady=4).pack(side="right")

        tf = tk.Frame(panel, bg=C["bg"], padx=28)
        tf.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("U2.Treeview",
                         background=C["panel"], foreground=C["text"],
                         rowheight=36, fieldbackground=C["panel"],
                         font=F["body"], borderwidth=0)
        style.configure("U2.Treeview.Heading",
                         background=C["hi"], foreground=C["muted"],
                         font=F["badge"], relief="flat")
        style.map("U2.Treeview",
                  background=[("selected", C["admin2"])],
                  foreground=[("selected", "white")])

        cols = ("Username", "Saldo", "Punya PIN", "Terdaftar")
        self._a_utree = ttk.Treeview(tf, columns=cols,
                                      show="headings",
                                      style="U2.Treeview")
        for col in cols:
            self._a_utree.heading(col, text=col)
            self._a_utree.column(col, width=160)
        sb5 = ttk.Scrollbar(tf, orient="vertical",
                             command=self._a_utree.yview)
        self._a_utree.configure(yscrollcommand=sb5.set)
        sb5.pack(side="right", fill="y")
        self._a_utree.pack(fill="both", expand=True)

    def _refresh_a_users(self):
        for r in self._a_utree.get_children():
            self._a_utree.delete(r)
        from database import get_user as _gu
        for uname in get_all_regular_users():
            u   = _gu(uname)
            bal = get_balance(uname)
            pin = "✅ Ya" if has_pin(uname) else "❌ Belum"
            self._a_utree.insert("", "end",
                                  values=(uname,
                                          f"Rp {bal:,.0f}",
                                          pin,
                                          u["created_at"]))

    # ─────────────────────────────────────────
    #  Shared helpers
    # ─────────────────────────────────────────
    def _make_sidebar_btn(self, sidebar, tab_dict, active_var,
                          icon, label, key, switch_fn,
                          accent=None):
        acc = accent or C["accent"]
        fr = tk.Frame(sidebar, bg=C["sidebar"], cursor="hand2")
        fr.pack(fill="x", padx=8, pady=2)
        ind = tk.Frame(fr, bg=C["sidebar"], width=3)
        ind.pack(side="left", fill="y")
        b = tk.Button(fr,
                      text=f"  {icon}  {label}",
                      bg=C["sidebar"], fg=C["muted"],
                      font=F["body"], relief="flat",
                      anchor="w", pady=10, bd=0, cursor="hand2",
                      command=lambda k=key: switch_fn(k))
        b.pack(fill="x")
        tab_dict[key] = (b, ind, fr)

        def on_enter(e, _b=b, _fr=fr):
            if active_var.get() != key:
                _b.config(bg="#1C2128")
                _fr.config(bg="#1C2128")

        def on_leave(e, _b=b, _fr=fr):
            if active_var.get() != key:
                _b.config(bg=C["sidebar"])
                _fr.config(bg=C["sidebar"])

        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        fr.bind("<Enter>", on_enter)
        fr.bind("<Leave>", on_leave)

    def _do_logout(self):
        if messagebox.askyesno("Logout", "Yakin ingin logout?"):
            self.current_user = None
            self.current_role = None
            self._show("login")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
