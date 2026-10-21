"""Chat con CIPA en la terminal, sin interfaz.

Uso:  python -m Motores.CIPA.chat [--api deepseek|gemini]
      (con --api, la clave se lee de CCPDF_API_KEY y el texto SE ENVÍA al proveedor)
Salir: salir, exit, quit o Ctrl+D.
"""
import os
import sys

from .asistente import AsistenteCIPA
from .nucleo import configurar_modo, ErrorCIPA


def main():
    if "--api" in sys.argv:
        proveedor = sys.argv[sys.argv.index("--api") + 1:][:1] or ["deepseek"]
        configurar_modo("api", proveedor[0], os.environ.get("CCPDF_API_KEY", ""))
    asistente = AsistenteCIPA()
    print("CIPA — escribe tu mensaje (salir / exit para terminar).")
    while True:
        try:
            msg = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if msg.lower() in ("salir", "exit", "quit"):
            break
        if not msg:
            continue
        try:
            print("\nCIPA:", asistente.enviar(msg))
        except ErrorCIPA as e:
            print("\n[Error]", e)
        except Exception as e:
            print("\n[Error inesperado]", e)


if __name__ == "__main__":
    main()
