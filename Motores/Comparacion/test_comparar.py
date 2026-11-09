"""Prueba del comparador de PDFs.

Ejecutar desde la raíz del repo:  python -m Motores.Comparacion.test_comparar
"""
import os
import sys
import tempfile

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from Motores.Comparacion import comparar_pdfs, diferencias_texto, ErrorComparacion

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


T = tempfile.mkdtemp()


def hacer_pdf(ruta, paginas, cuadro_en=None):
    """paginas: lista de textos. cuadro_en: índice de página donde dibujar un rectángulo."""
    c = canvas.Canvas(ruta, pagesize=A4)
    for i, txt in enumerate(paginas):
        c.setFont("Helvetica", 14)
        y = 780
        for linea in txt.split("\n"):
            c.drawString(60, y, linea)
            y -= 22
        if cuadro_en == i:
            c.rect(300, 200, 150, 100, fill=1)
        c.showPage()
    c.save()


base = ["Contrato de servicio\nEl precio mensual es 500 pesos\nVigencia doce meses",
        "Clausula segunda\nEl cliente pagara puntualmente",
        "Firma del cliente"]

a = os.path.join(T, "contrato v1.pdf")
hacer_pdf(a, base)

# 1. Idénticos
a2 = os.path.join(T, "copia.pdf")
hacer_pdf(a2, base)
r = comparar_pdfs(a, a2, destino=T)
check(r.identicos, "dos PDFs iguales: sin diferencias")
check(os.path.isfile(r.ruta_salida), "genera informe aunque sean iguales")

# 2. Cambio de texto en pág. 1 y cambio solo visual (un cuadro) en pág. 3
b = os.path.join(T, "contrato v2.pdf")
mod = list(base)
mod[0] = mod[0].replace("500", "750")
hacer_pdf(b, mod, cuadro_en=2)
r = comparar_pdfs(a, b, destino=T)
paginas = {c.numero: c for c in r.cambios}
check(set(paginas) == {1, 3}, f"detecta cambios en págs. 1 y 3 (encontró {sorted(paginas)})")
check(paginas.get(1) and "750" in paginas[1].añadidas and "500" in paginas[1].quitadas,
      "pág. 1: 500 → 750 en el texto")
check(paginas.get(3) and paginas[3].zonas > 0 and not paginas[3].añadidas,
      "pág. 3: cambio solo visual (sin texto distinto)")
inf = PdfReader(r.ruta_salida)
check(len(inf.pages) == 1 + 2, f"informe: portada + 2 páginas ({len(inf.pages)})")
check("750" in (inf.pages[1].extract_text() or ""), "el informe lista la palabra añadida")
check(not (inf.metadata or {}).get("/Author"), "el informe no lleva autor")

# 3. Página añadida
c3 = os.path.join(T, "contrato v3.pdf")
hacer_pdf(c3, base + ["Anexo nuevo"])
r = comparar_pdfs(a, c3, destino=T)
check([c.estado for c in r.cambios] == ["añadida"] and r.cambios[0].numero == 4,
      "detecta página añadida al final")

# 4. Página quitada
c4 = os.path.join(T, "contrato v4.pdf")
hacer_pdf(c4, base[:2])
r = comparar_pdfs(a, c4, destino=T)
check([c.estado for c in r.cambios] == ["eliminada"], "detecta página quitada")

# 5. No pisa un informe previo ni los originales
r1 = comparar_pdfs(a, b, destino=T)
r2 = comparar_pdfs(a, b, destino=T)
check(r1.ruta_salida != r2.ruta_salida and os.path.isfile(r2.ruta_salida),
      "no sobrescribe un informe anterior")

# 6. Errores claros
for args, msg in (((a, a), "mismo archivo"), ((a, os.path.join(T, "no.pdf")), "archivo inexistente")):
    try:
        comparar_pdfs(*args, destino=T)
        check(False, f"error con {msg}")
    except ErrorComparacion:
        check(True, f"error claro con {msg}")

# 7. Diferencias de texto
añ, qu = diferencias_texto("uno dos tres", "uno cuatro tres cinco")
check(añ == ["cuatro", "cinco"] and qu == ["dos"], "diff de palabras")

sys.exit(0 if ok else 1)
