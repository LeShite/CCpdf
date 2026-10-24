"""BUG-017: el visor dibuja con PDFium. Un escaneo CCITT G4 (el formato típico de los
escaneos en blanco y negro) salía en blanco con el motor propio; /Rotate y cerrar el
documento a mitad de un render (los renders van en hilos) no pueden romper nada.
Uso: python3 test_render_pdfium.py"""
import io
import os
import sys
import tempfile
import threading

from PIL import Image, ImageDraw
from pypdf import PdfWriter
from pypdf.generic import BooleanObject, DictionaryObject, NameObject, NumberObject, StreamObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Visualizacion import DocumentoPDF, ErrorVisor, visor_pdf_motor

W, H = 400, 300                # píxeles del escaneo = puntos de la página
RECT = (20, 20, 180, 100)      # rectángulo negro, en píxeles desde arriba a la izquierda


def crear_ccitt(ruta, rotar=0):
    """Página con un escaneo CCITT G4: fondo blanco y un rectángulo negro."""
    img = Image.new("1", (W, H), 1)
    ImageDraw.Draw(img).rectangle(RECT, fill=0)
    tif = io.BytesIO()
    img.save(tif, "TIFF", compression="group4")
    t = Image.open(io.BytesIO(tif.getvalue()))
    assert len(t.tag_v2[273]) == 1, "se esperaba una sola tira en el TIFF"
    inicio = t.tag_v2[273][0]
    datos = tif.getvalue()[inicio:inicio + t.tag_v2[279][0]]

    w = PdfWriter()
    pag = w.add_blank_page(W, H)
    imagen = StreamObject()
    imagen._data = datos           # ya va comprimido en CCITT: sin recodificar
    imagen.update({
        NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(W), NameObject("/Height"): NumberObject(H),
        NameObject("/ColorSpace"): NameObject("/DeviceGray"),
        NameObject("/BitsPerComponent"): NumberObject(1),
        NameObject("/Filter"): NameObject("/CCITTFaxDecode"),
        NameObject("/DecodeParms"): DictionaryObject({
            NameObject("/K"): NumberObject(-1), NameObject("/Columns"): NumberObject(W),
            NameObject("/Rows"): NumberObject(H),
            # PIL guarda el modo "1" como BlackIsZero (262 = 1) sin invertir los bits;
            # el PDF por defecto lee lo contrario, así que hay que darle la vuelta
            NameObject("/BlackIs1"): BooleanObject(t.tag_v2[262] == 1)}),
    })
    pag[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject(
        {NameObject("/Im0"): w._add_object(imagen)})})
    flujo = StreamObject()
    flujo.set_data(b"q %d 0 0 %d 0 0 cm /Im0 Do Q" % (W, H))
    pag[NameObject("/Contents")] = w._add_object(flujo)
    if rotar:
        pag[NameObject("/Rotate")] = NumberObject(rotar)
    with open(ruta, "wb") as f:
        w.write(f)


def oscuro(img, caja):
    """Fracción de píxeles oscuros dentro de `caja` (en la imagen a zoom 1)."""
    zona = img.convert("L").crop(caja)
    return zona.point(lambda p: 255 if p < 128 else 0).histogram()[255] / (zona.width * zona.height)


def main() -> int:
    fallos = 0

    def check(nombre, bien, detalle=""):
        nonlocal fallos
        fallos += not bien
        print(f"  {nombre:55s} {detalle:24s} -> {'OK' if bien else 'FALLA'}")

    if visor_pdf_motor.pdfium is None:
        print("pypdfium2 no está instalado: pip install -r requirements.txt")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "escaneo.pdf")
        crear_ccitt(ruta)

        doc = DocumentoPDF(ruta)
        img = doc.renderizar(0, zoom=1.0)
        doc.cerrar()
        dentro, fuera = oscuro(img, RECT), oscuro(img, (220, 150, 380, 280))
        check("escaneo CCITT G4: el rectángulo se ve", dentro > 0.9, f"oscuro={dentro:.0%}")
        check("escaneo CCITT G4: el fondo sigue blanco", fuera < 0.05, f"oscuro={fuera:.0%}")

        ruta_rot = os.path.join(tmp, "rotada.pdf")
        crear_ccitt(ruta_rot, rotar=90)
        doc = DocumentoPDF(ruta_rot)
        img = doc.renderizar(0, zoom=1.0)
        tam = doc.tamano_pagina(0)
        doc.cerrar()
        check("/Rotate 90: imagen en horizontal como la página",
              img.size == (H, W) and tam == (H, W), f"img={img.size} pág={tam}")
        # girada 90° en horario, el rectángulo de arriba a la izquierda pasa a arriba a la derecha
        dentro = oscuro(img, (H - RECT[3], RECT[0], H - RECT[1], RECT[2]))
        check("/Rotate 90: el contenido gira en sentido horario", dentro > 0.9, f"oscuro={dentro:.0%}")

        # cerrar mientras otro hilo dibuja: sin crash; después, ErrorVisor
        doc = DocumentoPDF(ruta)
        errores = []

        def dibujar():
            for _ in range(50):
                try:
                    doc.renderizar(0, zoom=2.0)
                except ErrorVisor:
                    pass
                except Exception as e:      # cualquier otra cosa es un fallo
                    errores.append(repr(e))

        hilos = [threading.Thread(target=dibujar) for _ in range(3)]
        for h in hilos:
            h.start()
        doc.cerrar()
        for h in hilos:
            h.join()
        check("cerrar a mitad de renders en 3 hilos", not errores, f"errores={len(errores)}")

        # respaldo: sin PDFium sigue dibujando con el motor propio
        guardado, visor_pdf_motor.pdfium = visor_pdf_motor.pdfium, None
        try:
            doc = DocumentoPDF(ruta)
            img = doc.renderizar(0, zoom=1.0)
            doc.cerrar()
            check("sin PDFium usa el motor propio", doc._pdfium is None and img.size == (W, H),
                  f"img={img.size}")
        finally:
            visor_pdf_motor.pdfium = guardado

    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
