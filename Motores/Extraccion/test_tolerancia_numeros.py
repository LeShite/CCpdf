"""Con "Tolerancia ortográfica" los números también se toleraban: "folio 4587" coincidía con
"folio 4581" y "HGZ 51" con "HGZ 5 CHAPALA", y se cortaba o clasificaba la página equivocada.
Las letras siguen tolerando errores de OCR; los números deben coincidir exactos.
Uso: python3 test_tolerancia_numeros.py"""
import os
import sys
import tempfile

from pypdf import PdfReader
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Extraccion import pdf_motor as m


def coincide(clave, texto, **kw):
    return m.coincide(m.normalizar(clave), m.normalizar(texto), **kw)


def crear_pdf(ruta, paginas):
    c = canvas.Canvas(ruta, pagesize=(595, 842))
    for t in paginas:
        c.drawString(72, 700, t)
        c.showPage()
    c.save()


def main() -> int:
    casos = []
    # --- números exactos con tolerancia
    casos.append(("folio 4587 NO coincide con folio 4581",
                  not coincide("folio 4587", "recibo folio 4581 del mes", tolerar=True)))
    casos.append(("HGZ 51 NO coincide con HGZ 5 CHAPALA",
                  not coincide("HGZ 51", "HGZ 5 CHAPALA", tolerar=True)))
    casos.append(("HGZ 51 NO coincide con HGZ 510 (número más largo)",
                  not coincide("HGZ 51", "unidad HGZ 510", tolerar=True)))
    casos.append(("solo dígitos: 4587 NO coincide con 4581",
                  not coincide("4587", "folio 4581", tolerar=True)))
    casos.append(("varios números: todos deben estar (12 y 2025)",
                  coincide("oficio 12 de 2025", "oficio 12 de 2025 firmado", tolerar=True)
                  and not coincide("oficio 12 de 2025", "oficio 12 de 2024", tolerar=True)))
    # --- lo que debe seguir tolerándose
    casos.append(("folio 4587 SÍ coincide con el mismo folio",
                  coincide("folio 4587", "recibo folio 4587 del mes", tolerar=True)))
    casos.append(("letras con error de OCR siguen tolerándose (fol1o 4587)",
                  coincide("folio 4587", "recibo fol1o 4587 del mes", tolerar=True)))
    casos.append(("'firma' sigue tolerando 'firmaa'", coincide("firma", "la firmaa del cliente", tolerar=True)))
    casos.append(("'forma' NO coincide con 'firma' (umbral de claves cortas)",
                  not coincide("firma", "la forma del acta", tolerar=True)))
    casos.append(("sin tolerancia no cambia nada", coincide("folio 4587", "folio 4587", tolerar=False)
                  and not coincide("folio 4587", "folio 4581", tolerar=False)))
    # --- de punta a punta con PDFs: solo la página del folio correcto
    with tempfile.TemporaryDirectory() as tmp:
        origen = os.path.join(tmp, "in")
        os.mkdir(origen)
        crear_pdf(os.path.join(origen, "a.pdf"), ["portada", "recibo folio 4581", "recibo folio 4587", "anexo"])
        r = m.cortar_hasta_palabra(origen, os.path.join(tmp, "cortes"), "folio 4587", tolerar=True)
        corte = os.path.join(tmp, "cortes", "3P", "a_1-a-3.pdf")
        casos.append(("cortar_hasta_palabra corta en la página 3 (no en la 2)",
                      r.con_resultado == 1 and os.path.isfile(corte) and len(PdfReader(corte).pages) == 3))
        r = m.clasificar_por_lista(origen, os.path.join(tmp, "clas"), ["folio 4587"], tolerar=True)
        salida = os.path.join(tmp, "clas", "a_Filtro_folio_4587.pdf")
        casos.append(("clasificar_por_lista guarda solo la página del folio 4587",
                      os.path.isfile(salida) and len(PdfReader(salida).pages) == 1))
    fallos = 0
    for nombre, bien in casos:
        fallos += not bien
        print(f"  {nombre:66s} -> {'OK' if bien else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
