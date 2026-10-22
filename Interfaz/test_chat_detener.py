"""El botón "⏹ Detener" del asistente no hacía nada: con una petición en curso el campo de
texto está vacío (se vacía al enviar) y _chat_enviar salía por "texto vacío" antes de
mirar si había una petición en curso. Uso: python3 test_chat_detener.py

No abre ninguna ventana: llama a CCPdfApp._chat_enviar con un "self" falso. Si tkinter o
customtkinter no están instalados (servidor sin entorno gráfico) usa sustitutos vacíos."""
import os
import sys
import types

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


class Entrada:
    def __init__(self, texto=""): self.texto = texto
    def get(self): return self.texto
    def delete(self, *a): self.texto = ""


class Boton:
    def __init__(self): self.cfg = {}
    def configure(self, **k): self.cfg.update(k)


class Asistente:
    def __init__(self): self.cancelado = 0
    def cancelar(self): self.cancelado += 1


def crear_app(ocupado, texto):
    app = types.SimpleNamespace(_chat_ocupado=ocupado, _chat_entry=Entrada(texto),
                                _btn_chat_enviar=Boton(), _asistente=Asistente(), escrito=[])
    app._chat_append = lambda t: app.escrito.append(t)
    app._chat_hilo = lambda t: None
    app._chat_detener = lambda: APP.CCPdfApp._chat_detener(app)
    return app


def main() -> int:
    APP._HAY_ASISTENTE = True
    hilos = []

    class HiloFalso:
        def __init__(self, target=None, args=(), daemon=None): hilos.append(args)
        def start(self): pass
    APP.threading = types.SimpleNamespace(Thread=HiloFalso)

    casos = []

    # 1. petición en curso, campo vacío (lo normal): Detener debe cancelar
    app = crear_app(True, "")
    APP.CCPdfApp._chat_enviar(app)
    casos.append(("en curso + campo vacío -> cancela", app._asistente.cancelado == 1
                  and app._btn_chat_enviar.cfg.get("state") == "disabled" and not hilos))

    # 2. petición en curso y texto escrito: también detiene, sin lanzar otra petición
    app = crear_app(True, "otra pregunta")
    APP.CCPdfApp._chat_enviar(app)
    casos.append(("en curso + texto -> cancela y no envía", app._asistente.cancelado == 1
                  and not hilos and app._chat_entry.texto == "otra pregunta"))

    # 3. libre y campo vacío: no hace nada
    app = crear_app(False, "   ")
    APP.CCPdfApp._chat_enviar(app)
    casos.append(("libre + campo vacío -> nada", app._asistente.cancelado == 0 and not hilos
                  and not app.escrito and app._chat_ocupado is False))

    # 4. libre con texto: envía (el botón pasa a "Detener")
    app = crear_app(False, "hola")
    APP.CCPdfApp._chat_enviar(app)
    casos.append(("libre + texto -> envía", len(hilos) == 1 and app._chat_ocupado is True
                  and app._chat_entry.texto == "" and "Detener" in app._btn_chat_enviar.cfg.get("text", "")))

    fallos = 0
    for nombre, bien in casos:
        fallos += not bien
        print(f"  {nombre:42s} -> {'OK' if bien else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
