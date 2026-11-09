"""Prueba de BUG-011 / BUG-018: hilos del visor (necesita pantalla).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_visor_hilos
Corre dentro de mainloop(), como la app real.
"""
import os
import sys
import tempfile
import threading
import time
from unittest import mock

if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
    print("SKIP sin pantalla (DISPLAY)")
    sys.exit(0)

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from Interfaz import visor_pdf as V

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg, flush=True)
    ok = ok and cond


T = tempfile.mkdtemp()


def hacer(ruta, n, txt):
    c = canvas.Canvas(ruta, pagesize=A4)
    for i in range(n):
        c.setFont("Helvetica", 11)
        for l in range(45):
            c.drawString(40, 800 - l * 17, f"{txt} pagina {i + 1} linea {l} " + "relleno " * 6)
        for k in range(150):
            c.circle(50 + (k * 7) % 500, 100 + (k * 13) % 600, 20)
        c.showPage()
    c.save()


grande = os.path.join(T, "grande.pdf")
hacer(grande, 300, "GRANDE")
chico = os.path.join(T, "chico.pdf")
hacer(chico, 3, "CHICO")

errores_hilo = []
threading.excepthook = lambda a: errores_hilo.append(f"{a.exc_type.__name__}: {a.exc_value}")

root = ctk.CTk()
root.geometry("900x700")
v = V.VisorPDF(root)
v.pack(fill="both", expand=True)
msgs = []
for k in ("showinfo", "showwarning", "showerror"):
    mock.patch.object(V.messagebox, k,
                      lambda *a, _k=k, **kw: msgs.append((_k, a[1] if len(a) > 1 else ""))).start()

pasos = []


def siguiente(ms=10):
    if pasos:
        root.after(ms, pasos.pop(0))
    else:
        root.after(ms, root.quit)


def esperar(cond, despues, limite=30.0, t0=None):
    t0 = t0 or time.time()
    if cond() or time.time() - t0 > limite:
        despues()
    else:
        root.after(20, lambda: esperar(cond, despues, limite, t0))


def buscar(termino):
    v.entry_buscar.delete(0, "end")
    v.entry_buscar.insert(0, termino)
    v._buscar()


# 1. Búsqueda que termina bien: encuentra la página 250 y salta a ella
def p1():
    v.cargar(grande)
    msgs.clear()
    buscar("GRANDE pagina 250 linea 3")
    esperar(lambda: msgs, p1b)


def p1b():
    check(msgs and "250" in msgs[0][1], f"la búsqueda encuentra la página 250 ({msgs[:1]})")
    check(v.pagina == 249, f"y salta a ella (página {v.pagina + 1})")
    check(v.btn_buscar.cget("text") == "🔎", "el botón vuelve a 🔎 al terminar")
    siguiente()


# 2. Abrir otro PDF durante la búsqueda: el resultado viejo se descarta
def p2():
    v.cargar(grande)
    msgs.clear()
    buscar("GRANDE pagina 299 linea")
    root.after(30, lambda: v.cargar(chico))
    root.after(8000, p2b)


def p2b():
    check(not msgs, f"abrir otro PDF descarta la búsqueda en curso (mensajes: {msgs})")
    check(os.path.basename(v.ruta) == "chico.pdf" and v.pagina == 0,
          "el PDF nuevo queda en su página 1")
    check(v.btn_buscar.cget("text") == "🔎", "el botón de buscar no se queda en ⏳")
    siguiente()


# 3. Una búsqueda nueva cancela la anterior
def p3():
    v.cargar(grande)
    msgs.clear()
    buscar("GRANDE pagina 299 linea")
    root.after(20, lambda: buscar("GRANDE pagina 7 linea 2"))
    esperar(lambda: msgs, p3b)


def p3b():
    root.after(1500, lambda: (
        check(len(msgs) == 1 and "7" in msgs[0][1] and "299" not in msgs[0][1],
              f"solo responde la última búsqueda ({msgs})"),
        siguiente()))


# 4. Pasar 40 páginas seguidas: se dibuja la última, no las 40
estado = {}


def p4():
    v.cargar(grande)
    esperar(lambda: v._img_ref is not None, p4b)


def p4b():
    llamadas = []
    orig = v._doc.renderizar

    def contar(idx, **kw):
        llamadas.append(idx)
        return orig(idx, **kw)

    v._doc.renderizar = contar
    estado.update(llamadas=llamadas, hilos=threading.active_count())
    for _ in range(40):
        v.pagina_siguiente()
    estado["hilos_pico"] = threading.active_count()
    esperar(lambda: llamadas and llamadas[-1] == 40 and v.entry_pagina.get() == "41", p4c)


def p4c():
    ll = estado["llamadas"]
    check(len(ll) <= 3, f"40 cambios de página → {len(ll)} render(s), no 40")
    check(ll and ll[-1] == 40, "se dibuja la página final (41)")
    check(estado["hilos_pico"] <= estado["hilos"], "no se crean hilos nuevos por cada página")
    siguiente()


# 5. Buscar mientras se pasan páginas: sin errores y resultado correcto
def p5():
    msgs.clear()
    buscar("GRANDE pagina 150 linea 1")
    for i in range(0, 60, 3):
        root.after(i * 5, v.pagina_siguiente)
    esperar(lambda: msgs, p5b)


def p5b():
    check(msgs and msgs[0][0] == "showinfo" and "150" in msgs[0][1],
          f"buscar mientras se navega: resultado correcto ({msgs[:1]})")
    siguiente()


# 6. Cerrar la ventana con un render en curso: ningún error en los hilos
def p6():
    v.ir_a(200)
    v.ir_a(201)
    root.after(1, root.quit)


pasos.extend([p1, p2, p3, p4, p5, p6])
siguiente(300)
root.mainloop()
root.destroy()
time.sleep(1.0)
check(not errores_hilo, f"cerrar con trabajo en curso no deja errores en los hilos {errores_hilo}")
sys.exit(0 if ok else 1)
