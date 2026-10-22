"""Un PDF con contraseña no debe "comprimirse" a un PDF en blanco: Ghostscript termina con
código 0 y escribe 1 página vacía, y antes eso se guardaba como "ahorro 100 %".
Uso: python3 test_protegido.py"""
import os
import sys
import tempfile

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Compresion import pdf_compresor as m

PAGINAS = 3


def crear_pdfs(carpeta):
    """(normal, protegido): PDFs de 3 páginas con una imagen pesada cada una."""
    jpg = os.path.join(carpeta, "ruido.jpg")
    Image.effect_noise((600, 800), 60).convert("RGB").resize((2000, 2800)).save(jpg, quality=95)
    normal = os.path.join(carpeta, "normal.pdf")
    c = canvas.Canvas(normal, pagesize=(595, 842))
    for _ in range(PAGINAS):
        c.drawImage(jpg, 0, 0, 595, 842)
        c.showPage()
    c.save()
    protegido = os.path.join(carpeta, "protegido.pdf")
    w = PdfWriter()
    w.append(PdfReader(normal))
    w.encrypt("secreto")
    with open(protegido, "wb") as f:
        w.write(f)
    return normal, protegido


def main() -> int:
    fallos = 0
    motores = ["interno", "auto"] + (["ghostscript"] if m.buscar_ghostscript() else [])
    with tempfile.TemporaryDirectory() as tmp:
        normal, protegido = crear_pdfs(tmp)
        for motor in motores:
            destino = os.path.join(tmp, "sal_" + motor)
            r = m.comprimir_pdfs([normal, protegido], destino, "media", motor)
            guardados = sorted(os.listdir(destino)) if os.path.isdir(destino) else []
            bien_normal = ("normal_comprimido.pdf" in guardados
                           and len(PdfReader(os.path.join(destino, "normal_comprimido.pdf")).pages) == PAGINAS)
            bien_prot = (len(r.errores) == 1 and r.errores[0][0] == "protegido.pdf"
                         and "contraseña" in r.errores[0][1]
                         and "protegido_comprimido.pdf" not in guardados)
            ok = bien_normal and bien_prot
            fallos += not ok
            print(f"motor={motor:11s} normal comprimido={bien_normal} | protegido rechazado y sin "
                  f"archivo={bien_prot} (errores={r.errores}, archivos={guardados})  -> "
                  f"{'OK' if ok else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
