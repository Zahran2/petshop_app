"""Layar Kasir - proses transaksi penjualan."""

import customtkinter as ctk
from tkinter import messagebox
import db
import utils


class KasirFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.cart = []  # list of dict: produk_id, nama_produk, harga_satuan, jumlah, stok_tersedia
        self._current_total = 0
        self._build_ui()
        self.refresh_produk_list()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Kolom kiri: pencarian + daftar produk ---
        search_entry = ctk.CTkEntry(self, placeholder_text="🔍  Cari produk...", height=38)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.search_var = ctk.StringVar()
        search_entry.configure(textvariable=self.search_var)
        self.search_var.trace_add("write", lambda *a: self.refresh_produk_list())

        self.produk_scroll = ctk.CTkScrollableFrame(self, label_text="Daftar Produk")
        self.produk_scroll.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

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

        self.total_label = ctk.CTkLabel(cart_panel, text="Total: Rp 0",
                                          font=ctk.CTkFont(size=19, weight="bold"))
        self.total_label.grid(row=2, column=0, pady=(10, 5), padx=15, sticky="w")

        # Nielsen #5 (visibility) + #5 error prevention: tombol nonaktif kalau keranjang kosong,
        # jadi user langsung tahu belum bisa lanjut tanpa perlu coba klik dulu.
        self.bayar_btn = ctk.CTkButton(
            cart_panel, text="Bayar", height=46, corner_radius=10,
            fg_color="#D98E3F", hover_color="#BC7A32",
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self.buka_dialog_bayar,
        )
        self.bayar_btn.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))

    # ---------- Daftar produk ----------

    def refresh_produk_list(self):
        for widget in self.produk_scroll.winfo_children():
            widget.destroy()

        keyword = self.search_var.get()
        produk_list = db.get_semua_produk(keyword)

        if not produk_list:
            ctk.CTkLabel(self.produk_scroll, text="Belum ada produk. Tambahkan dulu di menu Stok.",
                         text_color=("gray50", "gray60")).pack(pady=20)
            return

        for p in produk_list:
            row = ctk.CTkFrame(self.produk_scroll, corner_radius=8)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(0, weight=1)

            sub = f"{utils.format_rupiah(p['harga_jual'])}  •  stok: {p['stok']} {p['satuan']}"
            text_col = ctk.CTkFrame(row, fg_color="transparent")
            text_col.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            ctk.CTkLabel(text_col, text=p["nama"], anchor="w", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(text_col, text=sub, anchor="w", text_color=("gray40", "gray65"),
                        font=ctk.CTkFont(size=12)).pack(anchor="w")

            add_btn = ctk.CTkButton(row, text="+ Tambah", width=90,
                                      command=lambda prod=p: self.tambah_ke_cart(prod))
            add_btn.grid(row=0, column=1, padx=12)
            if p["stok"] <= 0:
                add_btn.configure(state="disabled", text="Stok habis", fg_color="gray")

    # ---------- Keranjang ----------

    def tambah_ke_cart(self, produk):
        for item in self.cart:
            if item["produk_id"] == produk["id"]:
                if item["jumlah"] + 1 > produk["stok"]:
                    messagebox.showwarning("Stok tidak cukup", f"Stok {produk['nama']} tidak cukup")
                    return
                item["jumlah"] += 1
                self.refresh_cart()
                return

        self.cart.append({
            "produk_id": produk["id"],
            "nama_produk": produk["nama"],
            "harga_satuan": produk["harga_jual"],
            "jumlah": 1,
            "stok_tersedia": produk["stok"],
        })
        self.refresh_cart()

    def ubah_jumlah(self, item, delta):
        baru = item["jumlah"] + delta
        if baru <= 0:
            self.cart.remove(item)
        elif baru > item["stok_tersedia"]:
            messagebox.showwarning("Stok tidak cukup", "Jumlah melebihi stok yang tersedia")
            return
        else:
            item["jumlah"] = baru
        self.refresh_cart()

    def refresh_cart(self):
        for widget in self.cart_scroll.winfo_children():
            widget.destroy()

        if not self.cart:
            ctk.CTkLabel(self.cart_scroll, text="Keranjang masih kosong",
                        text_color=("gray50", "gray60")).pack(pady=20)
            self.total_label.configure(text="Total: Rp 0")
            self._current_total = 0
            self.bayar_btn.configure(state="disabled")
            return

        total = 0
        for item in self.cart:
            subtotal = item["harga_satuan"] * item["jumlah"]
            total += subtotal

            row = ctk.CTkFrame(self.cart_scroll, fg_color="transparent")
            row.pack(fill="x", pady=6)

            ctk.CTkLabel(row, text=item["nama_produk"], anchor="w",
                        font=ctk.CTkFont(size=13)).pack(fill="x")

            ctrl = ctk.CTkFrame(row, fg_color="transparent")
            ctrl.pack(fill="x")
            ctk.CTkButton(ctrl, text="-", width=26, height=26,
                         command=lambda it=item: self.ubah_jumlah(it, -1)).pack(side="left")
            ctk.CTkLabel(ctrl, text=str(item["jumlah"]), width=30).pack(side="left")
            ctk.CTkButton(ctrl, text="+", width=26, height=26,
                         command=lambda it=item: self.ubah_jumlah(it, 1)).pack(side="left")
            ctk.CTkLabel(ctrl, text=utils.format_rupiah(subtotal), anchor="e").pack(side="right", padx=4)

        self.total_label.configure(text=f"Total: {utils.format_rupiah(total)}")
        self._current_total = total
        self.bayar_btn.configure(state="normal")

    # ---------- Pembayaran ----------

    def buka_dialog_bayar(self):
        # Nielsen #3 (user control) + #5 (error prevention): review keranjang dan hitung
        # kembalian secara live SEBELUM transaksi di-commit, bukan langsung minta nominal.
        if not self.cart:
            return
        total = self._current_total

        win = ctk.CTkToplevel(self)
        win.title("Pembayaran")
        win.resizable(False, True)
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

            win.destroy()
            messagebox.showinfo(
                "Transaksi Berhasil",
                f"Transaksi #{trans_id}\n\n"
                f"Total   : {utils.format_rupiah(total_final)}\n"
                f"Dibayar : {utils.format_rupiah(dibayar)}\n"
                f"Kembali : {utils.format_rupiah(kembalian)}",
            )
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
        win.geometry(f"380x{win.winfo_reqheight() + 10}")
