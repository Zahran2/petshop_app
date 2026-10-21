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

# Buka koneksi satu kali saja saat aplikasi berjalan (persistent connection).
# check_same_thread=False diperlukan agar aman diakses oleh UI CustomTkinter.
GLOBAL_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
GLOBAL_CONN.row_factory = sqlite3.Row
GLOBAL_CONN.execute("PRAGMA foreign_keys = ON")

def get_connection():
    """Mengembalikan koneksi global yang sudah terbuka."""
    return GLOBAL_CONN

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

    # --- Tabel Riwayat Stok & Kolom Expired ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produk_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            jumlah INTEGER NOT NULL,
            harga_beli REAL NOT NULL,
            keterangan TEXT DEFAULT 'Restock'
        )
    """)

    # Trik menyisipkan kolom expired_date tanpa merusak data lama
    try:
        cur.execute("ALTER TABLE produk ADD COLUMN expired_date TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    conn.commit()


# ---------------- PRODUK ----------------

def tambah_riwayat_stok(produk_id, jumlah, harga_beli, keterangan="Restock"):
    conn = get_connection()
    tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO riwayat_stok (produk_id, tanggal, jumlah, harga_beli, keterangan) VALUES (?, ?, ?, ?, ?)",
        (produk_id, tanggal, jumlah, harga_beli, keterangan)
    )
    conn.commit()

def tambah_produk(nama, kategori, harga_beli, harga_jual, stok, satuan="pcs", gambar="", expired_date=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO produk (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar, expired_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar, expired_date),
    )
    id_baru = cur.lastrowid
    conn.commit()
    return id_baru

def update_produk(produk_id, nama, kategori, harga_beli, harga_jual, stok, satuan, gambar, expired_date):
    conn = get_connection()
    conn.execute(
        "UPDATE produk SET nama=?, kategori=?, harga_beli=?, harga_jual=?, stok=?, satuan=?, gambar=?, expired_date=? WHERE id=?",
        (nama, kategori, harga_beli, harga_jual, stok, satuan, gambar, expired_date, produk_id),
    )
    conn.commit()


def hapus_produk(produk_id):
    conn = get_connection()
    conn.execute("DELETE FROM produk WHERE id=?", (produk_id,))
    conn.commit()


def get_semua_produk(keyword=None, kategori=None, limit=None, offset=0):
    conn = get_connection()
    query = "SELECT * FROM produk WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND nama LIKE ?"
        params.append(f"%{keyword}%")
        
    if kategori and kategori != "Semua Kategori":
        query += " AND kategori = ?"
        params.append(kategori)
        
    # Tambahkan fungsi LOWER() agar huruf besar dan kecil disetarakan saat diurutkan
    query += " ORDER BY LOWER(nama)"
    
    # Terapkan pembatasan (limit & offset) HANYA jika diminta oleh layar Kasir
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def count_semua_produk(keyword=None, kategori=None):
    """Menghitung total barang untuk menentukan jumlah halaman (Pagination)"""
    conn = get_connection()
    query = "SELECT COUNT(*) as total FROM produk WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND nama LIKE ?"
        params.append(f"%{keyword}%")
        
    if kategori and kategori != "Semua Kategori":
        query += " AND kategori = ?"
        params.append(kategori)
        
    total = conn.execute(query, params).fetchone()["total"]
    return total

def get_produk_by_id(produk_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM produk WHERE id=?", (produk_id,)).fetchone()
    return dict(row) if row else None

def cek_nama_produk_ada(nama, produk_id_kecuali=None):
    """
    Mengecek apakah nama produk sudah dipakai.
    LOWER() digunakan agar 'Whiskas' dan 'whiskas' dianggap sama.
    """
    conn = get_connection()
    if produk_id_kecuali:
        # Pengecekan saat mode Edit (abaikan nama produk itu sendiri)
        row = conn.execute(
            "SELECT id FROM produk WHERE LOWER(nama) = LOWER(?) AND id != ?", 
            (nama, produk_id_kecuali)
        ).fetchone()
    else:
        # Pengecekan saat mode Tambah Baru
        row = conn.execute(
            "SELECT id FROM produk WHERE LOWER(nama) = LOWER(?)", 
            (nama,)
        ).fetchone()
    return row is not None

# ---------------- KATEGORI ----------------

def tambah_kategori(nama):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO kategori (nama) VALUES (?)", (nama,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Abaikan jika nama kategori sudah ada
    finally:
        pass

def get_semua_kategori():
    conn = get_connection()
    rows = conn.execute("SELECT nama FROM kategori ORDER BY nama").fetchall()
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
        pass

def hapus_kategori(kategori_id):
    conn = get_connection()
    conn.execute("DELETE FROM kategori WHERE id=?", (kategori_id,))
    conn.commit()

def get_kategori_lengkap():
    """Mengembalikan list of dictionary berisi id dan nama kategori."""
    conn = get_connection()
    rows = conn.execute("SELECT id, nama FROM kategori ORDER BY nama").fetchall()
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
            raise ValueError(f"Produk '{item['nama_produk']}' tidak ditemukan di database")
        if row["stok"] < item["jumlah"]:
            raise ValueError(
                f"Stok '{row['nama']}' tidak cukup - tersedia {row['stok']}, diminta {item['jumlah']}"
            )
        # Simpan modal ke memory sementara (tidak masuk ke UI kasir, hanya untuk hitungan)
        item["db_harga_beli"] = row["harga_beli"]

    # 2. Hitung Total, Kembalian, dan Profit
    total = sum(item["harga_satuan"] * item["jumlah"] for item in items)
    kembalian = dibayar - total
    
    if kembalian < 0:
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
    return [dict(r) for r in rows]


def get_detail_transaksi(transaksi_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transaksi_detail WHERE transaksi_id=?", (transaksi_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_total_penjualan_hari_ini():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COALESCE(SUM(total), 0) as total, COUNT(*) as jumlah FROM transaksi WHERE tanggal LIKE ?",
        (f"{today}%",),
    ).fetchone()
    return dict(row)


# ---------------- PENGATURAN ----------------

def get_pengaturan(kunci, default=None):
    conn = get_connection()
    row = conn.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (kunci,)).fetchone()
    return row["nilai"] if row else default


def set_pengaturan(kunci, nilai):
    conn = get_connection()
    conn.execute(
        "INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?) "
        "ON CONFLICT(kunci) DO UPDATE SET nilai=excluded.nilai",
        (kunci, str(nilai)),
    )
    conn.commit()