"""Prueba del limpiador de metadatos.

Ejecutar desde la raíz del repo:  python -m Motores.Metadatos.test_limpieza
"""
import os
import sys
import tempfile

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, StreamObject

from Motores.Metadatos import leer_metadatos, limpiar_metadatos

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


T = tempfile.mkdtemp()
src = os.path.join(T, "con metadatos.pdf")

# PDF de 3 páginas con /Info, XMP de documento, XMP y PieceInfo de página
w = PdfWriter()
for _ in range(3):
    w.add_blank_page(300, 300)
w.add_metadata({"/Author": "Juan Pérez SECRETO", "/Creator": "WordSECRETO",
                "/Producer": "ProdSECRETO", "/Title": "Contrato SECRETO",
                "/Empresa": "ACME SECRETO"})
xmp = StreamObject()
xmp.set_data(b"<x:xmpmeta>XMPSECRETO</x:xmpmeta>")
w._root_object[NameObject("/Metadata")] = w._add_object(xmp)
xmp_pag = StreamObject()
xmp_pag.set_data(b"<x:xmpmeta>PAGSECRETO</x:xmpmeta>")
w.pages[0][NameObject("/Metadata")] = w._add_object(xmp_pag)
w.pages[1][NameObject("/PieceInfo")] = w._add_object(StreamObject())
w.write(src)
original = open(src, "rb").read()

info = leer_metadatos(src)
check(info.info.get("Autor") == "Juan Pérez SECRETO", "lee el autor")
check(info.info.get("Empresa") == "ACME SECRETO", "lee claves propias")
check(info.tiene_xmp and info.paginas_con_xmp == 1 and info.paginas_con_pieceinfo == 1,
      "detecta XMP y PieceInfo")

dest = os.path.join(T, "salida")
res = limpiar_metadatos([src, src], destino=dest)
check(res.limpiados == 1 and len(res.omitidos) == 1 and not res.errores,
      f"limpia 1 y omite el duplicado ({res.a_texto()!r})")

salida = os.path.join(dest, "con metadatos_limpio.pdf")
check(os.path.isfile(salida), "crea el archivo de salida")
datos = open(salida, "rb").read()
check(b"SECRETO" not in datos, "ningún byte de los metadatos queda en el archivo")
check(len(PdfReader(salida).pages) == 3, "conserva las 3 páginas")
check(leer_metadatos(salida).vacio, "el resultado no tiene metadatos")
check(open(src, "rb").read() == original, "el original no se modificó")

# Segunda pasada: no pisa el resultado anterior
res2 = limpiar_metadatos([src], destino=dest)
check(os.path.isfile(os.path.join(dest, "con metadatos_limpio (2).pdf")),
      "no sobrescribe un resultado existente")

# Destino = carpeta del original: nunca pisa el original
res3 = limpiar_metadatos([src], destino=T, sufijo="")
check(open(src, "rb").read() == original and res3.limpiados == 1,
      "con sufijo vacío en la misma carpeta no pisa el original")

# PDF protegido
prot = os.path.join(T, "protegido.pdf")
wp = PdfWriter()
wp.add_blank_page(100, 100)
wp.encrypt("clave")
wp.write(prot)
check(leer_metadatos(prot).cifrado, "detecta PDF protegido")
r4 = limpiar_metadatos([prot], destino=dest)
check(len(r4.errores) == 1, "un PDF protegido da error claro, no revienta")

from Motores.Metadatos.pdf_metadatos import formatear_fecha_pdf
check(formatear_fecha_pdf("D:20261028031946-06'00'") == "28/10/2026 03:19:46 (UTC-06:00)",
      "formatea fecha con zona horaria")
check(formatear_fecha_pdf("D:20261028031946Z") == "28/10/2026 03:19:46 (UTC)", "formatea fecha UTC")
check(formatear_fecha_pdf("D:2026") == "01/01/2026", "formatea fecha incompleta")
check(formatear_fecha_pdf("ayer") == "ayer", "deja igual lo que no es fecha PDF")

sys.exit(0 if ok else 1)
