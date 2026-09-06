"""
Modul database untuk aplikasi Kasir & Stok Petshop.
Pakai SQLite bawaan Python - satu file petshop.db, tanpa perlu install
database server apa pun.
"""

import sqlite3
import os
from datetime import datetime
import utils

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "petshop.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            kategori TEXT DEFAULT '',
            harga_jual REAL NOT NULL,
            stok INTEGER NOT NULL DEFAULT 0,
            satuan TEXT DEFAULT 'pcs'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            total REAL NOT NULL,
            dibayar REAL NOT NULL,
            kembalian REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transaksi_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaksi_id INTEGER NOT NULL,
            produk_id INTEGER,
            nama_produk TEXT NOT NULL,
            harga_satuan REAL NOT NULL,
            jumlah INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (transaksi_id) REFERENCES transaksi(id),
            FOREIGN KEY (produk_id) REFERENCES produk(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT PRIMARY KEY,
            nilai TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- PRODUK ----------------

def tambah_produk(nama, kategori, harga_jual, stok, satuan="pcs"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO produk (nama, kategori, harga_jual, stok, satuan) VALUES (?, ?, ?, ?, ?)",
        (nama, kategori, harga_jual, stok, satuan),
    )
    conn.commit()
    conn.close()


def update_produk(produk_id, nama, kategori, harga_jual, stok, satuan):
    conn = get_connection()
    conn.execute(
        "UPDATE produk SET nama=?, kategori=?, harga_jual=?, stok=?, satuan=? WHERE id=?",
        (nama, kategori, harga_jual, stok, satuan, produk_id),
    )
    conn.commit()
    conn.close()


def hapus_produk(produk_id):
    conn = get_connection()
    conn.execute("DELETE FROM produk WHERE id=?", (produk_id,))
    conn.commit()
    conn.close()


def get_semua_produk(keyword=None):
    conn = get_connection()
    if keyword:
        rows = conn.execute(
            "SELECT * FROM produk WHERE nama LIKE ? ORDER BY nama",
            (f"%{keyword}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM produk ORDER BY nama").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_produk_by_id(produk_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------- TRANSAKSI ----------------

def buat_transaksi(items, dibayar):
    """
    items: list of dict {produk_id, nama_produk, harga_satuan, jumlah}
    Validasi stok, simpan transaksi + detail, dan kurangi stok otomatis.
    Return: (transaksi_id, total, kembalian)
    Raise ValueError kalau stok kurang atau uang dibayar kurang dari total.
    """
    if not items:
        raise ValueError("Keranjang masih kosong")

    conn = get_connection()
    cur = conn.cursor()

    for item in items:
        row = cur.execute("SELECT stok, nama FROM produk WHERE id=?", (item["produk_id"],)).fetchone()
        if row is None:
            conn.close()
            raise ValueError(f"Produk '{item['nama_produk']}' tidak ditemukan di database")
        if row["stok"] < item["jumlah"]:
            conn.close()
            raise ValueError(
                f"Stok '{row['nama']}' tidak cukup - tersedia {row['stok']}, diminta {item['jumlah']}"
            )

    total = sum(item["harga_satuan"] * item["jumlah"] for item in items)
    kembalian = dibayar - total
    if kembalian < 0:
        conn.close()
        raise ValueError(
            f"Uang dibayar (Rp {utils.format_ribuan(dibayar)}) kurang dari "
            f"total (Rp {utils.format_ribuan(total)})"
        )

    tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO transaksi (tanggal, total, dibayar, kembalian) VALUES (?, ?, ?, ?)",
        (tanggal, total, dibayar, kembalian),
    )
    transaksi_id = cur.lastrowid

    for item in items:
        subtotal = item["harga_satuan"] * item["jumlah"]
        cur.execute(
            """INSERT INTO transaksi_detail
               (transaksi_id, produk_id, nama_produk, harga_satuan, jumlah, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (transaksi_id, item["produk_id"], item["nama_produk"],
             item["harga_satuan"], item["jumlah"], subtotal),
        )
        cur.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (item["jumlah"], item["produk_id"]))

    conn.commit()
    conn.close()
    return transaksi_id, total, kembalian


def get_riwayat_transaksi():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM transaksi ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_detail_transaksi(transaksi_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transaksi_detail WHERE transaksi_id=?", (transaksi_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_penjualan_hari_ini():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COALESCE(SUM(total), 0) as total, COUNT(*) as jumlah FROM transaksi WHERE tanggal LIKE ?",
        (f"{today}%",),
    ).fetchone()
    conn.close()
    return dict(row)


# ---------------- PENGATURAN ----------------

def get_pengaturan(kunci, default=None):
    conn = get_connection()
    row = conn.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (kunci,)).fetchone()
    conn.close()
    return row["nilai"] if row else default


def set_pengaturan(kunci, nilai):
    conn = get_connection()
    conn.execute(
        "INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?) "
        "ON CONFLICT(kunci) DO UPDATE SET nilai=excluded.nilai",
        (kunci, str(nilai)),
    )
    conn.commit()
    conn.close()
