"""Layar Riwayat - lihat riwayat transaksi dan ringkasan penjualan hari ini."""

import customtkinter as ctk
from tkinter import ttk
import db
import utils


class RiwayatFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure(0, weight=1)

        self.ringkasan_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=17, weight="bold"))
        self.ringkasan_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="🔄 Refresh", width=100, command=self.refresh).grid(row=0, column=1)

        self._kolom_headings = {"waktu": "Waktu", "total": "Total", "dibayar": "Dibayar", "kembalian": "Kembalian"}

        self._apply_treeview_style()
        columns = ("waktu", "total", "dibayar", "kembalian")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self._apply_treeview_columns()
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
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
        for t in db.get_riwayat_transaksi():
            self.tree.insert(
                "", "end", iid=str(t["id"]),
                values=(t["tanggal"], utils.format_rupiah(t["total"]),
                       utils.format_rupiah(t["dibayar"]), utils.format_rupiah(t["kembalian"])),
            )

        ringkasan = db.get_total_penjualan_hari_ini()
        self.ringkasan_label.configure(
            text=f"Hari ini: {ringkasan['jumlah']} transaksi  •  {utils.format_rupiah(ringkasan['total'])}"
        )

    def tampilkan_detail(self, event=None):
        sel = self.tree.selection()
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        if sel:
            trans_id = int(sel[0])
            for d in db.get_detail_transaksi(trans_id):
                self.detail_box.insert(
                    "end",
                    f"{d['nama_produk']}  x{d['jumlah']}  @ {utils.format_rupiah(d['harga_satuan'])}"
                    f"  =  {utils.format_rupiah(d['subtotal'])}\n",
                )
        self.detail_box.configure(state="disabled")
