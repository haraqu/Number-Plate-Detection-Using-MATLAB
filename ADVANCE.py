import cv2
import easyocr
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, Canvas, messagebox
import random
from datetime import datetime

# ================= OCR =================
reader = easyocr.Reader(['en'], gpu=False)

# ================= PLATE DETECTION (UNCHANGED) =================
def detect_plate_by_edges(img):
    img = cv2.resize(img, (600, 400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=-1)
    sobelx = cv2.convertScaleAbs(sobelx)

    blur = cv2.GaussianBlur(sobelx, (9, 9), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / float(h)
        area = w * h
        if 2.0 < aspect < 6.0 and 1000 < area < 50000:
            return img, (x, y, w, h)

    return img, None

# ================= OCR =================
def extract_and_ocr(img, rect):
    if rect is None:
        return img, "NOT FOUND"

    x, y, w, h = rect
    cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 3)

    roi = img[y:y+h, x:x+w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    results = reader.readtext(
        gray,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        detail=0
    )

    text = " ".join(results)
    return img, text if text else "UNCLEAR"

# ================= CHALLAN DATA =================
def generate_challan_data(plate):
    city = "Islamabad" if plate.startswith("ISB") or plate.startswith("LEA") else "Lahore"
    violations = ["Wrong Lane", "Over Speeding", "Signal Violation", "No Helmet"]
    fines = [1500, 2000, 1800, 1000]

    return {
        "Plate Number": plate,
        "City": city,
        "Violation": random.choice(violations),
        "Fine": random.choice(fines),
        "Challan ID": f"CH-{random.randint(10000,99999)}",
        "Date": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    }

# ================= MAIN GUI =================
class ANPRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ANPR & E-Challan System")
        self.root.state("zoomed")
        self.root.configure(bg="#0f172a")

        self.detected_plate = None

        # -------- HEADER --------
        tk.Label(
            root,
            text="AUTOMATIC NUMBER PLATE RECOGNITION",
            font=("Segoe UI", 24, "bold"),
            fg="#38bdf8",
            bg="#020617",
            pady=20
        ).pack(fill="x")

        # -------- CANVAS --------
        self.canvas = Canvas(root, width=880, height=420, bg="#020617", highlightthickness=0)
        self.canvas.pack(pady=25)
        self.canvas.create_text(
            440, 210, text="📷 Load Vehicle Image",
            fill="#94a3b8", font=("Segoe UI", 18)
        )

        # -------- STATUS --------
        self.status = tk.Label(
            root, text="Status: Waiting for image...",
            font=("Segoe UI", 14),
            fg="white", bg="#020617", pady=10, width=80
        )
        self.status.pack()

        # -------- BUTTONS --------
        btn_frame = tk.Frame(root, bg="#0f172a")
        btn_frame.pack(pady=20)

        tk.Button(
            btn_frame, text="📂 Load Image",
            font=("Segoe UI", 14, "bold"),
            bg="#22c55e", fg="black",
            padx=20, pady=10, command=self.load_image
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            btn_frame, text="🚨 Generate E-Challan",
            font=("Segoe UI", 14, "bold"),
            bg="#facc15", fg="black",
            padx=20, pady=10, command=self.show_challan
        ).grid(row=0, column=1, padx=10)

        tk.Button(
            btn_frame, text="❌ Exit",
            font=("Segoe UI", 14, "bold"),
            bg="#ef4444", fg="white",
            padx=20, pady=10, command=root.quit
        ).grid(row=0, column=2, padx=10)

    # -------- IMAGE PROCESS --------
    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png")]
        )
        if not path:
            return

        self.status.config(text="Processing image...")
        self.root.update()

        img = cv2.imread(path)
        processed, rect = detect_plate_by_edges(img)
        final_img, plate = extract_and_ocr(processed, rect)
        self.detected_plate = plate

        rgb = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb).resize((880, 420), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(pil)

        self.canvas.delete("all")
        self.canvas.create_image(440, 210, image=self.photo)

        self.status.config(text=f"Detected Plate: {plate}")

    # -------- E-CHALLAN WINDOW --------
    def show_challan(self):
        if not self.detected_plate or self.detected_plate in ["NOT FOUND", "UNCLEAR"]:
            messagebox.showwarning("Warning", "Valid number plate not detected!")
            return

        data = generate_challan_data(self.detected_plate)

        win = tk.Toplevel(self.root)
        win.title("E-Challan | Traffic Police")
        win.state("zoomed")          # Full screen challan window
        win.configure(bg="#020617")
        win.resizable(True, True)

        tk.Label(
            win, text="🚨 E-CHALLAN 🚨",
            font=("Segoe UI", 22, "bold"),
            fg="#facc15", bg="#020617", pady=20
        ).pack()

        card = tk.Frame(win, bg="#111827")
        card.pack(padx=25, pady=15, fill="both", expand=True)

        def row(label, value, highlight=False):
            tk.Label(card, text=label, font=("Segoe UI", 13, "bold"),
                     fg="#93c5fd", bg="#111827", anchor="w").pack(fill="x", padx=20, pady=(12, 0))
            tk.Label(card, text=value,
                     font=("Segoe UI", 16, "bold" if highlight else "normal"),
                     fg="#facc15" if highlight else "#e5e7eb",
                     bg="#111827", anchor="w").pack(fill="x", padx=20)
            tk.Frame(card, bg="#1f2937", height=1).pack(fill="x", padx=20, pady=8)

        row("Plate Number", data["Plate Number"], True)
        row("City", data["City"])
        row("Violation", data["Violation"])
        row("Fine (PKR)", str(data["Fine"]))
        row("Challan ID", data["Challan ID"])
        row("Date & Time", data["Date"])

        tk.Button(
            win, text="Close",
            font=("Segoe UI", 13, "bold"),
            bg="#ef4444", fg="white",
            padx=20, pady=8, command=win.destroy
        ).pack(pady=15)

# ================= RUN =================
if __name__ == "__main__":
    root = tk.Tk()
    app = ANPRApp(root)
    root.mainloop()
