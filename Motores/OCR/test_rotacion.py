"""BUG-001: una página girada 90°/180°/270° debe dar las mismas palabras
y en las mismas coordenadas que la página derecha. Uso: python3 test_rotacion.py"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.OCR import pdf_ocr as m

# palabras únicas, para poder emparejarlas por texto entre páginas
LINEAS = [" ".join(f"Palabra{i}{chr(97 + j)}" for j in range(6)) for i in range(12)]


def pagina_falsa():
    fuente = glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)[0]
    img = Image.new("RGB", (1700, 2200), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(fuente, 40)
    for i in range(12):
        d.text((100, 120 + i * 150), LINEAS[i], font=f, fill="black")
    return img


def centros(palabras):
    return {p["texto"]: (p["x"] + p["w"] / 2, p["y"] + p["h"] / 2) for p in palabras}


def a_espacio_girado(x, y, giro, W, H):
    """Dónde cae el punto (x, y) de la página derecha tras PIL rotate(giro, expand)."""
    return {90: (y, W - x), 180: (W - x, H - y), 270: (H - y, x)}[giro]


base = pagina_falsa()
ref = centros(m._extraer_palabras_con_osd(base, "eng"))
assert len(ref) > 10, "la página de referencia no dio texto"
ok = True
for giro in (90, 180, 270):
    girada = base.rotate(giro, expand=True)  # simula un escaneo girado
    osd = m.pytesseract.image_to_osd(girada, config="--psm 0")
    horario = int(osd.split("Rotate:")[1].split()[0])
    esperado = giro  # PIL gira antihorario; OSD pide el mismo ángulo en horario
    got = centros(m._extraer_palabras_con_osd(girada, "eng"))
    comunes = [w for w in ref if w in got]
    # las coordenadas deben quedar en el espacio de la imagen GIRADA (la del PDF)
    esp = {w: a_espacio_girado(*ref[w], giro, *base.size) for w in comunes}
    dif = max((abs(esp[w][0] - got[w][0]) + abs(esp[w][1] - got[w][1]) for w in comunes), default=999)
    bien = horario == esperado and len(comunes) >= 0.9 * len(ref) and dif < 15
    ok &= bien
    print(f"giro={giro:3d} OSD={horario:3d} esperado={esperado:3d} "
          f"palabras={len(got)}/{len(ref)} desvio_max_px={dif:.1f} -> {'OK' if bien else 'FALLO'}")
print("RESULTADO:", "OK" if ok else "FALLO")
sys.exit(0 if ok else 1)
