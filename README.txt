APLIKASI KASIR & STOK PETSHOP
==============================

CARA MENJALANKAN (Windows)
1. Install Python dari https://python.org (saat instalasi, centang "Add
   python.exe to PATH").
2. Buka folder ini, lalu buka Command Prompt di folder ini
   (klik kanan folder > "Open in Terminal", atau ketik cmd di address bar).
3. Jalankan sekali saja:  py -m pip install -r requirements.txt
   (kalau command "python" saja error soal Microsoft Store, pakai "py"
   seperti di atas - itu launcher terpisah yang lebih reliable di Windows)
4. Setelah itu, cukup double-click run.bat setiap mau buka aplikasinya.
   (atau jalankan manual dengan: py main.py)

STRUKTUR FILE
- main.py           -> jalankan file ini untuk membuka aplikasi
- db.py              -> semua logika penyimpanan data (SQLite)
- kasir_frame.py      -> layar Kasir
- stok_frame.py       -> layar Stok
- riwayat_frame.py    -> layar Riwayat transaksi
- petshop.db          -> file database, otomatis dibuat saat pertama kali
                         dijalankan. Ini yang menyimpan semua data produk
                         dan transaksi. JANGAN dihapus kalau tidak mau
                         kehilangan data. Cadangkan (copy) file ini
                         sesekali sebagai backup.

CATATAN
- Semua data tersimpan lokal di laptop ini saja (tidak perlu internet).
- Belum ada fitur cetak struk ke printer - transaksi selesai ditampilkan
  di layar dulu. Bisa ditambahkan belakangan kalau sudah perlu.
