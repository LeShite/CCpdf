"""
pdf_metadatos.py — Ver y limpiar los metadatos de PDFs (privacidad).

Qué se elimina al limpiar:
  - Diccionario de información del documento (/Info): autor, título, asunto,
    palabras clave, programa creador, productor, fechas y claves propias.
  - Metadatos XMP del documento (/Metadata del catálogo).
  - Metadatos XMP y datos privados de aplicación (/PieceInfo) de cada página.
  - /PieceInfo del catálogo.
  - Los objetos que quedan huérfanos tras quitar lo anterior, para que los
    datos borrados no sigan dentro del archivo como bytes sueltos.

Qué NO toca: el contenido visible, las páginas, marcadores, formularios ni
anotaciones. El archivo original nunca se modifica: el resultado se escribe
aparte (escritura atómica con verificación de páginas).
"""
from __future__ import annotations

import inspect
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


class ErrorMetadatos(Exception):
    """Error de validación (sin archivos, carpeta de salida inválida...)."""


# Nombres legibles de las claves estándar de /Info.
CAMPOS_INFO = {
    "/Title": "Título",
    "/Author": "Autor",
    "/Subject": "Asunto",
    "/Keywords": "Palabras clave",
    "/Creator": "Programa creador",
    "/Producer": "Productor PDF",
    "/CreationDate": "Fecha de creación",
    "/ModDate": "Fecha de modificación",
    "/Trapped": "Trapped",
}


@dataclass
class InfoMetadatos:
    """Lo que un PDF revela sobre sí mismo."""
    ruta: str
    info: dict = field(default_factory=dict)      # {"Autor": "...", ...}
    tiene_xmp: bool = False
    paginas_con_xmp: int = 0
    paginas_con_pieceinfo: int = 0
    catalogo_pieceinfo: bool = False
    cifrado: bool = False

    @property
    def vacio(self) -> bool:
        return not (self.info or self.tiene_xmp or self.paginas_con_xmp
                    or self.paginas_con_pieceinfo or self.catalogo_pieceinfo)

    def a_texto(self) -> str:
        l = [os.path.basename(self.ruta)]
        if self.cifrado:
            l.append("  🔒 Protegido con contraseña: no se puede leer ni limpiar.")
            return "\n".join(l)
        if self.vacio:
            l.append("  ✔ Sin metadatos.")
            return "\n".join(l)
        for k, v in self.info.items():
            l.append(f"  • {k}: {v}")
        if self.tiene_xmp:
            l.append("  • Metadatos XMP del documento")
        if self.paginas_con_xmp:
            l.append(f"  • XMP en {self.paginas_con_xmp} página(s)")
        if self.paginas_con_pieceinfo or self.catalogo_pieceinfo:
            l.append("  • Datos privados de aplicación (PieceInfo)")
        return "\n".join(l)


@dataclass
class ResumenMetadatos:
    total: int = 0
    limpiados: int = 0
    resultados: list = field(default_factory=list)   # (nombre, campos_quitados)
    sin_metadatos: list = field(default_factory=list)
    omitidos: list = field(default_factory=list)
    errores: list = field(default_factory=list)      # (nombre, mensaje)
    cancelado: bool = False
    carpeta_salida: str = ""

    def a_texto(self) -> str:
        l = []
        if self.cancelado:
            l.append("⚠ Proceso cancelado por el usuario.")
        l.append(f"Archivos: {self.total}  ·  Limpiados: {self.limpiados}")
        if self.sin_metadatos:
            l.append(f"Ya estaban limpios (copiados igual): {len(self.sin_metadatos)}")
        if self.omitidos:
            l.append(f"Omitidos: {len(self.omitidos)}")
        if self.errores:
            l.append(f"Con error: {len(self.errores)}")
            for nombre, msg in self.errores[:5]:
                l.append(f"  ✖ {nombre}: {msg}")
        if self.carpeta_salida:
            l.append(f"Carpeta de salida: {self.carpeta_salida}")
        return "\n".join(l)


# ─────────────────────────────────────────────────────────────
#  LECTURA
# ─────────────────────────────────────────────────────────────
_RE_FECHA_PDF = re.compile(
    r"^D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz]|[+-]\d{2}'?\d{2}'?)?")


def formatear_fecha_pdf(valor: str) -> str:
    """'D:20261028031946-06'00'' → '28/10/2026 03:19:46 (UTC-06:00)'. Si no encaja, igual."""
    m = _RE_FECHA_PDF.match(valor or "")
    if not m:
        return valor
    a, mes, d, h, mi, s, tz = m.groups()
    txt = f"{d or '01'}/{mes or '01'}/{a}"
    if h:
        txt += f" {h}:{mi or '00'}:{s or '00'}"
    if tz:
        if tz.upper() == "Z":
            txt += " (UTC)"
        else:
            dig = re.sub(r"\D", "", tz)
            txt += f" (UTC{tz[0]}{dig[:2]}:{dig[2:4] or '00'})"
    return txt


def _texto(valor, clave: str = "") -> str:
    try:
        s = str(valor)
    except Exception:
        return "?"
    s = s.strip()
    if clave in ("/CreationDate", "/ModDate"):
        s = formatear_fecha_pdf(s)
    return s if len(s) <= 200 else s[:197] + "…"


def leer_metadatos(ruta: str) -> InfoMetadatos:
    """Devuelve los metadatos de un PDF sin modificarlo."""
    res = InfoMetadatos(ruta=ruta)
    reader = PdfReader(ruta, strict=False)
    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                res.cifrado = True
                return res
        except Exception:
            res.cifrado = True
            return res

    for clave, valor in (reader.metadata or {}).items():
        if valor in (None, ""):
            continue
        res.info[CAMPOS_INFO.get(clave, clave.lstrip("/"))] = _texto(valor, clave)

    raiz = reader.trailer["/Root"]
    res.tiene_xmp = "/Metadata" in raiz
    res.catalogo_pieceinfo = "/PieceInfo" in raiz
    for page in reader.pages:
        if "/Metadata" in page:
            res.paginas_con_xmp += 1
        if "/PieceInfo" in page:
            res.paginas_con_pieceinfo += 1
    return res


# ─────────────────────────────────────────────────────────────
#  LIMPIEZA
# ─────────────────────────────────────────────────────────────
def _quitar_huerfanos(writer: PdfWriter) -> None:
    """Elimina objetos ya no referenciados (los metadatos recién quitados).

    pypdf 7 renombró el parámetro (remove_orphans → remove_unreferenced).
    """
    try:
        params = inspect.signature(writer.compress_identical_objects).parameters
    except (TypeError, ValueError, AttributeError):
        return
    if "remove_unreferenced" in params:
        writer.compress_identical_objects(remove_unreferenced=True)
    elif "remove_orphans" in params:
        writer.compress_identical_objects(remove_orphans=True)


def _limpiar_writer(writer: PdfWriter) -> int:
    """Quita los metadatos del writer. Devuelve cuántos elementos se quitaron."""
    quitados = 0
    if writer.metadata:
        quitados += len(writer.metadata)
    writer.metadata = None

    raiz = writer._root_object
    for clave in ("/Metadata", "/PieceInfo"):
        if NameObject(clave) in raiz:
            del raiz[NameObject(clave)]
            quitados += 1

    for page in writer.pages:
        for clave in ("/Metadata", "/PieceInfo"):
            if NameObject(clave) in page:
                del page[NameObject(clave)]
                quitados += 1

    _quitar_huerfanos(writer)
    return quitados


def _ruta_unica(ruta: str, usadas: set) -> str:
    base, ext = os.path.splitext(ruta)
    candidato, n = ruta, 2
    while os.path.exists(candidato) or os.path.normcase(os.path.abspath(candidato)) in usadas:
        candidato = f"{base} ({n}){ext}"
        n += 1
    usadas.add(os.path.normcase(os.path.abspath(candidato)))
    return candidato


def limpiar_metadatos(
    archivos: list,
    destino: str = "",
    sufijo: str = "_limpio",
    callback_progreso: Optional[Callable[[int, int, str], None]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    cancelar: Optional[threading.Event] = None,
) -> ResumenMetadatos:
    """Escribe una copia sin metadatos de cada PDF en `destino`.

    destino vacío → <carpeta del primer PDF>/PDFs_Sin_Metadatos.
    Nunca sobrescribe un original ni otro resultado.
    """
    log = callback_log or (lambda m: None)
    progreso = callback_progreso or (lambda a, t, f: None)
    archivos = [a for a in archivos if a]
    if not archivos:
        raise ErrorMetadatos("Agrega al menos un PDF.")

    destino = (destino or "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(archivos[0])), "PDFs_Sin_Metadatos")
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError as e:
        raise ErrorMetadatos(f"No se pudo crear la carpeta de salida: {e}")

    res = ResumenMetadatos(total=len(archivos), carpeta_salida=destino)
    usadas = {os.path.normcase(os.path.abspath(a)) for a in archivos}  # nunca pisar un original
    ya_vistos: set = set()

    for i, ruta in enumerate(archivos, start=1):
        if cancelar is not None and cancelar.is_set():
            res.cancelado = True
            break
        nombre = os.path.basename(ruta)
        progreso(i - 1, len(archivos), nombre)
        tmp = None
        try:
            if not os.path.isfile(ruta):
                raise FileNotFoundError("el archivo ya no existe")
            real = os.path.realpath(ruta)
            if real in ya_vistos:
                res.omitidos.append(nombre)
                log(f"[DUPLICADO] {nombre}")
                continue
            ya_vistos.add(real)

            reader = PdfReader(ruta, strict=False)
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("está protegido con contraseña")

            paginas = len(reader.pages)
            writer = PdfWriter(clone_from=reader)
            quitados = _limpiar_writer(writer)

            stem = os.path.splitext(nombre)[0]
            salida = _ruta_unica(os.path.join(destino, f"{stem}{sufijo}.pdf"), usadas)
            tmp = salida + ".tmp"
            with open(tmp, "wb") as f:
                writer.write(f)

            # Verificación antes de dar el resultado por bueno
            comprobado = PdfReader(tmp, strict=False)
            if len(comprobado.pages) != paginas:
                raise RuntimeError("el resultado no conserva todas las páginas; se descartó")
            if comprobado.metadata:
                raise RuntimeError("quedaron metadatos tras limpiar; se descartó")
            os.replace(tmp, salida)
            tmp = None

            if quitados:
                res.limpiados += 1
                res.resultados.append((nombre, quitados))
                log(f"[OK] {nombre}: {quitados} elemento(s) de metadatos eliminados")
            else:
                res.sin_metadatos.append(nombre)
                log(f"[SIN METADATOS] {nombre}: copiado sin cambios")
        except Exception as e:
            res.errores.append((nombre, str(e)))
            log(f"[ERROR] {nombre}: {e}")
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    progreso(len(archivos), len(archivos), "")
    return res
