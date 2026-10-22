"""Detener con el asistente a medias: si se pulsa mientras el modelo responde, la respuesta
que llega tarde no debe mostrarse ni ejecutar herramientas, y el historial no debe quedar con
un mensaje sin respuesta. Uso: python3 test_asistente_cancelar.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.CIPA.asistente import AsistenteCIPA


class CipaFalsa:
    _backend_nombre = "ollama"
    def backend_instalado(self): return True


class BackendFalso:
    """Responde con tool_calls y, durante la llamada, 'el usuario pulsa Detener'."""
    def __init__(self, asistente, pulsar_detener, con_herramienta=False):
        self.asistente, self.pulsar, self.llamadas = asistente, pulsar_detener, 0
        self.con_herramienta = con_herramienta
    def disponible(self): return True
    def chat_con_tools(self, mensajes, tools):
        self.llamadas += 1
        if self.pulsar:
            self.asistente.cancelar()
        msg = {"role": "assistant", "content": "respuesta tardía"}
        if self.con_herramienta:
            msg["tool_calls"] = [{"function": {"name": "info_documento", "arguments": {}}}]
        return {"message": msg}


def crear(pulsar_detener, con_herramienta=False):
    a = AsistenteCIPA.__new__(AsistenteCIPA)       # sin llamar a __init__ (no consulta Ollama)
    import threading
    a._cipa, a._historial, a._cancelar = CipaFalsa(), [], threading.Event()
    a._system_prompt, a._documento_texto, a._documento_ruta, a._documento_info = "", "", "", {}
    a._backend = BackendFalso(a, pulsar_detener, con_herramienta)
    a.herramientas = 0
    a._ejecutar_tool = lambda nombre, args: setattr(a, "herramientas", a.herramientas + 1) or "ok"
    return a


def main() -> int:
    casos = []
    a = crear(pulsar_detener=True)
    r = a.enviar("hola, qué tal")
    casos.append(("Detener durante la llamada -> '(Cancelado.)'", r == "(Cancelado.)"))
    casos.append(("no deja el mensaje del usuario en el historial", a._historial == []))

    a = crear(pulsar_detener=True, con_herramienta=True)
    r = a.enviar("lee el informe")
    casos.append(("Detener con tool_calls: no ejecuta la herramienta",
                  r == "(Cancelado.)" and a.herramientas == 0 and a._backend.llamadas == 1
                  and a._historial == []))

    a = crear(pulsar_detener=False)
    a._backend.chat_con_tools = lambda mensajes, tools: {"message": {"role": "assistant", "content": "hola"}}
    casos.append(("sin Detener responde normal", a.enviar("hola") == "hola" and len(a._historial) == 2))

    a = crear(pulsar_detener=False)
    a._cancelar.set()                                  # un Detener anterior no debe afectar a la siguiente pregunta
    a._backend.chat_con_tools = lambda mensajes, tools: {"message": {"role": "assistant", "content": "ok"}}
    casos.append(("un Detener anterior no cancela la pregunta siguiente", a.enviar("otra") == "ok"))

    fallos = 0
    for nombre, bien in casos:
        fallos += not bien
        print(f"  {nombre:55s} -> {'OK' if bien else 'FALLA'}")
    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
