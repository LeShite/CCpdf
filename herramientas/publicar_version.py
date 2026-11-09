"""
publicar_version.py — Prepara una versión de CCpdf para kodesoft.site.

Genera o actualiza `version.json`, la ÚNICA fuente de la información de
versiones: la lee la app (actualizador) y la lee el script de la web para
regenerar ccpdf.html, la página de descargas y el historial de cambios. Se puede
editar a mano después; este script respeta lo editado (notas e historial de
versiones anteriores).

Uso (desde la raíz del repo):

    python -m herramientas.publicar_version --salida /ruta/a/Downloads/ccpdf \\
        --binario linux=dist/CCpdf [--binario windows=dist/CCpdf.exe]

    Opciones:
      --version 1.5.0           por defecto, APP_VERSION de Interfaz/app.py
      --fecha 2026-11-08        por defecto, hoy
      --url-base URL            URL absoluta de la carpeta (por defecto, relativa al JSON)
      --historial-completo      reconstruye todo el historial desde CHANGELOG.md
      --comprobar               solo valida un version.json existente

Copia cada binario como CCpdf-<versión>-<sistema>[.exe], calcula su SHA-256 y
tamaño, y añade al historial la sección de CHANGELOG.md de esta versión si aún
no estaba. Nunca borra binarios de versiones anteriores (avisa de cuáles hay).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL_BASE = "https://kodesoft.site/Downloads/ccpdf"
PAGINA = "https://kodesoft.site/ccpdf.html"
SISTEMAS = {"linux": "", "windows": ".exe", "macos": ""}
SECCIONES = ("Añadido", "Cambiado", "Corregido", "Eliminado", "Seguridad", "Obsoleto")


def version_app() -> str:
    txt = (RAIZ / "Interfaz" / "app.py").read_text(encoding="utf-8")
    m = re.search(r'^APP_VERSION\s*=\s*"v?([^"]+)"', txt, re.M)
    if not m:
        raise SystemExit("No se encontró APP_VERSION en Interfaz/app.py")
    return m.group(1)


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────
#  CHANGELOG.md → historial
# ─────────────────────────────────────────────────────────────
def leer_changelog(md: str) -> list:
    """[{version, fecha, secciones: {nombre: [items]}}] de las versiones publicadas."""
    versiones, actual, seccion = [], None, None
    for linea in md.splitlines():
        m = re.match(r"^##\s+\[([^\]]+)\](?:\s+-\s+(\d{4}-\d\d-\d\d))?\s*$", linea)
        if m:
            actual = None
            if m.group(2):                       # «Sin publicar» no tiene fecha: se omite
                actual = {"version": m.group(1), "fecha": m.group(2), "secciones": {}}
                versiones.append(actual)
            seccion = None
            continue
        if actual is None:
            continue
        if linea.startswith("### "):
            seccion = linea[4:].strip()
            actual["secciones"].setdefault(seccion, [])
            continue
        if not linea.strip():
            continue
        destino = actual["secciones"].setdefault(seccion or "Cambios", [])
        if re.match(r"^[-*]\s+", linea):
            destino.append(re.sub(r"^[-*]\s+", "", linea).strip())
        elif destino and (linea.startswith("  ") or not destino[-1].endswith((".", ":", ")"))) \
                and not linea.startswith("_"):
            destino[-1] += " " + linea.strip()   # continuación de la viñeta anterior
        else:
            destino.append(linea.strip())        # párrafo suelto (p. ej. notas en cursiva)
    # unir párrafos en cursiva partidos en varias líneas
    for v in versiones:
        for nombre, items in v["secciones"].items():
            unidos = []
            for it in items:
                if unidos and unidos[-1].startswith("_") and not unidos[-1].rstrip().endswith("_"):
                    unidos[-1] += " " + it
                else:
                    unidos.append(it)
            v["secciones"][nombre] = unidos
    return versiones


def sin_markdown(t: str) -> str:
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return t.strip("_ ").strip()


def notas_de(entrada: dict, maximo: int = 8) -> list:
    """Resumen para la app: el título en negrita de cada novedad (o su inicio)."""
    notas = []
    for solo_titulos in (True, False):        # primero las novedades con título en negrita
        for sec in ("Añadido", "Cambiado", "Corregido"):
            for it in entrada.get("secciones", {}).get(sec, []):
                m = re.match(r"\*\*([^*]+)\*\*", it)
                if solo_titulos and not m:
                    continue
                texto = m.group(1) if m else sin_markdown(it).split(":")[0]
                texto = texto.strip(" .:—-")
                if texto and len(texto) <= 60 and texto not in notas:
                    notas.append(texto)
                if len(notas) >= maximo:
                    return notas
    return notas


# ─────────────────────────────────────────────────────────────
#  version.json
# ─────────────────────────────────────────────────────────────
def validar(datos: dict) -> list:
    errores = []
    if datos.get("producto") != "CCpdf":
        errores.append("«producto» debe ser «CCpdf»")
    if not re.match(r"^\d+\.\d+\.\d+$", str(datos.get("version", ""))):
        errores.append("«version» debe ser del tipo 1.5.0")
    if not re.match(r"^\d{4}-\d\d-\d\d$", str(datos.get("fecha", ""))):
        errores.append("«fecha» debe ser AAAA-MM-DD")
    if not isinstance(datos.get("notas"), list):
        errores.append("«notas» debe ser una lista")
    for sis, a in (datos.get("archivos") or {}).items():
        if sis not in SISTEMAS:
            errores.append(f"sistema desconocido en «archivos»: {sis}")
        for k in ("nombre", "url", "sha256", "tamano"):
            if not a.get(k):
                errores.append(f"archivos.{sis}.{k} vacío")
        if a.get("sha256") and not re.match(r"^[0-9a-f]{64}$", a["sha256"]):
            errores.append(f"archivos.{sis}.sha256 no es un SHA-256")
    hist = datos.get("historial")
    if not isinstance(hist, list) or not hist:
        errores.append("«historial» debe ser una lista con al menos la versión actual")
    elif hist[0].get("version") != datos.get("version"):
        errores.append("la primera entrada del historial debe ser la versión actual")
    return errores


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--salida", required=True, help="carpeta Downloads/ccpdf de la web")
    ap.add_argument("--binario", action="append", default=[], help="sistema=ruta")
    ap.add_argument("--version")
    ap.add_argument("--fecha", default=date.today().isoformat())
    ap.add_argument("--url-base", default="",
                    help="URL absoluta de la carpeta; por defecto las descargas son relativas al JSON")
    ap.add_argument("--historial-completo", action="store_true")
    ap.add_argument("--comprobar", action="store_true")
    a = ap.parse_args(argv)

    salida = Path(a.salida)
    manifiesto = salida / "version.json"
    if a.comprobar:
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        errores = validar(datos)
        for sis, arch in (datos.get("archivos") or {}).items():
            f = salida / arch.get("nombre", "")
            if not f.is_file():
                errores.append(f"falta el archivo {f.name}")
            elif sha256(f) != arch.get("sha256") or f.stat().st_size != arch.get("tamano"):
                errores.append(f"{f.name}: SHA-256 o tamaño no coinciden con version.json")
        print("\n".join(f"✖ {e}" for e in errores) or f"✔ version.json válido (CCpdf {datos['version']})")
        return 1 if errores else 0

    version = (a.version or version_app()).lstrip("vV")
    salida.mkdir(parents=True, exist_ok=True)
    datos = json.loads(manifiesto.read_text(encoding="utf-8")) if manifiesto.is_file() else {}
    nueva_version = datos.get("version") != version

    changelog = leer_changelog((RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))
    historial = [] if a.historial_completo else list(datos.get("historial") or [])
    if a.historial_completo:
        historial = changelog
    elif not any(h.get("version") == version for h in historial):
        entrada = next((v for v in changelog if v["version"] == version), None)
        if entrada is None:
            print(f"⚠ CHANGELOG.md no tiene la sección [{version}] con fecha: el historial "
                  "llevará una entrada vacía (edítala en version.json).")
            entrada = {"version": version, "fecha": a.fecha, "secciones": {}}
        historial.insert(0, entrada)
    actual = next(h for h in historial if h.get("version") == version)
    historial = [actual] + [h for h in historial if h is not actual]

    archivos = dict(datos.get("archivos") or {}) if not nueva_version else {}
    for par in a.binario:
        sis, _, ruta = par.partition("=")
        if sis not in SISTEMAS or not ruta:
            raise SystemExit(f"--binario debe ser sistema=ruta con sistema en {list(SISTEMAS)}")
        origen = Path(ruta)
        if not origen.is_file():
            raise SystemExit(f"No existe el binario {origen}")
        nombre = f"CCpdf-{version}-{sis}{SISTEMAS[sis]}"
        destino = salida / nombre
        tmp = destino.with_suffix(destino.suffix + ".tmp")
        shutil.copyfile(origen, tmp)
        if sis != "windows":
            os.chmod(tmp, 0o755)
        os.replace(tmp, destino)
        url = f"{a.url_base.rstrip('/')}/{nombre}" if a.url_base else nombre   # relativa: vale en QA y prod
        archivos[sis] = {"nombre": nombre, "url": url,
                         "sha256": sha256(destino), "tamano": destino.stat().st_size}

    datos = {
        "producto": "CCpdf",
        "version": version,
        "fecha": actual.get("fecha") or a.fecha,
        "notas": datos.get("notas") if (datos.get("notas") and not nueva_version) else notas_de(actual),
        "pagina": datos.get("pagina") or PAGINA,
        "archivos": archivos,
        "historial": historial,
    }
    errores = validar(datos)
    if errores:
        print("\n".join(f"✖ {e}" for e in errores))
        return 1
    tmp = manifiesto.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, manifiesto)

    print(f"✔ {manifiesto}  ·  CCpdf {version} ({datos['fecha']})")
    for sis, arch in archivos.items():
        print(f"   {sis:8} {arch['nombre']}  {arch['tamano'] / 1048576:.1f} MB  sha256 {arch['sha256'][:16]}…")
    print(f"   notas: {len(datos['notas'])} · historial: {len(historial)} versiones")
    viejos = sorted(f.name for f in salida.glob("CCpdf-*")
                    if f.name not in {x["nombre"] for x in archivos.values()} and not f.name.endswith(".tmp"))
    if viejos:
        print("   (binarios de versiones anteriores, no se borran: " + ", ".join(viejos) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
