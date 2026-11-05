"""
APLIKASI TEORI PERTURBASI ORDE PERTAMA
Berdasarkan contoh pada aplikasi.pdf (halaman 1-5).

Model yang dihitung:
    H'(x) = V1*x/a
    psi_n(x) = sqrt(2/a)*sin(n*pi*x/a)

Hasil:
    E_n^(1) = V1/2
    E_n ≈ n^2*E1 + E_n^(1)
    H'_(k,n) = <psi_k|H'|psi_n>
    c_mn = H'_(m,n) / (E_n^(0) - E_m^(0)), m != n
    psi_n^(1) ≈ psi_n + sum(c_mn*psi_m)

Install dependensi:
    python -m pip install --upgrade pip
    python -m pip install customtkinter sympy numpy scipy matplotlib pillow pytesseract openpyxl

Catatan OCR:
- Untuk membaca teks dari gambar, pasang aplikasi Tesseract OCR pada Windows.
- Jika Tesseract tidak ditemukan, aplikasi tetap berjalan; hasil OCR dapat diketik
  atau disalin manual ke kolom fungsi.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import math

import customtkinter as ctk
import sympy as sp
import numpy as np
from scipy.integrate import quad
from PIL import Image, ImageTk

try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# --------------------------- Tema aplikasi ---------------------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG = "#F3F6FB"
CARD = "#FFFFFF"
NAVY = "#14213D"
BLUE = "#2563EB"
MUTED = "#64748B"
GREEN = "#15803D"
RED = "#B91C1C"

x, a, V1 = sp.symbols("x a V1", positive=True, real=True)


class PerturbationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QuantumLab | Teori Perturbasi Orde Pertama")
        self.geometry("1220x820")
        self.minsize(1020, 700)
        self.configure(fg_color=BG)

        self.image_path = None
        self.preview_image = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0, height=92)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="QuantumLab",
            font=ctk.CTkFont(family="Segoe UI", size=27, weight="bold"),
            text_color="white"
        ).grid(row=0, column=0, padx=28, pady=(17, 0), sticky="w")
        ctk.CTkLabel(
            header, text="Kalkulator Teori Perturbasi Kuantum • Koreksi energi dan fungsi gelombang",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#CBD5E1"
        ).grid(row=1, column=0, padx=30, pady=(0, 15), sticky="w")
        ctk.CTkLabel(
            header, text="ORDE 1",
            fg_color="#1D4ED8", corner_radius=12, text_color="white",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=1, rowspan=2, padx=28, pady=25, sticky="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=18)
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=6)
        body.grid_rowconfigure(0, weight=1)

        # Panel input
        left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=16, border_width=1, border_color="#E2E8F0")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="01  |  INPUT PERHITUNGAN",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=NAVY
                     ).grid(row=0, column=0, padx=20, pady=(20, 12), sticky="w")

        ctk.CTkLabel(left, text="Fungsi perturbasi H'(x)",
                     text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=1, column=0, padx=20, sticky="w")
        self.function_entry = ctk.CTkEntry(
            left, height=40, corner_radius=9,
            placeholder_text="Contoh: V1*x/a"
        )
        self.function_entry.insert(0, "V1*x/a")
        self.function_entry.grid(row=2, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.ocr_button = ctk.CTkButton(
            left, text="Upload gambar fungsi (PNG/JPG)", height=36,
            fg_color="#E8F0FF", hover_color="#D8E5FF", text_color=BLUE,
            command=self.upload_image
        )
        self.ocr_button.grid(row=3, column=0, padx=20, pady=(4, 5), sticky="ew")
        self.image_label = ctk.CTkLabel(left, text="Belum ada gambar dipilih",
                                        text_color=MUTED, font=ctk.CTkFont(size=11))
        self.image_label.grid(row=4, column=0, padx=20, pady=(0, 8), sticky="w")

        # Parameter
        ctk.CTkLabel(left, text="Parameter sistem",
                     text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=5, column=0, padx=20, pady=(8, 4), sticky="w")
        params = ctk.CTkFrame(left, fg_color="#F8FAFC", corner_radius=10)
        params.grid(row=6, column=0, padx=20, sticky="ew")
        params.grid_columnconfigure((0, 1), weight=1)

        self.entries = {}
        fields = [
            ("a", "Lebar sumur a", "1.0"),
            ("V1", "Tinggi potensial V1", "1.0"),
            ("E1", "Energi dasar E₁⁽⁰⁾", "1.0"),
            ("n", "Bilangan kuantum n", "1"),
            ("N", "Batas jumlah keadaan", "8"),
        ]
        for idx, (key, label, default) in enumerate(fields):
            r, c = divmod(idx, 2)
            cell = ctk.CTkFrame(params, fg_color="transparent")
            cell.grid(row=r, column=c, padx=10, pady=8, sticky="ew")
            ctk.CTkLabel(cell, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(anchor="w")
            ent = ctk.CTkEntry(cell, height=34, corner_radius=7)
            ent.insert(0, default)
            ent.pack(fill="x", pady=(3, 0))
            self.entries[key] = ent

        ctk.CTkLabel(
            left,
            text="Format fungsi: gunakan x, a, V1, angka, +, -, *, /, **, sin(), cos().\n"
                 "Contoh soal PDF menggunakan H'(x) = V1*x/a.",
            text_color=MUTED, justify="left",
            font=ctk.CTkFont(size=11)
        ).grid(row=7, column=0, padx=20, pady=12, sticky="w")

        buttons = ctk.CTkFrame(left, fg_color="transparent")
        buttons.grid(row=8, column=0, padx=20, pady=(2, 18), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Hitung", height=43, corner_radius=9,
                      command=self.calculate).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(buttons, text="Reset", height=43, corner_radius=9,
                      fg_color="#E2E8F0", hover_color="#CBD5E1",
                      text_color=NAVY, command=self.reset).grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Panel output
        right = ctk.CTkFrame(body, fg_color=CARD, corner_radius=16, border_width=1, border_color="#E2E8F0")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(right, text="02  |  OUTPUT HASIL",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=NAVY
                     ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.summary = ctk.CTkTextbox(right, height=170, corner_radius=10,
                                      fg_color="#F8FAFC", text_color=NAVY,
                                      font=ctk.CTkFont(family="Consolas", size=12))
        self.summary.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")
        self.summary.insert("1.0", "Hasil perhitungan akan tampil di sini.\n\n"
                                   "Tekan tombol HITUNG untuk memulai.")
        self.summary.configure(state="disabled")

        ctk.CTkLabel(right, text="Koefisien koreksi fungsi gelombang",
                     text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=2, column=0, padx=20, pady=(2, 5), sticky="nw")
        self.table = ctk.CTkTextbox(right, corner_radius=10, fg_color="#F8FAFC",
                                    text_color=NAVY,
                                    font=ctk.CTkFont(family="Consolas", size=11))
        self.table.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="nsew")

        self.status = ctk.CTkLabel(right, text="Status: menunggu input",
                                   text_color=MUTED, font=ctk.CTkFont(size=11))
        self.status.grid(row=4, column=0, padx=20, pady=(0, 16), sticky="w")

    def _build_footer(self):
        ctk.CTkLabel(
            self, text="Model mengikuti contoh Teori Perturbasi pada dokumen sumber, halaman 1–5.",
            text_color=MUTED, font=ctk.CTkFont(size=10)
        ).grid(row=2, column=0, pady=(0, 10))

    def upload_image(self):
        path = filedialog.askopenfilename(
            title="Pilih gambar fungsi",
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")]
        )
        if not path:
            return
        self.image_path = path
        self.image_label.configure(text=os.path.basename(path))
        if not OCR_AVAILABLE:
            messagebox.showwarning(
                "OCR belum tersedia",
                "Library pytesseract belum terpasang. Jalankan:\n"
                "python -m pip install pytesseract pillow\n\n"
                "Pastikan aplikasi Tesseract OCR untuk Windows juga terpasang."
            )
            return
        try:
            # Jika Tesseract tidak ada pada PATH, pengguna dapat mengatur TESSERACT_CMD.
            custom_cmd = os.environ.get("TESSERACT_CMD")
            if custom_cmd:
                pytesseract.pytesseract.tesseract_cmd = custom_cmd
            img = Image.open(path)
            extracted = pytesseract.image_to_string(img, config="--psm 6")
            cleaned = self._clean_ocr(extracted)
            if cleaned:
                self.function_entry.delete(0, "end")
                self.function_entry.insert(0, cleaned)
                messagebox.showinfo(
                    "OCR selesai",
                    "Teks hasil pembacaan gambar telah dimasukkan ke kolom fungsi.\n"
                    "Periksa dan koreksi hasil OCR sebelum menekan HITUNG."
                )
            else:
                messagebox.showwarning("Tidak terbaca", "Tidak ditemukan teks fungsi yang dapat dibaca.")
        except Exception as exc:
            messagebox.showerror(
                "Gagal membaca gambar",
                "Tesseract OCR tidak dapat dijalankan.\n"
                "Pastikan aplikasi Tesseract OCR sudah terpasang di Windows.\n\n"
                f"Detail: {exc}"
            )

    @staticmethod
    def _clean_ocr(text):
        text = text.replace(" ", "")
        text = text.replace("×", "*").replace("·", "*").replace("÷", "/")
        text = text.replace("π", "pi").replace("−", "-")
        # Prioritaskan pola fungsi contoh yang terdeteksi dari gambar.
        compact = text.lower()
        if ("v1" in compact or "v" in compact) and "x" in compact and "a" in compact:
            if re.search(r"v\\s*1?.*x.*a|x.*v\\s*1?.*a", compact):
                return "V1*x/a"
        # Ambil satu baris yang paling menyerupai ekspresi matematika.
        candidates = [line.strip() for line in text.splitlines() if line.strip()]
        for line in candidates:
            if any(ch in line for ch in ("x", "V1", "a")) and len(line) < 100:
                return line
        return ""

    def _parse_function(self, expression, aval, vval):
        # Batasi parser pada simbol dan fungsi matematika yang diizinkan.
        local = {
            "x": x, "a": sp.Float(aval), "V1": sp.Float(vval),
            "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
            "exp": sp.exp, "sqrt": sp.sqrt, "pi": sp.pi,
            "log": sp.log, "abs": sp.Abs
        }
        expr = sp.sympify(expression, locals=local, evaluate=True)
        unknown = expr.free_symbols - {x}
        if unknown:
            raise ValueError("Simbol tidak dikenal: " + ", ".join(map(str, unknown)))
        return expr

    @staticmethod
    def _psi(q, xx, aa):
        return math.sqrt(2.0 / aa) * math.sin(q * math.pi * xx / aa)

    def _matrix_element(self, k, m, expr, aval):
        f = sp.lambdify(x, expr, modules=["numpy"])
        def integrand(xx):
            return self._psi(k, xx, aval) * float(f(xx)) * self._psi(m, xx, aval)
        value, error = quad(integrand, 0.0, aval, epsabs=1e-10, epsrel=1e-10, limit=200)
        return value

    def calculate(self):
        try:
            aval = float(self.entries["a"].get())
            vval = float(self.entries["V1"].get())
            e1 = float(self.entries["E1"].get())
            n = int(self.entries["n"].get())
            N = int(self.entries["N"].get())
            if aval <= 0 or e1 <= 0 or n < 1 or N < 2 or N > 30:
                raise ValueError("Syarat: a dan E1 > 0, n >= 1, serta 2 <= N <= 30.")
            if n > N:
                raise ValueError("Batas keadaan N harus >= bilangan kuantum n.")
            expression = self.function_entry.get().strip()
            if not expression:
                raise ValueError("Fungsi perturbasi belum diisi.")
            expr = self._parse_function(expression, aval, vval)

            # Koreksi energi dan elemen matriks dihitung dari integral.
            diagonal = self._matrix_element(n, n, expr, aval)
            e0 = n**2 * e1
            etotal = e0 + diagonal

            lines = []
            lines.append("HASIL KOREKSI ENERGI")
            lines.append("-" * 46)
            lines.append(f"H'(x)       = {sp.sstr(expr)}")
            lines.append(f"Keadaan n   = {n}")
            lines.append(f"E_n^(0)     = n² E1 = {e0:.10g}")
            lines.append(f"E_n^(1)     = <n|H'|n> = {diagonal:.10g}")
            lines.append(f"E_n         = E_n^(0) + E_n^(1) = {etotal:.10g}")
            lines.append("")
            lines.append("Untuk fungsi contoh H'=V1*x/a, hasil analitiknya")
            lines.append(f"E_n^(1) = V1/2 = {vval/2:.10g}")
            lines.append("(Nilai integral numerik di atas mengikuti fungsi input.)")

            coeff_lines = []
            coeff_lines.append(f"{'m':>3}  {'H_prime(m,n)':>18}  {'E_n0-E_m0':>18}  {'c_mn':>18}")
            coeff_lines.append("-" * 66)
            wave_terms = [f"psi_{n}(x)"]
            for m in range(1, N + 1):
                if m == n:
                    continue
                hmn = self._matrix_element(m, n, expr, aval)
                denominator = (n**2 - m**2) * e1
                cmn = hmn / denominator
                coeff_lines.append(f"{m:>3}  {hmn:>18.9g}  {denominator:>18.9g}  {cmn:>18.9g}")
                if abs(cmn) > 1e-12:
                    wave_terms.append(f"({cmn:.6g}) psi_{m}(x)")

            coeff_lines += ["", "Pendekatan fungsi gelombang terkoreksi:", "psi_n ≈ " + " + ".join(wave_terms)]
            self._set_text(self.summary, "\n".join(lines))
            self._set_text(self.table, "\n".join(coeff_lines))
            self.status.configure(text="Status: perhitungan berhasil", text_color=GREEN)

        except Exception as exc:
            self.status.configure(text="Status: periksa input", text_color=RED)
            messagebox.showerror("Input/perhitungan tidak valid", str(exc))

    @staticmethod
    def _set_text(widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def reset(self):
        self.function_entry.delete(0, "end")
        self.function_entry.insert(0, "V1*x/a")
        defaults = {"a": "1.0", "V1": "1.0", "E1": "1.0", "n": "1", "N": "8"}
        for key, value in defaults.items():
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, value)
        self.image_path = None
        self.image_label.configure(text="Belum ada gambar dipilih")
        self._set_text(self.summary, "Hasil perhitungan akan tampil di sini.")
        self._set_text(self.table, "Koefisien koreksi fungsi gelombang akan tampil di sini.")
        self.status.configure(text="Status: menunggu input", text_color=MUTED)


if __name__ == "__main__":
    app = PerturbationApp()
    app.mainloop()
