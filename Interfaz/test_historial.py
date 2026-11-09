"""Prueba del historial y de los temporales (deshacer / rehacer / restaurar).

Ejecutar desde la raíz del repo:  python -m Interfaz.test_historial
Usa una carpeta de configuración temporal: no toca el historial real.
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pypdf import PdfWriter

ok = True


def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg)
    ok = ok and cond


CONF = Path(tempfile.mkdtemp()) / "config.json"
with mock.patch("Interfaz.config._ruta_config", lambda: CONF):
    from Interfaz import historial as H
    from Interfaz import temporales as TMP

    T = tempfile.mkdtemp()

    def pdf(nombre, autor="x"):
        p = os.path.join(T, nombre)
        w = PdfWriter()
        w.add_blank_page(100, 100)
        w.add_metadata({"/Author": autor})
        w.write(p)
        return p

    check(H.cargar() == [], "historial vacío al empezar")

    a, b = pdf("a.pdf", "A"), pdf("b.pdf", "B")
    contenido_a = open(a, "rb").read()

    # Simula una acción: guarda versiones, "procesa" y detecta salidas
    t0 = time.time()
    kwargs = {"archivos": [a, b], "destino": os.path.join(T, "salida")}
    versiones = TMP.guardar_versiones([a, b, a])
    check(len({v["sha"] for v in versiones}) == 2, "no duplica la misma versión")
    os.makedirs(kwargs["destino"])
    out1 = pdf("salida/a_limpio.pdf")
    out2 = pdf("salida/b_limpio.pdf")
    resumen = SimpleNamespace(carpeta_salida=kwargs["destino"], cancelado=False, errores=[],
                              a_texto=lambda: "Archivos: 2 · Limpiados: 2")
    e = H.nueva_entrada("metadatos", "Metadatos", kwargs, resumen)
    e["versiones"] = versiones
    e["salidas"] = H.detectar_salidas(resumen, kwargs, t0)
    check(sorted(e["salidas"]) == sorted([out1, out2]), "detecta los archivos generados")
    check(e["archivos"] == ["a.pdf", "b.pdf"] and e["estado"] == "ok", "datos de la entrada")
    H.agregar(e)
    check(len(H.cargar()) == 1 and H.cargar()[0]["id"] == e["id"], "se guarda en disco")
    if os.name == "posix":
        check(oct(os.stat(H.ruta_historial()).st_mode & 0o777) == "0o600", "permisos 600")

    # Deshacer: las salidas desaparecen pero se pueden recuperar
    check(H.puede_deshacer(e), "se puede deshacer")
    e = H.deshacer(e)
    check(not os.path.exists(out1) and not os.path.exists(out2), "deshacer retira las salidas")
    check(e["deshecho"] and len(e["retirados"]) == 2, "quedan guardadas en temporales")
    check(H.puede_rehacer(e) and not H.puede_deshacer(e), "ahora se puede rehacer")

    e = H.rehacer(e)
    check(os.path.exists(out1) and os.path.exists(out2), "rehacer las devuelve a su sitio")
    check(not e["deshecho"], "estado vuelve a normal")

    # Restaurar original modificado/borrado varios pasos después
    os.remove(a)
    rest = H.restaurar_originales(e)
    check(os.path.exists(a) and open(a, "rb").read() == contenido_a,
          "restaura el original borrado, idéntico")
    rest2 = H.restaurar_originales(e)
    check(all("(restaurado)" in os.path.basename(p) for p in rest2), "no sobrescribe: crea (restaurado)")

    H.actualizar(e)
    check(H.cargar()[0]["deshecho"] is False, "actualizar guarda los cambios")

    # Caducidad: una entrada de hace 40 días pierde sus copias con retención 30
    vieja = dict(e, id="viejo", fecha=(datetime.now() - timedelta(days=40)).isoformat(timespec="seconds"),
                 versiones=[TMP.guardar_versiones([pdf("vieja.pdf", "viejo")])[0]])
    usado_antes = TMP.espacio_usado()
    entradas, liberados = TMP.purgar([e, vieja], dias=30)
    check(entradas[1]["versiones"] == [] and entradas[1].get("temporales_caducados"),
          "purga las copias vencidas")
    check(entradas[0]["versiones"], "conserva las vigentes")
    check(liberados > 0 and TMP.espacio_usado() < usado_antes, "libera espacio")
    check(not H.puede_restaurar(entradas[1]), "una entrada vencida ya no se puede restaurar")

    check(TMP.purgar([e], dias=99999)[0][0]["versiones"], "días fuera de rango se acotan (≤365)")
    check(dict(TMP.OPCIONES_RETENCION)[30].endswith("(recomendado)") and TMP.DIAS_DEFECTO == 30,
          "1 mes recomendado por defecto")

    H.vaciar()
    check(H.cargar() == [], "vaciar el historial")
    # historial dañado no rompe nada
    H.ruta_historial().write_text("{no es json", encoding="utf-8")
    check(H.cargar() == [], "historial dañado se lee como vacío")

sys.exit(0 if ok else 1)
