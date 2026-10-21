"""El asistente no inventa archivos. Uso: python3 test_asistente.py (sin Ollama: prueba atajos y filtros)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.CIPA import asistente as A

d = tempfile.mkdtemp(); os.makedirs(d + "/sub")
open(d + "/Órdenes_de_Compra-2026.pdf", "wb").close(); open(d + "/sub/otro.pdf", "wb").close()
open(d + "/ordenes.xlsx", "wb").close()
A._detectar_carpetas_comunes = lambda: {"descargas": d}
a = A.AsistenteCIPA()

r = a._detectar_atajo("busca un pdf llamado ordenes de compra en descargas")
assert d + "/Órdenes_de_Compra-2026.pdf" in r and "xlsx" not in r, r
assert "No encontré" in a._detectar_atajo("busca un pdf llamado facturas en descargas")
assert "otro.pdf" in a._detectar_atajo("encuentra el pdf otro")          # subcarpeta
for q in ("quien eres", "como funcionas", "que puedes hacer"):
    assert "Soy CIPA" in a._detectar_atajo(q), q
a._detectar_atajo("busca un pdf llamado ordenes de compra en descargas")
assert a._ultimo_encontrado.endswith("Compra-2026.pdf")
# ruta inventada -> se bloquea; ruta real -> pasa
assert "No puedo confirmar" in a._sin_rutas_inventadas("Aquí tienes: /home/iker/Descargas/ordenes de compra.pdf.")
real = f"Aquí: {d}/sub/otro.pdf listo"
assert a._sin_rutas_inventadas(real) == real
assert a._sin_rutas_inventadas("Hola, ¿en qué te ayudo?") == "Hola, ¿en qué te ayudo?"
assert "Soy CIPA" in a._detectar_atajo("como funcinas")
assert "Sí: CCpdf procesa" in a._detectar_atajo("¿Es seguro usar CCpdf con documentos confidenciales?")
assert "Aún no" in A.AsistenteCIPA()._detectar_atajo("y traelo")
print("RESULTADO: OK")
