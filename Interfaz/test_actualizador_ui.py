"""Prueba de punta a punta de Configuración → Actualizaciones (necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_actualizador_ui
Un servidor local hace de kodesoft.site y un archivo temporal hace de ejecutable
instalado. No toca la configuración real ni ningún ejecutable real.
"""
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg, flush=True)
    ok = ok and cond


WEB = Path(tempfile.mkdtemp())
(WEB / "Downloads/ccpdf").mkdir(parents=True)
nuevo = b"CCPDF-1.6.0-BINARIO" + os.urandom(500_000)
(WEB / "Downloads/ccpdf/CCpdf-1.6.0-linux").write_bytes(nuevo)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_port}/Downloads/ccpdf"
archivo = {"nombre": "CCpdf-1.6.0-linux", "url": f"{BASE}/CCpdf-1.6.0-linux",
           "sha256": hashlib.sha256(nuevo).hexdigest(), "tamano": len(nuevo)}
(WEB / "Downloads/ccpdf/version.json").write_text(json.dumps({
    "producto": "CCpdf", "version": "1.6.0", "fecha": "2026-12-01",
    "notas": ["Proteger PDFs con contraseña", "Imágenes a PDF"],
    "archivos": {"linux": archivo, "windows": archivo, "macos": archivo}}), encoding="utf-8")
os.environ["CCPDF_URL_ACTUALIZACIONES"] = f"{BASE}/version.json"

# Datos de una versión anterior (1.0.x, sin app_version) → deben migrarse al abrir
CONF = Path(tempfile.mkdtemp()) / "config.json"
CONF.write_text(json.dumps({"tema": "enterprise", "idioma": "es",
                            "carpetas": {"compresor": "/mis/comprimidos"}, "version_prefs": 2}),
                encoding="utf-8")
parche = mock.patch("Interfaz.config._ruta_config", lambda: CONF)
parche.start()

APP = Path(tempfile.mkdtemp())
EXE = APP / "CCpdf"
EXE.write_bytes(b"CCPDF-1.5.0-BINARIO")
os.chmod(EXE, 0o755)

from Interfaz import actualizador as ACT
mock.patch.object(ACT, "ejecutable_actual", return_value=str(EXE)).start()
from Interfaz import app as A
from Interfaz import migracion as M

check(A._MIGRACION["cambio"] and A._MIGRACION["respaldo"], "al abrir, migra los datos de la versión anterior")
datos = json.loads(CONF.read_text(encoding="utf-8"))
check(datos["carpetas"]["compresor"] == "/mis/comprimidos" and datos["app_version"] == A.APP_VERSION,
      "conserva la carpeta del usuario y marca la versión")

dialogos = []
# Todos los diálogos se interceptan durante la prueba (la app programa sola un
# _post_arranque a los 1,5 s; ningún diálogo real debe quedar esperando un clic).
respuesta = {"si": False}
for _k in ("showinfo", "showwarning", "showerror"):
    mock.patch.object(A.messagebox, _k,
                      lambda *a, _k=_k, **k: dialogos.append((_k.replace("show", ""), a))).start()
mock.patch.object(A.messagebox, "askyesno",
                  lambda *a, **k: dialogos.append(("pregunta", a)) or respuesta["si"]).start()
app = A.CCPdfApp()
app.update()


def bombear(cond, limite=20):
    t = time.time()
    while not cond() and time.time() - t < limite:
        app.update()
        time.sleep(0.02)
    for _ in range(5):
        app.update()


# Aviso de migración + búsqueda automática al arrancar (con versión nueva disponible)
app._post_arranque()
bombear(lambda: any(d[0] == "pregunta" for d in dialogos))
check(any(d[0] == "info" and "conservaron" in d[1][1] for d in dialogos),
      "avisa que los datos se conservaron tras actualizar")
check(any(d[0] == "pregunta" and "1.6.0" in d[1][1] for d in dialogos),
      "al abrir, avisa que hay versión nueva (1.6.0)")
check(A._PREFS.get("ultima_comprobacion"), "anota la fecha de la búsqueda automática")
bombear(lambda: False, limite=2)        # deja que corra también el _post_arranque automático
dialogos.clear()
app._post_arranque()
bombear(lambda: False, limite=1.5)
check(not dialogos, "no repite el aviso de datos ni vuelve a buscar el mismo día")

# Pestaña Actualizaciones
app._abrir_config(pestana="actualizaciones")
app.update()
ui = app._ui_act
ui["buscar"]()
bombear(lambda: ui["estado"]["info"] is not None)
info = ui["estado"]["info"]
check(info and info.hay_nueva and "1.6.0" in ui["lbl"].cget("text"), f"muestra la versión nueva ({ui['lbl'].cget('text')})")
check("Proteger PDFs" in ui["notas"].get("1.0", "end"), "muestra las novedades")
check(ui["btn_instalar"].winfo_ismapped(), "ofrece «Descargar e instalar»")

respaldos_antes = len(M.listar_respaldos())
respuesta["si"] = True
ui["btn_instalar"].invoke()
bombear(lambda: "instalado" in ui["lbl"].cget("text") or "⚠" in ui["lbl"].cget("text"), limite=30)
check("instalado" in ui["lbl"].cget("text"), f"descarga e instala ({ui['lbl'].cget('text')})")
check(EXE.read_bytes() == nuevo, "el ejecutable es ahora la versión nueva")
check((APP / "CCpdf.anterior").read_bytes() == b"CCPDF-1.5.0-BINARIO", "la versión anterior queda guardada")
check(len(M.listar_respaldos()) == respaldos_antes + 1, "respalda los datos antes de actualizar")
check(not (APP / ".ccpdf-actualizacion").exists(), "no deja archivos temporales de la descarga")
check(ui["btn_reiniciar"].winfo_ismapped(), "ofrece «Reiniciar ahora»")

lanzado = []
with mock.patch.object(ACT, "reiniciar", lambda e=None: lanzado.append(e)), \
     mock.patch.object(app, "_al_cerrar", lambda: lanzado.append("cerrar")):
    ui["btn_reiniciar"].invoke()
check(lanzado == [str(EXE), "cerrar"], "Reiniciar abre la versión nueva y cierra la actual")

# Archivo alterado en el servidor: no se instala
(WEB / "Downloads/ccpdf/CCpdf-1.6.0-linux").write_bytes(b"alterado" + nuevo[8:])
EXE.write_bytes(b"CCPDF-1.5.0-BINARIO")
ui["buscar"]()
ui["estado"]["info"] = None
bombear(lambda: ui["estado"]["info"] is not None)
ui["btn_instalar"].invoke()
bombear(lambda: "⚠" in ui["lbl"].cget("text"), limite=30)
check("SHA-256" in ui["lbl"].cget("text") and EXE.read_bytes() == b"CCPDF-1.5.0-BINARIO",
      "si el archivo no coincide con su SHA-256, no se instala")

app.destroy()
srv.shutdown()
parche.stop()
sys.exit(0 if ok else 1)
