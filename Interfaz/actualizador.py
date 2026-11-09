"""
actualizador.py — Actualizaciones de CCpdf desde kodesoft.site (sin GitHub).

Kodesoft publica un manifiesto JSON:

    https://kodesoft.site/Downloads/ccpdf/version.json

    {
      "producto": "CCpdf",
      "version": "1.5.0",
      "fecha": "2026-11-08",
      "notas": ["Arrastrar y soltar", "..."],
      "pagina": "https://kodesoft.site/ccpdf.html",
      "archivos": {
        "linux":   {"nombre": "CCpdf-1.5.0-linux", "url": "CCpdf-1.5.0-linux",   # relativa al JSON
                    "sha256": "...", "tamano": 33696880},
        "windows": {"nombre": "CCpdf-1.5.0-windows.exe", "url": "...", "sha256": "...", "tamano": 0}
      }
    }

Flujo: comprobar() → descargar() (verifica tamaño y SHA-256) → instalar()
(sustituye el ejecutable y guarda el anterior como «.anterior»). Los datos del
usuario están fuera del programa y los adapta Interfaz/migracion.py al abrir la
versión nueva. Solo usa la biblioteca estándar.

Para probar contra otro servidor (p. ej. QA):
    CCPDF_URL_ACTUALIZACIONES=https://qa-web.kodesoft.site/Downloads/ccpdf/version.json
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

URL_MANIFIESTO_DEFECTO = "https://kodesoft.site/Downloads/ccpdf/version.json"
PAGINA_DEFECTO = "https://kodesoft.site/ccpdf.html"
TIMEOUT = 8
USER_AGENT = "CCpdf-Actualizador"
DOMINIOS_PERMITIDOS = ("kodesoft.site",)   # y sus subdominios (qa-web.kodesoft.site…)


class ErrorActualizacion(Exception):
    pass


def url_manifiesto() -> str:
    return os.environ.get("CCPDF_URL_ACTUALIZACIONES", "").strip() or URL_MANIFIESTO_DEFECTO


def plataforma() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def ejecutable_actual() -> Optional[str]:
    """Ruta del ejecutable si CCpdf corre empaquetado; None si corre desde el código."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    return None


def _version_tupla(v: str) -> tuple:
    partes = []
    for p in (v or "").strip().lstrip("vV").split(".")[:3]:
        num = "".join(c for c in p if c.isdigit())
        partes.append(int(num) if num else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes)


def _url_permitida(url: str) -> bool:
    """Solo se descarga por HTTPS desde kodesoft.site (o http a la red local, para pruebas)."""
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if u.scheme == "https" and any(host == d or host.endswith("." + d) for d in DOMINIOS_PERMITIDOS):
        return True
    if u.scheme in ("http", "https") and (host.startswith("192.168.") or host in ("127.0.0.1", "localhost")):
        return True
    return False


@dataclass
class InfoActualizacion:
    hay_nueva: bool = False
    version_actual: str = ""
    version_remota: str = ""
    fecha: str = ""
    notas: list = field(default_factory=list)
    archivo: Optional[dict] = None        # el de esta plataforma (url, sha256, tamano, nombre)
    pagina: str = PAGINA_DEFECTO
    error: str = ""

    @property
    def puede_instalar(self) -> bool:
        """Instalación automática: hay archivo para este sistema y CCpdf corre empaquetado."""
        return bool(self.hay_nueva and self.archivo and ejecutable_actual())

    @property
    def url_descarga(self) -> str:   # compatibilidad con la interfaz anterior
        return (self.archivo or {}).get("url") or self.pagina


def _leer_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json",
                                               "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        crudo = resp.read(256 * 1024)
    datos = json.loads(crudo.decode("utf-8"))
    if not isinstance(datos, dict):
        raise ValueError("el manifiesto no es un objeto JSON")
    return datos


def comprobar(version_actual: str, url: str | None = None, timeout: float = TIMEOUT) -> InfoActualizacion:
    """Consulta kodesoft.site y compara con la versión actual. Nunca lanza: informa en .error."""
    url = url or url_manifiesto()
    info = InfoActualizacion(version_actual=version_actual)
    if not _url_permitida(url):
        info.error = f"Dirección de actualizaciones no permitida: {url}"
        return info
    try:
        datos = _leer_json(url, timeout)
    except urllib.error.HTTPError as e:
        info.error = ("Aún no hay versiones publicadas en kodesoft.site." if e.code == 404
                      else f"kodesoft.site respondió con error HTTP {e.code}.")
        return info
    except urllib.error.URLError as e:
        info.error = f"Sin conexión con kodesoft.site ({e.reason})."
        return info
    except (ValueError, UnicodeDecodeError):
        info.error = "La información de versiones de kodesoft.site no es válida."
        return info
    except Exception as e:
        info.error = f"No se pudo consultar kodesoft.site: {e}"
        return info

    version = str(datos.get("version") or "").strip()
    if not version:
        info.error = "La información de versiones de kodesoft.site no indica la versión."
        return info
    info.version_remota = version
    info.fecha = str(datos.get("fecha") or "")
    notas = datos.get("notas") or []
    info.notas = [str(n) for n in notas] if isinstance(notas, list) else [str(notas)]
    pagina = str(datos.get("pagina") or "")
    info.pagina = pagina if _url_permitida(pagina) else PAGINA_DEFECTO
    archivo = (datos.get("archivos") or {}).get(plataforma())
    # La url puede ser relativa al manifiesto («CCpdf-1.5.0-linux»): así el mismo
    # version.json vale en kodesoft.site y en QA sin editarlo.
    url_archivo = urllib.parse.urljoin(url, str(archivo.get("url") or "")) \
        if isinstance(archivo, dict) else ""
    if isinstance(archivo, dict) and archivo.get("url") and archivo.get("sha256") \
            and _url_permitida(url_archivo):
        info.archivo = {"url": url_archivo, "sha256": str(archivo["sha256"]).lower(),
                        "tamano": int(archivo.get("tamano") or 0),
                        "nombre": str(archivo.get("nombre") or os.path.basename(archivo["url"]))}
    info.hay_nueva = _version_tupla(version) > _version_tupla(version_actual)
    return info


def descargar(info: InfoActualizacion, carpeta: str,
              progreso: Optional[Callable[[int, int], None]] = None,
              cancelar: Optional[threading.Event] = None,
              timeout: float = 30) -> str:
    """Descarga el archivo de la actualización verificando tamaño y SHA-256.

    Devuelve la ruta del archivo descargado. Si algo no cuadra, lo borra y lanza
    ErrorActualizacion: nunca se deja un archivo a medias o alterado.
    """
    if not info.archivo:
        raise ErrorActualizacion("No hay descarga para este sistema.")
    url, esperado = info.archivo["url"], info.archivo["sha256"]
    total = int(info.archivo.get("tamano") or 0)
    if not _url_permitida(url):
        raise ErrorActualizacion(f"Dirección de descarga no permitida: {url}")
    os.makedirs(carpeta, exist_ok=True)
    final = os.path.join(carpeta, os.path.basename(info.archivo["nombre"]) or "CCpdf-nuevo")
    parcial = final + ".part"
    h = hashlib.sha256()
    recibidos = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(parcial, "wb") as f:
            if not total:
                total = int(resp.headers.get("Content-Length") or 0)
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise ErrorActualizacion("Descarga cancelada.")
                bloque = resp.read(256 * 1024)
                if not bloque:
                    break
                f.write(bloque)
                h.update(bloque)
                recibidos += len(bloque)
                if progreso:
                    progreso(recibidos, total)
        if total and recibidos != total:
            raise ErrorActualizacion(f"Descarga incompleta ({recibidos} de {total} bytes).")
        if h.hexdigest() != esperado:
            raise ErrorActualizacion("El archivo descargado no coincide con su SHA-256: se descartó.")
        os.replace(parcial, final)
        return final
    except ErrorActualizacion:
        raise
    except urllib.error.URLError as e:
        raise ErrorActualizacion(f"No se pudo descargar: {getattr(e, 'reason', e)}")
    except OSError as e:
        raise ErrorActualizacion(f"No se pudo guardar la descarga: {e}")
    finally:
        if os.path.exists(parcial):
            try:
                os.remove(parcial)
            except OSError:
                pass


def instalar(descargado: str, ejecutable: Optional[str] = None) -> dict:
    """Sustituye el ejecutable por el descargado. El anterior queda como «.anterior».

    Funciona con el programa abierto: en Linux/macOS se reemplaza el archivo; en
    Windows un .exe en uso no se puede borrar pero sí renombrar, así que se
    renombra el actual y se pone el nuevo en su lugar.
    """
    ejecutable = ejecutable or ejecutable_actual()
    if not ejecutable:
        raise ErrorActualizacion("CCpdf se está ejecutando desde el código fuente: "
                                 "actualiza el código (git) o descarga el programa.")
    if not os.path.isfile(descargado):
        raise ErrorActualizacion("No se encuentra el archivo descargado.")
    carpeta = os.path.dirname(ejecutable)
    if not os.access(carpeta, os.W_OK):
        raise ErrorActualizacion(f"Sin permiso para escribir en {carpeta}. "
                                 "Ejecuta CCpdf con permisos o instala la versión nueva a mano.")
    anterior = ejecutable + ".anterior"
    nuevo_tmp = ejecutable + ".nuevo"
    try:
        if os.path.exists(nuevo_tmp):
            os.remove(nuevo_tmp)
        try:
            os.replace(descargado, nuevo_tmp)          # mismo disco: se mueve
        except OSError:
            _copiar(descargado, nuevo_tmp)             # otro disco: copiar y borrar
            try:
                os.remove(descargado)
            except OSError:
                pass
        if not sys.platform.startswith("win"):
            modo = os.stat(nuevo_tmp).st_mode
            os.chmod(nuevo_tmp, modo | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if os.path.exists(anterior):
            os.remove(anterior)
        os.replace(ejecutable, anterior)
        try:
            os.replace(nuevo_tmp, ejecutable)
        except OSError:
            os.replace(anterior, ejecutable)      # deshacer: el programa sigue como estaba
            raise
    except OSError as e:
        raise ErrorActualizacion(f"No se pudo instalar la actualización: {e}")
    finally:
        if os.path.exists(nuevo_tmp):
            try:
                os.remove(nuevo_tmp)
            except OSError:
                pass
    return {"ejecutable": ejecutable, "anterior": anterior}


def _copiar(origen: str, destino: str) -> None:
    import shutil
    shutil.copyfile(origen, destino)


def revertir(ejecutable: Optional[str] = None) -> str:
    """Vuelve al ejecutable «.anterior» (si la versión nueva falla)."""
    ejecutable = ejecutable or ejecutable_actual()
    if not ejecutable or not os.path.isfile(ejecutable + ".anterior"):
        raise ErrorActualizacion("No hay una versión anterior guardada.")
    fallida = ejecutable + ".fallida"
    if os.path.exists(fallida):
        os.remove(fallida)
    os.replace(ejecutable, fallida)
    os.replace(ejecutable + ".anterior", ejecutable)
    return ejecutable


def reiniciar(ejecutable: Optional[str] = None) -> None:
    """Lanza el ejecutable (la versión nueva). La app debe cerrarse después."""
    ejecutable = ejecutable or ejecutable_actual()
    if not ejecutable:
        raise ErrorActualizacion("No se puede reiniciar desde el código fuente.")
    opciones = {}
    if sys.platform.startswith("win"):
        opciones["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    subprocess.Popen([ejecutable], close_fds=True, **opciones)


def tam_legible(n: int) -> str:
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} GB"
