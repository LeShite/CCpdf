"""Modo híbrido: CIPA con una API externa falsa (servidor local compatible con OpenAI).
Uso: python3 test_api_externa.py"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.CIPA import CIPA, configurar_modo
from Motores.CIPA.config import PROVEEDORES_API

visto = []


class Falsa(BaseHTTPRequestHandler):
    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        visto.append((self.path, self.headers.get("Authorization"), cuerpo))
        if self.headers.get("Authorization") != "Bearer clave-ok":
            self.send_response(401); self.end_headers(); self.wfile.write(b'{"error":"clave"}'); return
        if cuerpo.get("tools") and not any(m["role"] == "tool" for m in cuerpo["messages"]):
            msg = {"role": "assistant", "content": None, "tool_calls": [
                {"id": "x", "type": "function", "function": {"name": "info_documento", "arguments": "{}"}}]}
        else:
            msg = {"role": "assistant", "content": "texto limpio"}
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({"choices": [{"message": msg}]}).encode())

    def log_message(self, *a): pass


srv = HTTPServer(("127.0.0.1", 0), Falsa)
threading.Thread(target=srv.serve_forever, daemon=True).start()
PROVEEDORES_API["deepseek"]["url"] = f"http://127.0.0.1:{srv.server_port}"

# sin clave: error claro, y no se llama a la red
configurar_modo("api", "deepseek", "")
try:
    CIPA().cargar_modelo("limpieza"); raise SystemExit("FALLO: debía exigir la clave")
except RuntimeError as e:
    assert "clave" in str(e).lower() and not visto, e

# con clave: genera
configurar_modo("api", "deepseek", "clave-ok")
c = CIPA()
assert c.cargar_modelo("limpieza") and c.estado()["backend_activo"] == "api"
assert c._backend.generar("hola") == "texto limpio"
assert visto[-1][0] == "/chat/completions" and visto[-1][2]["messages"][0]["content"] == "hola"

# clave mala: error sin filtrar la clave
configurar_modo("api", "deepseek", "mala")
c = CIPA(); c.cargar_modelo("limpieza")
try:
    c._backend.generar("x"); raise SystemExit("FALLO: debía fallar")
except RuntimeError as e:
    assert "401" in str(e) and "mala" not in str(e)

# herramientas: se convierte el historial al formato OpenAI y la respuesta al de Ollama
configurar_modo("api", "deepseek", "clave-ok")
c = CIPA(); c.cargar_modelo("limpieza")
r = c._backend.chat_con_tools([{"role": "user", "content": "info"}], [{"type": "function"}])
tc = r["message"]["tool_calls"][0]["function"]
assert tc["name"] == "info_documento" and tc["arguments"] == {}
r = c._backend.chat_con_tools([
    {"role": "user", "content": "info"},
    {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "info_documento", "arguments": {"a": 1}}}]},
    {"role": "tool", "name": "info_documento", "content": "datos"}], [{"type": "function"}])
m = visto[-1][2]["messages"]
assert m[1]["tool_calls"][0]["id"] == m[2]["tool_call_id"] and m[1]["tool_calls"][0]["function"]["arguments"] == '{"a": 1}'
assert r["message"]["content"] == "texto limpio"

# por defecto, local
configurar_modo()
assert CIPA()._backend_api is None
print("RESULTADO: OK")
