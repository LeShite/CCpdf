"""
api_externa.py — Backend CIPA con una API externa (DeepSeek, Gemini).

Ambos proveedores ofrecen un endpoint compatible con OpenAI
(`POST {url}/chat/completions`), así que un solo backend sirve para los dos.

⚠ PRIVACIDAD: a diferencia de Ollama, este backend ENVÍA el texto de los
documentos al proveedor. Nunca se activa por defecto; la interfaz exige
elegirlo de forma explícita y avisa de ello.
"""
import json
import urllib.error
import urllib.request
from typing import Iterator

from .base import BackendBase
from ..config import PROVEEDORES_API

TIMEOUT_API = 120


class BackendAPIExterna(BackendBase):
    def __init__(self, proveedor: str, clave: str):
        if proveedor not in PROVEEDORES_API:
            raise ValueError(f"Proveedor desconocido: {proveedor}")
        self._proveedor = proveedor
        self._url = PROVEEDORES_API[proveedor]["url"].rstrip("/")
        self._modelo = PROVEEDORES_API[proveedor]["modelo"]
        self._clave = (clave or "").strip()
        self._params: dict = {}
        self._listo = False

    # ─── Carga: aquí solo se valida que haya clave ───
    def cargar(self, ruta_modelo: str = "", **kwargs) -> bool:
        if not self._clave:
            raise RuntimeError(
                f"Falta la clave de API de {PROVEEDORES_API[self._proveedor]['nombre']} "
                "(Configuración → IA).")
        self._listo = True
        return True

    def descargar(self) -> None:
        self._listo = False

    def disponible(self) -> bool:
        return self._listo

    # ─── Generación ───
    def generar(self, prompt: str, **kwargs) -> str:
        return self._chat([{"role": "user", "content": prompt}], kwargs)["content"].strip()

    def generar_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        # shortcut: sin streaming real, devuelve todo de una vez; mejorar si se quiere progreso en vivo.
        yield self.generar(prompt, **kwargs)

    def chat_con_tools(self, mensajes: list, tools: list, timeout: int = TIMEOUT_API) -> dict:
        """Misma forma de respuesta que BackendOllama.chat_con_tools."""
        return {"message": self._chat(_a_openai(mensajes), {}, tools or None, timeout)}

    # ─── Interno ───
    def _chat(self, mensajes: list, opciones: dict, tools=None, timeout: int = TIMEOUT_API) -> dict:
        if not self.disponible():
            raise RuntimeError("API no lista. Llama primero a cargar().")
        payload = {
            "model": self._modelo,
            "messages": mensajes,
            "temperature": opciones.get("temperature", 0.2),
            "max_tokens": opciones.get("max_tokens", 2048),
        }
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            self._url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self._clave},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                msg = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            # el cuerpo del error no incluye la clave; la cabecera nunca se imprime
            detalle = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"La API respondió {e.code}: {detalle}")
        except Exception as e:
            raise RuntimeError(f"Error llamando a la API externa: {e}")
        msg["content"] = msg.get("content") or ""
        for tc in msg.get("tool_calls") or []:
            args = tc.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                try:
                    tc["function"]["arguments"] = json.loads(args or "{}")
                except json.JSONDecodeError:
                    tc["function"]["arguments"] = {}
        return msg


def _a_openai(mensajes: list) -> list:
    """El historial del asistente usa el formato de Ollama (argumentos como
    dict, mensajes `tool` sin id). OpenAI exige ids y argumentos en JSON."""
    salida, pendientes, n = [], [], 0
    for m in mensajes:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            llamadas = []
            for tc in m["tool_calls"]:
                n += 1
                pendientes.append(f"call_{n}")
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                llamadas.append({"id": f"call_{n}", "type": "function", "function": {
                    "name": fn.get("name", ""),
                    "arguments": args if isinstance(args, str) else json.dumps(args)}})
            salida.append({"role": "assistant", "content": m.get("content") or "",
                           "tool_calls": llamadas})
        elif m.get("role") == "tool":
            salida.append({"role": "tool", "content": m.get("content", ""),
                           "tool_call_id": pendientes.pop(0) if pendientes else "call_0"})
        else:
            salida.append(m)
    return salida
