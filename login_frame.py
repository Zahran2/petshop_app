import customtkinter as ctk
from tkinter import messagebox
import db

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success
        self._build_ui()

    def _build_ui(self):
        # Buat kotak form di tengah layar
        box = ctk.CTkFrame(self, width=350, height=400, corner_radius=15)
        box.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(box, text="🐾 Petshop Login", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(40, 20))
        
        # Kolom Username
        ctk.CTkLabel(box, text="Username", anchor="w").pack(fill="x", padx=40, pady=(10, 0))
        self.entry_user = ctk.CTkEntry(box, height=40)
        self.entry_user.pack(fill="x", padx=40, pady=(5, 10))
        
        # Kolom PIN
        ctk.CTkLabel(box, text="PIN", anchor="w").pack(fill="x", padx=40, pady=(10, 0))
        self.entry_pin = ctk.CTkEntry(box, height=40, show="*")
        self.entry_pin.pack(fill="x", padx=40, pady=(5, 20))
        
        # Tombol Masuk
        ctk.CTkButton(box, text="MASUK", height=45, font=ctk.CTkFont(weight="bold"), 
                     command=self.proses_login).pack(fill="x", padx=40, pady=(10, 30))
                     
        # Bind tombol Enter agar praktis
        self.entry_pin.bind("<Return>", lambda e: self.proses_login())

    def proses_login(self):
        user = self.entry_user.get().strip()
        pin = self.entry_pin.get().strip()
        
        role = db.verifikasi_login(user, pin)
        if role:
            self.on_login_success(role) # Beri tahu main.py bahwa login berhasil
        else:
            messagebox.showerror("Akses Ditolak", "Username atau PIN salah!")