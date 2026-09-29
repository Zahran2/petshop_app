"""Layar Kasir - proses transaksi penjualan."""

import customtkinter as ctk
from tkinter import messagebox
import db
import utils
import os
from PIL import Image

class KasirFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.cart = []  # list of dict: produk_id, nama_produk, harga_satuan, jumlah, stok_tersedia
        self._current_total = 0
        self.image_cache = {}  # <-- TAMBAHKAN BARIS INI (Wadah memori untuk menyimpan gambar)
        self.halaman_sekarang = 1
        self.batas_per_halaman = 10
        self._build_ui()
        self.refresh_produk_list()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Kolom kiri: pencarian + daftar produk ---
        search_frame = ctk.CTkFrame(self, fg_color="#F5F5F5") 
        search_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        
        self._timer_pencarian = None

        def jalankan_pencarian(*args):
            self.halaman_sekarang = 1 # Reset ke halaman 1 saat mengetik
            if self._timer_pencarian:
                self.after_cancel(self._timer_pencarian)
            self._timer_pencarian = self.after(500, self.refresh_produk_list)

        self.search_var.trace_add("write", jalankan_pencarian)
        
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, placeholder_text="🔍  Cari produk...", height=38)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Reset ke halaman 1 saat kategori diubah
        def ganti_kategori(pilihan):
            self.halaman_sekarang = 1
            self.refresh_produk_list()

        self.filter_kat_var = ctk.StringVar(value="Semua Kategori")
        self.filter_kat_combo = ctk.CTkComboBox(
            search_frame, variable=self.filter_kat_var, width=140, height=38,
            command=ganti_kategori
        )
        self.filter_kat_combo.grid(row=0, column=1)

        self.produk_scroll = ctk.CTkScrollableFrame(self, label_text="Daftar Produk")
        self.produk_scroll.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.page_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.page_frame.grid(row=2, column=0, sticky="ew", padx=(0, 10), pady=(5, 10))
        
        self.btn_prev = ctk.CTkButton(self.page_frame, text="< Sebelumnya", width=110, command=self.halaman_sebelumnya)
        self.btn_prev.pack(side="left")
        
        self.lbl_page = ctk.CTkLabel(self.page_frame, text="Hal 1 / 1", font=ctk.CTkFont(weight="bold"))
        self.lbl_page.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.page_frame, text="Selanjutnya >", width=110, command=self.halaman_selanjutnya)
        self.btn_next.pack(side="right")

        # --- Kolom kanan: keranjang ---
        cart_panel = ctk.CTkFrame(self, corner_radius=12)
        cart_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
        cart_panel.grid_rowconfigure(1, weight=1)
        cart_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cart_panel, text="Keranjang", font=ctk.CTkFont(size=17, weight="bold")).grid(
            row=0, column=0, pady=(15, 5), padx=15, sticky="w"
        )

        self.cart_scroll = ctk.CTkScrollableFrame(cart_panel, fg_color="transparent")
        self.cart_scroll.grid(row=1, column=0, sticky="nsew", padx=10)
        ctk.CTkLabel(self.cart_scroll, text="Keranjang masih kosong",
                    text_color=("gray50", "gray60")).pack(pady=20)

        bottom_bar = ctk.CTkFrame(cart_panel, fg_color="transparent")
        bottom_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 5))
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.total_label = ctk.CTkLabel(bottom_bar, text="Total: Rp 0",
                                          font=ctk.CTkFont(size=19, weight="bold"),
                                          width=250, anchor="w") # <-- Tambahkan width dan anchor di sini
        self.total_label.grid(row=0, column=0, sticky="w")

        self.btn_kosongkan = ctk.CTkButton(
            bottom_bar, text="🗑️ Kosongkan Keranjang", width=80, height=28, 
            fg_color="transparent", text_color="#C0392B", hover_color="#FADBD8",
            font=ctk.CTkFont(size=12, weight="bold"), 
            command=self.kosongkan_keranjang
        )
        self.btn_kosongkan.grid(row=0, column=1, sticky="e")

        # Hapus state="disabled"
        self.bayar_btn = ctk.CTkButton(
            cart_panel, text="Bayar", height=46, corner_radius=10,
            fg_color="#D98E3F", hover_color="#BC7A32",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.buka_dialog_bayar,
        )
        self.bayar_btn.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))

        self._update_total_keranjang()

    # ---------- Daftar produk ----------

    def refresh_kategori_filter(self):
        daftar_kat = db.get_semua_kategori()
        self.filter_kat_combo.configure(values=["Semua Kategori"] + daftar_kat)

    def halaman_sebelumnya(self):
        if self.halaman_sekarang > 1:
            self.halaman_sekarang -= 1
            self.refresh_produk_list()

    def halaman_selanjutnya(self):
        if self.halaman_sekarang < self.total_halaman:
            self.halaman_sekarang += 1
            self.refresh_produk_list()

    def refresh_produk_list(self):
        self.refresh_kategori_filter()
        
        for widget in self.produk_scroll.winfo_children():
            widget.destroy()

        keyword = self.search_var.get()
        kategori = self.filter_kat_var.get() 
        
        # --- HITUNG TOTAL HALAMAN ---
        import math
        total_data = db.count_semua_produk(keyword, kategori)
        self.total_halaman = math.ceil(total_data / self.batas_per_halaman)
        if self.total_halaman == 0:
            self.total_halaman = 1
            
        if self.halaman_sekarang > self.total_halaman:
            self.halaman_sekarang = self.total_halaman
            
        # Update teks pagination dan kunci tombol jika mentok
        self.lbl_page.configure(text=f"Halaman {self.halaman_sekarang} dari {self.total_halaman}")
        self.btn_prev.configure(state="normal" if self.halaman_sekarang > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.halaman_sekarang < self.total_halaman else "disabled")

        # --- AMBIL 30 BARANG UNTUK HALAMAN SAAT INI ---
        offset = (self.halaman_sekarang - 1) * self.batas_per_halaman
        produk_list = db.get_semua_produk(keyword, kategori, limit=self.batas_per_halaman, offset=offset)

        if not produk_list:
            ctk.CTkLabel(self.produk_scroll, text="Produk tidak ditemukan.", text_color=("gray50", "gray60")).pack(pady=20)
            return

        for p in produk_list:
            row = ctk.CTkFrame(self.produk_scroll, corner_radius=8, fg_color="#FFFFFF")
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(1, weight=1)

            # --- RENDER GAMBAR DENGAN CACHE ---
            img_path = ""
            if p.get("gambar"):
                folder_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img_produk")
                img_path = os.path.join(folder_img, p["gambar"])
            
            if img_path and os.path.exists(img_path):
                # 1. Cek apakah gambar SUDAH ADA di dalam memori cache
                if img_path not in self.image_cache:
                    # 2. Jika belum ada, baru baca dari hardisk dan simpan ke cache
                    pil_img = Image.open(img_path)
                    self.image_cache[img_path] = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(50, 50))
                
                # 3. Gunakan gambar yang sudah standby di memori
                lbl_img = ctk.CTkLabel(row, image=self.image_cache[img_path], text="")
            else:
                lbl_img = ctk.CTkLabel(row, text="🖼️", font=ctk.CTkFont(size=25), width=50, height=50, fg_color="#e0e0e0", corner_radius=6)
            
            lbl_img.grid(row=0, column=0, padx=(10, 0), pady=8)
            # ---------------------

            sub = f"{utils.format_rupiah(p['harga_jual'])}  •  stok: {p['stok']} {p['satuan']}"
            text_col = ctk.CTkFrame(row, fg_color="transparent")
            text_col.grid(row=0, column=1, sticky="ew", padx=12, pady=8)
            ctk.CTkLabel(text_col, text=p["nama"], anchor="w", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(text_col, text=sub, anchor="w", text_color=("gray40", "gray65"),
                        font=ctk.CTkFont(size=12)).pack(anchor="w")

            add_btn = ctk.CTkButton(row, text="+ Tambah", width=90,
                                      command=lambda prod=p: self.tambah_ke_cart(prod))
            add_btn.grid(row=0, column=2, padx=12)
            if p["stok"] <= 0:
                add_btn.configure(state="disabled", text="Stok habis", fg_color="gray")

    # ---------- Keranjang ----------

    def _update_total_keranjang(self):
        total = sum(item["harga_satuan"] * item["jumlah"] for item in self.cart)
        self.total_label.configure(text=f"Total: {utils.format_rupiah(total)}")
        self._current_total = total
        
        # --- TRIK UX: FAKE DISABLED STATE ---
        if len(self.cart) > 0:
            # Tampilan Aktif (Menyala)
            self.bayar_btn.configure(fg_color="#D98E3F", hover_color="#BC7A32", text_color="white")
            if hasattr(self, 'btn_kosongkan'):
                self.btn_kosongkan.configure(text_color="#C0392B", hover_color="#FADBD8")
        else:
            # Tampilan Nonaktif (Abu-abu pudar)
            self.bayar_btn.configure(fg_color="#E0E0E0", hover_color="#E0E0E0", text_color="#A0A0A0")
            if hasattr(self, 'btn_kosongkan'):
                self.btn_kosongkan.configure(text_color="#A0A0A0", hover_color="#EBEBEB")

    def hapus_dari_cart(self, item):
        if item in self.cart:
            self.cart.remove(item)
            if "ui_row" in item:
                item["ui_row"].destroy() # Hancurkan satu baris ini saja secara instan
            
            if not self.cart:
                self.refresh_cart() # Jika habis, panggil refresh agar teks "Keranjang kosong" muncul
            else:
                self._update_total_keranjang()

    def kosongkan_keranjang(self):
        if not self.cart:
            return
        konfirmasi = messagebox.askyesno("Kosongkan Keranjang", "Yakin ingin menghapus semua barang dari keranjang?")
        if konfirmasi:
            self.cart = []
            self.refresh_cart()

    def _gambar_satu_baris(self, item):
        row = ctk.CTkFrame(self.cart_scroll, fg_color="transparent")
        row.pack(fill="x", pady=6)
        item["ui_row"] = row 

        ctk.CTkLabel(row, text=item["nama_produk"], anchor="w",
                    font=ctk.CTkFont(size=13)).pack(fill="x")

        ctrl = ctk.CTkFrame(row, fg_color="transparent")
        ctrl.pack(fill="x")
        
        ctk.CTkButton(ctrl, text="-", width=26, height=26,
                     command=lambda it=item: self.ubah_jumlah(it, -1)).pack(side="left")
        
        # KUNCI 2: Skala sudah 100%, kembali pakai StringVar + CTkLabel. Super instan!
        item["var_jumlah"] = ctk.StringVar(value=str(item["jumlah"]))
        lbl_jumlah = ctk.CTkLabel(ctrl, textvariable=item["var_jumlah"], width=35, justify="center")
        lbl_jumlah.pack(side="left")
        
        ctk.CTkButton(ctrl, text="+", width=26, height=26,
                     command=lambda it=item: self.ubah_jumlah(it, 1)).pack(side="left")
        
        ctk.CTkButton(ctrl, text="X", width=26, height=26, 
                     fg_color="#C0392B", hover_color="#922B21", font=ctk.CTkFont(weight="bold"),
                     command=lambda it=item: self.hapus_dari_cart(it)).pack(side="right")
                     
        subtotal = item["harga_satuan"] * item["jumlah"]
        item["var_subtotal"] = ctk.StringVar(value=utils.format_rupiah(subtotal))
        lbl_subtotal = ctk.CTkLabel(ctrl, textvariable=item["var_subtotal"], width=110, anchor="e")
        lbl_subtotal.pack(side="right", padx=(0, 10))

    def tambah_ke_cart(self, produk):
        for item in self.cart:
            if item["produk_id"] == produk["id"]:
                if item["jumlah"] + 1 > produk["stok"]:
                    messagebox.showwarning("Stok tidak cukup", f"Stok {produk['nama']} tidak cukup")
                    return
                item["jumlah"] += 1
                
                # Update teks secara instan (tanpa bongkar pasang frame)
                if "var_jumlah" in item:
                    item["var_jumlah"].set(str(item["jumlah"]))
                    item["var_subtotal"].set(utils.format_rupiah(item["harga_satuan"] * item["jumlah"]))
                
                self._update_total_keranjang()
                return

        item_baru = {
            "produk_id": produk["id"],
            "nama_produk": produk["nama"],
            "harga_satuan": produk["harga_jual"],
            "jumlah": 1,
            "stok_tersedia": produk["stok"],
        }
        self.cart.append(item_baru)
        
        # Hapus label kosong jika ini barang pertama
        if len(self.cart) == 1:
            for widget in self.cart_scroll.winfo_children():
                widget.destroy()
                
        self._gambar_satu_baris(item_baru)
        self._update_total_keranjang()

    def ubah_jumlah(self, item, delta):
        baru = item["jumlah"] + delta
        if baru <= 0:
            self.hapus_dari_cart(item)
            return
        elif baru > item["stok_tersedia"]:
            messagebox.showwarning("Stok tidak cukup", "Jumlah melebihi stok yang tersedia")
            return
        else:
            item["jumlah"] = baru
            
            # Update teks secara instan
            if "var_jumlah" in item:
                item["var_jumlah"].set(str(item["jumlah"]))
                item["var_subtotal"].set(utils.format_rupiah(item["harga_satuan"] * item["jumlah"]))
            
            self._update_total_keranjang()

    def refresh_cart(self):
        for widget in self.cart_scroll.winfo_children():
            widget.destroy()

        if not self.cart:
            ctk.CTkLabel(self.cart_scroll, text="Keranjang masih kosong",
                        text_color=("gray50", "gray60")).pack(pady=20)
            
            # --- KUNCI PERBAIKAN ---
            # Wajib dipanggil agar sistem mengubah warna tombol jadi abu-abu
            self._update_total_keranjang() 
            return

        for item in self.cart:
            self._gambar_satu_baris(item)

        self._update_total_keranjang()
        
    # ---------- Pembayaran ----------

    def buka_dialog_bayar(self):
        # Nielsen #3 (user control) + #5 (error prevention): review keranjang dan hitung
        # kembalian secara live SEBELUM transaksi di-commit, bukan langsung minta nominal.
        if not self.cart:
            return
        total = self._current_total

        win = ctk.CTkToplevel(self)
        win.title("Pembayaran")
        win.resizable(True, True)
        win.grab_set()

        ctk.CTkLabel(win, text="Ringkasan Belanja", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=20, pady=(18, 8)
        )

        ringkasan_box = ctk.CTkTextbox(win, height=110, width=320)
        ringkasan_box.pack(padx=20, fill="x")
        for item in self.cart:
            subtotal = item["harga_satuan"] * item["jumlah"]
            ringkasan_box.insert(
                "end", f"{item['nama_produk']}  x{item['jumlah']}  =  {utils.format_rupiah(subtotal)}\n"
            )
        ringkasan_box.configure(state="disabled")

        ctk.CTkLabel(win, text=f"Total: {utils.format_rupiah(total)}",
                    font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", padx=20, pady=(12, 5))

        ctk.CTkLabel(win, text="Uang Dibayar (Rp)", anchor="w").pack(fill="x", padx=20, pady=(8, 2))
        dibayar_entry = ctk.CTkEntry(win, height=36)
        dibayar_entry.pack(fill="x", padx=20)
        dibayar_entry.insert(0, "Rp ")
        dibayar_entry.focus()
        dibayar_entry.icursor("end")

        quick_frame = ctk.CTkFrame(win, fg_color="transparent")
        quick_frame.pack(fill="x", padx=20, pady=(8, 0))
        
        # Bagi frame menjadi 3 kolom dengan proporsi ukuran persis sama besar
        quick_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def set_dibayar(nominal):
            dibayar_entry.delete(0, "end")
            dibayar_entry.insert(0, utils.format_rupiah(nominal))
            update_kembalian() 

        # Tombol Uang Pas (Warna Hijau)
        ctk.CTkButton(quick_frame, text="Uang Pas", height=28,
                      fg_color="#27ae60", hover_color="#2ecc71", font=ctk.CTkFont(size=12, weight="bold"),
                      command=lambda: set_dibayar(total)).grid(row=0, column=0, sticky="ew", padx=(0, 4))
                      
        # Tombol 50 Ribu (Warna Biru)
        ctk.CTkButton(quick_frame, text="Rp 50.000", height=28,
                      fg_color="#3498db", hover_color="#2980b9", font=ctk.CTkFont(size=12, weight="bold"),
                      command=lambda: set_dibayar(50000)).grid(row=0, column=1, sticky="ew", padx=4)
                      
        # Tombol 100 Ribu (Warna Biru)
        ctk.CTkButton(quick_frame, text="Rp 100.000", height=28,
                      fg_color="#3498db", hover_color="#2980b9", font=ctk.CTkFont(size=12, weight="bold"),
                      command=lambda: set_dibayar(100000)).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        kembalian_label = ctk.CTkLabel(win, text="Kembalian: -", font=ctk.CTkFont(size=13),
                                         text_color=("gray40", "gray65"))
        kembalian_label.pack(anchor="w", padx=20, pady=(8, 0))

        def update_kembalian(event=None):
            try:
                dibayar = utils.parse_angka(dibayar_entry.get())
            except ValueError:
                kembalian_label.configure(text="Kembalian: -", text_color=("gray40", "gray65"))
                return
            sisa = dibayar - total
            if sisa < 0:
                kembalian_label.configure(text=f"Kurang {utils.format_rupiah(abs(sisa))}", text_color="#C0392B")
            else:
                kembalian_label.configure(text=f"Kembalian: {utils.format_rupiah(sisa)}",
                                          text_color=("gray40", "gray65"))

        # Nielsen #5 (error prevention): sama seperti Harga Jual di form Stok -
        # format ribuan + prefix "Rp " langsung LIVE saat diketik, karakter
        # selain angka otomatis kebuang.
        dibayar_entry.bind("<KeyRelease>", utils.buat_pemformat_ketik(prefix="Rp "))
        dibayar_entry.bind("<KeyRelease>", update_kembalian, add="+")

        def batal():
            win.destroy()

        def konfirmasi_bayar():
            try:
                dibayar = utils.parse_angka(dibayar_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Masukkan jumlah uang yang valid")
                return

            try:
                trans_id, total_final, kembalian = db.buat_transaksi(self.cart, dibayar)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return

            win.destroy() # Tutup dialog pembayaran
            
            # --- AWAL PERUBAHAN ---
            # Hapus messagebox.showinfo dan ganti dengan toast melayang
            pesan_sukses = f"✅ Transaksi #{trans_id} Berhasil! Kembalian: {utils.format_rupiah(kembalian)}"
            self.tampilkan_toast(pesan_sukses)
            # --- AKHIR PERUBAHAN ---

            self.cart = []
            self.refresh_cart()
            self.refresh_produk_list()

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(pady=20, padx=20, fill="x")
        btn_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_row, text="Batal", height=40,
                     fg_color=("#E0E0E0", "#3A3A3A"), hover_color=("#CFCFCF", "#4A4A4A"),
                     text_color=("#333333", "#EAEAEA"),
                     command=batal).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Bayar", height=40, fg_color="#D98E3F", hover_color="#BC7A32",
                     font=ctk.CTkFont(weight="bold"),
                     command=konfirmasi_bayar).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Nielsen #7 (flexibility/efficiency): Enter = konfirmasi, Esc = batal.
        # Berguna karena dialog ini dibuka berkali-kali tiap hari.
        win.bind("<Return>", lambda e: konfirmasi_bayar())
        win.bind("<Escape>", lambda e: batal())

        win.update_idletasks()
        win.geometry(f"450x{win.winfo_reqheight() + 10}")

    def tampilkan_toast(self, pesan):
        # Buat label melayang dengan warna background hijau
        toast = ctk.CTkLabel(
            self, text=pesan, fg_color="#27ae60", text_color="white",
            corner_radius=8, font=ctk.CTkFont(size=14, weight="bold"),
            padx=20, pady=10
        )
        # Posisikan melayang (floating) di tengah atas layar
        toast.place(relx=0.5, rely=0.05, anchor="n")
        
        # Perintahkan aplikasi untuk menghancurkan (menghapus) toast ini setelah 5000 ms (5 detik)
        self.after(5000, toast.destroy)