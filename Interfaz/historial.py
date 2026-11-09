"""
historial.py — Registro local de los procesos terminados.

Se guarda en historial.json junto a config.json (~/.config/CCpdf en Linux,
%APPDATA%/CCpdf en Windows), con permisos 600 donde se puede. Nunca sale del
equipo. Guarda solo nombres de archivo y la carpeta de salida, no contenidos.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from Interfaz import config as cfg_prefs
from Interfaz import temporales

MAX_ENTRADAS = 200
MAX_ARCHIVOS_POR_ENTRADA = 20
_lock = threading.Lock()


def ruta_historial() -> Path:
    return cfg_prefs._ruta_config().with_name("historial.json")


def cargar(ruta: Path | None = None) -> list:
    """Entradas más recientes primero. Si el archivo no existe o está dañado: []."""
    ruta = ruta or ruta_historial()
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        entradas = datos.get("entradas", []) if isinstance(datos, dict) else []
        return [e for e in entradas if isinstance(e, dict)]
    except (OSError, ValueError):
        return []


def _guardar(entradas: list, ruta: Path) -> bool:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), prefix=".historial-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "entradas": entradas}, f, ensure_ascii=False, indent=1)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, ruta)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def rutas_entrada(kwargs: dict) -> list:
    """Archivos PDF de entrada de un proceso, según sus parámetros."""
    rutas = list(kwargs.get("archivos") or [])
    for clave in ("origen", "archivo_a", "archivo_b"):
        v = kwargs.get(clave)
        if v and os.path.isfile(v):
            rutas.append(v)
    return rutas


def nueva_entrada(modulo: str, titulo: str, kwargs: dict, resumen=None,
                  error: str | None = None) -> dict:
    """Construye una entrada a partir de lo que se lanzó y de cómo terminó."""
    entradas_archivos = rutas_entrada(kwargs)

    salida = ""
    if resumen is not None:
        salida = getattr(resumen, "ruta_salida", "") or getattr(resumen, "carpeta_salida", "") or ""
    if not salida:
        salida = kwargs.get("salida") or kwargs.get("destino") or ""

    if error:
        estado = "error"
    elif resumen is not None and getattr(resumen, "cancelado", False):
        estado = "cancelado"
    elif resumen is not None and getattr(resumen, "errores", None):
        estado = "con avisos"
    else:
        estado = "ok"

    texto = error or (resumen.a_texto() if hasattr(resumen, "a_texto") else str(resumen or ""))
    lineas = [l for l in texto.splitlines() if l.strip()][:4]

    return {
        "id": uuid.uuid4().hex,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modulo": modulo,
        "titulo": titulo,
        "archivos": [os.path.basename(a) for a in entradas_archivos[:MAX_ARCHIVOS_POR_ENTRADA]],
        "n_archivos": len(entradas_archivos),
        "carpeta_origen": os.path.dirname(os.path.abspath(entradas_archivos[0])) if entradas_archivos else "",
        "salida": salida,
        "estado": estado,
        "resumen": "\n".join(lineas),
        "entradas_rutas": [os.path.abspath(a) for a in entradas_archivos],
        "versiones": [],    # copias de las entradas (temporales.guardar_versiones)
        "salidas": [],      # archivos generados
        "retirados": [],    # salidas movidas a temporales al deshacer
        "deshecho": False,
    }


def detectar_salidas(resumen, kwargs: dict, desde: float) -> list:
    """PDFs que generó el proceso: el archivo de salida, o los PDFs nuevos de la
    carpeta de salida (y sus subcarpetas directas) creados desde `desde`."""
    ruta = getattr(resumen, "ruta_salida", "") if resumen is not None else ""
    if ruta and os.path.isfile(ruta):
        return [os.path.abspath(ruta)]
    carpeta = (getattr(resumen, "carpeta_salida", "") if resumen is not None else "") \
        or kwargs.get("destino") or ""
    if not carpeta or not os.path.isdir(carpeta):
        return []
    entradas = {os.path.realpath(a) for a in (kwargs.get("archivos") or [])}
    for clave in ("origen", "archivo_a", "archivo_b"):
        if kwargs.get(clave):
            entradas.add(os.path.realpath(kwargs[clave]))
    salidas = []
    base_prof = carpeta.rstrip(os.sep).count(os.sep)
    for raiz, dirs, archivos in os.walk(carpeta):
        if raiz.count(os.sep) - base_prof >= 1:
            dirs[:] = []
        for a in archivos:
            p = os.path.join(raiz, a)
            if not a.lower().endswith(".pdf") or os.path.realpath(p) in entradas:
                continue
            try:
                if os.path.getmtime(p) >= desde - 1:
                    salidas.append(os.path.abspath(p))
            except OSError:
                pass
    return sorted(salidas)


def reemplazar(entradas: list, ruta: Path | None = None) -> bool:
    ruta = ruta or ruta_historial()
    with _lock:
        return _guardar(entradas[:MAX_ENTRADAS], ruta)


def actualizar(entrada: dict, ruta: Path | None = None) -> bool:
    """Sustituye la entrada con el mismo id."""
    ruta = ruta or ruta_historial()
    with _lock:
        entradas = [entrada if e.get("id") == entrada.get("id") else e for e in cargar(ruta)]
        return _guardar(entradas, ruta)


# ─────────────────────────────────────────────────────────────
#  DESHACER / REHACER / RESTAURAR
# ─────────────────────────────────────────────────────────────
def deshacer(entrada: dict) -> dict:
    """Retira los archivos generados (los mueve a temporales). Devuelve la entrada nueva."""
    retirados = list(entrada.get("retirados") or [])
    quedan = []
    for p in entrada.get("salidas") or []:
        reg = temporales.mover_a_temporales(p)
        if reg:
            retirados.append(reg)
        elif os.path.exists(p):
            quedan.append(p)
    return dict(entrada, retirados=retirados, salidas=quedan, deshecho=True)


def rehacer(entrada: dict) -> dict:
    """Vuelve a poner los archivos retirados donde estaban."""
    salidas = list(entrada.get("salidas") or [])
    for reg in entrada.get("retirados") or []:
        salidas.append(temporales.restaurar(reg, sufijo=" (rehecho)"))
    return dict(entrada, retirados=[], salidas=salidas, deshecho=False)


def restaurar_originales(entrada: dict, carpeta: str = "") -> list:
    """Escribe de nuevo las versiones de entrada de esa acción. Nunca sobrescribe."""
    return [temporales.restaurar(reg, carpeta) for reg in entrada.get("versiones") or []]


def puede_deshacer(entrada: dict) -> bool:
    return not entrada.get("deshecho") and any(os.path.isfile(p) for p in entrada.get("salidas") or [])


def puede_rehacer(entrada: dict) -> bool:
    return bool(entrada.get("deshecho")) and all(
        temporales.disponible(r) for r in entrada.get("retirados") or [])


def puede_restaurar(entrada: dict) -> bool:
    vs = entrada.get("versiones") or []
    return bool(vs) and all(temporales.disponible(r) for r in vs)


def agregar(entrada: dict, ruta: Path | None = None) -> bool:
    ruta = ruta or ruta_historial()
    with _lock:
        entradas = [entrada] + cargar(ruta)
        return _guardar(entradas[:MAX_ENTRADAS], ruta)


def vaciar(ruta: Path | None = None) -> bool:
    ruta = ruta or ruta_historial()
    with _lock:
        return _guardar([], ruta)


def fecha_legible(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return iso or "?"
