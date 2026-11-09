"""Prueba del arrastrar y soltar y de la vista de Metadatos (necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_arrastrar_soltar
Simula lo que llega al soltar archivos (la lista de rutas) en cada módulo.
"""
import os
import sys
import tempfile
from unittest import mock

from pypdf import PdfWriter

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

from Interfaz import app as A

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


T = tempfile.mkdtemp()
carpeta = os.path.join(T, "carpeta con espacios")
os.makedirs(carpeta)
pdfs = []
for i in range(3):
    ruta = os.path.join(carpeta, f"doc {i}.pdf")
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.add_metadata({"/Author": f"Autor {i}"})
    w.write(ruta)
    pdfs.append(ruta)
txt = os.path.join(T, "notas.txt")
open(txt, "w").write("x")

app = A.CCPdfApp()
app.update()
check(app._dnd_activo == A._HAY_DND, f"arrastrar y soltar activo: {app._dnd_activo}")
check("metadatos" in app._vistas, "existe la vista Metadatos")
check(A.APP_VERSION == "v1.5.0", "versión v1.5.0")

# El texto que entrega tkdnd usa llaves para rutas con espacios
datos = " ".join("{%s}" % p for p in pdfs[:2])
check(list(app.tk.splitlist(datos)) == pdfs[:2], "rutas con espacios se separan bien")

with mock.patch.object(A.messagebox, "showwarning") as aviso, \
     mock.patch.object(A.messagebox, "showinfo"):
    app.mostrar_vista("fusionador")
    app._enrutar_soltados(pdfs[:2] + [txt])
    check(app._lista_fusion == pdfs[:2], "Fusionar recibe los PDFs soltados")
    check(aviso.called, "avisa que se ignoró el .txt")
    app._enrutar_soltados(pdfs[:2])
    check(len(app._lista_fusion) == 2, "no duplica al soltar lo mismo")

    app.mostrar_vista("compresor")
    app._enrutar_soltados([carpeta])
    check(len(app._lista_compresion) == 3, "Comprimir: soltar una carpeta añade sus PDFs")

    app.mostrar_vista("ocr")
    app._enrutar_soltados([pdfs[0]])
    check(app._lista_ocr == [pdfs[0]], "OCR recibe el PDF")

    app.mostrar_vista("divisor")
    app._enrutar_soltados([pdfs[1]])
    check(app._div_origen.get() == pdfs[1], "Dividir: el PDF soltado pasa a PDF origen")

    app.mostrar_vista("extractor")
    app._enrutar_soltados([pdfs[2]])
    check(app._ext_origen.get() == carpeta, "Extracción: usa la carpeta del PDF soltado")

    app.mostrar_vista("metadatos")
    app._enrutar_soltados(pdfs)
    check(len(app._lista_meta) == 3, "Metadatos recibe los PDFs")
    info = app.txt_meta_info.get("1.0", "end")
    check("Autor 0" in info, "muestra lo que revela el PDF al añadirlo")

    cargado = {}
    with mock.patch.object(app.visor, "cargar", lambda r: cargado.setdefault("r", r)):
        app.mostrar_vista("inicio")
        app._enrutar_soltados([pdfs[0]])
    check(app._clave_actual == "visor" and cargado.get("r") == pdfs[0],
          "en el Dashboard un PDF soltado se abre en el Visor")

    app._procesando = True
    app.mostrar_vista("ocr")
    app._enrutar_soltados([pdfs[1]])
    check(app._lista_ocr == [pdfs[0]], "no acepta archivos mientras hay un proceso en curso")
    app._procesando = False

app.destroy()
sys.exit(0 if ok else 1)
