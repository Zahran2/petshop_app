"""Layar Stok - kelola daftar produk (tambah, edit, hapus)."""

import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
import csv
import db
import utils
import os
import shutil
from PIL import Image

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
        
        # 1. Tambahkan Variabel & Dropdown Filter Kategori
        self.filter_kat_var = ctk.StringVar(value="Semua Kategori")
        self.filter_kat_combo = ctk.CTkComboBox(top, variable=self.filter_kat_var, height=36, 
                                                command=lambda e: self.refresh_list())
        self.filter_kat_combo.grid(row=0, column=1, padx=(0, 10))
        
        # 2. Geser kolom grid untuk tombol Kelola dan Tambah (column=2 dan 3)
        ctk.CTkButton(top, text="Kelola Kategori", height=36, fg_color="#636e72", hover_color="#2d3436",
                     command=self.buka_kelola_kategori).grid(row=0, column=2, padx=(0, 10))
                     
        ctk.CTkButton(top, text="+ Tambah Produk", height=36,
                     command=self.form_tambah).grid(row=0, column=3)

        ctk.CTkButton(top, text="⬇️ Export CSV", height=36, fg_color="#27ae60", hover_color="#2ecc71",
                     command=self.export_csv).grid(row=0, column=4, padx=(10, 0))
        
        self.filter_stok_var = ctk.BooleanVar(value=False)

        # 3. Panggil fungsi refresh filter saat UI pertama kali dibentuk
        self.refresh_kategori_filter()

        self._kolom_headings = {"nama": "Nama Produk", "kategori": "Kategori", "harga_beli": "Harga Modal", "harga_jual": "Harga Jual", "stok": "Stok", "satuan": "Satuan"}
        
        # Atur lebar kolom agar muat
        self._kolom_widths = {"nama": 200, "kategori": 120, "harga_beli": 110, "harga_jual": 110, "stok": 70, "satuan": 80}

        self._apply_treeview_style()
        columns = ("nama", "kategori", "harga_beli", "harga_jual", "stok", "satuan")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self._apply_treeview_columns()

        self.tree.grid(row=1, column=0, sticky="nsew", pady=(0, 5))
        self.tree.tag_configure("low_stock", background="#FBE0E0")

        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        
        # Label indikator warna merah (kiri)
        ctk.CTkLabel(info_row, text=f"🔴  Baris merah = stok tinggal {BATAS_STOK_MENIPIS} atau kurang",
                    text_color=("gray40", "gray65"), font=ctk.CTkFont(size=12)).pack(side="left")

        # Checkbox Filter Stok Menipis (kanan)
        ctk.CTkCheckBox(
            info_row, text="⚠️ Hanya tampilkan stok menipis", 
            variable=self.filter_stok_var, command=self.refresh_list,
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="#C0392B", fg_color="#C0392B", hover_color="#922B21"
        ).pack(side="right", padx=(0, 10))

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
            # Tambahkan command agar saat diklik memicu fungsi sorting
            self.tree.heading(col, text=teks, command=lambda c=col: self._sort_by_kolom(c, False))
            anchor = "e" if col == "harga" else ("center" if col in ("stok", "satuan") else "w")
            self.tree.column(col, width=utils.ukuran(self._kolom_widths[col]), anchor=anchor)

    def _sort_by_kolom(self, col, reverse):
        # Ambil semua data (nilai dan ID baris) dari Treeview
        data_list = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        
        # Fungsi khusus untuk mengonversi tipe data sebelum diurutkan
        def parse_data(val):
            if col == "harga":
                # Ambil hanya angka murninya saja (hapus 'Rp ' dan titik)
                bersih = "".join(c for c in val if c.isdigit())
                return int(bersih) if bersih else 0
            elif col == "stok":
                return int(val) if val.isdigit() else 0
            else:
                # Untuk teks, ubah jadi huruf kecil semua agar sortingnya konsisten (A-Z)
                return val.lower()

        # Urutkan data berdasarkan konversi tipe datanya
        data_list.sort(key=lambda t: parse_data(t[0]), reverse=reverse)

        # Geser ulang posisi baris di dalam UI (sangat ringan karena tidak query database)
        for index, (_, k) in enumerate(data_list):
            self.tree.move(k, "", index)

        # Update fungsi di judul kolom agar klik berikutnya membalik urutan (Ascending/Descending)
        self.tree.heading(col, command=lambda c=col: self._sort_by_kolom(c, not reverse))
        
        # Tambahkan indikator panah ▲ / ▼ di judul yang sedang diklik (opsional UX)
        for c, teks in self._kolom_headings.items():
            if c == col:
                panah = " ▼" if reverse else " ▲"
                self.tree.heading(c, text=teks + panah)
            else:
                self.tree.heading(c, text=teks)

    def refresh_style(self):
        """Dipanggil dari main.py pas skala teks diubah - ttk.Treeview gak
        ikut ke-scale otomatis sama CustomTkinter, jadi perlu di-refresh manual."""
        self._apply_treeview_style()
        self._apply_treeview_columns()

    def refresh_kategori_filter(self):
        """Memperbarui daftar pilihan pada dropdown filter kategori di layar stok"""
        daftar_kat = db.get_semua_kategori()
        pilihan = ["Semua Kategori"] + daftar_kat
        
        self.filter_kat_combo.configure(values=pilihan)
        # Jika kategori yang sedang difilter tiba-tiba dihapus, kembalikan ke "Semua Kategori"
        if self.filter_kat_var.get() not in pilihan:
            self.filter_kat_var.set("Semua Kategori")
            self.refresh_list()

    def refresh_list(self, highlight_id=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        keyword = self.search_var.get()
        kategori_terpilih = self.filter_kat_var.get() 
        hanya_menipis = self.filter_stok_var.get() # Ambil status checkbox (True/False)
        
        for p in db.get_semua_produk(keyword, kategori_terpilih):
            # Jika dicentang, dan stoknya masih lebih dari batas aman, abaikan (jangan ditampikan)
            if hanya_menipis and p["stok"] > BATAS_STOK_MENIPIS:
                continue
                
            tag = "low_stock" if p["stok"] <= BATAS_STOK_MENIPIS else ""
            self.tree.insert(
                "", "end", iid=str(p["id"]),
                values=(p["nama"], p["kategori"], utils.format_rupiah(p["harga_beli"]), utils.format_rupiah(p["harga_jual"]), p["stok"], p["satuan"]),
                tags=(tag,) if tag else (),
            )

        # --- TAMBAHKAN LOGIKA HIGHLIGHT DI SINI (Di luar/bawah loop for) ---
        if highlight_id:
            item_id = str(highlight_id)
            if self.tree.exists(item_id):
                self.tree.selection_set(item_id) # Blok dengan warna seleksi (biru)
                self.tree.focus(item_id)         # Fokuskan sistem ke baris tersebut
                self.tree.see(item_id)           # Otomatis scroll tabel sampai barang ini terlihat

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

    def export_csv(self):
        # Minta user memilih lokasi dan nama file
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Simpan Data Stok",
            initialfile="Data_Stok_Petshop.csv"
        )
        if not filepath: # Jika user menekan Cancel
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # 1. Tulis Header (Hapus panah sorting ▲/▼ jika ada)
                headers = [self.tree.heading(col)["text"].replace(" ▼", "").replace(" ▲", "") for col in self.tree["columns"]]
                writer.writerow(headers)

                # 2. Tulis Data Baris demi Baris
                for row_id in self.tree.get_children():
                    row_data = self.tree.item(row_id)["values"]
                    writer.writerow(row_data)

            messagebox.showinfo("Berhasil", f"Data stok berhasil diexport ke:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file:\n{str(e)}")

    def _buka_form(self, produk=None):
        self.path_gambar_baru = ""
        nama_gambar_lama = produk["gambar"] if produk and produk.get("gambar") else ""

        win = ctk.CTkToplevel(self)
        win.title("Edit Produk" if produk else "Tambah Produk")
        win.resizable(False, True)
        win.grab_set()

        labels = [
            ("nama", "Nama Produk", ""),
            ("kategori", "Kategori", ""),
            ("harga_beli", "Harga Modal / Beli (Rp)", ""),
            ("harga_jual", "Harga Jual (Rp)", ""),
            ("stok", "Stok", ""),
            ("satuan", "Satuan (pcs / kg / pack / dll)", "pcs"),
        ]

        fields = {}
        warnings = {}
        for key, label, default in labels:
            ctk.CTkLabel(win, text=label, anchor="w").pack(fill="x", padx=25, pady=(14, 2))
            
            if key == "kategori":
                cat_frame = ctk.CTkFrame(win, fg_color="transparent")
                cat_frame.pack(fill="x", padx=25)
                
                # Ambil list kategori dari database
                list_kategori = db.get_semua_kategori()
                if not list_kategori:
                    list_kategori = ["Pilih Kategori..."]
                
                # Buat variabel untuk mengontrol teks yang tampil di ComboBox
                cat_var = ctk.StringVar()
                if produk and produk.get("kategori"):
                    cat_var.set(produk["kategori"])
                else:
                    cat_var.set(list_kategori[0] if list_kategori else "")
                
                # BEDA NAMA VARIABEL: Gunakan kategori_combo agar tidak tertimpa oleh loop field lain
                kategori_combo = ctk.CTkComboBox(cat_frame, values=list_kategori, variable=cat_var, height=34)
                kategori_combo.pack(side="left", fill="x", expand=True)
                
                # Fungsi memunculkan pop-up tambah kategori baru
                def aksi_tambah_kategori():
                    dialog = ctk.CTkInputDialog(text="Nama kategori baru (misal: Dry Food):", title="Tambah Kategori")
                    kategori_baru = dialog.get_input()
                    
                    if kategori_baru and kategori_baru.strip():
                        bersih = kategori_baru.strip()
                        
                        # Simpan ke database
                        db.tambah_kategori(bersih)
                        
                        # Ambil data terbaru
                        kategori_terbaru = db.get_semua_kategori()
                        if not kategori_terbaru:
                            kategori_terbaru = ["Pilih Kategori..."]
                            
                        # Update nilai menggunakan kategori_combo (BUKAN entry)
                        kategori_combo.configure(values=kategori_terbaru)
                        
                        # Update teks yang terpilih
                        cat_var.set(bersih)
                        kategori_combo.set(bersih)
                        
                        # Paksa update tampilan
                        win.update_idletasks()

                        self.refresh_kategori_filter()
                        
                btn_plus = ctk.CTkButton(cat_frame, text="+", width=34, height=34, command=aksi_tambah_kategori)
                btn_plus.pack(side="right", padx=(8, 0))
                
                # Simpan kategori_combo ke dict fields, bukan entry
                fields[key] = kategori_combo
                continue
            
            entry = ctk.CTkEntry(win, height=34)
            entry.pack(fill="x", padx=25)

            if key in ("harga_beli", "harga_jual"):
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

        img_frame = ctk.CTkFrame(win, fg_color="transparent")
        img_frame.pack(fill="x", padx=25, pady=(15, 0))
        
        lbl_gambar = ctk.CTkLabel(img_frame, text="Gambar: " + (nama_gambar_lama or "Tidak ada"), text_color="gray")
        lbl_gambar.pack(side="left")

        def pilih_gambar():
            filepath = filedialog.askopenfilename(
                title="Pilih Gambar Produk",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
            )
            if filepath:
                self.path_gambar_baru = filepath
                lbl_gambar.configure(text="Gambar: Terpilih (Belum disimpan)", text_color="#27ae60")
                
        ctk.CTkButton(img_frame, text="Pilih Gambar", width=100, command=pilih_gambar).pack(side="right")

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

        def simpan(tutup_jendela=True):
            nama = fields["nama"].get().strip()
            kategori = fields["kategori"].get().strip()
            satuan = fields["satuan"].get().strip() or "pcs"
            
            # --- PROSES GAMBAR ---
            nama_file_gambar = nama_gambar_lama
            if self.path_gambar_baru:
                folder_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img_produk")
                os.makedirs(folder_img, exist_ok=True)
                ekstensi = os.path.splitext(self.path_gambar_baru)[1]
                import time
                nama_file_gambar = f"prod_{int(time.time())}{ekstensi}"
                tujuan = os.path.join(folder_img, nama_file_gambar)
                import shutil
                shutil.copy(self.path_gambar_baru, tujuan)

            if not nama:
                cek_nama()
                messagebox.showerror("Error", "Nama produk tidak boleh kosong")
                return
            id_sekarang = produk["id"] if produk else None
            if db.cek_nama_produk_ada(nama, id_sekarang):
                messagebox.showerror(
                    "Peringatan", 
                    f"Produk dengan nama '{nama}' sudah ada di database!\n\nSilakan gunakan nama lain atau tambahkan ukuran/rasa (misal: {nama} 500gr)."
                )
                fields["nama"].focus() # Kembalikan kursor ke kolom nama
                return
            try:
                harga_beli = utils.parse_angka(fields["harga_beli"].get())
                harga_jual = utils.parse_angka(fields["harga_jual"].get())
                stok = utils.parse_angka(fields["stok"].get())
            except ValueError:
                messagebox.showerror("Error", "Harga dan stok harus diisi dengan benar")
                return

            if produk:
                db.update_produk(produk["id"], nama, kategori, harga_beli, harga_jual, stok, satuan, nama_file_gambar)
                id_terbaru = produk["id"]
            else:
                id_terbaru = db.tambah_produk(nama, kategori, harga_beli, harga_jual, stok, satuan, nama_file_gambar)

            # Perbarui tabel dan perintahkan untuk menyorot barang terbaru
            self.refresh_list(highlight_id=id_terbaru)

            # --- LOGIKA TOMBOL BARU ---
            if tutup_jendela:
                messagebox.showinfo("Tersimpan", f"Produk '{nama}' berhasil disimpan")
                win.destroy()
            else:
                # Bersihkan form untuk barang selanjutnya
                fields["nama"].delete(0, "end")
                fields["stok"].delete(0, "end")
                
                fields["harga_beli"].delete(0, "end")
                fields["harga_beli"].insert(0, "Rp ")
                
                fields["harga_jual"].delete(0, "end")
                fields["harga_jual"].insert(0, "Rp ")
                
                self.path_gambar_baru = ""
                lbl_gambar.configure(text="Gambar: Tidak ada", text_color="gray")
                
                # Arahkan kursor balik ke kolom nama secara otomatis
                fields["nama"].focus()
                
                # Notifikasi singkat yang tidak mengganggu alur kerja
                messagebox.showinfo("Berhasil", f"'{nama}' tersimpan!\nSilakan lanjut ketik barang berikutnya.")

        def batal():
            win.destroy()

        # --- UI TOMBOL DINAMIS ---
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(pady=25, padx=25, fill="x")
        
        # Gunakan pack agar tombol membagi ruang secara otomatis dan rapi
        ctk.CTkButton(btn_row, text="Batal", height=38,
                     fg_color=("#E0E0E0", "#3A3A3A"), hover_color=("#CFCFCF", "#4A4A4A"),
                     text_color=("#333333", "#EAEAEA"),
                     command=batal).pack(side="left", expand=True, fill="x", padx=(0, 5))

        # Tombol "Simpan & Tambah Lagi" HANYA muncul jika sedang menambah barang baru (bukan edit)
        if not produk:
            ctk.CTkButton(btn_row, text="Simpan & Tambah Lagi", height=38, 
                         fg_color="#27ae60", hover_color="#2ecc71",
                         command=lambda: simpan(tutup_jendela=False)).pack(side="left", expand=True, fill="x", padx=5)

        ctk.CTkButton(btn_row, text="Simpan", height=38, fg_color="#D98E3F", hover_color="#BC7A32",
                     command=lambda: simpan(tutup_jendela=True)).pack(side="left", expand=True, fill="x", padx=(5, 0))

        # Hotkeys
        win.bind("<Return>", lambda e: simpan(tutup_jendela=True))
        win.bind("<Escape>", lambda e: batal())

        win.update_idletasks()
        win.geometry(f"420x{win.winfo_reqheight() + 10}") # Lebar ditambah sedikit (420x) agar 3 tombol tidak sempit

    def buka_kelola_kategori(self):
        win = ctk.CTkToplevel(self)
        win.title("Kelola Kategori")
        win.geometry("400x500")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Daftar Kategori", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))

        # Frame untuk daftar (bisa di-scroll)
        list_frame = ctk.CTkScrollableFrame(win)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        def refresh_kategori_list():
            # Bersihkan layar sebelum menampilkan data terbaru
            for widget in list_frame.winfo_children():
                widget.destroy()

            daftar_kat = db.get_kategori_lengkap()
            
            if not daftar_kat:
                ctk.CTkLabel(list_frame, text="Belum ada kategori", text_color="gray").pack(pady=20)
                return

            for kat in daftar_kat:
                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                
                # Nama kategori di sebelah kiri
                ctk.CTkLabel(row, text=kat["nama"], anchor="w", font=ctk.CTkFont(size=14)).pack(side="left", fill="x", expand=True)

                # Tombol Edit (Tengah)
                ctk.CTkButton(row, text="Edit", width=50, height=28, fg_color="#3498db", hover_color="#2980b9",
                              command=lambda k=kat: aksi_edit_kategori(k)).pack(side="left", padx=5)
                
                # Tombol Hapus (Kanan)
                ctk.CTkButton(row, text="Hapus", width=50, height=28, fg_color="#e74c3c", hover_color="#c0392b",
                              command=lambda k=kat: aksi_hapus_kategori(k)).pack(side="left")
            
            self.refresh_kategori_filter()

        def aksi_edit_kategori(kat):
            dialog = ctk.CTkInputDialog(text=f"Ubah nama kategori '{kat['nama']}':", title="Edit Kategori")
            nama_baru = dialog.get_input()
            if nama_baru and nama_baru.strip() and nama_baru.strip() != kat["nama"]:
                db.update_kategori(kat["id"], nama_baru.strip())
                refresh_kategori_list()
                self.refresh_list() # Opsional: refresh layar utama jika diperlukan

        def aksi_hapus_kategori(kat):
            konfirmasi = messagebox.askyesno("Hapus Kategori", f"Yakin ingin menghapus kategori '{kat['nama']}'?")
            if konfirmasi:
                db.hapus_kategori(kat["id"])
                refresh_kategori_list()

        def aksi_tambah_kategori_dari_manajer():
            dialog = ctk.CTkInputDialog(text="Nama kategori baru:", title="Tambah Kategori")
            nama_baru = dialog.get_input()
            if nama_baru and nama_baru.strip():
                db.tambah_kategori(nama_baru.strip())
                refresh_kategori_list()

        # Tombol Tambah di paling bawah
        ctk.CTkButton(win, text="+ Tambah Kategori Baru", height=40, font=ctk.CTkFont(weight="bold"),
                     command=aksi_tambah_kategori_dari_manajer).pack(fill="x", padx=20, pady=(0, 20))

        # Tampilkan data pertama kali dibuka
        refresh_kategori_list()
