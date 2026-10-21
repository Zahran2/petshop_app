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
        
        # Tempat penampung data (akan diisi oleh fungsi refresh)
        self.frame_ringkasan = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_ringkasan.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        self.frame_ringkasan.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.frame_top_produk = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_top_produk.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        
        self.frame_top_kategori = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.frame_top_kategori.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        
        # Jalankan refresh pertama kali
        self.refresh_dashboard()

    def _buat_kartu_metrik(self, master, judul, nilai, warna_teks, kolom):
        card = ctk.CTkFrame(master, corner_radius=10)
        card.grid(row=0, column=kolom, sticky="ew", padx=5)
        
        ctk.CTkLabel(card, text=judul, font=ctk.CTkFont(size=14, weight="bold"), text_color="gray60").pack(pady=(15, 5))
        ctk.CTkLabel(card, text=nilai, font=ctk.CTkFont(size=22, weight="bold"), text_color=warna_teks).pack(pady=(0, 15))

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
        for i, item in enumerate(data_list):
            row = ctk.CTkFrame(master, fg_color="transparent")
            row.pack(fill="x", pady=4)
            
            ctk.CTkLabel(row, text=f"{i+1}.", width=30, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            nama = item.get("nama_produk") if jenis == "produk" else item.get("kategori", "Tanpa Kategori")
            ctk.CTkLabel(row, text=nama, anchor="w").pack(side="left", expand=True, fill="x")
            
            qty = str(item["total_qty"])
            ctk.CTkLabel(row, text=qty, width=60, anchor="e", font=ctk.CTkFont(weight="bold"), text_color="#27ae60").pack(side="right")

    def refresh_dashboard(self):
        conn = db.get_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 1. Metrik Hari Ini (Omzet & Profit)
            # Karena struktur db.py milikmu menyimpan profit per struk (kolom keuntungan di tabel transaksi)
            query_hari_ini = "SELECT SUM(total) as omzet, SUM(keuntungan) as profit, COUNT(id) as jml_struk FROM transaksi WHERE tanggal LIKE ?"
            hasil_hari_ini = conn.execute(query_hari_ini, (f"{today}%",)).fetchone()
            
            omzet_hari_ini = hasil_hari_ini["omzet"] or 0
            profit_hari_ini = hasil_hari_ini["profit"] or 0
            jml_struk = hasil_hari_ini["jml_struk"] or 0
            
            # Bersihkan frame ringkasan
            for widget in self.frame_ringkasan.winfo_children():
                widget.destroy()
                
            self._buat_kartu_metrik(self.frame_ringkasan, "💰 Omzet Hari Ini", utils.format_rupiah(omzet_hari_ini), "#27ae60", 0)
            self._buat_kartu_metrik(self.frame_ringkasan, "📈 Profit Hari Ini", utils.format_rupiah(profit_hari_ini), "#2980b9", 1)
            self._buat_kartu_metrik(self.frame_ringkasan, "🧾 Transaksi Hari Ini", f"{jml_struk} Struk", "#d35400", 2)
            
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