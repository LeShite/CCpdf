#!/usr/bin/env python3
"""CCpdf — Lanzador. Ejecuta: python3 main.py"""
import os
import sys

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
if DIRECTORIO_ACTUAL not in sys.path:
    sys.path.insert(0, DIRECTORIO_ACTUAL)

# Con ibus/fcitx por XIM, Tk espera al servidor en cada widget nuevo (~0,3 s cada
# uno; la ventana tardaba 87 s en abrir). Va antes de importar Tk.
if sys.platform.startswith("linux"):
    os.environ["XMODIFIERS"] = "@im=none"

from Interfaz.app import CCPdfApp


if __name__ == "__main__":
    CCPdfApp().mainloop()
