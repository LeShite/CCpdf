"""Comprimir → «Mejoras extras»: la tarjeta para instalar Ghostscript sale solo si no está
instalado, y en macOS el usuario puede ocultarla para siempre (se guarda en las preferencias
y se vuelve a mostrar desde Configuración → Apariencia). Uso: python3 test_mejoras_extras.py

No abre ninguna ventana: llama a los métodos de CCPdfApp con un "self" falso. Si tkinter o
customtkinter no están instalados (servidor sin entorno gráfico) usa sustitutos vacíos."""
import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sin_tkinter():
    from importlib.util import find_spec
    return find_spec("tkinter") is None or find_spec("customtkinter") is None


if _sin_tkinter():
    class _Cualquiera:
        def __init__(self, *a, **k): pass
        def __getattr__(self, n): return lambda *a, **k: _Cualquiera()

    for nombre in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.font",
                   "customtkinter", "PIL.ImageTk"):
        m = types.ModuleType(nombre)
        m.__getattr__ = lambda n: _Cualquiera
        sys.modules[nombre] = m

from Interfaz import app as APP  # noqa: E402
from Interfaz import config as CFG  # noqa: E402


class Widget:
    def __init__(self): self.visible = False
    def pack(self, **kw): self.visible = True
    def pack_forget(self): self.visible = False
    def configure(self, **kw): pass


class Var:
    def __init__(self, v): self.v = v
    def get(self): return self.v
    def set(self, v): self.v = v


def app_falsa():
    a = types.SimpleNamespace(
        _radios_motor_comp={"ghostscript": Widget(), "interno": Widget()},
        _card_extras_comp=Widget(), var_motor_comp=Var("auto"),
        lbl_comp_motor_info=Widget(), btn_run_comp=Widget())
    a._comp_actualizar_info_motor = lambda: APP.CCPdfApp._comp_actualizar_info_motor(a)
    return a


def main() -> int:
    fallos = 0

    def check(nombre, bien):
        nonlocal fallos
        fallos += not bien
        print(f"  {nombre:60s} -> {'OK' if bien else 'FALLA'}")

    avisos, guardados = [], []
    guardar_real = CFG.guardar          # APP.cfg_prefs es este mismo módulo
    APP._info_motor = lambda: "Motor: interno"
    APP.messagebox.showinfo = lambda titulo, texto, **k: avisos.append(texto)
    APP.cfg_prefs.guardar = lambda prefs: guardados.append(dict(prefs)) or True

    def preparar(gs, ocultable, oculta):
        APP._buscar_ghostscript = lambda: "/usr/bin/gs" if gs else None
        APP.EXTRAS_GS_OCULTABLE = ocultable
        APP._PREFS.clear()
        APP._PREFS.update(CFG._prefs_vacias(), ocultar_mejoras_gs=oculta)
        a = app_falsa()
        a._comp_actualizar_info_motor()
        return a

    a = preparar(gs=False, ocultable=True, oculta=False)
    check("macOS sin Ghostscript: tarjeta visible", a._card_extras_comp.visible)
    check("macOS sin Ghostscript: sin opción de motor «Ghostscript»",
          not a._radios_motor_comp["ghostscript"].visible)

    APP.CCPdfApp._comp_ocultar_extras(a)
    check("pulsar Ocultar: la tarjeta desaparece", not a._card_extras_comp.visible)
    check("pulsar Ocultar: se guarda en las preferencias",
          bool(guardados) and guardados[-1]["ocultar_mejoras_gs"] is True)
    check("pulsar Ocultar: avisa de cómo volver a mostrarla",
          bool(avisos) and "Configuración → Apariencia" in avisos[-1])

    a = preparar(gs=False, ocultable=True, oculta=True)
    check("macOS, oculta y al volver a abrir: sigue oculta", not a._card_extras_comp.visible)

    a = preparar(gs=True, ocultable=True, oculta=False)
    check("con Ghostscript: sin tarjeta y con la opción de motor",
          not a._card_extras_comp.visible and a._radios_motor_comp["ghostscript"].visible)

    a = preparar(gs=False, ocultable=False, oculta=True)
    check("Windows/Linux: la preferencia no oculta la tarjeta", a._card_extras_comp.visible)

    APP.cfg_prefs.guardar = lambda prefs: False
    a = preparar(gs=False, ocultable=True, oculta=False)
    APP.CCPdfApp._comp_ocultar_extras(a)
    check("si no se puede guardar: se oculta y avisa de que volverá",
          not a._card_extras_comp.visible and "no se pudo guardar" in avisos[-1])

    # la preferencia sobrevive a guardar/cargar; un valor que no es bool se ignora
    CFG.guardar = guardar_real
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "config.json"
        CFG._ruta_config = lambda: ruta
        CFG.guardar({**CFG._prefs_vacias(), "ocultar_mejoras_gs": True})
        check("guardar → cargar conserva «ocultar»", CFG.cargar()["ocultar_mejoras_gs"] is True)
        ruta.write_text('{"version_prefs": 2, "ocultar_mejoras_gs": "si"}', encoding="utf-8")
        check("un valor no booleano se ignora", CFG.cargar()["ocultar_mejoras_gs"] is False)

    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
