"""
Modul database untuk aplikasi Kasir & Stok Petshop.
Pakai SQLite bawaan Python - satu file petshop.db, tanpa perlu install
database server apa pun.
"""

import sqlite3
import os
from datetime import datetime, timedelta
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
            harga_beli REAL DEFAULT 0,
            harga_jual REAL NOT NULL,
            stok INTEGER NOT NULL DEFAULT 0,
            satuan TEXT DEFAULT 'pcs',
            gambar TEXT DEFAULT ''
        )
    """)

    # --- TRIK PENYELAMATAN DATA MODAL ---
    # --- TRIK PENYELAMATAN DATA MODAL ---
    try:
        cur.execute("ALTER TABLE produk ADD COLUMN harga_beli REAL DEFAULT 0")
        cur.execute("UPDATE produk SET harga_beli = harga_jual")
    except sqlite3.OperationalError:
        pass 

    # --- TAMBAHKAN BARIS INI ---
    # Otomatis jadikan Harga Jual = 0 JIKA angkanya masih sama persis dengan Harga Beli
    cur.execute("UPDATE produk SET harga_jual = 0 WHERE harga_jual = harga_beli")
    # Memperbarui database lama dengan kolom baru tanpa menghapus data
    try:
        cur.execute("ALTER TABLE produk ADD COLUMN gambar TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        # Jika error (artinya kolom gambar sudah berhasil ditambahkan sebelumnya), abaikan saja
        pass

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS kategori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE NOT NULL
        )
    """)

    # --- TAMBAHAN: Kolom Keuntungan di Riwayat Transaksi ---
    try:
        cur.execute("ALTER TABLE transaksi ADD COLUMN keuntungan REAL DEFAULT 0")
        cur.execute("ALTER TABLE transaksi_detail ADD COLUMN harga_beli REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ---------------- PRODUK ----------------

def tambah_produk(nama, kategori, harga_beli, harga_jual, stok, satuan="pcs", gambar=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO produk (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar),
    )
    id_baru = cur.lastrowid  # Tangkap ID barang yang baru saja masuk
    conn.commit()
    conn.close()
    return id_baru           # Kembalikan ID tersebut ke aplikasi

def update_produk(produk_id, nama, kategori, harga_beli, harga_jual, stok, satuan, gambar):
    conn = get_connection()
    conn.execute(
        "UPDATE produk SET nama=?, kategori=?, harga_beli=?, harga_jual=?, stok=?, satuan=?, gambar=? WHERE id=?",
        (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar, produk_id),
    )
    conn.commit()
    conn.close()


def hapus_produk(produk_id):
    conn = get_connection()
    conn.execute("DELETE FROM produk WHERE id=?", (produk_id,))
    conn.commit()
    conn.close()


def get_semua_produk(keyword=None, kategori=None):
    conn = get_connection()
    
    # Gunakan 1=1 agar mudah menambahkan kondisi AND selanjutnya
    query = "SELECT * FROM produk WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND nama LIKE ?"
        params.append(f"%{keyword}%")
        
    if kategori and kategori != "Semua Kategori":
        query += " AND kategori = ?"
        params.append(kategori)
        
    query += " ORDER BY nama"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_produk_by_id(produk_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ---------------- KATEGORI ----------------

def tambah_kategori(nama):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO kategori (nama) VALUES (?)", (nama,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Abaikan jika nama kategori sudah ada
    finally:
        conn.close()

def get_semua_kategori():
    conn = get_connection()
    rows = conn.execute("SELECT nama FROM kategori ORDER BY nama").fetchall()
    conn.close()
    return [r["nama"] for r in rows]

def update_kategori(kategori_id, nama_baru):
    conn = get_connection()
    try:
        conn.execute("UPDATE kategori SET nama=? WHERE id=?", (nama_baru, kategori_id))
        
        # (Opsional tapi disarankan) Update juga nama kategori di tabel produk agar sinkron
        # Tapi karena ini SQLite sederhana dan kita tak memisahkan id_kategori di tabel produk,
        # kita hanya biarkan dulu seperti ini.
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Abaikan jika namanya sudah dipakai kategori lain
    finally:
        conn.close()

def hapus_kategori(kategori_id):
    conn = get_connection()
    conn.execute("DELETE FROM kategori WHERE id=?", (kategori_id,))
    conn.commit()
    conn.close()

def get_kategori_lengkap():
    """Mengembalikan list of dictionary berisi id dan nama kategori."""
    conn = get_connection()
    rows = conn.execute("SELECT id, nama FROM kategori ORDER BY nama").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- TRANSAKSI ----------------

def buat_transaksi(items, dibayar):
    if not items:
        raise ValueError("Keranjang masih kosong")

    conn = get_connection()
    cur = conn.cursor()
    
    total_keuntungan = 0

    # 1. Validasi stok sekaligus mengambil Harga Beli (modal) saat ini
    for item in items:
        row = cur.execute("SELECT stok, nama, harga_beli FROM produk WHERE id=?", (item["produk_id"],)).fetchone()
        if row is None:
            conn.close()
            raise ValueError(f"Produk '{item['nama_produk']}' tidak ditemukan di database")
        if row["stok"] < item["jumlah"]:
            conn.close()
            raise ValueError(
                f"Stok '{row['nama']}' tidak cukup - tersedia {row['stok']}, diminta {item['jumlah']}"
            )
        # Simpan modal ke memory sementara (tidak masuk ke UI kasir, hanya untuk hitungan)
        item["db_harga_beli"] = row["harga_beli"]

    # 2. Hitung Total, Kembalian, dan Profit
    total = sum(item["harga_satuan"] * item["jumlah"] for item in items)
    kembalian = dibayar - total
    
    if kembalian < 0:
        conn.close()
        raise ValueError(
            f"Uang dibayar (Rp {utils.format_ribuan(dibayar)}) kurang dari total (Rp {utils.format_ribuan(total)})"
        )
        
    for item in items:
        # Profit per item = (Harga Jual - Harga Beli) x Jumlah Barang
        profit_per_item = (item["harga_satuan"] - item["db_harga_beli"]) * item["jumlah"]
        total_keuntungan += profit_per_item

    # 3. Simpan ke database
    tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO transaksi (tanggal, total, dibayar, kembalian, keuntungan) VALUES (?, ?, ?, ?, ?)",
        (tanggal, total, dibayar, kembalian, total_keuntungan),
    )
    transaksi_id = cur.lastrowid

    for item in items:
        subtotal = item["harga_satuan"] * item["jumlah"]
        cur.execute(
            """INSERT INTO transaksi_detail
               (transaksi_id, produk_id, nama_produk, harga_satuan, jumlah, subtotal, harga_beli)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (transaksi_id, item["produk_id"], item["nama_produk"],
             item["harga_satuan"], item["jumlah"], subtotal, item["db_harga_beli"]),
        )
        cur.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (item["jumlah"], item["produk_id"]))

    conn.commit()
    conn.close()
    return transaksi_id, total, kembalian


def get_riwayat_transaksi(filter_waktu="Semua Waktu"):
    conn = get_connection()
    query = "SELECT * FROM transaksi"
    params = []
    
    today = datetime.now()
    
    if filter_waktu == "Hari Ini":
        query += " WHERE tanggal LIKE ?"
        params.append(f"{today.strftime('%Y-%m-%d')}%")
    elif filter_waktu == "7 Hari Terakhir":
        tujuh_hari_lalu = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        query += " WHERE tanggal >= ?"
        params.append(tujuh_hari_lalu)
    elif filter_waktu == "Bulan Ini":
        query += " WHERE tanggal LIKE ?"
        params.append(f"{today.strftime('%Y-%m')}%")
        
    query += " ORDER BY id DESC"
    
    rows = conn.execute(query, params).fetchall()
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
