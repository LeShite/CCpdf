"""Prueba del idioma en la interfaz y de que Configuración siempre se vea
(necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_idioma_interfaz
Arranca la app en inglés con una configuración temporal.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest import mock

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

CONF = Path(tempfile.mkdtemp()) / "config.json"
CONF.write_text(json.dumps({"idioma": "en", "version_prefs": 2}), encoding="utf-8")
parche = mock.patch("Interfaz.config._ruta_config", lambda: CONF)
parche.start()

import customtkinter as ctk
from Interfaz import app as A
from Interfaz import config as C

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


# Toda clave usada con T() tiene traducción en los dos idiomas
src = open(A.__file__, encoding="utf-8").read()
usadas = set(re.findall(r'\bT(?:_btn)?\(\s*"([a-z_0-9]+)"', src))
for cod in ("es", "en"):
    faltan = sorted(k for k in usadas if k not in C.IDIOMAS[cod])
    check(not faltan, f"todas las claves usadas existen en '{cod}'" + (f": {faltan}" if faltan else ""))

check(A.MODULO_POR_CLAVE["historial"].titulo == "History", "módulo Historial en inglés")
check(A.MODULO_POR_CLAVE["comparar"].titulo == "Compare", "módulo Comparar en inglés")
check(A.MODULO_POR_CLAVE["metadatos"].titulo == "Metadata", "módulo Metadatos en inglés")
check(A.T_btn("explorar", "Explorar") == "Browse", "botón Explorar sin emoji y traducido")

app = A.CCPdfApp()
app.update()

# El pie con Configuración debe verse aunque la lista de módulos no quepa
app.geometry("1100x600")
for _ in range(5):
    app.update()
cfg = [w for w in app.sidebar.winfo_children()]
pie = next(w for w in cfg if any(isinstance(h, A.NavItem) for h in w.winfo_children()))
y_pie = pie.winfo_rooty() + pie.winfo_height()
y_ven = app.winfo_rooty() + app.winfo_height()
check(pie.winfo_ismapped() and y_pie <= y_ven + 1, "Configuración visible con ventana de 600 px de alto")

with mock.patch.object(A.messagebox, "showinfo"):
    app._abrir_config()
    app.update()
dlg = next(w for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel))
tabs = next(h for h in dlg.winfo_children() if isinstance(h, ctk.CTkTabview))
nombres = " ".join(tabs._tab_dict)
check(all(p in nombres for p in ("Folders", "Appearance", "Updates", "About")),
      f"pestañas de Configuración en inglés ({nombres})")
menus = []


def recoger_menus(w):
    for h in w.winfo_children():
        if isinstance(h, ctk.CTkOptionMenu):
            menus.append(list(h.cget("values")))
        recoger_menus(h)


recoger_menus(dlg)
check(any("Dark" in v and "Enterprise (default)" in v for v in menus),
      "los nombres de los temas salen en inglés (etiqueta_tema)")
dlg.destroy()

app.mostrar_vista("compresor")
app.update()
textos = []


def recoger(w):
    for h in w.winfo_children():
        if isinstance(h, ctk.CTkLabel):
            textos.append(h.cget("text"))
        recoger(h)


recoger(app._vistas["compresor"])
check(C.IDIOMAS["en"]["mod_compresor_sub"] in textos, "se muestra la ayuda del módulo (mod_*_sub)")

app.destroy()
parche.stop()
sys.exit(0 if ok else 1)
