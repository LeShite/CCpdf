"""
instalar_gs.py — Instala Ghostscript bajo demanda ("Mejoras extras" del compresor).

Ghostscript es AGPL-3, así que CCpdf no lo incluye (ver docs/LICENCIAS.md): el usuario lo
obtiene de su fuente oficial, como un programa aparte.

  - Windows: instalador oficial de Artifex (GitHub). Versión y SHA-256 fijos: si la descarga
    no coincide, no se ejecuta. Windows pide permiso de administrador.
  - macOS:   Homebrew (`brew install ghostscript`); Artifex no publica binarios para Mac.
  - Linux:   el gestor de paquetes del sistema vía pkexec (pide la contraseña).
"""
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from .pdf_compresor import ErrorCompresion, buscar_ghostscript, olvidar_ghostscript, version_ghostscript

# shortcut: versión fija; para actualizar, cambiar las tres constantes (el SHA-256 sale en la
# página de la release: github.com/ArtifexSoftware/ghostpdl-downloads/releases).
GS_VERSION = "10.08.0"
GS_URL_WIN = ("https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/"
              "gs10080/gs10080w64.exe")
GS_SHA256_WIN = "52a91b8bf09298788d7a57b9206127026c23eacd75405f0a131e26dc381dce50"

_BREW = ("/opt/homebrew/bin/brew", "/usr/local/bin/brew")   # Apple Silicon, Intel
_GESTORES_LINUX = (
    ("apt-get", ["install", "-y", "ghostscript"]),
    ("dnf", ["install", "-y", "ghostscript"]),
    ("zypper", ["--non-interactive", "install", "ghostscript"]),
    ("pacman", ["-S", "--noconfirm", "ghostscript"]),
)


class _Cancelado(Exception):
    pass


@dataclass
class ResumenInstalacion:
    ruta: str = ""
    version: str = ""
    cancelado: bool = False

    def a_texto(self) -> str:
        if self.cancelado:
            return "Instalación de Ghostscript cancelada."
        return f"Ghostscript {self.version} instalado.\n{self.ruta}"


def instalar_ghostscript(
    callback_progreso: Optional[Callable[[float, int, str], None]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    cancelar=None,
) -> ResumenInstalacion:
    """Instala Ghostscript según el sistema. Misma firma que los motores (para `_lanzar`)."""
    log = callback_log or (lambda m: None)
    progreso = callback_progreso or (lambda a, t, f: None)

    if buscar_ghostscript():
        return ResumenInstalacion(buscar_ghostscript(), version_ghostscript() or "")
    try:
        if sys.platform.startswith("win"):
            _instalar_windows(log, progreso, cancelar)
        elif sys.platform == "darwin":
            _instalar_mac(log, progreso)
        else:
            _instalar_linux(log, progreso)
    except _Cancelado:
        return ResumenInstalacion(cancelado=True)

    olvidar_ghostscript()
    ruta = buscar_ghostscript()
    if not ruta:
        raise ErrorCompresion("La instalación terminó, pero no se encuentra Ghostscript. "
                              "Reinicia CCpdf y vuelve a mirar.")
    progreso(1, 1, "Ghostscript instalado")
    return ResumenInstalacion(ruta, version_ghostscript(ruta) or "")


# ─── Windows ───
def _instalar_windows(log, progreso, cancelar) -> None:
    if not platform.machine().endswith("64"):
        raise ErrorCompresion("El instalador automático es para Windows de 64 bits.")
    fd, exe = tempfile.mkstemp(prefix="ccpdf_gs_", suffix=".exe")
    os.close(fd)
    try:
        log(f"Descargando Ghostscript {GS_VERSION} del servidor oficial de Artifex…")
        _descargar(GS_URL_WIN, exe, GS_SHA256_WIN, progreso, cancelar)
        log("Descarga verificada (SHA-256). Instalando: Windows pedirá permiso de administrador.")
        progreso(0.95, 1, "Instalando…")
        ruta_ps = exe.replace("'", "''")   # comillas simples de PowerShell
        r = _ejecutar(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                       f"Start-Process -FilePath '{ruta_ps}' -ArgumentList '/S' -Verb RunAs -Wait"],
                      log)
        if r != 0:
            raise ErrorCompresion("No se instaló: se denegó el permiso de administrador "
                                  "o el instalador falló.")
    finally:
        try:
            os.remove(exe)
        except OSError:
            pass


def _descargar(url: str, destino: str, sha256: str, progreso, cancelar) -> None:
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=30) as resp, open(destino, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            hecho = 0
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise _Cancelado()
                bloque = resp.read(1 << 16)
                if not bloque:
                    break
                f.write(bloque)
                h.update(bloque)
                hecho += len(bloque)
                if total:
                    # la descarga ocupa el 90 % de la barra; el resto, la instalación
                    progreso(0.9 * hecho / total, 1, f"Descargando… {hecho >> 20} de {total >> 20} MB")
    except _Cancelado:
        raise
    except Exception as e:
        raise ErrorCompresion(f"No se pudo descargar Ghostscript: {e}")
    if h.hexdigest() != sha256:
        raise ErrorCompresion("La descarga de Ghostscript no coincide con la oficial (SHA-256): "
                              "no se instala.")


# ─── macOS ───
def _instalar_mac(log, progreso) -> None:
    brew = next((b for b in _BREW if os.path.isfile(b)), None) or shutil.which("brew")
    if not brew:
        raise ErrorCompresion(
            "En macOS, Ghostscript se instala con Homebrew y no está instalado.\n"
            "Instálalo desde https://brew.sh y vuelve a pulsar el botón, "
            "o ejecuta en Terminal: brew install ghostscript")
    log("Instalando Ghostscript con Homebrew (puede tardar unos minutos)…")
    progreso(0.1, 1, "Instalando con Homebrew…")
    if _ejecutar([brew, "install", "ghostscript"], log) != 0:
        raise ErrorCompresion("Homebrew no pudo instalar Ghostscript. Revisa el registro.")


# ─── Linux ───
def comando_linux() -> Optional[list]:
    """Comando del gestor de paquetes disponible (sin pkexec), o None."""
    for gestor, args in _GESTORES_LINUX:
        ruta = shutil.which(gestor)
        if ruta:
            return [ruta] + args
    return None


def _instalar_linux(log, progreso) -> None:
    cmd = comando_linux()
    if not cmd:
        raise ErrorCompresion("No se encontró el gestor de paquetes (apt, dnf, zypper o pacman). "
                              "Instala el paquete «ghostscript» de tu distribución.")
    pkexec = shutil.which("pkexec")
    if not pkexec:
        raise ErrorCompresion("Falta pkexec para pedir permisos. Instálalo en una terminal:\n"
                              "sudo " + " ".join([os.path.basename(cmd[0])] + cmd[1:]))
    log("Instalando Ghostscript con el gestor de paquetes del sistema (pedirá tu contraseña)…")
    progreso(0.1, 1, "Instalando…")
    r = _ejecutar([pkexec] + cmd, log)
    if r in (126, 127):          # pkexec: ventana cerrada o permiso denegado
        raise _Cancelado()
    if r != 0:
        raise ErrorCompresion("El gestor de paquetes no pudo instalar Ghostscript. Revisa el registro.")


def _ejecutar(cmd: list, log) -> int:
    """Ejecuta `cmd` volcando su salida al registro. Devuelve el código de salida."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace",
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as e:
        raise ErrorCompresion(f"No se pudo ejecutar {os.path.basename(cmd[0])}: {e}")
    for linea in proc.stdout:
        if linea.strip():
            log(linea.rstrip())
    return proc.wait()
