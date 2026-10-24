"""
pdf_ocr.py — Motor OCR de CCpdf (Tesseract + capa de texto).

    aplicar_ocr(archivos, destino, idioma="spa", ...) -> ResumenOCR

Toma PDFs escaneados (imágenes sin capa de texto) y produce PDFs
con capa de texto invisible encima. El resultado es buscable y
seleccionable, como un PDF nativo.

El OCR se decide POR PÁGINA: en PDFs híbridos solo se procesan las
páginas que lo necesitan; las demás pasan intactas al PDF final.

Pipeline:
    PDF → imagen de UNA página (PDFium) → OCR con coordenadas (Tesseract)
        → capa de texto invisible (reportlab) → PDF final (pypdf)

Requiere:
  - Tesseract (motor OCR)
  - pypdfium2 (renderizar PDF a imagen; PDFium, BSD-3 / Apache-2.0)
  - Datos de idioma: tesseract-ocr-spa, tesseract-ocr-eng
"""
import difflib
import io
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from PIL import Image, ImageDraw, ImageFilter, ImageOps

try:
    import pytesseract
    from pytesseract import Output, TesseractNotFoundError, TesseractError
    HAY_TESSERACT = True
except ImportError:
    pytesseract = None
    Output = None
    TesseractNotFoundError = Exception
    TesseractError = Exception
    HAY_TESSERACT = False

try:
    import pypdfium2 as pdfium
    HAY_PDFIUM = True
except ImportError:
    pdfium = None
    HAY_PDFIUM = False

from Motores import LOCK_PDFIUM


__all__ = [
    "ErrorOCR", "ResumenOCR",
    "aplicar_ocr", "info_motor_ocr",
    "pdf_es_escaneado", "paginas_sin_texto",
    "IDIOMAS_DISPONIBLES",
]


class ErrorOCR(Exception):
    """Error de validación o de instalación (Tesseract, pypdfium2...)."""


class _Cancelado(Exception):
    pass


IDIOMAS_DISPONIBLES = {
    "spa": "Español",
    "eng": "Inglés",
    "spa+eng": "Español + Inglés",
}

DPI_DEFECTO = 300

# Una página con menos caracteres extraíbles que esto se considera "sin texto".
MIN_CARACTERES_POR_PAGINA = 20

# Una página que ADEMÁS contiene una imagen y tiene menos caracteres que
# esto también se considera escaneada (típico: escaneo con un pie de página,
# sello o marca de agua que sí trae texto real).
MAX_TEXTO_CON_IMAGEN = 80

# Confianza mínima del OCR para incluir una palabra en la capa de texto.
# 15 = descarta basura (manchas, ruido). Bajo a propósito para no perder datos.
CONFIANZA_MINIMA = 15

# Orientaciones mezcladas (BUG-001, punto 3): tras leer la orientación principal,
# la tinta que queda sin leer se agrupa en regiones y cada una se lee girada a
# las 4 orientaciones (psm 6), quedándose con la que lee más texto seguro.
TINTA_RESTANTE_MIN = 0.0015       # fracción de píxeles oscuros sin cubrir para intentarlo
TINTA_REGION_MIN = 800            # píxeles oscuros mínimos en una región
LADO_REGION_MIN = 60              # px
MAX_REGIONES = 6
FACTOR_REGIONES = 8               # las regiones se buscan en una imagen 8 veces menor
DILATACION_REGIONES = 11          # celdas: junta líneas y palabras de un mismo bloque
CONFIANZA_ORIENTACION_EXTRA = 75
CARACTERES_MIN_REGION = 8
CONFIANZA_YA_LEIDA = 60  # por debajo, una palabra no "tapa" lo que hay debajo: puede ser basura
MARGEN_MASCARA_PX = 6
# Un bloque cuyas cajas son altas y estrechas (o anchas, si la página está de
# lado) no encaja con la orientación asignada: se comprueba girando su recorte.
RELACION_VERTICAL = 1.5
CONFIANZA_ORIENTAR_BLOQUE = 70

# Capa de texto: 3 = invisible. (Constante para poder cambiarla en pruebas.)
MODO_RENDER_TEXTO = 3
FUENTE_TEXTO = "Helvetica"
ESCALA_H_MIN = 20.0     # % mínimo de escala horizontal al ajustar al ancho
ESCALA_H_MAX = 400.0    # % máximo

# CIPA: una corrección que se parezca menos que esto al original se descarta
# (protege contra "alucinaciones" del modelo).
CIPA_SIMILITUD_MINIMA = 0.6
# CIPA: líneas que se corrigen en una sola llamada al modelo (BUG-002).
# Las instrucciones del prompt (~240 tokens) se envían una vez por bloque.
CIPA_LINEAS_POR_LLAMADA = 20

# Preprocesado de imagen antes del OCR.
# El autocontraste normaliza la iluminación; el median reduce ruido.
PREPROCESAR_IMAGEN = True
MEDIAN_FILTER_SIZE = 3   # 0 = desactivado; impar: 3, 5...
AUTOCONTRAST_CUTOFF = 2  # % de píxeles extremos a ignorar

# Modo PSM de Tesseract. 3 = automático (mixto). Alternativas útiles:
#   3  → Auto (mixto) — default
#   6  → Bloque único de texto (mejor para documentos uniformes)
#   11 → Texto disperso (busca en cualquier parte — bueno para tablas)
#   12 → Texto disperso + OSD
PSM_DEFECTO = 3

@dataclass
class ResumenOCR:
    total: int = 0
    procesados: int = 0
    omitidos_ya_con_texto: list = field(default_factory=list)
    paginas_procesadas: int = 0
    palabras_insertadas: int = 0
    palabras_corregidas_cipa: int = 0
    errores: list = field(default_factory=list)
    cancelado: bool = False
    carpeta_salida: str = ""
    idioma: str = ""
    motor: str = ""

    def a_texto(self) -> str:
        l = []
        if self.cancelado:
            l.append("⚠ Proceso cancelado por el usuario.")
        l.append(f"PDFs procesados: {self.procesados} de {self.total}")
        l.append(f"Páginas con OCR: {self.paginas_procesadas}")
        l.append(f"Palabras insertadas en la capa de texto: {self.palabras_insertadas}")
        if self.palabras_corregidas_cipa:
            l.append(f"Palabras corregidas por CIPA: {self.palabras_corregidas_cipa}")
        l.append(f"Motor: {self.motor}  ·  Idioma: {self.idioma}")
        if self.omitidos_ya_con_texto:
            l.append(f"Omitidos (ya tenían texto) ({len(self.omitidos_ya_con_texto)}): "
                     + ", ".join(self.omitidos_ya_con_texto[:10]))
        for archivo, msg in self.errores:
            l.append(f"ERROR {archivo}: {msg}")
        if self.carpeta_salida:
            l.append(f"Salida: {self.carpeta_salida}")
        return "\n".join(l)


# ═══════════════════════════════════════════════════════════════
#  COMPROBACIONES
# ═══════════════════════════════════════════════════════════════
def info_motor_ocr() -> str:
    if not HAY_TESSERACT:
        return "Motor OCR: no instalado (falta pytesseract)"
    if not HAY_PDFIUM:
        return "Motor OCR: parcial (falta pypdfium2)"
    try:
        version = pytesseract.get_tesseract_version()
        langs = pytesseract.get_languages(config="")
        return f"Motor OCR: Tesseract {version}  ·  Idiomas: {', '.join(langs[:5])}"
    except TesseractNotFoundError:
        return "Motor OCR: Tesseract no está en PATH"
    except Exception as e:
        return f"Motor OCR: error ({e})"


def _comprobar_dependencias() -> None:
    if not HAY_TESSERACT:
        raise ErrorOCR("Falta pytesseract. Instálalo con: pip install pytesseract")
    if not HAY_PDFIUM:
        raise ErrorOCR("Falta pypdfium2. Instálalo con: pip install pypdfium2")
    try:
        pytesseract.get_tesseract_version()
    except TesseractNotFoundError:
        raise ErrorOCR(
            "Tesseract no está instalado o no está en PATH.\n"
            "En Ubuntu:\n"
            "  sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng"
        )


def _comprobar_idioma(idioma: str) -> None:
    """Falla con un mensaje claro si Tesseract no tiene los datos del idioma. Sin esto, una
    página sin el idioma instalado daba "[OK] 0 palabras" y un PDF sin capa de texto."""
    try:
        instalados = set(pytesseract.get_languages(config=""))
    except Exception:
        return          # no se pudo listar: Tesseract dará su propio error al leer
    if not instalados:
        return
    faltan = [c for c in idioma.split("+") if c and c not in instalados]
    if not faltan:
        return
    nombres = ", ".join(f"{c} ({IDIOMAS_DISPONIBLES.get(c, c)})" for c in faltan)
    raise ErrorOCR(
        f"Tesseract no tiene instalado el idioma: {nombres}.\n"
        f"Idiomas instalados: {', '.join(sorted(instalados))}.\n"
        "En Ubuntu/Debian:  sudo apt install "
        + " ".join(f"tesseract-ocr-{c}" for c in faltan) + "\n"
        "En Windows: vuelve a ejecutar el instalador de Tesseract y marca el idioma, o copia "
        "su archivo .traineddata a la carpeta «tessdata».")


def _es_error_de_idioma(mensaje: str) -> bool:
    m = (mensaje or "").lower()
    return any(t in m for t in ("failed loading language", "error opening data file",
                                "couldn't load any languages", "could not initialize tesseract"))


def _abrir_pdf(ruta: str) -> PdfReader:
    """Abre el PDF y lo descifra (contraseña vacía). Lanza ErrorOCR si no se puede."""
    reader = PdfReader(ruta, strict=False)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ErrorOCR("el PDF está protegido con contraseña")
    return reader


def pdf_es_escaneado(ruta: str, max_paginas: int = 5) -> bool:
    """Decide por DOCUMENTO si parece escaneado (mira las primeras páginas)."""
    try:
        reader = PdfReader(ruta, strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            return True
        limite = min(len(reader.pages), max_paginas)
        if limite == 0:
            return True
        for i in range(limite):
            try:
                texto = reader.pages[i].extract_text() or ""
            except Exception:
                texto = ""
            if len(texto.strip()) >= MIN_CARACTERES_POR_PAGINA:
                return False
        return True
    except Exception:
        return True


def _recursos_tienen_imagen(recursos, profundidad: int = 0) -> bool:
    if recursos is None or profundidad > 4:
        return False
    xobjetos = recursos.get_object().get("/XObject")
    if xobjetos is None:
        return False
    xobjetos = xobjetos.get_object()
    for nombre in xobjetos:
        obj = xobjetos[nombre].get_object()
        subtipo = obj.get("/Subtype")
        if subtipo == "/Image":
            return True
        if subtipo == "/Form" and _recursos_tienen_imagen(
                obj.get("/Resources"), profundidad + 1):
            return True
    return False


def _pagina_tiene_imagen(page) -> bool:
    """¿La página declara alguna imagen en sus recursos, también dentro de
    Form XObjects? (heurística barata)."""
    try:
        return _recursos_tienen_imagen(page.get("/Resources"))
    except Exception:
        return False


def paginas_sin_texto(
    ruta: str,
    min_caracteres: int = MIN_CARACTERES_POR_PAGINA,
    reader: Optional[PdfReader] = None,
) -> list:
    """Devuelve los índices (0-based) de las páginas que necesitan OCR.

    A diferencia de pdf_es_escaneado() —que decide por documento—
    esta función decide página a página (útil en PDFs híbridos).

    Una página necesita OCR si:
      - tiene menos de `min_caracteres` caracteres extraíbles, o
      - contiene una imagen y menos de MAX_TEXTO_CON_IMAGEN caracteres
        (escaneo con un pie de página o sello que sí trae texto real).

    Si pasas `reader` (ya abierto y descifrado) se reutiliza en vez de
    abrir el archivo otra vez. Los errores de lectura NO se ocultan:
    la excepción sube para que el llamador la reporte.
    """
    if reader is None:
        reader = _abrir_pdf(ruta)

    limite_con_imagen = max(MAX_TEXTO_CON_IMAGEN, min_caracteres)
    indices = []
    for i, page in enumerate(reader.pages):
        try:
            texto = page.extract_text() or ""
        except Exception:
            texto = ""
        n = len(texto.strip())
        if n < min_caracteres or (n < limite_con_imagen and _pagina_tiene_imagen(page)):
            indices.append(i)
    return indices


def _ruta_unica(ruta: str, usadas: set) -> str:
    base, ext = os.path.splitext(ruta)
    candidata, n = ruta, 2
    while os.path.normcase(candidata) in usadas:
        candidata = f"{base} ({n}){ext}"
        n += 1
    usadas.add(os.path.normcase(candidata))
    return candidata

def _preprocesar_imagen(img):
    """Aplica mejoras a la imagen antes del OCR.

    - Escala de grises: Tesseract espera L o RGB. L es más rápido.
    - Autocontraste: normaliza scans con iluminación desigual.
    - Median filter: elimina ruido de sal (típico en escaneos viejos).
    """
    if not PREPROCESAR_IMAGEN:
        return img
    try:
        if img.mode != "L":
            img = img.convert("L")
        img = ImageOps.autocontrast(img, cutoff=AUTOCONTRAST_CUTOFF)
        if MEDIAN_FILTER_SIZE >= 3:
            size = MEDIAN_FILTER_SIZE if MEDIAN_FILTER_SIZE % 2 == 1 else MEDIAN_FILTER_SIZE + 1
            img = img.filter(ImageFilter.MedianFilter(size=size))
    except Exception:
        return img
    return img


# ═══════════════════════════════════════════════════════════════
#  OCR POR PÁGINA CON COORDENADAS
# ═══════════════════════════════════════════════════════════════
def _extraer_palabras_con_coords(imagen, idioma: str, psm: int = PSM_DEFECTO,
                                 confianza_min: float = CONFIANZA_MINIMA) -> list:
    """Devuelve una lista de dicts con texto y coordenadas en píxeles:
        [{"texto": str, "x": int, "y": int, "w": int, "h": int,
          "linea": (bloque, párrafo, línea), "conf": float}, ...]

    Preprocesa la imagen antes del OCR (escala de grises + autocontraste
    + reducción de ruido) y permite elegir el modo PSM de Tesseract.
    """
    img_proc = _preprocesar_imagen(imagen)
    config = f"--psm {psm}"
    try:
        data = pytesseract.image_to_data(
            img_proc, lang=idioma, config=config, output_type=Output.DICT
        )
    except TesseractError as e:
        if _es_error_de_idioma(str(e)):
            raise ErrorOCR(f"Tesseract no pudo cargar el idioma «{idioma}»: {e}")
        return []

    palabras = []
    n = len(data.get("text", []))
    bloques = data.get("block_num", [0] * n)
    parrafos = data.get("par_num", [0] * n)
    lineas = data.get("line_num", [0] * n)

    for i in range(n):
        texto = (data["text"][i] or "").strip()
        if not texto:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if conf < confianza_min:
            continue
        palabras.append({
            "texto": texto,
            "x": int(data["left"][i]),
            "y": int(data["top"][i]),
            "w": int(data["width"][i]),
            "h": int(data["height"][i]),
            "linea": (bloques[i], parrafos[i], lineas[i]),
            "conf": conf,
        })
    return palabras

def _desrotar_palabras(palabras: list, rot: int,
                       ancho_orig: int, alto_orig: int) -> list:
    """Convierte coordenadas del espacio de la imagen ROTADA al original.

    Usa coordenadas CONTINUAS (no índices de píxel). Tesseract devuelve
    left/top/width/height en un sistema continuo donde la caja abarca
    [left, left+width] × [top, top+height].

    Convención PIL: rotate(angle) = CCW, expand=True → la imagen crece.
      - rot=0   → imagen W×H
      - rot=90  → imagen H×W  (rotación 90° CCW)
      - rot=180 → imagen W×H
      - rot=270 → imagen H×W  (rotación 270° CCW = 90° CW)
    """
    if rot == 0:
        return palabras

    resultado = []
    for p in palabras:
        x_r, y_r, w_r, h_r = p["x"], p["y"], p["w"], p["h"]

        if rot == 90:
            # rot=90 CCW: inverse mapping.
            # forward: (x_o, y_o) → (y_o, W - x_o)
            x_o = ancho_orig - y_r - h_r
            y_o = x_r
            w_o = h_r
            h_o = w_r
        elif rot == 180:
            x_o = ancho_orig - x_r - w_r
            y_o = alto_orig - y_r - h_r
            w_o = w_r
            h_o = h_r
        elif rot == 270:
            # rot=270 CCW = 90° CW
            # forward: (x_o, y_o) → (H - y_o, x_o)
            # inverse: x_o = y_r, y_o = H - x_r - w_r
            x_o = y_r
            y_o = alto_orig - x_r - w_r
            w_o = h_r
            h_o = w_r
        else:
            x_o, y_o, w_o, h_o = x_r, y_r, w_r, h_r

        resultado.append({**p, "x": x_o, "y": y_o, "w": w_o, "h": h_o})
    return resultado


def _tapar_palabras(gris, palabras) -> None:
    """Pinta de blanco las cajas de `palabras` (en el espacio de `gris`)."""
    lapiz = ImageDraw.Draw(gris)
    m = MARGEN_MASCARA_PX
    for p in palabras:
        lapiz.rectangle([p["x"] - m, p["y"] - m, p["x"] + p["w"] + m, p["y"] + p["h"] + m],
                        fill=255)


def _tapada_por(p, otras: list) -> bool:
    """¿El centro de la caja de `p` cae dentro de alguna de `otras`?"""
    cx, cy = p["x"] + p["w"] / 2, p["y"] + p["h"] / 2
    return any(q["x"] <= cx <= q["x"] + q["w"] and q["y"] <= cy <= q["y"] + q["h"] for q in otras)


def _forma_coherente(p) -> bool:
    """¿La caja de `p` cuadra con la orientación que lleva? Una palabra de 3 o más
    letras en una caja alta y estrecha, con texto que va en horizontal (o al
    revés), está mal leída aunque Tesseract le dé confianza alta: «unidad» leída
    de lado sale «pepiun» con 89 %."""
    if len(p["texto"]) < 3:
        return True
    if p.get("rot_texto", 0) in (90, 270):
        return not p["w"] > RELACION_VERTICAL * p["h"]
    return not p["h"] > RELACION_VERTICAL * p["w"]


def _palabra_creible(p) -> bool:
    t = p["texto"]
    return len(t) >= 2 and sum(ch.isalnum() for ch in t) * 2 >= len(t)


def _regiones_con_tinta(gris) -> list:
    """Zonas con tinta de `gris` como cajas (x0, y0, x1, y1) en sus píxeles.

    Se trabaja sobre una versión reducida: se quita el ruido, se marca toda celda
    con tinta, se dilata para juntar las líneas de un mismo bloque y se agrupan
    las celdas conectadas.
    """
    ancho, alto = gris.size
    negro = gris.filter(ImageFilter.MedianFilter(3)).point(lambda v: 255 if v < 128 else 0)
    celdas = negro.reduce(FACTOR_REGIONES).point(lambda v: 255 if v > 0 else 0)
    celdas = celdas.filter(ImageFilter.MaxFilter(DILATACION_REGIONES))
    cw, ch = celdas.size
    px = celdas.load()
    visto = bytearray(cw * ch)
    regiones = []
    for sy in range(ch):
        for sx in range(cw):
            if not px[sx, sy] or visto[sy * cw + sx]:
                continue
            visto[sy * cw + sx] = 1
            pila = [(sx, sy)]
            x0 = x1 = sx
            y0 = y1 = sy
            while pila:
                x, y = pila.pop()
                x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < cw and 0 <= ny < ch and px[nx, ny] and not visto[ny * cw + nx]:
                        visto[ny * cw + nx] = 1
                        pila.append((nx, ny))
            f = FACTOR_REGIONES
            caja = (x0 * f, y0 * f, min(ancho, (x1 + 1) * f), min(alto, (y1 + 1) * f))
            tinta = negro.crop(caja).histogram()[255]
            if (tinta >= TINTA_REGION_MIN and caja[2] - caja[0] >= LADO_REGION_MIN
                    and caja[3] - caja[1] >= LADO_REGION_MIN):
                regiones.append((tinta, caja))
    regiones.sort(reverse=True)
    return [caja for _, caja in regiones[:MAX_REGIONES]]


def _palabras_otras_orientaciones(imagen, palabras: list, idioma: str) -> list:
    """BUG-001, punto 3: una página puede mezclar orientaciones (encabezado
    derecho y una tabla girada) y la pasada principal las lee mal o no las lee.
    Se tapa lo ya leído con seguridad y cada región con tinta que queda se lee
    girada a las 4 orientaciones. Cada palabra nueva lleva su "rot_texto" y sus
    cajas quedan en el espacio de `imagen`.
    """
    gris = imagen.convert("L")
    # Un bloque girado sale como basura, a veces con confianza alta; si esas
    # cajas taparan la tinta, la lectura buena nunca llegaría a intentarse.
    _tapar_palabras(gris, [p for p in palabras
                           if p.get("conf", 100) >= CONFIANZA_YA_LEIDA and _forma_coherente(p)])
    ancho, alto = imagen.size
    negro = gris.point(lambda v: 255 if v < 128 else 0)
    if negro.histogram()[255] / float(ancho * alto) < TINTA_RESTANTE_MIN:
        return []
    nuevas: list = []
    for n, caja in enumerate(_regiones_con_tinta(gris)):
        recorte = gris.crop(caja)
        mejor = (0, None, [])
        for rot in (0, 90, 180, 270):
            leidas = _extraer_palabras_con_coords(
                recorte.rotate(rot, expand=True) if rot else recorte, idioma, psm=6,
                confianza_min=CONFIANZA_ORIENTACION_EXTRA)
            leidas = [p for p in leidas if _palabra_creible(p)]
            puntos = sum(len(p["texto"]) for p in leidas)
            if puntos > mejor[0]:
                mejor = (puntos, rot, leidas)
        puntos, rot, leidas = mejor
        if puntos < CARACTERES_MIN_REGION:
            continue
        for p in _desrotar_palabras(leidas, rot, recorte.size[0], recorte.size[1]):
            p["x"] += caja[0]
            p["y"] += caja[1]
            p["rot_texto"] = (360 - rot) % 360
            # otro grupo de líneas: la corrección con CIPA no debe mezclarlas
            p["linea"] = (f"g{n}",) + tuple(p["linea"])
            nuevas.append(p)
    return nuevas


def _orientar_bloques(imagen, palabras: list, idioma: str) -> None:
    """Corrige "rot_texto" por bloque. Tesseract lee con acierto un bloque girado
    dentro de una página, pero no dice cómo está girado: sus palabras salen con
    cajas altas y estrechas y, sin esto, la capa de texto las dibujaría rectas.
    Si las cajas de un bloque no cuadran con la orientación que lleva (altas con
    0°/180°, anchas con 90°/270°), se lee su recorte girado a las dos posibles
    y se queda la que lee más texto con confianza.
    """
    bloques: dict = {}
    for p in palabras:
        bloques.setdefault(p["linea"][:-2] if len(p["linea"]) > 3 else p["linea"][:1], []).append(p)
    for ps in bloques.values():
        largas = [p for p in ps if len(p["texto"]) >= 3]
        if len(largas) < 2:
            continue  # una letra suelta no dice hacia dónde está girada
        altas = sum(1 for p in largas if p["h"] > RELACION_VERTICAL * p["w"])
        anchas = sum(1 for p in largas if p["w"] > RELACION_VERTICAL * p["h"])
        esperada_vertical = ps[0].get("rot_texto", 0) in (90, 270)
        if altas >= 0.7 * len(largas) and not esperada_vertical:
            candidatas = (270, 90)  # PIL antihorario: 270 endereza texto que sube
        elif anchas >= 0.7 * len(largas) and esperada_vertical:
            candidatas = (0, 180)
        else:
            continue
        m = 12
        recorte = imagen.crop((max(0, min(p["x"] for p in ps) - m), max(0, min(p["y"] for p in ps) - m),
                               max(p["x"] + p["w"] for p in ps) + m, max(p["y"] + p["h"] for p in ps) + m))
        puntos = {}
        for rot in candidatas:
            leidas = _extraer_palabras_con_coords(
                recorte.rotate(rot, expand=True) if rot else recorte, idioma, psm=6,
                confianza_min=CONFIANZA_ORIENTAR_BLOQUE)
            puntos[rot] = sum(len(q["texto"]) for q in leidas if _palabra_creible(q))
        mejor = max(candidatas, key=lambda c: puntos[c])
        if puntos[mejor] > 0 and puntos[mejor] > puntos[min(candidatas, key=lambda c: puntos[c])]:
            for p in ps:
                p["rot_texto"] = (360 - mejor) % 360


def _extraer_palabras_con_osd(imagen, idioma: str, psm: int = PSM_DEFECTO) -> list:
    """BUG-001: detecta la rotación con OSD (--psm 0), hace el OCR sobre la
    imagen enderezada y des-rota las coordenadas al espacio original, que
    es el que usa la capa de texto sobre la página del PDF. Si tras eso queda
    tinta sin leer (otra orientación en la misma página), la lee también.

    Cada palabra lleva "rot_texto": grados (antihorarios, 0/90/180/270) que
    lleva el texto en la página tal como se ve. Sus cajas "w" y "h" siguen
    siendo las de la página, así que con 90/270 el ancho del texto es "h".
    """
    try:
        osd = pytesseract.image_to_osd(imagen, config="--psm 0")
        horario = int(re.search(r"Rotate:\s*(\d+)", osd).group(1))
    except (TesseractError, AttributeError):
        horario = 0  # OSD falla en páginas casi vacías
    rot = (360 - horario) % 360  # OSD da grados horarios; PIL rota antihorario
    ancho, alto = imagen.size
    if rot == 0:
        palabras = _extraer_palabras_con_coords(imagen, idioma, psm=psm)
    else:
        palabras = _extraer_palabras_con_coords(
            imagen.rotate(rot, expand=True), idioma, psm=psm)
        palabras = _desrotar_palabras(palabras, rot, ancho, alto)
    for p in palabras:
        p["rot_texto"] = horario  # el texto ocupa la misma rotación que pide OSD
    extras = _palabras_otras_orientaciones(imagen, palabras, idioma)
    if extras:
        # lo que la pasada principal leyó mal debajo de una lectura buena se descarta
        palabras = [p for p in palabras if not _tapada_por(p, extras)] + extras
    _orientar_bloques(imagen, palabras, idioma)
    return palabras


def _extraer_palabras_con_auto_rotacion(imagen, idioma: str,
                                        psm: int = PSM_DEFECTO) -> tuple:
    """Prueba 4 rotaciones, elige la que da MÁS palabras y des-rota las
    coordenadas al espacio original.

    Devuelve (palabras_en_espacio_original, rotacion_elegida).
    Si el enfoque falla en las 4, devuelve la rotación 0°.
    """
    ancho, alto = imagen.size
    mejor_palabras: list = []
    mejor_rot = 0
    mejor_score = -1

    for rot in (0, 90, 180, 270):
        try:
            img_rot = imagen if rot == 0 else imagen.rotate(rot, expand=True)
            palabras_rot = _extraer_palabras_con_coords(img_rot, idioma, psm=psm)
        except Exception:
            continue

        score = len(palabras_rot)
        if score > mejor_score:
            mejor_score = score
            mejor_rot = rot
            mejor_palabras = _desrotar_palabras(palabras_rot, rot, ancho, alto)

    return mejor_palabras, mejor_rot

# ═══════════════════════════════════════════════════════════════
#  CIPA: CORRECCIÓN POR LÍNEA
# ═══════════════════════════════════════════════════════════════
def _aplicar_cipa_por_linea(palabras: list, cipa) -> int:
    """Corrige el texto de `palabras` (in situ) usando CIPA, línea por línea.

    Reglas de seguridad —un LLM puede inventar—:
      - Solo se acepta la corrección si tiene el MISMO número de palabras
        que la línea original (así cada palabra conserva su caja).
      - Las palabras que contienen dígitos NUNCA se tocan (folios, importes).
      - Si la corrección se parece poco al original, se descarta.
      - Cada línea de la respuesta se empareja por su número «[N]».

    Las líneas se envían en bloques de CIPA_LINEAS_POR_LLAMADA, numeradas
    ("[N] texto"), en una sola llamada al modelo; la respuesta se empareja
    por número. Una línea que falte en la respuesta se deja como estaba.

    Devuelve cuántas palabras se modificaron.
    """
    lineas: dict = {}
    for p in palabras:
        lineas.setdefault(p.get("linea"), []).append(p)

    grupos = [g for g in lineas.values()
              if any(ch.isalpha() for p in g for ch in p["texto"])]

    cambios = 0
    for inicio in range(0, len(grupos), CIPA_LINEAS_POR_LLAMADA):
        bloque = grupos[inicio:inicio + CIPA_LINEAS_POR_LLAMADA]
        texto_bloque = "\n".join(
            f"[{n}] {' '.join(p['texto'] for p in g)}"
            for n, g in enumerate(bloque, start=1))

        try:
            limpio = cipa.limpiar_texto(texto_bloque, contexto="documento escaneado",
                                        nombre_prompt="limpieza_ocr_lineas")
        except Exception:
            continue

        respuesta: dict = {}
        for linea in (limpio or "").splitlines():
            m = re.match(r"\s*\[(\d+)\]\s?(.*)$", linea)
            if m:
                respuesta.setdefault(int(m.group(1)), m.group(2))

        for n, grupo in enumerate(bloque, start=1):
            if n not in respuesta:
                continue
            originales = [p["texto"] for p in grupo]
            texto = " ".join(originales)
            nuevos = respuesta[n].split()
            if len(nuevos) != len(originales):
                continue
            if difflib.SequenceMatcher(None, texto, " ".join(nuevos)).ratio() < CIPA_SIMILITUD_MINIMA:
                continue

            for p, orig, nuevo in zip(grupo, originales, nuevos):
                if any(ch.isdigit() for ch in orig):
                    continue
                if nuevo != orig:
                    p["texto"] = nuevo
                    cambios += 1
    return cambios


# ═══════════════════════════════════════════════════════════════
#  GEOMETRÍA: CROPBOX Y ROTACIÓN
# ═══════════════════════════════════════════════════════════════
def _geometria_pagina(page) -> tuple:
    """(izq, abajo, ancho, alto, rotación) de la CropBox, sin rotar.

    La rotación se normaliza a 0, 90, 180 o 270 (sentido horario,
    tal como se muestra la página).
    """
    box = page.cropbox
    izq, abajo = float(box.left), float(box.bottom)
    ancho, alto = float(box.width), float(box.height)
    try:
        rot = int(page.rotation or 0)
    except Exception:
        rot = 0
    rot = (round(rot / 90) * 90) % 360
    return izq, abajo, ancho, alto, rot


def _visual_a_usuario(vx: float, vy: float, ancho: float, alto: float, rot: int) -> tuple:
    """Convierte un punto de la página TAL COMO SE VE (origen abajo-izquierda,
    ya rotada) al espacio de usuario SIN rotar (relativo a la CropBox).
    """
    if rot == 90:
        return ancho - vy, vx
    if rot == 180:
        return ancho - vx, alto - vy
    if rot == 270:
        return vy, alto - vx
    return vx, vy


def _limpiar_para_fuente(texto: str) -> str:
    """Helvetica estándar solo cubre cp1252; lo demás se cambia por '?'."""
    return texto.encode("cp1252", errors="replace").decode("cp1252")


def _renderizar_pagina(ruta: str, idx: int, dpi: int) -> Image.Image:
    """Página `idx` (0-based) como imagen RGB a `dpi`. PDFium dibuja la CropBox ya
    girada según /Rotate: la misma geometría que espera la capa de texto."""
    with LOCK_PDFIUM:
        doc = pdfium.PdfDocument(ruta)
        try:
            pag = doc[idx]
            try:
                return pag.render(scale=dpi / 72.0, may_draw_forms=True).to_pil().convert("RGB")
            finally:
                pag.close()
        finally:
            doc.close()


# ═══════════════════════════════════════════════════════════════
#  CAPA DE TEXTO INVISIBLE (reportlab)
# ═══════════════════════════════════════════════════════════════
def _crear_capa_texto(palabras: list, geometria: tuple, dpi: int) -> io.BytesIO:
    """Crea un PDF de una página con el texto invisible en su posición.

    - Las coordenadas de Tesseract están en píxeles de la imagen que
      PDFium renderizó (CropBox, ya rotada) a `dpi` DPI.
    - Las coordenadas PDF están en puntos (1 pt = 1/72 pulgada).
    - El eje Y de PDF va hacia ARRIBA; el de la imagen va hacia ABAJO.
    - Si la página tiene /Rotate, el texto se dibuja girado esa misma
      cantidad en el espacio sin rotar, para que al mostrarla quede recto.
    - Cada palabra se estira (escala horizontal) para ocupar el ancho de
      su caja, así la selección coincide con lo que se ve.
    """
    izq, abajo, ancho, alto, rot = geometria
    ancho_vis, alto_vis = (alto, ancho) if rot in (90, 270) else (ancho, alto)

    buffer = io.BytesIO()
    c = rl_canvas.Canvas(
        buffer, pagesize=(max(izq + ancho, 1.0), max(abajo + alto, 1.0)))

    escala = 72.0 / float(dpi)  # píxeles → puntos

    for p in palabras:
        texto = _limpiar_para_fuente(p["texto"])
        if not texto.strip():
            continue

        # Texto girado dentro de la página (escaneo de lado): el ancho del texto
        # es el alto de la caja en la página y su altura de letra, el ancho.
        giro = int(p.get("rot_texto", 0)) % 360
        de_lado = giro in (90, 270)
        w_pt = (p["h"] if de_lado else p["w"]) * escala
        h_pt = (p["w"] if de_lado else p["h"]) * escala

        # Caja en la página tal como se ve (origen abajo-izquierda)
        x0, x1 = p["x"] * escala, (p["x"] + p["w"]) * escala
        y0, y1 = alto_vis - (p["y"] + p["h"]) * escala, alto_vis - p["y"] * escala
        # Esquina donde empieza el texto (inicio de la línea base) según su giro
        vx, vy = {0: (x0, y0), 90: (x1, y0), 180: (x1, y1), 270: (x0, y1)}.get(giro, (x0, y0))
        ux, uy = _visual_a_usuario(vx, vy, ancho, alto, rot)

        font_size = max(1.0, h_pt * 0.95)

        c.saveState()
        try:
            c.translate(izq + ux, abajo + uy)
            c.rotate(rot + giro)
            t = c.beginText(0, 0)
            t.setTextRenderMode(MODO_RENDER_TEXTO)
            t.setFont(FUENTE_TEXTO, font_size)
            natural = stringWidth(texto, FUENTE_TEXTO, font_size)
            if natural > 0 and w_pt > 0:
                t.setHorizScale(
                    min(ESCALA_H_MAX, max(ESCALA_H_MIN, w_pt / natural * 100.0)))
            # pypdf no separa las palabras de texto a 180°/270° (las pega); un
            # espacio invisible tras cada una conserva los límites para buscar
            t.textOut(texto + (" " if giro in (180, 270) else ""))
            c.drawText(t)
        except Exception:
            pass  # una palabra rara no debe tumbar la página
        finally:
            c.restoreState()

    c.save()
    buffer.seek(0)
    return buffer


# ═══════════════════════════════════════════════════════════════
#  ESCRITURA DEL PDF FINAL
# ═══════════════════════════════════════════════════════════════
def _escribir_pdf_ocr(
    paginas_palabras: list,
    paginas_originales: list,
    ruta_salida: str,
    dpi: int,
) -> int:
    """Escribe el PDF resultado con la capa de texto superpuesta.

    `paginas_palabras[i]` puede ser:
      - list: palabras OCR → se añade capa de texto.
      - None: la página no necesitaba OCR → se deja intacta.

    Devuelve el número total de palabras insertadas.
    """
    writer = PdfWriter()
    total_palabras = 0

    for page, palabras in zip(paginas_originales, paginas_palabras):
        if palabras:
            geometria = _geometria_pagina(page)
            capa_buffer = _crear_capa_texto(palabras, geometria, dpi)
            capa_pagina = PdfReader(capa_buffer).pages[0]
            page.merge_page(capa_pagina)
            total_palabras += len(palabras)

        writer.add_page(page)

    # Escritura atómica
    tmp = ruta_salida + ".tmp"
    try:
        with open(tmp, "wb") as f:
            writer.write(f)

        # Verificación: reabrir y comprobar páginas
        try:
            r = PdfReader(tmp, strict=False)
            n = len(r.pages)
        except Exception as e:
            raise RuntimeError(f"el PDF generado no se pudo reabrir: {e}")
        if n != len(paginas_originales):
            raise RuntimeError(
                f"el PDF generado tiene {n} páginas, se esperaban {len(paginas_originales)}")

        os.replace(tmp, ruta_salida)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass

    return total_palabras


# ═══════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════
def aplicar_ocr(
    archivos: list,
    destino: str = "",
    idioma: str = "spa",
    dpi: int = DPI_DEFECTO,
    solo_si_escaneado: bool = True,
    usar_cipa: bool = False,
    sufijo: str = "_ocr",
    callback_progreso: Optional[Callable[[int, int, str], None]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    cancelar: Optional[threading.Event] = None,
    min_caracteres: int = MIN_CARACTERES_POR_PAGINA,
    psm: int = PSM_DEFECTO,
) -> ResumenOCR:
    """Aplica OCR (decidido por página) a los PDFs y genera PDFs buscables."""
    log = callback_log or (lambda m: None)

    archivos = [a for a in archivos if a]
    if not archivos:
        raise ErrorOCR("No hay archivos para procesar.")
    if idioma not in IDIOMAS_DISPONIBLES:
        raise ErrorOCR(f"Idioma no soportado: {idioma}")

    _comprobar_dependencias()
    _comprobar_idioma(idioma)

    destino = (destino or "").strip() or os.path.dirname(
        os.path.abspath(archivos[0]))
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError as e:
        raise ErrorOCR(f"No se pudo crear la carpeta de salida: {e}")

    res = ResumenOCR(
        total=len(archivos),
        carpeta_salida=destino,
        idioma=IDIOMAS_DISPONIBLES[idioma],
        motor=f"Tesseract {pytesseract.get_tesseract_version()}",
    )

    # CIPA opcional (para corregir el texto después del OCR)
    cipa = None
    if usar_cipa:
        try:
            from Motores.CIPA import CIPA
            cipa = CIPA()
            cipa.cargar_modelo("limpieza")  # sin cargar el modelo, nunca está disponible
        except Exception as e:
            log(f"[AVISO] CIPA no disponible ({e}); se usará solo OCR clásico.")
            cipa = None

    usadas = {os.path.normcase(os.path.abspath(a)) for a in archivos}   # nunca pisar un original

    try:
        for i, ruta in enumerate(archivos, start=1):
            if cancelar is not None and cancelar.is_set():
                res.cancelado = True
                break

            nombre = os.path.basename(ruta)
            try:
                if not os.path.isfile(ruta):
                    raise FileNotFoundError("el archivo ya no existe")

                # Abrir una sola vez (y descifrar) antes de contar páginas
                reader = _abrir_pdf(ruta)
                total_paginas = len(reader.pages)

                if solo_si_escaneado:
                    paginas_ocr = paginas_sin_texto(
                        ruta, min_caracteres=min_caracteres, reader=reader)
                    if not paginas_ocr:
                        res.omitidos_ya_con_texto.append(nombre)
                        log(f"[OMITIDO] {nombre}: todas las páginas ya tienen texto")
                        continue
                    log(f"[OCR] {nombre}: {len(paginas_ocr)} de {total_paginas} "
                        f"páginas necesitan OCR")
                else:
                    paginas_ocr = list(range(total_paginas))
                    log(f"[OCR] Procesando {nombre} completo "
                        f"({total_paginas} páginas)…")

                # None = página intacta (no necesitó OCR)
                paginas_palabras: list[Optional[list]] = [None] * total_paginas

                for idx in paginas_ocr:
                    if cancelar is not None and cancelar.is_set():
                        raise _Cancelado()

                    # Renderizar SOLO esta página (ahorra RAM).
                    img = _renderizar_pagina(ruta, idx, dpi)
                    palabras = _extraer_palabras_con_osd(img, idioma, psm=psm)
                    del img  # liberar la imagen cuanto antes

                    if cipa is not None and palabras:
                        cambios = _aplicar_cipa_por_linea(palabras, cipa)
                        if cambios:
                            res.palabras_corregidas_cipa += cambios
                            log(f"[CIPA] Página {idx + 1}: "
                                f"{cambios} palabras corregidas")

                    paginas_palabras[idx] = palabras
                    res.paginas_procesadas += 1
                    if callback_progreso:
                        hechas = len([x for x in paginas_palabras if x is not None])
                        try:
                            callback_progreso(
                                i - 1 + hechas / len(paginas_ocr) * 0.95, res.total,
                                f"{nombre} (página {hechas} de {len(paginas_ocr)})")
                        except Exception:
                            pass

                base, _ = os.path.splitext(nombre)
                ruta_salida = _ruta_unica(
                    os.path.join(destino, f"{base}{sufijo}.pdf"), usadas)

                palabras_insertadas = _escribir_pdf_ocr(
                    paginas_palabras, list(reader.pages), ruta_salida, dpi)

                res.palabras_insertadas += palabras_insertadas
                res.procesados += 1
                log(f"[OK] {nombre}: {len(paginas_ocr)} páginas con OCR, "
                    f"{palabras_insertadas} palabras insertadas")

            except _Cancelado:
                res.cancelado = True
                break
            except Exception as e:
                res.errores.append((nombre, str(e)))
                log(f"[ERROR] {nombre}: {e}")
            finally:
                if callback_progreso:
                    try:
                        callback_progreso(i, res.total, nombre)
                    except Exception:
                        pass
    finally:
        if cipa is not None:
            try:
                cipa.descargar_modelo()  # liberar RAM
            except Exception:
                pass

    return res