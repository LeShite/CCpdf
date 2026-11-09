"""
migracion.py — Conserva los datos del usuario entre versiones de CCpdf.

Los datos viven fuera del programa, en la carpeta de configuración
(~/.config/CCpdf en Linux, %APPDATA%/CCpdf en Windows): config.json,
historial.json y temporales/. Cambiar el ejecutable no los toca; este módulo
se asegura de que la versión nueva los entienda:

  - `respaldar()` copia config.json e historial.json a respaldos/<fecha>_<versión>_<motivo>/
    (antes de instalar una actualización y antes de migrar).
  - `migrar()` se llama al arrancar: si los datos los escribió otra versión, hace
    un respaldo, aplica las migraciones necesarias y anota la versión actual.
  - `restaurar()` devuelve un respaldo a su sitio.

Los temporales (copias de PDFs para deshacer) no se respaldan: pueden ocupar
mucho y ya son, en sí mismos, copias.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from Interfaz import config as cfg_prefs

ARCHIVOS_DATOS = ("config.json", "historial.json")
MAX_RESPALDOS = 10


def dir_datos() -> Path:
    return cfg_prefs._ruta_config().parent


def dir_respaldos() -> Path:
    return dir_datos() / "respaldos"


def _version_tupla(v: str) -> tuple:
    partes = []
    for p in (v or "").strip().lstrip("vV").split(".")[:3]:
        num = "".join(c for c in p if c.isdigit())
        partes.append(int(num) if num else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes)


def respaldar(version: str, motivo: str) -> Path | None:
    """Copia los archivos de datos a una carpeta nueva de respaldos. None si no hay nada."""
    origen = dir_datos()
    existentes = [a for a in ARCHIVOS_DATOS if (origen / a).is_file()]
    if not existentes:
        return None
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    nombre = f"{sello}_{(version or 'desconocida').lstrip('vV')}_{motivo}"
    destino = dir_respaldos() / nombre
    n = 2
    while destino.exists():
        destino = dir_respaldos() / f"{nombre}-{n}"
        n += 1
    destino.mkdir(parents=True)
    for a in existentes:
        shutil.copy2(origen / a, destino / a)
    with open(destino / "respaldo.json", "w", encoding="utf-8") as f:
        json.dump({"version": version, "motivo": motivo,
                   "fecha": datetime.now().isoformat(timespec="seconds"),
                   "archivos": existentes}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(destino, 0o700)
        for a in existentes:
            os.chmod(destino / a, 0o600)
    except OSError:
        pass
    _podar()
    return destino


def _podar() -> None:
    """Deja solo los MAX_RESPALDOS más recientes."""
    d = dir_respaldos()
    if not d.is_dir():
        return
    carpetas = sorted((c for c in d.iterdir() if c.is_dir()), key=lambda c: c.name)
    for vieja in carpetas[:-MAX_RESPALDOS]:
        shutil.rmtree(vieja, ignore_errors=True)


def listar_respaldos() -> list:
    """[(carpeta, datos_de_respaldo.json)], más reciente primero."""
    d = dir_respaldos()
    if not d.is_dir():
        return []
    res = []
    for c in sorted((c for c in d.iterdir() if c.is_dir()), key=lambda c: c.name, reverse=True):
        try:
            datos = json.loads((c / "respaldo.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        res.append((c, datos))
    return res


def restaurar(carpeta: Path) -> list:
    """Devuelve los archivos de un respaldo a la carpeta de datos (respaldando antes lo actual)."""
    carpeta = Path(carpeta)
    archivos = [a for a in ARCHIVOS_DATOS if (carpeta / a).is_file()]
    if not archivos:
        raise FileNotFoundError("el respaldo no contiene datos")
    respaldar(_leer_config().get("app_version", ""), "antes-de-restaurar")
    for a in archivos:
        shutil.copy2(carpeta / a, dir_datos() / a)
    return archivos


def _leer_config() -> dict:
    try:
        with open(cfg_prefs._ruta_config(), encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir_config(datos: dict) -> None:
    ruta = cfg_prefs._ruta_config()
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ruta)


# ─────────────────────────────────────────────────────────────
#  MIGRACIONES  (versión mínima → función que transforma el dict de config)
# ─────────────────────────────────────────────────────────────
def _a_1_5_0(datos: dict) -> dict:
    """1.0.x → 1.5.0: carpetas nuevas (OCR, Metadatos, Comparar) y prefs de historial."""
    carpetas = datos.get("carpetas") if isinstance(datos.get("carpetas"), dict) else {}
    for k in ("ocr", "metadatos", "comparar"):
        carpetas.setdefault(k, "")
    datos["carpetas"] = carpetas
    datos.setdefault("historial_activo", True)
    datos.setdefault("temporales_activo", True)
    datos.setdefault("temporales_dias", 30)
    datos.setdefault("actualizaciones_auto", True)
    return datos


MIGRACIONES = (
    ("1.5.0", _a_1_5_0),
)


def migrar(version_app: str) -> dict:
    """Llamar al arrancar. Devuelve {"de", "a", "cambio", "respaldo", "aplicadas"}."""
    resultado = {"de": None, "a": version_app, "cambio": False, "respaldo": None, "aplicadas": []}
    if not cfg_prefs._ruta_config().is_file():
        return resultado                      # primera ejecución: nada que migrar
    datos = _leer_config()
    anterior = datos.get("app_version") or ""
    resultado["de"] = anterior or None
    if anterior and _version_tupla(anterior) == _version_tupla(version_app):
        return resultado

    resultado["cambio"] = True
    resultado["respaldo"] = respaldar(anterior or "anterior-a-1.5", "antes-de-migrar")
    v_ant = _version_tupla(anterior) if anterior else (0, 0, 0)
    for v_min, funcion in MIGRACIONES:
        if v_ant < _version_tupla(v_min) <= _version_tupla(version_app):
            datos = funcion(datos)
            resultado["aplicadas"].append(v_min)
    datos["app_version"] = version_app
    _escribir_config(datos)
    return resultado
