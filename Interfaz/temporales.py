"""
temporales.py — Copias de seguridad de las acciones para poder deshacerlas.

Antes de cada proceso se guarda una copia de los PDFs de entrada; al deshacer,
los archivos generados se mueven aquí (no se borran) para poder rehacer.

Almacén por contenido: <config>/temporales/objetos/<sha256>.pdf. El mismo PDF
usado en varias acciones ocupa espacio una sola vez. Lo que ya no referencia
ninguna entrada del historial dentro del plazo de retención se elimina.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from Interfaz import config as cfg_prefs

# (días, etiqueta). El recomendado y el no recomendado se marcan en la interfaz.
OPCIONES_RETENCION = (
    (1, "1 día"),
    (7, "1 semana"),
    (30, "1 mes (recomendado)"),
    (90, "3 meses"),
    (180, "6 meses"),
    (365, "1 año (no recomendado: ocupa mucho espacio)"),
)
DIAS_DEFECTO = 30
DIAS_MIN, DIAS_MAX = 1, 365


def dir_temporales() -> Path:
    return cfg_prefs._ruta_config().with_name("temporales")


def _dir_objetos() -> Path:
    d = dir_temporales() / "objetos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _guardar_objeto(ruta: str) -> dict:
    sha = _sha256(ruta)
    destino = _dir_objetos() / f"{sha}.pdf"
    if not destino.exists():
        tmp = destino.with_suffix(".tmp")
        shutil.copy2(ruta, tmp)
        os.replace(tmp, destino)
        try:
            os.chmod(destino, 0o600)
        except OSError:
            pass
    return {"nombre": os.path.basename(ruta), "ruta_original": os.path.abspath(ruta),
            "sha": sha, "tam": os.path.getsize(destino)}


def guardar_versiones(rutas: list) -> list:
    """Copia los archivos de entrada al almacén. Ignora los que no se pueden leer."""
    registros = []
    for r in rutas:
        try:
            if r and os.path.isfile(r):
                registros.append(_guardar_objeto(r))
        except OSError:
            continue
    return registros


def mover_a_temporales(ruta: str) -> dict | None:
    """Guarda una copia del archivo y lo quita de su sitio (para deshacer)."""
    if not os.path.isfile(ruta):
        return None
    reg = _guardar_objeto(ruta)
    os.remove(ruta)
    return reg


def _ruta_libre(ruta: str, sufijo: str = " (restaurado)") -> str:
    if not os.path.exists(ruta):
        return ruta
    base, ext = os.path.splitext(ruta)
    candidato, n = f"{base}{sufijo}{ext}", 2
    while os.path.exists(candidato):
        candidato = f"{base}{sufijo} {n}{ext}"
        n += 1
    return candidato


def restaurar(registro: dict, carpeta: str = "", sufijo: str = " (restaurado)") -> str:
    """Vuelve a escribir un archivo guardado. Nunca sobrescribe nada.

    carpeta vacía → donde estaba originalmente. Devuelve la ruta escrita.
    """
    origen = _dir_objetos() / f"{registro['sha']}.pdf"
    if not origen.exists():
        raise FileNotFoundError("la copia temporal ya caducó y se eliminó")
    destino = registro["ruta_original"]
    if carpeta:
        destino = os.path.join(carpeta, registro["nombre"])
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    destino = _ruta_libre(destino, sufijo)
    shutil.copy2(origen, destino)
    return destino


def disponible(registro: dict) -> bool:
    return (_dir_objetos() / f"{registro.get('sha', '')}.pdf").exists()


def espacio_usado() -> int:
    d = dir_temporales() / "objetos"
    if not d.exists():
        return 0
    return sum(f.stat().st_size for f in d.glob("*.pdf") if f.is_file())


def _referencias(entrada: dict) -> list:
    return list(entrada.get("versiones") or []) + list(entrada.get("retirados") or [])


def purgar(entradas: list, dias: int) -> tuple:
    """Elimina las copias de entradas más viejas que `dias` y las no referenciadas.

    Devuelve (entradas_actualizadas, bytes_liberados). Las entradas vencidas se
    quedan en el historial pero sin copias (no se pueden deshacer ya).
    """
    dias = max(DIAS_MIN, min(DIAS_MAX, int(dias or DIAS_DEFECTO)))
    limite = datetime.now() - timedelta(days=dias)
    vigentes = set()
    actualizadas = []
    for e in entradas:
        try:
            fecha = datetime.fromisoformat(e.get("fecha", ""))
        except (TypeError, ValueError):
            fecha = datetime.min
        if fecha < limite and _referencias(e):
            e = dict(e, versiones=[], retirados=[], temporales_caducados=True)
        for reg in _referencias(e):
            vigentes.add(reg.get("sha"))
        actualizadas.append(e)

    liberados = 0
    d = dir_temporales() / "objetos"
    if d.exists():
        for f in d.iterdir():
            if f.suffix == ".tmp" or (f.suffix == ".pdf" and f.stem not in vigentes):
                try:
                    liberados += f.stat().st_size
                    f.unlink()
                except OSError:
                    pass
    return actualizadas, liberados


def tam_legible(n: int) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GB"
