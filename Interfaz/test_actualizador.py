"""Prueba del actualizador (kodesoft.site) y de la migración de datos.

Ejecutar desde la raíz del repo:  python -m Interfaz.test_actualizador
Levanta un servidor HTTP local que hace de kodesoft.site. No toca la
configuración real ni ningún ejecutable real.
"""
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest import mock

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg, flush=True)
    ok = ok and cond


WEB = Path(tempfile.mkdtemp())
(WEB / "Downloads" / "ccpdf").mkdir(parents=True)
binario_nuevo = b"#!/bin/sh\necho CCpdf 1.6.0\n" + os.urandom(300_000)
(WEB / "Downloads/ccpdf/CCpdf-1.6.0-linux").write_bytes(binario_nuevo)
sha = hashlib.sha256(binario_nuevo).hexdigest()


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, *a):
        pass


class Servidor(http.server.ThreadingHTTPServer):
    def handle_error(self, *a):      # la prueba de «cancelar» corta la conexión a propósito
        pass


srv = Servidor(("127.0.0.1", 0), Silencioso)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_port}/Downloads/ccpdf"


def publicar(manifiesto):
    (WEB / "Downloads/ccpdf/version.json").write_text(json.dumps(manifiesto), encoding="utf-8")


manifiesto = {
    "producto": "CCpdf", "version": "1.6.0", "fecha": "2026-12-01",
    "notas": ["Proteger PDFs con contraseña", "Corrige X"],
    "pagina": "https://kodesoft.site/ccpdf.html",
    "archivos": {p: {"nombre": "CCpdf-1.6.0-linux", "url": f"{BASE}/CCpdf-1.6.0-linux",
                     "sha256": sha, "tamano": len(binario_nuevo)}
                 for p in ("linux", "windows", "macos")},
}
publicar(manifiesto)

CONF = Path(tempfile.mkdtemp()) / "config.json"
parche = mock.patch("Interfaz.config._ruta_config", lambda: CONF)
parche.start()
from Interfaz import actualizador as A
from Interfaz import migracion as M

URL = f"{BASE}/version.json"

# ── comprobar ────────────────────────────────────────────────
i = A.comprobar("v1.5.0", url=URL)
check(not i.error and i.hay_nueva and i.version_remota == "1.6.0", f"detecta la versión nueva ({i.error})")
check(i.notas == manifiesto["notas"] and i.fecha == "2026-12-01", "lee notas y fecha")
check(i.archivo and i.archivo["sha256"] == sha, "elige el archivo de esta plataforma")
check(not A.comprobar("v1.6.0", url=URL).hay_nueva, "misma versión: no hay nueva")
check(not A.comprobar("v2.0.0", url=URL).hay_nueva, "versión más nueva instalada: no ofrece bajar")
check("no hay versiones" in A.comprobar("v1.5.0", url=f"{BASE}/no-existe.json").error.lower(),
      "404 → «Aún no hay versiones publicadas en kodesoft.site»")
check("no permitida" in A.comprobar("v1.5.0", url="https://github.com/x/version.json").error,
      "rechaza manifiestos fuera de kodesoft.site")
check("Sin conexión" in A.comprobar("v1.5.0", url="http://127.0.0.1:1/version.json", timeout=2).error,
      "sin conexión: mensaje claro, no revienta")
(WEB / "Downloads/ccpdf/roto.json").write_text("{no es json", encoding="utf-8")
check("no es válida" in A.comprobar("v1.5.0", url=f"{BASE}/roto.json").error, "JSON roto: mensaje claro")
malo = dict(manifiesto, archivos={"linux": dict(manifiesto["archivos"]["linux"],
                                                url="https://evil.example.com/x")})
publicar(malo)
check(A.comprobar("v1.5.0", url=URL).archivo is None, "ignora descargas fuera de kodesoft.site")
publicar(manifiesto)

relativo = dict(manifiesto, archivos={"linux": dict(manifiesto["archivos"]["linux"], url="CCpdf-1.6.0-linux"),
                                       "windows": dict(manifiesto["archivos"]["linux"], url="CCpdf-1.6.0-linux"),
                                       "macos": dict(manifiesto["archivos"]["linux"], url="CCpdf-1.6.0-linux")})
publicar(relativo)
check(A.comprobar("v1.5.0", url=URL).archivo["url"] == f"{BASE}/CCpdf-1.6.0-linux",
      "url de descarga relativa al manifiesto (el mismo JSON vale en QA y en kodesoft.site)")
publicar(manifiesto)

with mock.patch.object(A, "ejecutable_actual", return_value=None):
    check(not A.comprobar("v1.5.0", url=URL).puede_instalar,
          "desde el código fuente no ofrece instalar (solo la página)")

# ── descargar ────────────────────────────────────────────────
DL = tempfile.mkdtemp()
avance = []
ruta = A.descargar(i, DL, progreso=lambda r, t: avance.append((r, t)))
check(Path(ruta).read_bytes() == binario_nuevo, "descarga el archivo completo")
check(avance and avance[-1] == (len(binario_nuevo), len(binario_nuevo)), "informa el progreso")

alterado = A.InfoActualizacion(archivo=dict(i.archivo, sha256="0" * 64))
try:
    A.descargar(alterado, DL)
    check(False, "SHA-256 distinto debe fallar")
except A.ErrorActualizacion as e:
    check("SHA-256" in str(e) and not any(f.endswith(".part") for f in os.listdir(DL)),
          "SHA-256 distinto: se descarta y no quedan restos")

cancel = threading.Event()
cancel.set()
try:
    A.descargar(i, tempfile.mkdtemp(), cancelar=cancel)
    check(False, "cancelar debe detener")
except A.ErrorActualizacion as e:
    check("cancelada" in str(e), "la descarga se puede cancelar")

# ── instalar / revertir ─────────────────────────────────────
APP = Path(tempfile.mkdtemp())
exe = APP / "CCpdf"
exe.write_bytes(b"version vieja")
os.chmod(exe, 0o755)
r = A.instalar(ruta, ejecutable=str(exe))
check(exe.read_bytes() == binario_nuevo and os.access(exe, os.X_OK), "instala el nuevo y es ejecutable")
check(Path(r["anterior"]).read_bytes() == b"version vieja", "guarda el anterior como .anterior")
A.revertir(str(exe))
check(exe.read_bytes() == b"version vieja", "revertir vuelve a la versión anterior")
try:
    A.instalar(ruta, ejecutable=None) if A.ejecutable_actual() is None else None
    check(A.ejecutable_actual() is not None, "desde el código fuente instalar debe avisar")
except A.ErrorActualizacion as e:
    check("código fuente" in str(e), "desde el código fuente instalar avisa en lugar de romper nada")

# ── migración de datos ──────────────────────────────────────
check(M.migrar("v1.5.0")["cambio"] is False, "primera ejecución (sin datos): nada que migrar")
CONF.write_text(json.dumps({"tema": "oscuro", "idioma": "en",
                            "carpetas": {"extractor": "/datos/ext"}, "version_prefs": 2}),
                encoding="utf-8")
(CONF.parent / "historial.json").write_text('{"version":1,"entradas":[{"id":"x"}]}', encoding="utf-8")
res = M.migrar("v1.5.0")
datos = json.loads(CONF.read_text(encoding="utf-8"))
check(res["cambio"] and res["de"] is None and res["aplicadas"] == ["1.5.0"], "datos de 1.0.x → migra a 1.5.0")
check(datos["tema"] == "oscuro" and datos["idioma"] == "en" and datos["carpetas"]["extractor"] == "/datos/ext",
      "conserva tema, idioma y carpetas del usuario")
check(datos["carpetas"].get("metadatos") == "" and datos["app_version"] == "v1.5.0",
      "añade lo nuevo y anota la versión")
check(res["respaldo"] and (res["respaldo"] / "config.json").is_file()
      and (res["respaldo"] / "historial.json").is_file(), "respalda config e historial antes de migrar")
check(M.migrar("v1.5.0")["cambio"] is False, "al abrir otra vez la misma versión no vuelve a migrar")

res2 = M.migrar("v1.6.0")
check(res2["cambio"] and res2["de"] == "v1.5.0" and json.loads(CONF.read_text())["app_version"] == "v1.6.0",
      "actualizar a 1.6.0: datos marcados con la versión nueva")
check(json.loads(CONF.read_text())["tema"] == "oscuro", "los datos del usuario pasan a la versión nueva")

from Interfaz import config as C
p = C.cargar()
check(p["app_version"] == "v1.6.0" and p["tema"] == "oscuro", "config.cargar() conserva app_version")
C.guardar(p)
check(json.loads(CONF.read_text())["app_version"] == "v1.6.0", "guardar la configuración no borra app_version")

CONF.write_text(json.dumps(dict(json.loads(CONF.read_text()), tema="claro")), encoding="utf-8")
lista = M.listar_respaldos()
M.restaurar(lista[-1][0])
check(json.loads(CONF.read_text())["tema"] == "oscuro", "restaurar un respaldo devuelve los datos")
for _ in range(15):
    M.respaldar("v1.6.0", "prueba")
check(len(M.listar_respaldos()) == M.MAX_RESPALDOS, f"se conservan solo los {M.MAX_RESPALDOS} respaldos más recientes")

srv.shutdown()
parche.stop()
sys.exit(0 if ok else 1)
