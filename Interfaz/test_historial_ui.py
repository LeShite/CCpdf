"""Prueba de punta a punta en la interfaz: comparar dos PDFs, que quede en el
historial, deshacer, rehacer y restaurar (necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_historial_ui
Usa una carpeta de configuración temporal: no toca el historial real.
"""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

CONF = Path(tempfile.mkdtemp()) / "config.json"
parche = mock.patch("Interfaz.config._ruta_config", lambda: CONF)
parche.start()

from Interfaz import app as A
from Interfaz import historial as H

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


T = tempfile.mkdtemp()


def hacer(ruta, texto):
    c = canvas.Canvas(ruta, pagesize=A4)
    c.drawString(60, 780, texto)
    c.showPage()
    c.save()


a, b = os.path.join(T, "v1.pdf"), os.path.join(T, "v2.pdf")
hacer(a, "El precio es 500")
hacer(b, "El precio es 750")
contenido_a = open(a, "rb").read()

app = A.CCPdfApp()
app.update()
check("comparar" in app._vistas and "historial" in app._vistas, "existen las vistas Comparar e Historial")
check(app._hist_entradas == [], "historial vacío")
check(app.opt_retencion.get() == "1 mes (recomendado)", "retención por defecto: 1 mes (recomendado)")

app.mostrar_vista("comparar")
app._enrutar_soltados([a, b])
check(app._cmp_a.get() == a and app._cmp_b.get() == b, "soltar 2 PDFs llena A y B")


def esperar_fin(limite=60):
    t = time.time()
    while app._procesando and time.time() - t < limite:
        app.update()
        time.sleep(0.05)
    for _ in range(10):
        app.update()


with mock.patch.object(A.messagebox, "askyesno", return_value=False), \
     mock.patch.object(A.messagebox, "showinfo"), \
     mock.patch.object(A.messagebox, "showwarning"), \
     mock.patch.object(A.messagebox, "showerror") as err:
    app._iniciar_comparacion()
    esperar_fin()
    check(not err.called, "la comparación termina sin error")

entradas = H.cargar()
check(len(entradas) == 1 and entradas[0]["modulo"] == "comparar", "queda registrada en el historial")
e = entradas[0]
informe = e["salidas"][0] if e["salidas"] else ""
check(os.path.isfile(informe) and "Comparacion_v1_vs_v2" in informe, "detecta el informe generado")
check(len(e["versiones"]) == 2, "guardó copia de los 2 PDFs de entrada")
check(app._hist_listbox.size() == 1, "aparece en la lista del historial")

app.mostrar_vista("historial")
app._hist_listbox.selection_set(0)
app._hist_mostrar_sel()
check(str(app.btn_hist_deshacer.cget("state")) == "normal", "botón Deshacer activo")

with mock.patch.object(A.messagebox, "askyesno", return_value=True), \
     mock.patch.object(A.messagebox, "showinfo"), \
     mock.patch.object(A, "abrir_carpeta"):
    app._hist_deshacer()
    check(not os.path.exists(informe), "Deshacer retira el informe")
    app._hist_listbox.selection_set(0)
    app._hist_mostrar_sel()
    check(str(app.btn_hist_rehacer.cget("state")) == "normal", "botón Rehacer activo")
    app._hist_rehacer()
    check(os.path.exists(informe), "Rehacer lo devuelve")

    os.remove(a)
    app._hist_listbox.selection_set(0)
    app._hist_restaurar()
    check(os.path.exists(a) and open(a, "rb").read() == contenido_a,
          "Restaurar recupera el PDF de entrada borrado")

app._hist_cambiar_retencion("1 año (no recomendado: ocupa mucho espacio)")
check(A._PREFS["temporales_dias"] == 365 and "No recomendado" in app.lbl_ret_aviso.cget("text"),
      "1 año: se guarda y avisa que no es recomendado")
app._hist_cambiar_retencion("1 mes (recomendado)")

app.var_hist_activo.set(False)
app._hist_guardar_prefs()
check(A._PREFS["historial_activo"] is False and A._PREFS["temporales_activo"] is False,
      "sin historial se desactivan también los temporales")
app.var_hist_activo.set(True)
app.var_tmp_activo.set(True)
app._hist_guardar_prefs()

app.destroy()
parche.stop()
sys.exit(0 if ok else 1)
