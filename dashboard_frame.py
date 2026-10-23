import customtkinter as ctk
import db
import utils
from datetime import datetime, timedelta

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()
        
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- HEADER ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        ctk.CTkLabel(header_frame, text="📊 Dashboard Analitik", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        ctk.CTkButton(header_frame, text="🔄 Segarkan Data", width=120, fg_color="#3498db", hover_color="#2980b9", 
                      command=self.refresh_dashboard).pack(side="right")
        
        # --- AREA SCROLL UNTUK KONTEN ---
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=1, column=0, sticky="nsew")
        self.scroll_area.grid_columnconfigure((0, 1), weight=1)
        
        # 1. Penampung Panel Peringatan Kritis (Baru - di Row 0)
        self.frame_peringatan = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_peringatan.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # 2. Penampung Ringkasan (Geser ke Row 1)
        self.frame_ringkasan = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_ringkasan.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        self.frame_ringkasan.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        # 3. Penampung Top Produk & Top Profit (Baris 2, Kiri dan Kanan)
        self.frame_top_produk = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_top_produk.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 15))
        
        self.frame_top_profit = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_top_profit.grid(row=2, column=1, sticky="nsew", padx=(10, 0), pady=(0, 15))
        
        # 4. Penampung Top Kategori (Geser ke Baris 3, membentang penuh)
        self.frame_top_kategori = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_top_kategori.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        
        # Jalankan refresh pertama kali
        self.refresh_dashboard()

    def _buat_kartu_metrik(self, master, judul, nilai, warna_teks, kolom, sub_teks=""):
        card = ctk.CTkFrame(master, corner_radius=10)
        card.grid(row=0, column=kolom, sticky="ew", padx=5)
        
        ctk.CTkLabel(card, text=judul, font=ctk.CTkFont(size=14, weight="bold"), text_color="gray60").pack(pady=(15, 0))
        ctk.CTkLabel(card, text=nilai, font=ctk.CTkFont(size=26, weight="bold"), text_color=warna_teks).pack(pady=(5, 0))
        
        # Tambahkan sub-teks untuk data bulanan jika ada
        if sub_teks:
            ctk.CTkLabel(card, text=sub_teks, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray50").pack(pady=(0, 15))
        else:
            ctk.CTkFrame(card, height=27, fg_color="transparent").pack(pady=(0, 15)) # Pengganjal agar tinggi kartu seragam

    def _buat_list_item(self, master, judul_tabel, data_list, jenis="produk"):
        # Bersihkan frame lama
        for widget in master.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(master, text=judul_tabel, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 10))
        
        if not data_list:
            ctk.CTkLabel(master, text="Belum ada data transaksi.", text_color="gray").pack(pady=20)
            return
            
        # Header kolom
        header_row = ctk.CTkFrame(master, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header_row, text="No", width=30, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(header_row, text="Nama", anchor="w", text_color="gray").pack(side="left", expand=True, fill="x")
        ctk.CTkLabel(header_row, text="Terjual", width=60, anchor="e", text_color="gray").pack(side="right")
        
        # Isi data
        for i, row_item in enumerate(data_list):
            item = dict(row_item)
            
            row = ctk.CTkFrame(master, fg_color="transparent")
            row.pack(fill="x", pady=4)
            
            ctk.CTkLabel(row, text=f"{i+1}.", width=30, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            nama = item.get("nama_produk") if jenis in ["produk", "profit"] else item.get("kategori", "Tanpa Kategori")
            ctk.CTkLabel(row, text=nama, anchor="w").pack(side="left", expand=True, fill="x")
            
            if jenis == "profit":
                teks_kanan = utils.format_rupiah(item.get("total_profit", 0))
                warna = "#2980b9" # Biru untuk nominal profit
            else:
                teks_kanan = f"{item.get('total_qty', 0)} Terjual"
                warna = "#27ae60" # Hijau untuk jumlah barang
                
            ctk.CTkLabel(row, text=teks_kanan, width=100, anchor="e", font=ctk.CTkFont(weight="bold"), text_color=warna).pack(side="right")

    def refresh_dashboard(self):
        conn = db.get_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Tarik data semua produk untuk dievaluasi
        semua_produk = db.get_semua_produk("", "Semua Kategori")
        jml_stok_menipis = 0
        jml_hampir_expired = 0
        waktu_sekarang = datetime.now()
        
        for p in semua_produk:
            # 1. Cek Stok (Batas aman: 5)
            if p["stok"] <= 5:
                jml_stok_menipis += 1
            
            # 2. Cek Expired Date (Batas bahaya: 60 hari)
            exp_str = p.get("expired_date", "").strip()
            if exp_str:
                try:
                    if len(exp_str) == 7:
                        exp_date = datetime.strptime(exp_str, "%Y-%m")
                    else:
                        exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                        
                    if (exp_date - waktu_sekarang).days <= 60:
                        jml_hampir_expired += 1
                except ValueError:
                    pass
        
        # Bersihkan panel peringatan lama
        for widget in self.frame_peringatan.winfo_children():
            widget.destroy()
            
        # Munculkan banner merah HANYA jika ada status kritis
        if jml_stok_menipis > 0 or jml_hampir_expired > 0:
            alert_box = ctk.CTkFrame(self.frame_peringatan, fg_color="#FADBD8", border_width=1, border_color="#C0392B", corner_radius=8)
            alert_box.pack(fill="x", ipady=5)
            
            teks_alert = "⚠️ PERHATIAN: "
            if jml_stok_menipis > 0:
                teks_alert += f"{jml_stok_menipis} barang stok menipis. "
            if jml_hampir_expired > 0:
                teks_alert += f"{jml_hampir_expired} barang mendekati/sudah expired."
                
            ctk.CTkLabel(alert_box, text=teks_alert.strip(), text_color="#C0392B", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        try:
            # 1. Metrik Hari Ini & Bulan Ini
            query_transaksi = "SELECT SUM(total) as omzet, SUM(keuntungan) as profit, COUNT(id) as jml_struk FROM transaksi WHERE tanggal LIKE ?"
            
            # Tarik data HARI INI
            hasil_hari_ini = conn.execute(query_transaksi, (f"{today}%",)).fetchone()
            omzet_hari_ini = hasil_hari_ini["omzet"] or 0
            profit_hari_ini = hasil_hari_ini["profit"] or 0
            jml_struk = hasil_hari_ini["jml_struk"] or 0
            
            # Tarik data BULAN INI (Gunakan format YYYY-MM)
            bulan_ini = datetime.now().strftime('%Y-%m')
            hasil_bulan_ini = conn.execute(query_transaksi, (f"{bulan_ini}%",)).fetchone()
            omzet_bulan = hasil_bulan_ini["omzet"] or 0
            profit_bulan = hasil_bulan_ini["profit"] or 0
            struk_bulan = hasil_bulan_ini["jml_struk"] or 0

            # Cari jam berapa transaksi paling sering terjadi di bulan ini
            query_jam = """
                SELECT strftime('%H', tanggal) as jam, COUNT(id) as frekuensi
                FROM transaksi
                WHERE tanggal LIKE ?
                GROUP BY jam
                ORDER BY frekuensi DESC
                LIMIT 1
            """
            hasil_jam = conn.execute(query_jam, (f"{bulan_ini}%",)).fetchone()
            
            if hasil_jam and hasil_jam["jam"]:
                jam_awal = hasil_jam["jam"]
                # Tambah 1 jam untuk rentang (contoh: 16 -> 17) dan format selalu 2 digit (09, 10, dst)
                jam_akhir = str(int(jam_awal) + 1).zfill(2) 
                teks_jam_sibuk = f"{jam_awal}:00 - {jam_akhir}:00"
                teks_sub_jam = f"Puncak: {hasil_jam['frekuensi']} struk"
            else:
                teks_jam_sibuk = "Belum Terbaca"
                teks_sub_jam = "Butuh lebih banyak data"

            query_hari = """
                SELECT strftime('%w', tanggal) as hari_angka, COUNT(id) as frekuensi
                FROM transaksi
                WHERE tanggal LIKE ?
                GROUP BY hari_angka
                ORDER BY frekuensi DESC
                LIMIT 1
            """
            hasil_hari = conn.execute(query_hari, (f"{bulan_ini}%",)).fetchone()
            
            # Kamus penerjemah angka hari SQLite ke bahasa Indonesia
            kamus_hari = {"0": "Minggu", "1": "Senin", "2": "Selasa", "3": "Rabu", "4": "Kamis", "5": "Jumat", "6": "Sabtu"}
            
            if hasil_hari and hasil_hari["hari_angka"]:
                hari_puncak = kamus_hari.get(hasil_hari["hari_angka"], "-")
                teks_sub_hari = f"Puncak: {hasil_hari['frekuensi']} struk"
            else:
                hari_puncak = "Belum Terbaca"
                teks_sub_hari = "Butuh lebih banyak data"
            
            # Bersihkan frame ringkasan
            for widget in self.frame_ringkasan.winfo_children():
                widget.destroy()
                
            # Lempar data harian dan bulanan ke kartu metrik
            self._buat_kartu_metrik(self.frame_ringkasan, "💰 Omzet Hari Ini", utils.format_rupiah(omzet_hari_ini), "#27ae60", 0, f"Bulan ini: {utils.format_rupiah(omzet_bulan)}")
            
            self._buat_kartu_metrik(self.frame_ringkasan, "📈 Profit Hari Ini", utils.format_rupiah(profit_hari_ini), "#2980b9", 1, f"Bulan ini: {utils.format_rupiah(profit_bulan)}")
            
            self._buat_kartu_metrik(self.frame_ringkasan, "🧾 Transaksi Hari Ini", f"{jml_struk} Struk", "#d35400", 2, f"Bulan ini: {struk_bulan} Struk")

            self._buat_kartu_metrik(self.frame_ringkasan, "⏰ Jam Tersibuk", teks_jam_sibuk, "#8e44ad", 3, teks_sub_jam)

            self._buat_kartu_metrik(self.frame_ringkasan, "📅 Hari Teramai", hari_puncak, "#c0392b", 4, teks_sub_hari)
            
            # 2. Top 5 Produk Terlaris (Semua Waktu)
            query_top_produk = """
                SELECT nama_produk, SUM(jumlah) as total_qty 
                FROM transaksi_detail 
                GROUP BY produk_id 
                ORDER BY total_qty DESC 
                LIMIT 5
            """
            top_produk = conn.execute(query_top_produk).fetchall()
            self._buat_list_item(self.frame_top_produk, "🏆 Top 5 Produk Terlaris", top_produk, "produk")

            query_top_profit = """
                SELECT p.nama as nama_produk, SUM((td.harga_satuan - td.harga_beli) * td.jumlah) as total_profit
                FROM transaksi_detail td
                JOIN transaksi t ON td.transaksi_id = t.id
                JOIN produk p ON td.produk_id = p.id
                WHERE t.tanggal LIKE ?
                GROUP BY p.id
                ORDER BY total_profit DESC
                LIMIT 5
            """
            # Kita gunakan variabel bulan_ini yang sudah ada sebelumnya
            top_profit = conn.execute(query_top_profit, (f"{bulan_ini}%",)).fetchall()
            self._buat_list_item(self.frame_top_profit, "💎 Top 5 Produk Paling Profit", top_profit, "profit")
            
            # 3. Kategori Paling Laris (Semua Waktu)
            # Kita perlu JOIN dengan tabel produk karena transaksi_detail hanya menyimpan id produk
            query_top_kategori = """
                SELECT p.kategori, SUM(td.jumlah) as total_qty 
                FROM transaksi_detail td
                JOIN produk p ON td.produk_id = p.id
                GROUP BY p.kategori 
                ORDER BY total_qty DESC 
                LIMIT 5
            """
            top_kategori = conn.execute(query_top_kategori).fetchall()
            self._buat_list_item(self.frame_top_kategori, "👑 Top Kategori Terlaris", top_kategori, "kategori")
            
        except Exception as e:
            print(f"Error load dashboard: {e}")