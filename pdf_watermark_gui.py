"""
PDF Watermark Tool — GUI
=========================
A desktop app (Tkinter) that lets you add a tiled, multi-line, diagonal
watermark to any PDF — similar to "Strictly Private and Confidential"
stamps used on legal/financial documents.

HOW TO RUN
----------
1. Install Python 3.8+ (from python.org) if you don't have it.
2. Install the two required libraries:
       pip install pypdf reportlab
3. Run this file:
       python pdf_watermark_gui.py

USAGE
-----
1. Click "Browse" to pick your input PDF.
2. Type each watermark line in the text box (one line per row).
   They will alternate/cycle as they tile across the page, e.g.:
       Strictly Private and Confidential
       Prepared for John Smith
3. Adjust font size, angle, spacing, gray level and opacity as desired.
4. Click "Preview" to render the first page as an image so you can check
   how it looks before saving (optional — needs PyMuPDF, see note below).
5. Click "Generate Watermarked PDF" and choose where to save the result.
"""

import io
import math
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter


# --------------------------------------------------------------------------
# Core watermarking logic
# --------------------------------------------------------------------------

def make_tiled_watermark(lines, pagesize, angle, font_size, gray, alpha,
                          x_spacing, y_spacing):
    """Build a single-page in-memory PDF containing the tiled watermark.

    Horizontal step = measured text width + x_spacing (gap), so long phrases
    never overlap each other.
    """
    width, height = pagesize
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)

    font_name = "Helvetica"
    c.setFont(font_name, font_size)
    c.setFillColorRGB(gray, gray, gray)
    c.setFillAlpha(alpha)

    # Step = text width + gap so copies never overlap
    line_steps = [
        c.stringWidth(line, font_name, font_size) + x_spacing
        for line in lines
    ]

    diag = math.hypot(width, height)

    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(angle)

    line_idx = 0
    y = -diag
    while y < diag:
        text = lines[line_idx % len(lines)]
        step_x = line_steps[line_idx % len(lines)]
        row_offset = (step_x / 2) if line_idx % 2 else 0
        x = -diag
        while x < diag:
            c.drawString(x + row_offset, y, text)
            x += step_x
        y += y_spacing
        line_idx += 1

    c.restoreState()
    c.save()
    buf.seek(0)
    return buf


def add_tiled_watermark(input_pdf, output_pdf, lines, angle=45,
                         font_size=10, gray=0.6, alpha=0.35,
                         x_spacing=80, y_spacing=90,
                         progress_callback=None):
    # Clone into the writer first, then merge onto writer pages.
    # Merging on reader pages / reusing one watermark object can leave
    # some pages unmarked (esp. mixed sizes or rotated pages).
    writer = PdfWriter(clone_from=input_pdf)

    # Cache watermark PDF bytes by page size so mixed-size docs stay correct
    watermark_by_size = {}

    total = len(writer.pages)
    for i, page in enumerate(writer.pages):
        if getattr(page, "rotation", 0):
            page.transfer_rotation_to_content()

        pagesize = (float(page.mediabox.width), float(page.mediabox.height))
        if pagesize not in watermark_by_size:
            buf = make_tiled_watermark(
                lines, pagesize, angle, font_size, gray, alpha,
                x_spacing, y_spacing,
            )
            watermark_by_size[pagesize] = buf.getvalue()

        # Fresh page object each time so merge never shares/mutates state
        watermark_page = PdfReader(
            io.BytesIO(watermark_by_size[pagesize])
        ).pages[0]
        page.merge_page(watermark_page, over=True)

        if progress_callback:
            progress_callback(i + 1, total)

    with open(output_pdf, "wb") as f:
        writer.write(f)


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

class WatermarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Watermark Tool")
        self.geometry("560x640")
        self.resizable(False, False)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # --- Input file ---
        frame_in = ttk.LabelFrame(self, text="1. Input PDF")
        frame_in.pack(fill="x", **pad)
        ttk.Entry(frame_in, textvariable=self.input_path).pack(
            side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(frame_in, text="Browse...", command=self.browse_input).pack(
            side="left", padx=(0, 8), pady=8)

        # --- Watermark lines ---
        frame_lines = ttk.LabelFrame(
            self, text="2. Watermark text (one line per row; they cycle as they tile)")
        frame_lines.pack(fill="x", **pad)
        self.text_lines = tk.Text(frame_lines, height=4, wrap="none")
        self.text_lines.insert(
            "1.0",
            "Strictly Private and Confidential for [] Only",
        )
        self.text_lines.pack(fill="x", padx=8, pady=8)

        # --- Settings ---
        frame_settings = ttk.LabelFrame(self, text="3. Appearance")
        frame_settings.pack(fill="x", **pad)

        self.font_size = tk.IntVar(value=10)
        self.angle = tk.IntVar(value=45)
        self.gray = tk.DoubleVar(value=0.6)
        self.alpha = tk.DoubleVar(value=0.35)
        # Minimum horizontal step; actual step grows with text width automatically
        self.x_spacing = tk.IntVar(value=80)
        self.y_spacing = tk.IntVar(value=90)

        self._add_slider(frame_settings, "Font size", self.font_size, 6, 40, 0)
        self._add_slider(frame_settings, "Angle (degrees)", self.angle, 0, 90, 1)
        self._add_slider(frame_settings, "Gray level (0=black, 1=white)",
                          self.gray, 0.0, 1.0, 2, resolution=0.05)
        self._add_slider(frame_settings, "Opacity (0=invisible, 1=solid)",
                          self.alpha, 0.05, 1.0, 3, resolution=0.05)
        self._add_slider(frame_settings, "Gap between copies", self.x_spacing,
                          20, 200, 4)
        self._add_slider(frame_settings, "Vertical spacing", self.y_spacing,
                          40, 300, 5)

        # --- Output file ---
        frame_out = ttk.LabelFrame(self, text="4. Output location")
        frame_out.pack(fill="x", **pad)
        ttk.Entry(frame_out, textvariable=self.output_path).pack(
            side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(frame_out, text="Browse...", command=self.browse_output).pack(
            side="left", padx=(0, 8), pady=8)

        # --- Action ---
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(10, 4))

        self.status_label = ttk.Label(self, text="Ready.")
        self.status_label.pack(padx=10, anchor="w")

        ttk.Button(self, text="Generate Watermarked PDF",
                   command=self.run_watermark).pack(pady=14, ipadx=10, ipady=6)

    def _add_slider(self, parent, label, var, frm, to, row, resolution=1):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w",
                                            padx=8, pady=4)
        scale = ttk.Scale(parent, from_=frm, to=to, variable=var,
                           orient="horizontal", length=260)
        scale.grid(row=row, column=1, padx=8, pady=4)
        value_label = ttk.Label(parent, text=str(var.get()))
        value_label.grid(row=row, column=2, padx=8, pady=4)

        def update_label(*_):
            v = var.get()
            value_label.config(text=f"{v:.2f}" if resolution < 1 else str(int(v)))

        var.trace_add("write", update_label)

    # ----------------------------------------------------------------
    def browse_input(self):
        path = filedialog.askopenfilename(
            title="Select input PDF", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_path.set(path)
            if not self.output_path.get():
                base, ext = os.path.splitext(path)
                self.output_path.set(f"{base}_watermarked.pdf")

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save watermarked PDF as", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if path:
            self.output_path.set(path)

    def run_watermark(self):
        input_pdf = self.input_path.get().strip()
        output_pdf = self.output_path.get().strip()
        raw_lines = [l for l in self.text_lines.get("1.0", "end").splitlines()
                     if l.strip()]

        if not input_pdf or not os.path.isfile(input_pdf):
            messagebox.showerror("Error", "Please choose a valid input PDF.")
            return
        if not output_pdf:
            messagebox.showerror("Error", "Please choose an output file location.")
            return
        if not raw_lines:
            messagebox.showerror("Error", "Please enter at least one watermark line.")
            return

        self.status_label.config(text="Processing...")
        self.progress["value"] = 0
        self.update_idletasks()

        def worker():
            try:
                def on_progress(done, total):
                    self.progress["maximum"] = total
                    self.progress["value"] = done
                    self.status_label.config(text=f"Watermarking page {done}/{total}...")
                    self.update_idletasks()

                add_tiled_watermark(
                    input_pdf, output_pdf, raw_lines,
                    angle=self.angle.get(),
                    font_size=self.font_size.get(),
                    gray=self.gray.get(),
                    alpha=self.alpha.get(),
                    x_spacing=self.x_spacing.get(),
                    y_spacing=self.y_spacing.get(),
                    progress_callback=on_progress,
                )
                self.status_label.config(text=f"Done! Saved to: {output_pdf}")
                messagebox.showinfo("Success",
                                     f"Watermarked PDF saved to:\n{output_pdf}")
            except Exception as e:
                self.status_label.config(text="Failed.")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
