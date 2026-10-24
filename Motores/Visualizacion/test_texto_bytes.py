"""Una cadena de texto con ciertos bytes (0x85 = "…" en WinAnsi, 0x0D, 0x1C-0x1E) hacía
fallar PIL con raqm ("raqm_layout() failed"): la línea entera desaparecía del visor.
Prueba el motor propio (el respaldo cuando PDFium no está), no PDFium.
Uso: python3 test_texto_bytes.py"""
import os
import sys
import tempfile

from PIL import features
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Visualizacion import DocumentoPDF, visor_pdf_motor

visor_pdf_motor.pdfium = None   # forzar el motor propio

# una línea por byte problemático (octal), más una de control sin ninguno
LINEAS = [(150, b"Hola \\205 mundo"), (120, b"Salto \\015 de linea"), (90, b"Sep \\034\\035\\036 fin"),
          (60, b"Linea normal sin bytes raros")]


def crear_pdf(ruta):
    w = PdfWriter()
    pag = w.add_blank_page(300, 200)
    fuente = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                               NameObject("/Subtype"): NameObject("/Type1"),
                               NameObject("/BaseFont"): NameObject("/Helvetica")})
    pag[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): w._add_object(fuente)})})
    flujo = StreamObject()
    flujo.set_data(b"".join(b"BT /F1 14 Tf 20 %d Td (%s) Tj ET\n" % (y, t) for y, t in LINEAS))
    pag[NameObject("/Contents")] = w._add_object(flujo)
    with open(ruta, "wb") as f:
        w.write(f)


def tinta(img, y_pdf, alto_pag=200, margen=12):
    """Píxeles oscuros en la franja de la línea que tiene su base en y_pdf (puntos)."""
    gris = img.convert("L")
    y1 = int(alto_pag - y_pdf)
    caja = gris.crop((0, max(0, y1 - margen), gris.width, y1 + 4))
    return caja.point(lambda p: 255 if p < 128 else 0).histogram()[255]


def main() -> int:
    print(f"raqm disponible: {features.check('raqm')} (sin raqm este test no distingue el fallo)")
    avisos = []
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "t.pdf")
        crear_pdf(ruta)
        doc = DocumentoPDF(ruta, logger=avisos.append)
        img = doc.renderizar(0, zoom=2.0)
        doc.cerrar()
    fallos = 0
    for y, t in LINEAS:
        n = tinta(img.resize((300, 200)), y)
        bien = n > 20
        fallos += not bien
        print(f"  línea y={y:3d} {t.decode():32s} píxeles de tinta={n:4d} -> {'OK' if bien else 'FALLA (no se dibujó)'}")
    sin_avisos = not [a for a in avisos if "draw.text" in a]
    fallos += not sin_avisos
    print(f"  avisos de draw.text: {[a for a in avisos if 'draw.text' in a] or 'ninguno'} -> "
          f"{'OK' if sin_avisos else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
