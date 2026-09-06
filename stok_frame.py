"""Layar Stok - kelola daftar produk (tambah, edit, hapus)."""

import customtkinter as ctk
from tkinter import messagebox, ttk
import db
import utils

BATAS_STOK_MENIPIS = 5


class StokFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_list())
        ctk.CTkEntry(top, placeholder_text="🔍  Cari produk...", height=36,
                    textvariable=self.search_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(top, text="+ Tambah Produk", height=36,
                     command=self.form_tambah).grid(row=0, column=1)

        self._kolom_headings = {"nama": "Nama Produk", "kategori": "Kategori", "harga": "Harga Jual",
                                 "stok": "Stok", "satuan": "Satuan"}
        self._kolom_widths = {"nama": 220, "kategori": 140, "harga": 110, "stok": 80, "satuan": 90}

        self._apply_treeview_style()
        columns = ("nama", "kategori", "harga", "stok", "satuan")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self._apply_treeview_columns()

        self.tree.grid(row=1, column=0, sticky="nsew", pady=(0, 5))
        self.tree.tag_configure("low_stock", background="#FBE0E0")

        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        ctk.CTkLabel(info_row, text=f"🔴  Baris merah = stok tinggal {BATAS_STOK_MENIPIS} atau kurang",
                    text_color=("gray40", "gray65"), font=ctk.CTkFont(size=12)).pack(side="left")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ctk.CTkButton(btn_frame, text="Edit", width=100, command=self.form_edit).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Hapus", width=100, fg_color="#C0392B", hover_color="#922B21",
                     command=self.hapus_terpilih).pack(side="left")

    def _apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=utils.ukuran(30), font=("Segoe UI", utils.ukuran(11)),
                        borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", utils.ukuran(11), "bold"))
        style.map("Treeview", background=[("selected", "#D98E3F")])

    def _apply_treeview_columns(self):
        for col, teks in self._kolom_headings.items():
            self.tree.heading(col, text=teks)
            anchor = "e" if col == "harga" else ("center" if col in ("stok", "satuan") else "w")
            self.tree.column(col, width=utils.ukuran(self._kolom_widths[col]), anchor=anchor)

    def refresh_style(self):
        """Dipanggil dari main.py pas skala teks diubah - ttk.Treeview gak
        ikut ke-scale otomatis sama CustomTkinter, jadi perlu di-refresh manual."""
        self._apply_treeview_style()
        self._apply_treeview_columns()

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        keyword = self.search_var.get()
        for p in db.get_semua_produk(keyword):
            tag = "low_stock" if p["stok"] <= BATAS_STOK_MENIPIS else ""
            self.tree.insert(
                "", "end", iid=str(p["id"]),
                values=(p["nama"], p["kategori"], utils.format_rupiah(p["harga_jual"]), p["stok"], p["satuan"]),
                tags=(tag,) if tag else (),
            )

    def form_tambah(self):
        self._buka_form()

    def form_edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Pilih produk", "Pilih dulu produk yang mau diedit")
            return
        produk = db.get_produk_by_id(int(sel[0]))
        self._buka_form(produk)

    def hapus_terpilih(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Pilih produk", "Pilih dulu produk yang mau dihapus")
            return
        produk = db.get_produk_by_id(int(sel[0]))
        if messagebox.askyesno("Konfirmasi Hapus", f"Hapus produk '{produk['nama']}'?\n\n"
                                "Riwayat transaksi yang sudah ada tidak akan terpengaruh."):
            db.hapus_produk(produk["id"])
            self.refresh_list()

    def _buka_form(self, produk=None):
        win = ctk.CTkToplevel(self)
        win.title("Edit Produk" if produk else "Tambah Produk")
        win.resizable(False, True)
        win.grab_set()

        labels = [
            ("nama", "Nama Produk", ""),
            ("kategori", "Kategori", ""),
            ("harga_jual", "Harga Jual (Rp)", ""),
            ("stok", "Stok", ""),
            ("satuan", "Satuan (pcs / kg / pack / dll)", "pcs"),
        ]

        fields = {}
        warnings = {}
        for key, label, default in labels:
            ctk.CTkLabel(win, text=label, anchor="w").pack(fill="x", padx=25, pady=(14, 2))
            entry = ctk.CTkEntry(win, height=34)
            entry.pack(fill="x", padx=25)

            if key == "harga_jual":
                # "Rp " selalu ada di depan, bahkan pas kosong - biar user
                # langsung ngerti ini field duit dari awal lihat.
                entry.insert(0, "Rp " + utils.format_ribuan(produk[key]) if produk else "Rp ")
                entry.icursor("end")
                entry.bind("<KeyRelease>", utils.buat_pemformat_ketik(prefix="Rp "))
            elif key == "stok":
                if produk:
                    entry.insert(0, utils.format_ribuan(produk[key]))
                entry.bind("<KeyRelease>", utils.buat_pemformat_ketik())
            elif produk:
                entry.insert(0, str(produk[key]))
            elif default:
                entry.insert(0, default)
            fields[key] = entry

            # Nielsen #5 (error prevention): label peringatan kecil di bawah tiap
            # field wajib, terisi begitu user pindah/kosongin - bukan nunggu
            # sampai klik Simpan. Cek "harus angka" udah nggak relevan lagi buat
            # harga/stok karena karakter selain angka sekarang gak bisa masuk sama sekali.
            if key in ("nama", "harga_jual", "stok"):
                warn = ctk.CTkLabel(win, text="", text_color="#C0392B",
                                    font=ctk.CTkFont(size=11), anchor="w", height=16)
                warn.pack(fill="x", padx=25)
                warnings[key] = warn

        def cek_nama(event=None):
            warnings["nama"].configure(text="Nama tidak boleh kosong" if not fields["nama"].get().strip() else "")

        def cek_harga(saat_keluar=False):
            # "Rp " selalu ada, jadi field ini gak pernah string kosong -
            # cek yang bener adalah "ada digit apa nggak", bukan "ada isi apa nggak".
            kosong = not any(c.isdigit() for c in fields["harga_jual"].get())
            warnings["harga_jual"].configure(text="Harga tidak boleh kosong" if (kosong and saat_keluar) else "")

        def cek_stok(saat_keluar=False):
            kosong = not fields["stok"].get().strip()
            warnings["stok"].configure(text="Stok tidak boleh kosong" if (kosong and saat_keluar) else "")

        fields["nama"].bind("<FocusOut>", cek_nama, add="+")
        fields["harga_jual"].bind("<KeyRelease>", lambda e: cek_harga(False), add="+")
        fields["harga_jual"].bind("<FocusOut>", lambda e: cek_harga(True), add="+")
        fields["stok"].bind("<KeyRelease>", lambda e: cek_stok(False), add="+")
        fields["stok"].bind("<FocusOut>", lambda e: cek_stok(True), add="+")

        def simpan():
            nama = fields["nama"].get().strip()
            kategori = fields["kategori"].get().strip()
            satuan = fields["satuan"].get().strip() or "pcs"

            if not nama:
                cek_nama()
                messagebox.showerror("Error", "Nama produk tidak boleh kosong")
                return
            try:
                harga = utils.parse_angka(fields["harga_jual"].get())
                stok = utils.parse_angka(fields["stok"].get())
            except ValueError:
                cek_harga(True)
                cek_stok(True)
                messagebox.showerror("Error", "Harga dan stok tidak boleh kosong")
                return

            if produk:
                db.update_produk(produk["id"], nama, kategori, harga, stok, satuan)
            else:
                db.tambah_produk(nama, kategori, harga, stok, satuan)

            messagebox.showinfo("Tersimpan", f"Produk '{nama}' berhasil disimpan")
            win.destroy()
            self.refresh_list()

        def batal():
            win.destroy()

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(pady=25, padx=25, fill="x")
        btn_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_row, text="Batal", height=38,
                     fg_color=("#E0E0E0", "#3A3A3A"), hover_color=("#CFCFCF", "#4A4A4A"),
                     text_color=("#333333", "#EAEAEA"),
                     command=batal).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Simpan", height=38, fg_color="#D98E3F", hover_color="#BC7A32",
                     command=simpan).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Nielsen #7 (flexibility/efficiency): Enter = simpan, Esc = batal
        win.bind("<Return>", lambda e: simpan())
        win.bind("<Escape>", lambda e: batal())

        win.update_idletasks()
        win.geometry(f"380x{win.winfo_reqheight() + 10}")
