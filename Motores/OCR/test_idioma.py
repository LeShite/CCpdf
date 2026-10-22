"""Si falta el idioma en Tesseract (p. ej. tesseract-ocr-spa) el OCR terminaba con
"[OK] N páginas con OCR, 0 palabras insertadas" y un PDF sin capa de texto, sin avisar.
Ahora debe lanzar ErrorOCR con un mensaje claro. Uso: python3 test_idioma.py"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.OCR import pdf_ocr as m


def lanza(f, *a):
    try:
        f(*a)
        return None
    except m.ErrorOCR as e:
        return str(e)


def pruebas_con_get_languages_simulado():
    casos = []
    original = m.pytesseract

    def con_idiomas(lista):
        def get_languages(config=""):
            if isinstance(lista, Exception):
                raise lista
            return lista
        m.pytesseract = types.SimpleNamespace(get_languages=get_languages)

    try:
        con_idiomas(["eng", "osd"])
        msg = lanza(m._comprobar_idioma, "spa")
        casos.append(("falta spa -> ErrorOCR que nombra spa y el paquete",
                      msg is not None and "spa" in msg and "tesseract-ocr-spa" in msg and "eng, osd" in msg))
        msg = lanza(m._comprobar_idioma, "spa+eng")
        casos.append(("spa+eng con solo eng -> nombra spa y no eng como faltante",
                      msg is not None and "tesseract-ocr-spa" in msg and "tesseract-ocr-eng" not in msg))
        con_idiomas(["eng", "osd", "spa"])
        casos.append(("spa+eng con ambos instalados -> sin error", lanza(m._comprobar_idioma, "spa+eng") is None))
        con_idiomas(RuntimeError("tesseract no responde"))
        casos.append(("no se pueden listar idiomas -> no bloquea", lanza(m._comprobar_idioma, "spa") is None))
        con_idiomas([])
        casos.append(("lista vacía -> no bloquea", lanza(m._comprobar_idioma, "spa") is None))
    finally:
        m.pytesseract = original
    return casos


def pruebas_error_de_pagina():
    """Un fallo de datos de idioma al leer una página ya no se traga como 'sin palabras'."""
    casos = []
    original = m.pytesseract
    TErr = m.TesseractError

    def con_error(texto):
        def image_to_data(*a, **k):
            raise TErr(1, texto)
        m.pytesseract = types.SimpleNamespace(image_to_data=image_to_data)

    img = Image.new("L", (50, 50), 255)
    try:
        con_error("Error opening data file spa.traineddata  Failed loading language 'spa'")
        casos.append(("datos de idioma ilegibles -> ErrorOCR", lanza(m._extraer_palabras_con_coords, img, "spa") is not None))
        con_error("otro fallo cualquiera de Tesseract")
        casos.append(("otro TesseractError -> sigue devolviendo []", m._extraer_palabras_con_coords(img, "spa") == []))
    finally:
        m.pytesseract = original
    return casos


def carpeta_tessdata():
    """Carpeta tessdata real, leída de 'tesseract --list-langs'."""
    salida = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
    hallado = re.search(r'directory "?([^"\n]+?)"?:?\s*\n|in "([^"]+)"', salida)
    return next((g for g in (hallado.groups() if hallado else ()) if g), None)


def prueba_de_extremo_a_extremo():
    """aplicar_ocr con Tesseract real y un tessdata sin spa. None = no se pudo probar."""
    if not m.HAY_TESSERACT or not m.HAY_PDF2IMAGE or not shutil.which("tesseract"):
        return None
    origen = carpeta_tessdata()
    if not origen or not all(os.path.isfile(os.path.join(origen, f"{c}.traineddata")) for c in ("eng", "osd")):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        datos = os.path.join(tmp, "tessdata")
        os.mkdir(datos)
        for c in ("eng", "osd"):
            shutil.copy(os.path.join(origen, f"{c}.traineddata"), datos)
        img = Image.new("L", (1240, 1754), 255)
        ImageDraw.Draw(img).text((100, 150), "Contrato de servicio 4587", fill=0)
        pdf = os.path.join(tmp, "e.pdf")
        img.save(pdf, "PDF", resolution=150.0)
        anterior = os.environ.get("TESSDATA_PREFIX")
        os.environ["TESSDATA_PREFIX"] = datos
        try:
            msg = lanza(lambda: m.aplicar_ocr([pdf], os.path.join(tmp, "o"), "spa"))
        finally:
            if anterior is None:
                os.environ.pop("TESSDATA_PREFIX")
            else:
                os.environ["TESSDATA_PREFIX"] = anterior
        salida = os.path.join(tmp, "o", "e_ocr.pdf")
        return [("extremo a extremo (Tesseract real sin spa): ErrorOCR y sin PDF de salida",
                 msg is not None and "spa" in msg and not os.path.exists(salida))]


def main() -> int:
    casos = pruebas_con_get_languages_simulado() + pruebas_error_de_pagina()
    e2e = prueba_de_extremo_a_extremo()
    if e2e is None:
        print("  (extremo a extremo omitido: no hay Tesseract/Poppler o faltan eng/osd)")
    else:
        casos += e2e
    fallos = 0
    for nombre, bien in casos:
        fallos += not bien
        print(f"  {nombre:75s} -> {'OK' if bien else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
