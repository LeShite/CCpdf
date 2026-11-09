"""
pdf_comparador.py — Compara dos versiones de un PDF.

Dos comparaciones complementarias, página a página (la página N de A con la N de B):
  - Texto: palabras añadidas y quitadas (difflib sobre el texto extraído).
  - Visual: se renderizan ambas páginas y se marcan las zonas donde cambian los
    píxeles. Detecta cambios que el texto no ve (imágenes, firmas, sellos,
    escaneos sin capa de texto, cambios de formato).

Genera un informe PDF: una portada con el resumen y, por cada página con
diferencias, la página de B con las zonas cambiadas marcadas en rojo junto a la
lista de palabras añadidas/quitadas.

Limitación: no realinea páginas. Si en B se insertó una página en medio, todas
las siguientes aparecen como cambiadas.
"""
from __future__ import annotations

import difflib
import io
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from pypdf import PdfReader

try:
    import pypdfium2 as pdfium
    HAY_PDFIUM = True
except Exception:  # pragma: no cover
    pdfium = None
    HAY_PDFIUM = False


class ErrorComparacion(Exception):
    """Error de validación (archivos inexistentes, protegidos, iguales...)."""


DPI_COMPARACION = 100        # suficiente para ver cambios, rápido
UMBRAL_PIXEL = 40            # diferencia de gris (0-255) para contar un píxel como cambiado
TAM_CELDA = 12               # px: se marcan celdas, no píxeles sueltos
MIN_PIXELES_CELDA = 3        # píxeles distintos para marcar una celda (ignora ruido de antialias)
MAX_PALABRAS_LISTA = 60      # por página en el informe


@dataclass
class CambioPagina:
    numero: int                                   # 1-based
    estado: str                                   # "cambiada" | "añadida" | "eliminada"
    añadidas: list = field(default_factory=list)  # palabras nuevas en B
    quitadas: list = field(default_factory=list)  # palabras que estaban en A
    zonas: int = 0                                # celdas con cambios visuales
    porcentaje_visual: float = 0.0
    sin_texto: bool = False                       # ninguna de las dos tiene capa de texto


@dataclass
class ResumenComparacion:
    archivo_a: str = ""
    archivo_b: str = ""
    paginas_a: int = 0
    paginas_b: int = 0
    cambios: list = field(default_factory=list)   # CambioPagina
    ruta_salida: str = ""
    cancelado: bool = False
    errores: list = field(default_factory=list)

    @property
    def identicos(self) -> bool:
        return not self.cambios and self.paginas_a == self.paginas_b

    def a_texto(self) -> str:
        l = []
        if self.cancelado:
            l.append("⚠ Proceso cancelado por el usuario.")
        l.append(f"A: {os.path.basename(self.archivo_a)} ({self.paginas_a} págs.)")
        l.append(f"B: {os.path.basename(self.archivo_b)} ({self.paginas_b} págs.)")
        if self.identicos:
            l.append("✔ No se encontraron diferencias.")
        else:
            n_añ = sum(len(c.añadidas) for c in self.cambios)
            n_qu = sum(len(c.quitadas) for c in self.cambios)
            l.append(f"Páginas con diferencias: {len(self.cambios)}")
            l.append(f"Palabras añadidas: {n_añ}  ·  quitadas: {n_qu}")
            for c in self.cambios[:10]:
                l.append(f"  • Pág. {c.numero}: {_describir(c)}")
            if len(self.cambios) > 10:
                l.append(f"  … y {len(self.cambios) - 10} más")
        if self.ruta_salida:
            l.append(f"Informe: {self.ruta_salida}")
        return "\n".join(l)


def _describir(c: CambioPagina) -> str:
    if c.estado == "añadida":
        return "página nueva en B"
    if c.estado == "eliminada":
        return "página quitada en B"
    partes = []
    if c.añadidas or c.quitadas:
        partes.append(f"+{len(c.añadidas)} / −{len(c.quitadas)} palabras")
    if c.zonas:
        partes.append(f"cambio visual en {c.porcentaje_visual:.1f}% de la página")
    if c.sin_texto:
        partes.append("sin capa de texto (solo comparación visual)")
    return ", ".join(partes) or "cambio menor"


# ─────────────────────────────────────────────────────────────
#  TEXTO
# ─────────────────────────────────────────────────────────────
_RE_PALABRA = re.compile(r"\S+")


def _palabras(texto: str) -> list:
    return _RE_PALABRA.findall(texto or "")


def diferencias_texto(texto_a: str, texto_b: str) -> tuple:
    """Devuelve (añadidas, quitadas) a nivel de palabra."""
    a, b = _palabras(texto_a), _palabras(texto_b)
    añadidas, quitadas = [], []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("replace", "delete"):
            quitadas.extend(a[i1:i2])
        if op in ("replace", "insert"):
            añadidas.extend(b[j1:j2])
    return añadidas, quitadas


# ─────────────────────────────────────────────────────────────
#  VISUAL
# ─────────────────────────────────────────────────────────────
def _render(doc, idx: int, dpi: int) -> Image.Image:
    pagina = doc[idx]
    try:
        img = pagina.render(scale=dpi / 72).to_pil()
    finally:
        pagina.close()
    return img.convert("L")


def mascara_diferencias(img_a: Image.Image, img_b: Image.Image) -> tuple:
    """Compara dos imágenes en gris. Devuelve (celdas_cambiadas, porcentaje)."""
    if img_a.size != img_b.size:
        img_a = img_a.resize(img_b.size)
    diff = ImageChops.difference(img_a, img_b).point(lambda v: 255 if v > UMBRAL_PIXEL else 0)
    if diff.getbbox() is None:
        return [], 0.0
    # Reducir por bloques de TAM_CELDA: cada píxel resultante es la media de su
    # celda, así que "≥ MIN_PIXELES_CELDA píxeles distintos" equivale a una
    # media ≥ MIN·255/TAM². Mucho más rápido que recorrer píxel a píxel.
    reducida = diff.reduce(TAM_CELDA)
    umbral = MIN_PIXELES_CELDA * 255 / (TAM_CELDA * TAM_CELDA) - 0.5
    datos = reducida.load()
    rw, rh = reducida.size
    celdas = [(cx * TAM_CELDA, cy * TAM_CELDA)
              for cy in range(rh) for cx in range(rw) if datos[cx, cy] >= umbral]
    return celdas, 100.0 * len(celdas) / max(rw * rh, 1)


def _marcar(img_b: Image.Image, celdas: list) -> Image.Image:
    """Página B en color con las celdas cambiadas resaltadas en rojo."""
    base = img_b.convert("RGB")
    capa = Image.new("L", base.size, 0)
    d = ImageDraw.Draw(capa)
    for x, y in celdas:
        d.rectangle([x, y, x + TAM_CELDA - 1, y + TAM_CELDA - 1], fill=255)
    capa = capa.filter(ImageFilter.MaxFilter(5))           # unir celdas vecinas
    rojo = Image.new("RGB", base.size, (230, 40, 40))
    resaltado = Image.composite(Image.blend(base, rojo, 0.45), base, capa)
    # Contorno de las zonas para verlas aunque la marca sea pequeña
    borde = ImageChops.subtract(capa, capa.filter(ImageFilter.MinFilter(5)))
    return Image.composite(rojo, resaltado, borde)


# ─────────────────────────────────────────────────────────────
#  INFORME
# ─────────────────────────────────────────────────────────────
def _escribir_informe(ruta: str, res: ResumenComparacion, imagenes: dict) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    W, H = A4
    M = 40
    c = canvas.Canvas(ruta, pagesize=A4)
    c.setTitle("Comparación de PDFs")
    c.setAuthor("")
    c.setCreator("")
    c.setProducer("CCpdf")

    def texto_ajustado(x, y, txt, ancho_max, fuente="Helvetica", tam=9, color="#333333"):
        c.setFont(fuente, tam)
        c.setFillColor(HexColor(color))
        linea = ""
        for palabra in txt.split(" "):
            prueba = (linea + " " + palabra).strip()
            if c.stringWidth(prueba, fuente, tam) > ancho_max and linea:
                c.drawString(x, y, linea)
                y -= tam + 3
                linea = palabra
            else:
                linea = prueba
        if linea:
            c.drawString(x, y, linea)
            y -= tam + 3
        return y

    # Portada
    y = H - M
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HexColor("#111827"))
    c.drawString(M, y, "Comparación de PDFs")
    y -= 28
    for etq, ruta_x, n in (("A (original)", res.archivo_a, res.paginas_a),
                           ("B (nuevo)", res.archivo_b, res.paginas_b)):
        y = texto_ajustado(M, y, f"{etq}: {os.path.basename(ruta_x)} — {n} página(s)",
                           W - 2 * M, "Helvetica", 11, "#111827")
    y -= 10
    if res.identicos:
        texto_ajustado(M, y, "No se encontraron diferencias.", W - 2 * M,
                       "Helvetica-Bold", 12, "#15803D")
    else:
        y = texto_ajustado(M, y, f"Páginas con diferencias: {len(res.cambios)}",
                           W - 2 * M, "Helvetica-Bold", 12, "#B91C1C")
        y -= 6
        for cp in res.cambios:
            if y < M + 20:
                c.showPage()
                y = H - M
            y = texto_ajustado(M + 10, y, f"• Página {cp.numero}: {_describir(cp)}",
                               W - 2 * M - 10, tam=10)
        y -= 10
        texto_ajustado(M, y, "En las páginas siguientes se muestra la versión B con las zonas "
                             "cambiadas en rojo. La comparación es página a página (no realinea "
                             "páginas insertadas o quitadas).", W - 2 * M, tam=9, color="#6B7280")
    c.showPage()

    # Una hoja por página cambiada
    for cp in res.cambios:
        y = H - M
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(HexColor("#111827"))
        c.drawString(M, y, f"Página {cp.numero} — {_describir(cp)}")
        y -= 18
        if cp.añadidas:
            muestra = " ".join(cp.añadidas[:MAX_PALABRAS_LISTA])
            if len(cp.añadidas) > MAX_PALABRAS_LISTA:
                muestra += " …"
            y = texto_ajustado(M, y, "Añadido: " + muestra, W - 2 * M, tam=8, color="#15803D")
        if cp.quitadas:
            muestra = " ".join(cp.quitadas[:MAX_PALABRAS_LISTA])
            if len(cp.quitadas) > MAX_PALABRAS_LISTA:
                muestra += " …"
            y = texto_ajustado(M, y, "Quitado: " + muestra, W - 2 * M, tam=8, color="#B91C1C")
        img = imagenes.get(cp.numero)
        if img is not None:
            y -= 6
            alto_disp = y - M
            ancho_disp = W - 2 * M
            escala = min(ancho_disp / img.width, alto_disp / img.height)
            w, h = img.width * escala, img.height * escala
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80)
            buf.seek(0)
            c.drawImage(ImageReader(buf), M + (ancho_disp - w) / 2, y - h, w, h)
            c.setStrokeColor(HexColor("#D1D5DB"))
            c.rect(M + (ancho_disp - w) / 2, y - h, w, h)
        c.showPage()
    c.save()


# ─────────────────────────────────────────────────────────────
#  PRINCIPAL
# ─────────────────────────────────────────────────────────────
def _abrir(ruta: str) -> PdfReader:
    if not ruta or not os.path.isfile(ruta):
        raise ErrorComparacion(f"No existe el archivo: {ruta or '(vacío)'}")
    try:
        r = PdfReader(ruta, strict=False)
    except Exception as e:
        raise ErrorComparacion(f"No se pudo abrir {os.path.basename(ruta)}: {e}")
    if r.is_encrypted and not r.decrypt(""):
        raise ErrorComparacion(f"{os.path.basename(ruta)} está protegido con contraseña.")
    return r


def comparar_pdfs(
    archivo_a: str,
    archivo_b: str,
    destino: str = "",
    visual: bool = True,
    callback_progreso: Optional[Callable[[int, int, str], None]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    cancelar: Optional[threading.Event] = None,
) -> ResumenComparacion:
    log = callback_log or (lambda m: None)
    progreso = callback_progreso or (lambda a, t, f: None)

    if archivo_a and archivo_b and os.path.realpath(archivo_a) == os.path.realpath(archivo_b):
        raise ErrorComparacion("Elegiste el mismo archivo como A y como B.")
    ra, rb = _abrir(archivo_a), _abrir(archivo_b)
    visual = visual and HAY_PDFIUM
    if not HAY_PDFIUM:
        log("[AVISO] Sin pypdfium2: solo se compara el texto.")

    destino = (destino or "").strip() or os.path.dirname(os.path.abspath(archivo_b))
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError as e:
        raise ErrorComparacion(f"No se pudo crear la carpeta de salida: {e}")

    res = ResumenComparacion(archivo_a=archivo_a, archivo_b=archivo_b,
                             paginas_a=len(ra.pages), paginas_b=len(rb.pages))
    total = max(res.paginas_a, res.paginas_b)
    log(f"Comparando {res.paginas_a} vs {res.paginas_b} páginas"
        + (" (texto + visual)" if visual else " (solo texto)"))

    doc_a = pdfium.PdfDocument(archivo_a) if visual else None
    doc_b = pdfium.PdfDocument(archivo_b) if visual else None
    imagenes = {}
    try:
        for i in range(total):
            if cancelar is not None and cancelar.is_set():
                res.cancelado = True
                break
            progreso(i, total, f"Página {i + 1}")
            n = i + 1
            if i >= res.paginas_a:
                res.cambios.append(CambioPagina(n, "añadida"))
                if visual:
                    imagenes[n] = _render(doc_b, i, DPI_COMPARACION).convert("RGB")
                log(f"[+] Página {n}: nueva en B")
                continue
            if i >= res.paginas_b:
                res.cambios.append(CambioPagina(n, "eliminada"))
                log(f"[−] Página {n}: ya no está en B")
                continue

            ta = ra.pages[i].extract_text() or ""
            tb = rb.pages[i].extract_text() or ""
            añadidas, quitadas = diferencias_texto(ta, tb)
            cp = CambioPagina(n, "cambiada", añadidas, quitadas,
                              sin_texto=not ta.strip() and not tb.strip())
            if visual:
                img_a = _render(doc_a, i, DPI_COMPARACION)
                img_b = _render(doc_b, i, DPI_COMPARACION)
                celdas, pct = mascara_diferencias(img_a, img_b)
                cp.zonas, cp.porcentaje_visual = len(celdas), pct
                if celdas:
                    imagenes[n] = _marcar(img_b, celdas)
            if cp.añadidas or cp.quitadas or cp.zonas:
                res.cambios.append(cp)
                log(f"[≠] Página {n}: {_describir(cp)}")
    finally:
        for d in (doc_a, doc_b):
            if d is not None:
                d.close()

    progreso(total, total, "Generando informe")
    if not res.cancelado:
        base_a = os.path.splitext(os.path.basename(archivo_a))[0]
        base_b = os.path.splitext(os.path.basename(archivo_b))[0]
        salida = os.path.join(destino, f"Comparacion_{base_a}_vs_{base_b}.pdf")
        k = 2
        while os.path.exists(salida) or os.path.realpath(salida) in (
                os.path.realpath(archivo_a), os.path.realpath(archivo_b)):
            salida = os.path.join(destino, f"Comparacion_{base_a}_vs_{base_b} ({k}).pdf")
            k += 1
        tmp = salida + ".tmp"
        try:
            _escribir_informe(tmp, res, imagenes)
            os.replace(tmp, salida)
            res.ruta_salida = salida
            log(f"Informe: {salida}")
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return res
