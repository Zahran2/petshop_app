"""
Aplikasi Kasir & Stok Petshop
Jalankan dengan: python main.py
"""

import customtkinter as ctk
import db
import utils
from kasir_frame import KasirFrame
from stok_frame import StokFrame
from riwayat_frame import RiwayatFrame
from dashboard_frame import DashboardFrame
from login_frame import LoginFrame # <-- Import file login yang baru dibuat

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        utils.skala_teks = float(db.get_pengaturan("skala_teks", "1.0"))
        ctk.set_widget_scaling(utils.skala_teks)

        self.title("Kasir & Stok - Petshop")
        self.geometry("1050x680")
        self.minsize(900, 560)

        # Siapkan wadah (container) layar penuh
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.container_utama = ctk.CTkFrame(self, fg_color="transparent")
        self.container_utama.grid(row=0, column=0, sticky="nsew")
        self.container_utama.grid_columnconfigure(0, weight=1)
        self.container_utama.grid_rowconfigure(0, weight=1)

        # Tampilkan layar Login pertama kali
        self.tampilkan_login()

    def tampilkan_login(self):
        # Bersihkan layar jika ada komponen sisa (misal saat proses Logout)
        for widget in self.container_utama.winfo_children():
            widget.destroy()

        # Kembalikan kolom 0 agar meregang penuh dan matikan regangan kolom 1
        self.container_utama.grid_columnconfigure(0, weight=1)
        self.container_utama.grid_columnconfigure(1, weight=0)
            
        self.login_frame = LoginFrame(self.container_utama, self.masuk_sistem)
        self.login_frame.grid(row=0, column=0, sticky="nsew")

    def konfirmasi_logout(self):
        from tkinter import messagebox
        konfirmasi = messagebox.askyesno(
            "Konfirmasi Logout", 
            "Yakin ingin keluar dari sistem?\nAnda harus memasukkan PIN lagi untuk masuk."
        )
        if konfirmasi:
            self.tampilkan_login()

    def masuk_sistem(self, role):
        # Hancurkan layar login
        self.login_frame.destroy()
        
        # Ubah konfigurasi grid utama untuk memunculkan Sidebar (kolom 0) dan Konten (kolom 1)
        self.container_utama.grid_columnconfigure(0, weight=0) # Sidebar tidak meregang
        self.container_utama.grid_columnconfigure(1, weight=1) # Konten meregang penuh
        
        # Simpan hak akses pengguna saat ini
        self.role_saat_ini = role
        
        # Bangun menu dan layar sesuai jabatan
        self._build_sidebar()
        self._build_content()
        
        # Arahkan langsung ke menu Kasir sebagai beranda
        self.tampilkan("kasir")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.container_utama, width=190, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="🐾 Petshop", font=ctk.CTkFont(size=21, weight="bold")).pack(pady=(28, 4), padx=20, anchor="w")
        
        # Tampilkan status login (Admin / Kasir) di bawah logo
        teks_status = "Mode Bos/Admin" if self.role_saat_ini == "admin" else "Mode Kasir"
        warna_status = "#27ae60" if self.role_saat_ini == "admin" else "#2980b9"
        ctk.CTkLabel(self.sidebar, text=teks_status, font=ctk.CTkFont(size=12, weight="bold"), text_color=warna_status).pack(pady=(0, 25), padx=20, anchor="w")

        self.buttons = {}
        
        # MENU DINAMIS BERDASARKAN HAK AKSES
        menu_items = []
        if self.role_saat_ini == "admin":
            # Jika Admin (ayahmu): Buka semua akses
            menu_items = [
                ("kasir", "🛒  Kasir"),
                ("stok", "📦  Stok"),
                ("riwayat", "📜  Riwayat"),
                ("dashboard", "📊  Dashboard")
            ]
        else:
            # Jika Kasir (karyawan): Cuma bisa melihat mesin kasir!
            menu_items = [
                ("kasir", "🛒  Kasir")
            ]

        # Rakit tombol menu berdasarkan list di atas
        for key, label in menu_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=42, corner_radius=8,
                fg_color="transparent", text_color=("gray10", "gray90"), font=ctk.CTkFont(size=14),
                command=lambda k=key: self.tampilkan(k),
            )
            btn.pack(fill="x", padx=15, pady=4)
            self.buttons[key] = btn

        # Tombol LOGOUT di paling bawah
        ctk.CTkButton(self.sidebar, text="Keluar (Logout)", height=35, fg_color="#c0392b", hover_color="#922B21", 
                     command=self.konfirmasi_logout).pack(side="bottom", fill="x", padx=15, pady=20)

    def _build_content(self):
        self.konten_area = ctk.CTkFrame(self.container_utama, fg_color="transparent")
        self.konten_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.konten_area.grid_rowconfigure(0, weight=1)
        self.konten_area.grid_columnconfigure(0, weight=1)

        # Rakit layar yang dibutuhkan saja untuk menghemat memori
        self.frames = {"kasir": KasirFrame(self.konten_area)}
        
        # Layar rahasia hanya dibentuk jika yang login adalah admin
        if self.role_saat_ini == "admin":
            self.frames["stok"] = StokFrame(self.konten_area)
            self.frames["riwayat"] = RiwayatFrame(self.konten_area)
            self.frames["dashboard"] = DashboardFrame(self.konten_area)

        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def tampilkan(self, key):
        if hasattr(self, "_menu_saat_ini") and getattr(self, "_menu_saat_ini") == key:
            return
        self._menu_saat_ini = key

        # Ubah warna tombol aktif
        for k, btn in self.buttons.items():
            btn.configure(fg_color=("#E8C9A0", "#5A4527") if k == key else "transparent")

        # Refresh data menggunakan trik anti-lag yang sudah kita buat sebelumnya
        if key == "riwayat" and "riwayat" in self.frames:
            self.after(50, self.frames["riwayat"].refresh)
        elif key == "stok" and "stok" in self.frames:
            self.after(50, self.frames["stok"].refresh_list)
        elif key == "kasir":
            self.after(50, self.frames["kasir"].refresh_produk_list)
        elif key == "dashboard" and "dashboard" in self.frames:
             self.after(50, self.frames["dashboard"].refresh_dashboard)

        self.frames[key].tkraise()


if __name__ == "__main__":
    db.init_db()
    app = App()
    app.mainloop()