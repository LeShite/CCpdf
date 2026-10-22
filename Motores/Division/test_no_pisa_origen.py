"""Si la carpeta de salida era la del PDF de origen y una unidad (o las páginas sin asignar)
tenía el mismo nombre que ese PDF, os.replace lo sobrescribía: el original se perdía y quedaba
con las páginas de una sola unidad. Uso: python3 test_no_pisa_origen.py"""
import os
import sys
import tempfile

from pypdf import PdfReader
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Division import pdf_divisor as m

UNIDADES = ["UMF 7 TORREON", "HGZ 51 CHAPALA DURANGO"]
PAGINAS = ["UMF 7 TORREON", "UMF 7 TORREON", "HGZ 51 CHAPALA DURANGO", "OTRA UNIDAD 99"]


def crear_pdf(ruta):
    c = canvas.Canvas(ruta, pagesize=(595, 842))
    for valor in PAGINAS:
        c.drawString(60, 780, f"UNIDAD MEDICA: {valor}")
        c.drawString(60, 760, "MODELO: XYZ")
        c.showPage()
    c.save()


def dividir(origen, destino, logs):
    return m.dividir_por_unidad(origen, destino, UNIDADES, callback_log=logs.append)


def original_intacto(ruta, bytes_antes):
    return os.path.isfile(ruta) and open(ruta, "rb").read() == bytes_antes and len(PdfReader(ruta).pages) == len(PAGINAS)


def main() -> int:
    casos = []
    with tempfile.TemporaryDirectory() as tmp:
        # 1. unidad con el mismo nombre que el origen, salida = carpeta del origen
        c1 = os.path.join(tmp, "c1"); os.mkdir(c1)
        origen = os.path.join(c1, "UMF 7 TORREON.pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        logs = []
        r = dividir(origen, c1, logs)
        casos.append(("1. original intacto (mismo nombre que una unidad)", original_intacto(origen, antes)))
        casos.append(("1. la unidad se guardó como 'UMF 7 TORREON (2).pdf' con sus 2 páginas",
                      os.path.isfile(os.path.join(c1, "UMF 7 TORREON (2).pdf"))
                      and len(PdfReader(os.path.join(c1, "UMF 7 TORREON (2).pdf")).pages) == 2))
        casos.append(("1. avisa en el log y no hay errores",
                      any("PDF de origen" in l for l in logs) and not r.errores and r.unidades_generadas == 2))

        # 2. destino vacío = carpeta del origen (el valor por defecto del motor)
        c2 = os.path.join(tmp, "c2"); os.mkdir(c2)
        origen = os.path.join(c2, "UMF 7 TORREON.pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        dividir(origen, "", [])
        casos.append(("2. destino vacío: original intacto", original_intacto(origen, antes)))

        # 3. destino = symlink a la carpeta del origen
        c3 = os.path.join(tmp, "c3"); os.mkdir(c3)
        origen = os.path.join(c3, "UMF 7 TORREON.pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        enlace = os.path.join(tmp, "enlace")
        os.symlink(c3, enlace)
        dividir(origen, enlace, [])
        casos.append(("3. destino por symlink: original intacto", original_intacto(origen, antes)))

        # 4. el origen se llama como el archivo de páginas sin asignar
        c4 = os.path.join(tmp, "c4"); os.mkdir(c4)
        origen = os.path.join(c4, m.NOMBRE_HUERFANAS + ".pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        r = dividir(origen, c4, [])
        casos.append(("4. origen = _PAGINAS_SIN_ASIGNAR.pdf: original intacto y huérfanas guardadas aparte",
                      original_intacto(origen, antes) and r.paginas_huerfanas == 1
                      and os.path.basename(r.archivo_huerfanas) != m.NOMBRE_HUERFANAS + ".pdf"))

        # 5. mayúsculas distintas (en Windows/macOS serían el mismo archivo)
        c5 = os.path.join(tmp, "c5"); os.mkdir(c5)
        origen = os.path.join(c5, "umf 7 torreon.pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        dividir(origen, c5, [])
        casos.append(("5. nombre en otras mayúsculas: original intacto", original_intacto(origen, antes)))

        # 6. caso normal: otra carpeta de salida, sin renombrar nada
        c6 = os.path.join(tmp, "c6"); os.mkdir(c6)
        origen = os.path.join(c6, "UMF 7 TORREON.pdf")
        crear_pdf(origen)
        antes = open(origen, "rb").read()
        salida = os.path.join(tmp, "salida6")
        logs = []
        dividir(origen, salida, logs)
        casos.append(("6. carpeta distinta: nombres normales, sin avisos",
                      sorted(os.listdir(salida)) == ["HGZ 51 CHAPALA DURANGO.pdf", "UMF 7 TORREON.pdf",
                                                      "_PAGINAS_SIN_ASIGNAR.pdf"]
                      and not any("PDF de origen" in l for l in logs) and original_intacto(origen, antes)))

    fallos = 0
    for nombre, bien in casos:
        fallos += not bien
        print(f"  {nombre:88s} -> {'OK' if bien else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
