"""BUG-001: la capa de texto de un escaneo girado debe quedar donde está el texto.

Se hace OCR de la misma página derecha y girada 90°/180°/270°, y cada palabra
del PDF resultante se compara con la de la página derecha (posición, tamaño de
fuente y dirección del texto). También cubre una página con /Rotate.
Uso: python3 test_capa_texto.py   (necesita tesseract con osd y eng)
"""
import glob
import math
import os
import statistics
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.OCR import aplicar_ocr

DPI = 200
T = Path(tempfile.mkdtemp(prefix="capa_texto_"))


def pagina_derecha():
    fuente = glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)[0]
    img = Image.new("RGB", (1700, 2200), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(fuente, 44)
    for i in range(14):
        d.text((120, 140 + i * 140),
               f"Linea {i} documento escaneado reconocimiento optico caracteres", font=f, fill="black")
    return img


def ocr(img, nombre, rotate_pdf=0):
    src = T / f"{nombre}.pdf"
    img.save(str(src), "PDF", resolution=DPI)
    if rotate_pdf:
        w = PdfWriter(clone_from=str(src))
        w.pages[0].rotate(rotate_pdf)
        w.write(str(src))
    dest = T / f"{nombre}_ocr"
    dest.mkdir()
    aplicar_ocr([str(src)], destino=str(dest), idioma="eng", dpi=DPI)
    return next(dest.glob("*.pdf"))


def palabras(pdf):
    """[(texto, x, y, ángulo°, tamaño_fuente)] en el espacio de usuario de la página."""
    out = []

    def visita(text, cm, tm, fd, fs):
        if not text.strip():
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        dx = tm[0] * cm[0] + tm[1] * cm[2]
        dy = tm[0] * cm[1] + tm[1] * cm[3]
        out.append((text.strip(), x, y, math.degrees(math.atan2(dy, dx)) % 360, fs))

    PdfReader(str(pdf)).pages[0].extract_text(visitor_text=visita)
    return out


def mapear(x, y, giro, wp, hp):
    """Dónde cae el punto (x, y) de la página derecha (pt, y hacia arriba) si la imagen
    se gira `giro`° antihorario (PIL rotate con expand)."""
    return {0: (x, y), 90: (hp - y, x), 180: (wp - x, hp - y), 270: (y, wp - x)}[giro]


def comprobar(nombre, got, ref, giro, wp, hp, angulo_esperado):
    assert len(got) == len(ref), f"{nombre}: {len(got)} palabras, se esperaban {len(ref)}"
    assert [g[0] for g in got] == [r[0] for r in ref], f"{nombre}: el texto o su orden cambió"
    dist = [math.dist(mapear(r[1], r[2], giro, wp, hp), (g[1], g[2])) for g, r in zip(got, ref)]
    # Tesseract mueve a veces el borde de una palabra suelta unos píxeles (1 px = 0,36 pt a 200 dpi):
    # se exige que casi todas coincidan, no que ninguna se mueva.
    cerca = sum(d <= 3 for d in dist) / len(dist)
    dang = max(abs((g[3] - angulo_esperado + 180) % 360 - 180) for g in got)
    fs = statistics.median(g[4] for g in got)
    fs_ref = statistics.median(r[4] for r in ref)
    ok = cerca >= 0.97 and statistics.median(dist) <= 1 and dang <= 3 and abs(fs - fs_ref) <= 0.15 * fs_ref
    print(f"{nombre:<22} palabras={len(got)} dentro_de_3pt={cerca:5.1%} mediana={statistics.median(dist):4.2f} pt "
          f"ángulo_máx_err={dang:4.1f}°  fuente={fs:5.1f} pt (ref {fs_ref:.1f})  -> {'OK' if ok else 'FALLO'}")
    return ok


base = pagina_derecha()
ref = palabras(ocr(base, "derecha"))
assert len(ref) > 80, "la página de referencia no dio texto"
wp, hp = base.size[0] * 72 / DPI, base.size[1] * 72 / DPI
todo = True

for giro in (90, 180, 270):
    pdf = ocr(base.rotate(giro, expand=True), f"girada{giro}")
    got = palabras(pdf)
    todo &= comprobar(f"escaneo girado {giro}°", got, ref, giro, wp, hp, giro)
    # el extractor y el visor de CCpdf leen el texto con pypdf: debe verlo con sus espacios
    n = len(PdfReader(str(pdf)).pages[0].extract_text().split())
    if n != len(ref):
        print(f"  FALLO: pypdf extrae {n} palabras, se esperaban {len(ref)}")
        todo = False

# Página con /Rotate: el contenido está de lado pero se muestra derecho. El texto debe quedar
# girado en el espacio de usuario (rot=90) y la fuente igual de grande que en la página derecha.
got = palabras(ocr(base.rotate(90, expand=True), "con_rotate", rotate_pdf=90))
fs = statistics.median(g[4] for g in got)
fs_ref = statistics.median(r[4] for r in ref)
ang = max(abs((g[3] - 90 + 180) % 360 - 180) for g in got)
ok = len(got) == len(ref) and abs(fs - fs_ref) <= 0.15 * fs_ref and ang <= 3
print(f"{'página con /Rotate 90':<22} palabras={len(got)} ángulo_máx_err={ang:4.1f}°  "
      f"fuente={fs:5.1f} pt (ref {fs_ref:.1f})  -> {'OK' if ok else 'FALLO'}")
todo &= ok

print("RESULTADO:", "OK" if todo else "FALLO")
sys.exit(0 if todo else 1)
