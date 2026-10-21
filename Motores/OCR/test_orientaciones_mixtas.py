"""BUG-001, punto 3: una página con un bloque girado respecto al resto.

Página con un encabezado derecho y una tabla girada 90°: el OCR debe leer las dos
partes, con la orientación de cada una, sin inventar palabras, y una página
normal no debe pagar lecturas extra.
Uso: python3 test_orientaciones_mixtas.py   (necesita tesseract con osd y eng)
"""
import glob
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.OCR import aplicar_ocr
from Motores.OCR import pdf_ocr

DPI = 200
T = Path(tempfile.mkdtemp(prefix="mixtas_"))
FUENTE = glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)[0]
ENCABEZADO = ["informe", "general", "del", "documento", "principal"]   # solo en el encabezado
TABLA = ["cantidad", "precio", "total", "unidad", "importe"]           # solo en la tabla


def lineas(prefijo, vocab, n):
    return [" ".join([f"{prefijo}{i}"] + vocab) for i in range(n)]


def texto(lns, ancho, alto, tam=40, paso=100):
    img = Image.new("RGB", (ancho, alto), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FUENTE, tam)
    for i, ln in enumerate(lns):
        d.text((20, 20 + i * paso), ln, font=f, fill="black")
    return img


def pagina_mixta(giro=90):
    """giro 90: la tabla se lee de abajo hacia arriba; 270: de arriba hacia abajo."""
    pag = texto(lineas("Encabezado", ENCABEZADO, 10), 1700, 2200)
    bloque = texto(lineas("Tabla", TABLA, 5), 900, 560).rotate(giro, expand=True)
    pag.paste(bloque, (900, 1300))
    return pag, 10 * 6, 5 * 6


def ocr(img, nombre):
    src = T / f"{nombre}.pdf"
    img.save(str(src), "PDF", resolution=DPI)
    dest = T / f"{nombre}_ocr"
    dest.mkdir()
    aplicar_ocr([str(src)], destino=str(dest), idioma="eng", dpi=DPI)
    return next(dest.glob("*.pdf"))


def palabras(pdf):
    out = []

    def visita(text, cm, tm, fd, fs):
        if text.strip():
            dx = tm[0] * cm[0] + tm[1] * cm[2]
            dy = tm[0] * cm[1] + tm[1] * cm[3]
            out.append((text.strip().lower(), math.degrees(math.atan2(dy, dx)) % 360))

    PdfReader(str(pdf)).pages[0].extract_text(visitor_text=visita)
    return out


def con_tinta(pdf):
    html = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True).stdout
    cajas = [tuple(map(float, c)) for c in re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)"', html)]
    png = pdf.with_suffix("")
    subprocess.run(["pdftoppm", "-r", "72", "-png", "-singlefile", str(pdf), str(png)], check=True)
    img = np.array(Image.open(str(png) + ".png").convert("L"))
    bien = sum(1 for x0, y0, x1, y1 in cajas
               if (img[int(y0):int(y1) + 1, int(x0):int(x1) + 1] < 128).mean() >= 0.04)
    return bien, len(cajas)


todo = True

# --- página mixta, con la tabla girada a cada lado ---
for giro in (90, 270):
    pag, n_enc, n_tab = pagina_mixta(giro)
    esperadas = n_enc + n_tab
    pdf = ocr(pag, f"mixta{giro}")
    got = palabras(pdf)
    enc = [a for t, a in got if t in ENCABEZADO]
    tab = [a for t, a in got if t in TABLA]
    ang_enc = max((abs((a + 180) % 360 - 180) for a in enc), default=999)
    ang_tab = max((abs((a - giro + 180) % 360 - 180) for a in tab), default=999)
    tinta, cajas = con_tinta(pdf)
    ok = (len(enc) >= 0.95 * (n_enc - 10) and len(tab) >= 0.95 * (n_tab - 5)  # sin los «EncabezadoN»/«TablaN»
          and ang_enc <= 3 and ang_tab <= 3
          and len(got) <= 1.05 * esperadas and tinta >= 0.98 * cajas)
    print(f"mixta, tabla a {giro:3d}°: palabras={len(got)} (esperadas {esperadas}) | encabezado {len(enc)}/{n_enc - 10} "
          f"error {ang_enc:.1f}° | tabla {len(tab)}/{n_tab - 5} error {ang_tab:.1f}° | con tinta {tinta}/{cajas}  "
          f"-> {'OK' if ok else 'FALLO'}")
    todo &= ok

# --- pasadas extra: si la pasada principal no hubiera leído la tabla, se encuentra aparte ---
pag, _, _ = pagina_mixta(90)
principal = pdf_ocr._extraer_palabras_con_coords(pag.crop((0, 0, 1700, 1250)), "eng")  # solo el encabezado
extra = pdf_ocr._palabras_otras_orientaciones(pag, principal, "eng")
tabla = [p for p in extra if p["texto"].lower() in TABLA]
ok = (len(tabla) >= 0.95 * 25 and all(p["rot_texto"] == 90 for p in extra)
      and not [p for p in extra if p["texto"].lower() in ENCABEZADO] and len(extra) <= 1.05 * 30
      and all(p["h"] > p["w"] for p in tabla))
print(f"pasadas extra: leídas {len(tabla)}/25 palabras de la tabla (+{len(extra) - len(tabla)} otras), "
      f"rot_texto={{p['rot_texto'] for p in extra}}  -> {'OK' if ok else 'FALLO'}".replace("{p['rot_texto'] for p in extra}", str({p['rot_texto'] for p in extra})))
todo &= ok

# --- una página normal no paga lecturas extra ---
llamadas = []
original = pdf_ocr._extraer_palabras_con_coords
pdf_ocr._extraer_palabras_con_coords = lambda *a, **k: (llamadas.append(1), original(*a, **k))[1]
try:
    ocr(texto(lineas("Linea", ENCABEZADO, 14), 1700, 2200, paso=140), "normal")
finally:
    pdf_ocr._extraer_palabras_con_coords = original
ok = len(llamadas) == 1
print(f"página normal: lecturas de OCR = {len(llamadas)} (esperada 1)  -> {'OK' if ok else 'FALLO'}")
todo &= ok

print("RESULTADO:", "OK" if todo else "FALLO")
sys.exit(0 if todo else 1)
