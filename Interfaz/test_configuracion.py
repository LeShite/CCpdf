"""Prueba del diálogo de Configuración (necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_configuracion
Abre el diálogo, recorre las pestañas, pulsa cada «Guardar» y comprueba que las
carpetas configuradas se usan en los módulos. Usa una configuración temporal.
"""
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from unittest import mock

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

CONF = Path(tempfile.mkdtemp()) / "config.json"
parche = mock.patch("Interfaz.config._ruta_config", lambda: CONF)
parche.start()

import customtkinter as ctk
from Interfaz import app as A

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


def botones(w):
    for h in w.winfo_children():
        if isinstance(h, ctk.CTkButton):
            yield h
        yield from botones(h)


errores, mensajes = [], []
app = A.CCPdfApp()
app.report_callback_exception = lambda *e: errores.append("".join(traceback.format_exception(*e)))
app.update()

with mock.patch.object(A.messagebox, "showerror", lambda *a, **k: mensajes.append(("error", a))), \
     mock.patch.object(A.messagebox, "showinfo", lambda *a, **k: mensajes.append(("info", a))):
    app._abrir_config()
    app.update()
    dlg = [w for w in app.winfo_children() if isinstance(w, ctk.CTkToplevel)]
    check(len(dlg) == 1, "se abre el diálogo de Configuración")
    tabs = next(h for h in dlg[0].winfo_children() if isinstance(h, ctk.CTkTabview))
    nombres = list(tabs._tab_dict)
    check(len(nombres) == 5, f"5 pestañas ({len(nombres)})")

    # Carpetas: rellenar todas y guardar
    tab_carp = tabs.tab(nombres[0])
    entradas = []

    def buscar_entries(w):
        for h in w.winfo_children():
            if isinstance(h, ctk.CTkEntry):
                entradas.append(h)
            buscar_entries(h)

    buscar_entries(tab_carp)
    check(len(entradas) == 7, f"7 carpetas configurables, incluidas OCR, Metadatos y Comparar ({len(entradas)})")
    carpeta = tempfile.mkdtemp()
    for e in entradas:
        e.delete(0, "end")
        e.insert(0, carpeta)

    guardados = 0
    for n in nombres:
        tabs.set(n)
        app.update()
        for b in botones(tabs.tab(n)):
            if "uardar" in (b.cget("text") or ""):
                b.invoke()
                app.update()
                guardados += 1
    check(guardados == 3, "hay 3 botones Guardar (Carpetas, IA, Apariencia)")
    check(not [m for m in mensajes if m[0] == "error"], "ningún Guardar da error")
    check(not errores, "ninguna excepción en el diálogo" + ("" if not errores else ":\n" + errores[0]))
    dlg[0].destroy()

datos = json.loads(CONF.read_text(encoding="utf-8"))
check(all(datos["carpetas"].get(k) == carpeta for k in
          ("extractor", "fusionador", "divisor", "compresor", "ocr", "metadatos", "comparar")),
      "todas las carpetas quedan guardadas")
check(all(app._carpeta_defecto(k) == carpeta for k in ("ocr", "metadatos", "comparar")),
      "los módulos leen la carpeta configurada")

from Interfaz import actualizador
check(actualizador.URL_MANIFIESTO_DEFECTO.startswith("https://kodesoft.site/")
      and "github" not in actualizador.URL_MANIFIESTO_DEFECTO,
      "el actualizador consulta kodesoft.site, no GitHub")

app.destroy()
parche.stop()
sys.exit(0 if ok else 1)
