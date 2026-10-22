"""Layar Riwayat - lihat riwayat transaksi dan ringkasan penjualan hari ini."""

import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import csv
import db
import utils


class RiwayatFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Memastikan tabel treeview yang meluas

        # --- PERBAIKAN TATA LETAK PANEL ATAS (Menggunakan pack) ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # 1. Pasang Tombol & Dropdown di sisi KANAN terlebih dahulu
        ctk.CTkButton(top, text="⬇️ Export CSV", width=100, fg_color="#27ae60", hover_color="#2ecc71",
                      command=self.export_csv).pack(side="right", padx=(10, 0))
                      
        ctk.CTkButton(top, text="🔄 Refresh", width=100, command=self.refresh).pack(side="right", padx=(10, 0))

        self.filter_waktu_var = ctk.StringVar(value="Hari Ini")
        self.filter_waktu_combo = ctk.CTkComboBox(
            top, values=["Hari Ini", "7 Hari Terakhir", "Bulan Ini", "Semua Waktu"], 
            variable=self.filter_waktu_var, width=140,
            command=lambda e: self.refresh()
        )
        self.filter_waktu_combo.pack(side="right", padx=(10, 0))

        # 2. Pasang Label Ringkasan di sisi KIRI
        self.ringkasan_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        self.ringkasan_label.pack(side="left", fill="x", expand=True)
        # --- AKHIR PERBAIKAN PANEL ATAS ---

        self._kolom_headings = {"waktu": "Waktu", "total": "Pendapatan", "keuntungan": "Profit", "dibayar": "Dibayar", "kembalian": "Kembalian"}

        self._apply_treeview_style()
        columns = ("waktu", "total", "keuntungan", "dibayar", "kembalian")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self._apply_treeview_columns()
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        self.scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 5))
        
        # Hubungkan tabel Treeview dengan Scrollbar
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.tampilkan_detail)

        ctk.CTkLabel(self, text="Detail item transaksi terpilih:", anchor="w",
                    font=ctk.CTkFont(size=12), text_color=("gray40", "gray65")).grid(
            row=2, column=0, sticky="w"
        )
        
        self.detail_box = ctk.CTkTextbox(self, height=140)
        self.detail_box.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        self.detail_box.insert("1.0", "Klik salah satu transaksi di atas untuk melihat detail item yang terjual.")
        self.detail_box.configure(state="disabled")

    def _apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=utils.ukuran(30), font=("Segoe UI", utils.ukuran(11)))
        style.configure("Treeview.Heading", font=("Segoe UI", utils.ukuran(11), "bold"))

    def _apply_treeview_columns(self):
        for col, teks in self._kolom_headings.items():
            self.tree.heading(col, text=teks)
            self.tree.column(col, anchor="w" if col == "waktu" else "e", width=utils.ukuran(150))

    def refresh_style(self):
        """Dipanggil dari main.py pas skala teks diubah - ttk.Treeview gak
        ikut ke-scale otomatis sama CustomTkinter, jadi perlu di-refresh manual."""
        self._apply_treeview_style()
        self._apply_treeview_columns()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        filter_terpilih = self.filter_waktu_var.get()
        data_transaksi = db.get_riwayat_transaksi(filter_terpilih)
        
        total_pendapatan = 0
        total_profit = 0
        
        for t in data_transaksi:
            total_pendapatan += t["total"]
            profit_transaksi = t.get("keuntungan", 0) # Pakai .get() agar aman dari transaksi lama
            total_profit += profit_transaksi
            
            self.tree.insert(
                "", "end", iid=str(t["id"]),
                values=(
                    t["tanggal"], 
                    utils.format_rupiah(t["total"]),
                    utils.format_rupiah(profit_transaksi),
                    utils.format_rupiah(t["dibayar"]), 
                    utils.format_rupiah(t["kembalian"])
                ),
            )

        # Update label ringkasan agar memunculkan dua nominal
        teks_ringkasan = f"{filter_terpilih}: {len(data_transaksi)} transaksi   |   Omzet: {utils.format_rupiah(total_pendapatan)}   |   Profit Bersih: {utils.format_rupiah(total_profit)}"
        self.ringkasan_label.configure(text=teks_ringkasan)
        
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", "Klik salah satu transaksi di atas untuk melihat detail item yang terjual.")
        self.detail_box.configure(state="disabled")

    def tampilkan_detail(self, event=None):
        sel = self.tree.selection()
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        if sel:
            trans_id = int(sel[0])
            for d in db.get_detail_transaksi(trans_id):
                modal = d.get('harga_beli', 0)
                profit_item = (d['harga_satuan'] - modal) * d['jumlah']
                
                self.detail_box.insert(
                    "end",
                    f"{d['nama_produk']}  x{d['jumlah']}  @ {utils.format_rupiah(d['harga_satuan'])}  =  {utils.format_rupiah(d['subtotal'])}\n"
                    f"   ↳ (Modal: {utils.format_rupiah(modal)}  |  Profit: {utils.format_rupiah(profit_item)})\n\n"
                )
        self.detail_box.configure(state="disabled")

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Simpan Data Riwayat Transaksi",
            initialfile=f"Riwayat_Transaksi_{self.filter_waktu_var.get().replace(' ', '_')}.csv"
        )
        if not filepath:
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # 1. Tulis Header bawaan tabel, ditambah 1 Header baru khusus rincian barang
                headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
                headers.append("Detail Barang")
                writer.writerow(headers)

                # 2. Tarik dan tulis data baris demi baris
                for row_id in self.tree.get_children():
                    # Ambil data ringkasan dari layar (Waktu, Total, Profit, dll)
                    row_data = list(self.tree.item(row_id)["values"])
                    
                    # Karena iid baris adalah ID transaksi, kita ubah kembali jadi angka
                    trans_id = int(row_id)
                    
                    # Tarik rincian barang dari database berdasarkan ID transaksi tersebut
                    detail_items = db.get_detail_transaksi(trans_id)
                    
                    # Rangkai barang jadi teks rapi, contoh: "Baki Pasir (x1), Whiskas (x2)"
                    teks_detail = ", ".join([f"{d['nama_produk']} (x{d['jumlah']})" for d in detail_items])
                    
                    # Sisipkan teks rincian tersebut ke kolom paling akhir
                    row_data.append(teks_detail)

                    writer.writerow(row_data)

            messagebox.showinfo("Berhasil", f"Data riwayat berhasil diexport ke:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file:\n{str(e)}")
