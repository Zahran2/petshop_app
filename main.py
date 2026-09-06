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

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

MENU_ITEMS = [
    ("kasir", "🛒  Kasir"),
    ("stok", "📦  Stok"),
    ("riwayat", "🧾  Riwayat"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Muat skala teks yang tersimpan (kalau ada) SEBELUM widget dibikin,
        # biar langsung tampil di ukuran yang bener dari awal, gak "lompat".
        utils.skala_teks = float(db.get_pengaturan("skala_teks", "1.0"))
        ctk.set_widget_scaling(utils.skala_teks)

        self.title("Kasir & Stok - Petshop")
        self.geometry("1050x680")
        self.minsize(900, 560)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()
        self.tampilkan("kasir")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=190, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="🐾 Petshop", font=ctk.CTkFont(size=21, weight="bold")).pack(
            pady=(28, 4), padx=20, anchor="w"
        )
        ctk.CTkLabel(sidebar, text="Kasir & Stok", font=ctk.CTkFont(size=12),
                    text_color=("gray40", "gray65")).pack(pady=(0, 25), padx=20, anchor="w")

        self.buttons = {}
        for key, label in MENU_ITEMS:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w", height=42, corner_radius=8,
                fg_color="transparent", text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self.tampilkan(k),
            )
            btn.pack(fill="x", padx=15, pady=4)
            self.buttons[key] = btn

        # Kontrol ukuran teks - ditaruh di BAWAH sidebar (side="bottom") biar
        # selalu keliatan di layar mana pun, gak ketiban menu navigasi.
        skala_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        skala_frame.pack(side="bottom", fill="x", padx=15, pady=20)

        ctk.CTkLabel(skala_frame, text="Ukuran Teks", font=ctk.CTkFont(size=11),
                    text_color=("gray40", "gray65")).pack(anchor="w", pady=(0, 6))

        tombol_row = ctk.CTkFrame(skala_frame, fg_color="transparent")
        tombol_row.pack(fill="x")
        tombol_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_kecil = ctk.CTkButton(tombol_row, text="A-", width=44, height=34,
                                        font=ctk.CTkFont(size=13),
                                        command=self.perkecil_teks)
        self.btn_kecil.grid(row=0, column=0, padx=(0, 4))

        self.skala_label = ctk.CTkLabel(tombol_row, text="100%", font=ctk.CTkFont(size=12),
                                         text_color=("gray30", "gray80"))
        self.skala_label.grid(row=0, column=1)
        self.skala_label.bind("<Button-1>", lambda e: self.reset_skala())

        self.btn_besar = ctk.CTkButton(tombol_row, text="A+", width=44, height=34,
                                        font=ctk.CTkFont(size=15),
                                        command=self.perbesar_teks)
        self.btn_besar.grid(row=0, column=2, padx=(4, 0))

        ctk.CTkLabel(skala_frame, text="Klik angka % buat reset", font=ctk.CTkFont(size=10),
                    text_color=("gray55", "gray50")).pack(anchor="w", pady=(4, 0))

        self._perbarui_kontrol_skala()

    def _build_content(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {
            "kasir": KasirFrame(self.container),
            "stok": StokFrame(self.container),
            "riwayat": RiwayatFrame(self.container),
        }
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def tampilkan(self, key):
        self.frames[key].tkraise()
        if key == "riwayat":
            self.frames["riwayat"].refresh()
        elif key == "stok":
            self.frames["stok"].refresh_list()
        elif key == "kasir":
            self.frames["kasir"].refresh_produk_list()

        for k, btn in self.buttons.items():
            is_active = k == key
            btn.configure(fg_color=("#E8C9A0", "#5A4527") if is_active else "transparent")

    def _perbarui_kontrol_skala(self):
        self.skala_label.configure(text=f"{round(utils.skala_teks * 100)}%")
        self.btn_kecil.configure(state="disabled" if utils.skala_teks <= utils.SKALA_MIN else "normal")
        self.btn_besar.configure(state="disabled" if utils.skala_teks >= utils.SKALA_MAX else "normal")

    def terapkan_skala(self, skala_baru):
        skala_baru = round(max(utils.SKALA_MIN, min(utils.SKALA_MAX, skala_baru)), 1)
        if skala_baru == utils.skala_teks:
            return
        utils.skala_teks = skala_baru
        ctk.set_widget_scaling(skala_baru)
        db.set_pengaturan("skala_teks", skala_baru)
        self._perbarui_kontrol_skala()
        # ttk.Treeview (tabel Stok & Riwayat) gak ikut ke-scale otomatis sama
        # CustomTkinter, jadi perlu di-refresh manual.
        self.frames["stok"].refresh_style()
        self.frames["riwayat"].refresh_style()

    def perbesar_teks(self):
        self.terapkan_skala(utils.skala_teks + utils.SKALA_STEP)

    def perkecil_teks(self):
        self.terapkan_skala(utils.skala_teks - utils.SKALA_STEP)

    def reset_skala(self):
        self.terapkan_skala(1.0)


if __name__ == "__main__":
    db.init_db()
    app = App()
    app.mainloop()
