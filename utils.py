"""Fungsi bantuan kecil yang dipakai di beberapa layar."""

# Skala ukuran teks aplikasi saat ini (1.0 = normal/100%). Diubah dari
# main.py lewat tombol A-/A+, dibaca dari sini oleh layar lain yang butuh
# skala manual (elemen ttk.Treeview nggak ikut ter-scale otomatis sama
# CustomTkinter, beda dari widget CTk lainnya).
skala_teks = 1.0

SKALA_MIN = 0.8
SKALA_MAX = 2.0
SKALA_STEP = 0.1


def ukuran(dasar):
    """Hitung ukuran (font/dimensi) berdasarkan skala_teks yang lagi aktif.
    Dipakai buat elemen yang gak otomatis ke-scale sama CustomTkinter."""
    return round(dasar * skala_teks)


def format_ribuan(angka):
    """Ubah angka jadi string format ribuan ala Indonesia (tanpa prefix Rp).
    Contoh: 85000 -> '85.000' (bukan '85,000')"""
    try:
        return f"{int(float(angka)):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(angka)


def format_rupiah(angka):
    """Format angka jadi 'Rp 85.000' lengkap dengan prefix, buat ditampilkan di label."""
    return f"Rp {format_ribuan(angka)}"


def parse_angka(teks):
    """Ubah teks yang mungkin mengandung titik/koma pemisah ribuan jadi
    angka murni. Contoh: '85.000' atau '85,000' -> 85000.
    Raise ValueError kalau teksnya kosong / bukan angka."""
    bersih = "".join(c for c in teks.strip() if c.isdigit())
    if not bersih:
        raise ValueError("Masukkan angka yang valid")
    return int(bersih)


def posisi_kursor_setelah_format(teks_baru, jumlah_digit_sebelum_kursor):
    """Cari index di teks_baru tepat setelah digit ke-N (dihitung dari kiri).
    Dipakai supaya kursor tetap di posisi yang masuk akal walau teksnya
    diformat ulang (titik ribuan nambah/berkurang) live saat user ngetik."""
    if jumlah_digit_sebelum_kursor <= 0:
        return 0
    hitung = 0
    for i, c in enumerate(teks_baru):
        if c.isdigit():
            hitung += 1
            if hitung == jumlah_digit_sebelum_kursor:
                return i + 1
    return len(teks_baru)


def buat_pemformat_ketik(prefix=""):
    """Bikin event handler buat CTkEntry: format ulang isinya jadi angka
    ribuan (titik) LANGSUNG saat diketik, dengan prefix opsional (misal
    'Rp '). Karakter selain angka otomatis kebuang. Kursor dijaga di posisi
    yang masuk akal dan nggak pernah masuk ke area prefix. Dipakai bareng
    buat field Harga Jual dan Dibayar supaya perilakunya konsisten."""
    def handler(event):
        entry = event.widget
        old_text = entry.get()
        cursor_pos = entry.index("insert")
        digit_sebelum_kursor = sum(1 for c in old_text[:cursor_pos] if c.isdigit())
        semua_digit = "".join(c for c in old_text if c.isdigit())
        angka_terformat = format_ribuan(semua_digit) if semua_digit else ""
        new_text = prefix + angka_terformat
        if new_text == old_text:
            return
        entry.delete(0, "end")
        entry.insert(0, new_text)
        posisi = max(len(prefix), posisi_kursor_setelah_format(new_text, digit_sebelum_kursor))
        entry.icursor(posisi)
    return handler
