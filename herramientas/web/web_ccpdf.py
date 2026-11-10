#!/usr/bin/env python3
"""web_ccpdf.py — Regenera la web de CCpdf desde Downloads/ccpdf/version.json.

Sustituye a la sincronización desde GitHub (CHANGELOG.md del repositorio). La
única fuente es version.json, que se edita a mano (o con
`python -m herramientas.publicar_version` del repo de CCpdf) en cada versión.

Actualiza:
  - ccpdf.html: título, versión y fecha, botones y plataformas de descarga
    (con tamaño y SHA-256) e historial de versiones (CHANGELOG:START/END).
  - Downloads/index.html: tarjetas de CCpdf (CCPDF-DESCARGAS:START/END) y la
    versión y los sistemas de CCpdf en el selector de producto (data-ccpdf="…").
    La página de descargas tiene un apartado por producto (#ccpdf, #wcp,
    #batocera); los enlaces de CCpdf llevan a Downloads/#ccpdf.
  - index.html (portada): SOLO la tarjeta de CCpdf en «Lo último de Kodesoft»
    (CCPDF-RELEASE:START/END), si la portada tiene esos marcadores. El resto de la
    portada (y la tarjeta de WCP) no se toca.
  - Corrige el nombre del repositorio (LeShite/CCpdf-IA → LeShite/CCpdf) en los
    enlaces al código fuente.

Uso:  python3 web_ccpdf.py --dir <carpeta de la web>   (o variable SITE_DIR)
"""
import html
import json
from datetime import date
import os
import re
import sys

DIR = os.environ.get("SITE_DIR", ".")
MESES = "Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split()
SECCIONES_STD = ("Añadido", "Cambiado", "Corregido", "Eliminado", "Documentación",
                 "Obsoleto", "Seguridad", "Heredado")
REPO = "https://github.com/LeShite/CCpdf"
NOMBRE_SISTEMA = {"windows": "Windows", "linux": "Linux", "macos": "macOS"}
ICONO_SISTEMA = {"windows": "⊞", "linux": "🐧", "macos": ""}


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w/])_([^_]+)_(?![\w/])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t


def fecha_es(iso):
    a, m, d = iso.split("-")
    return f"{d} {MESES[int(m) - 1]} {a}"


def tam(n):
    return f"{n / 1048576:.1f} MB"


def leer(ruta):
    with open(ruta, encoding="utf8") as f:
        return f.read()


def escribir(ruta, texto):
    """Escribe solo si cambió, en el mismo inodo (los archivos van montados en Docker)."""
    if leer(ruta) != texto:
        with open(ruta, "w", encoding="utf8") as f:
            f.write(texto)
        return True
    return False


def asegurar_marcadores(s, nombre, patron):
    """Envuelve con <!-- NOMBRE:START/END --> el bloque que casa con `patron` (si aún no lo está)."""
    if f"<!-- {nombre}:START -->" in s:
        return s
    nuevo, n = re.subn(patron, lambda m: f"<!-- {nombre}:START -->\n{m.group(1)}<!-- {nombre}:END -->\n",
                       s, count=1, flags=re.S)
    if not n:
        raise RuntimeError(f"no se encontró dónde poner los marcadores {nombre}")
    return nuevo


def reemplazar_bloque(s, nombre, contenido):
    return re.sub(rf"(<!-- {nombre}:START -->\n).*?(<!-- {nombre}:END -->)",
                  lambda m: m.group(1) + contenido + m.group(2), s, count=1, flags=re.S)


def cargar_manifiesto(directorio):
    ruta = os.path.join(directorio, "Downloads", "ccpdf", "version.json")
    datos = json.loads(leer(ruta))
    for k in ("version", "fecha", "historial"):
        if not datos.get(k):
            raise RuntimeError(f"version.json no tiene «{k}»")
    if not re.match(r"^\d{4}-\d\d-\d\d$", datos["fecha"]):
        raise RuntimeError("version.json: «fecha» debe ser AAAA-MM-DD")
    return datos


# ─────────────────────────────────────────────────────────────
#  HTML
# ─────────────────────────────────────────────────────────────
def render_historial(historial):
    out = []
    for i, h in enumerate(historial):
        actual = i == 0
        secciones = h.get("secciones") or {}
        propias = [s for s in secciones if not s.startswith(SECCIONES_STD)]
        titulo = propias[0] if propias else \
            " · ".join(dict.fromkeys(s.split(" (")[0] for s in secciones)) or "Cambios"
        items = "".join(f"          <li>{inline(t)}</li>\n"
                        for lista in secciones.values() for t in lista)
        badge = '          <span class="release-item__badge">Latest</span>\n' if actual else ""
        out.append(f'''      <article class="release-item{' release-item--current' if actual else ''} reveal" data-reveal>
        <div class="release-item__head">
          <span class="release-item__version">v{html.escape(h["version"])}</span>
{badge}          <span class="release-item__date">{fecha_es(h["fecha"]) if h.get("fecha") else ""}</span>
        </div>
        <h3>{html.escape(titulo)}</h3>
        <ul>
{items}        </ul>
      </article>
''')
    return "\n".join(out) + "\n"


def bloque_hero(datos):
    v = html.escape(datos["version"])
    archivos = datos.get("archivos") or {}
    flecha = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
              'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 '
              '1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>')
    if len(archivos) == 1:
        sis, a = next(iter(archivos.items()))
        principal = (f'<a href="Downloads/ccpdf/{html.escape(a["nombre"])}" class="btn btn--primary btn--lg" '
                     f'data-magnetic download>\n        {flecha}\n        <span>Descargar v{v} · '
                     f'{NOMBRE_SISTEMA[sis]}</span>\n      </a>')
    else:
        principal = (f'<a href="Downloads/#ccpdf" class="btn btn--primary btn--lg" data-magnetic>\n        {flecha}\n'
                     f'        <span>Descargar v{v}</span>\n      </a>')
    plataformas = []
    for sis in ("windows", "linux", "macos"):
        a = archivos.get(sis)
        if a:
            plataformas.append(
                f'      <a href="Downloads/ccpdf/{html.escape(a["nombre"])}" class="platform" download>\n'
                f'        <span class="platform__icon">{ICONO_SISTEMA[sis]}</span>\n'
                f'        <span>{NOMBRE_SISTEMA[sis]}</span>\n'
                f'        <span class="platform__size">{tam(a["tamano"])}</span>\n      </a>\n')
        else:
            nota = "Desde código fuente" if sis == "macos" else "Próximamente"
            plataformas.append(
                f'      <a href="{REPO}" target="_blank" rel="noopener" class="platform">\n'
                f'        <span class="platform__icon">{ICONO_SISTEMA[sis]}</span>\n'
                f'        <span>{NOMBRE_SISTEMA[sis]}</span>\n'
                f'        <span class="platform__size">{nota}</span>\n      </a>\n')
    hashes = "".join(
        f'      <p style="margin:.35rem 0 0;font-size:.78rem;opacity:.7;word-break:break-all">SHA-256 '
        f'{NOMBRE_SISTEMA[s]}: <code>{html.escape(a["sha256"])}</code></p>\n'
        for s, a in archivos.items())
    return (f'''    <div class="product-hero__actions reveal" data-reveal>
      {principal}
      <a href="{REPO}" target="_blank" rel="noopener" class="btn btn--ghost btn--lg" data-magnetic>
        <span>Código fuente</span>
        <span aria-hidden="true">↗</span>
      </a>
    </div>

    <div class="product-hero__platforms reveal" data-reveal>
{"".join(plataformas)}    </div>
''' + (f'    <div class="reveal" data-reveal>\n{hashes}    </div>\n' if hashes else ""))


def tarjetas_descargas(datos):
    v = html.escape(datos["version"])
    archivos = datos.get("archivos") or {}
    icono = ('<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.6" '
             'stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 '
             '2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>')
    tarjetas = []
    for sis, req in (("linux", "Linux de 64 bits · Tesseract para el OCR (opcional)"),
                     ("windows", "Windows 10/11 de 64 bits")):
        a = archivos.get(sis)
        if a:
            boton = (f'<a href="ccpdf/{html.escape(a["nombre"])}" class="btn btn--primary btn--block" '
                     f'data-magnetic download>\n          <span>Descargar</span>\n          '
                     f'<span aria-hidden="true">↓</span>\n        </a>')
            meta = (f'v{v} · {tam(a["tamano"])} · Ejecutable</p>\n        <p class="dl-card__meta" '
                    f'style="word-break:break-all">SHA-256 <code>{html.escape(a["sha256"])}</code>')
            badge = f"v{v}"
        else:
            boton = (f'<a href="{REPO}" target="_blank" rel="noopener" class="btn btn--ghost btn--block" '
                     f'data-magnetic>\n          <span>Código fuente</span>\n          '
                     f'<span aria-hidden="true">↗</span>\n        </a>')
            meta = "Ejecutable: próximamente"
            badge = "Próximamente"
        tarjetas.append(f'''      <!-- CCpdf · {NOMBRE_SISTEMA[sis]} -->
      <article class="dl-card reveal" data-reveal>
        <div class="dl-card__head">
          <div class="dl-card__icon">
            {icono}
          </div>
          <span class="dl-card__badge">{badge}</span>
        </div>
        <h3>CCpdf · {NOMBRE_SISTEMA[sis]}</h3>
        <p class="dl-card__req">{req}</p>
        {boton}
        <p class="dl-card__meta">{meta}</p>
      </article>
''')
    tarjetas.append(f'''      <!-- CCpdf · macOS -->
      <article class="dl-card reveal" data-reveal>
        <div class="dl-card__head">
          <div class="dl-card__icon">
            {icono}
          </div>
          <span class="dl-card__badge">Código fuente</span>
        </div>
        <h3>CCpdf · macOS</h3>
        <p class="dl-card__req">Con Homebrew: Tesseract</p>
        <a href="{REPO}" target="_blank" rel="noopener" class="btn btn--primary btn--block" data-magnetic>
          <span>Ver instrucciones</span>
          <span aria-hidden="true">↗</span>
        </a>
        <p class="dl-card__meta">Se ejecuta con <code>python3 main.py</code></p>
      </article>
''')
    return "\n".join(tarjetas)


DIAS_NUEVO = 45   # la tarjeta de la portada dice «Nueva versión» durante este tiempo


def tarjeta_inicio(datos, hoy=None):
    """Tarjeta azul de CCpdf en la portada (index.html, bloque CCPDF-RELEASE)."""
    v = html.escape(datos["version"])
    archivos = datos.get("archivos") or {}
    sistemas = [NOMBRE_SISTEMA[s] for s in ("windows", "linux", "macos") if s in archivos]
    tamanos = sorted(a["tamano"] for a in archivos.values())
    if not tamanos:
        tam_txt = "Código fuente"
    elif tam(tamanos[0]) == tam(tamanos[-1]):
        tam_txt = tam(tamanos[0])
    else:
        tam_txt = f"{tamanos[0] / 1048576:.1f}–{tam(tamanos[-1])}"
    hoy = hoy or date.today()
    nuevo = (hoy - date.fromisoformat(datos["fecha"])).days <= DIAS_NUEVO
    ribbon = "Nueva versión" if nuevo else "Herramienta"
    badge = '        <span class="release__badge">Nuevo</span>\n' if nuevo else ""
    chips = "".join(f'        <span>{html.escape(str(n))}</span>\n' for n in (datos.get("notas") or [])[:8])
    if len(archivos) == 1:
        a = next(iter(archivos.values()))
        descarga = f'<a href="Downloads/ccpdf/{html.escape(a["nombre"])}" class="btn btn--ghost" data-magnetic download>'
    else:
        descarga = '<a href="Downloads/#ccpdf" class="btn btn--ghost" data-magnetic>'
    n_sis = len(sistemas)
    etiqueta_sis = " y ".join(sistemas) if sistemas else "desde código fuente"
    flecha = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" '
              'stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return f'''    <article class="release release--azul reveal" data-reveal id="ccpdf">
      <span class="release__ribbon">{ribbon}</span>
      <div class="release__header">
        <div class="release__id">
          <span class="release__dot"></span>
          <span class="release__product">CCpdf</span>
        </div>
        <span class="release__version">v{v}</span>
{badge}      </div>

      <h3 class="release__headline">Tus PDFs, <em>en tu equipo</em>.</h3>

      <p class="release__summary">
        Suite local de PDF: OCR, extracción, fusión, división, compresión, comparación y
        limpieza de metadatos. Ningún archivo sale de tu máquina.
      </p>

      <div class="release__stats release__stats--3">
        <div><b>100 %</b><span>local, sin nube</span></div>
        <div><b>{n_sis or "—"}</b><span>{"sistema" if n_sis == 1 else "sistemas"}: {etiqueta_sis}</span></div>
        <div><b>SHA-256</b><span>descargas y actualizaciones verificadas</span></div>
      </div>

      <p class="release__chips-label">Novedades de la v{v}</p>
      <div class="release__chips">
{chips}      </div>

      <div class="release__meta">
        <span>📅 {fecha_es(datos["fecha"])}</span>
        <span>💻 {" · ".join(sistemas) or "Código fuente"}</span>
        <span>📦 {tam_txt}</span>
      </div>

      <div class="release__actions">
        <a href="ccpdf.html" class="btn btn--azul" data-magnetic>
          <span>Ver CCpdf</span>
          {flecha}
        </a>
        {descarga}
          <span>Descargar v{v}</span>
          <span aria-hidden="true">↓</span>
        </a>
      </div>
    </article>
'''


# ─────────────────────────────────────────────────────────────
#  PRINCIPAL
# ─────────────────────────────────────────────────────────────
def sync(directorio=DIR):
    datos = cargar_manifiesto(directorio)
    v, fecha = datos["version"], fecha_es(datos["fecha"])

    p = os.path.join(directorio, "ccpdf.html")
    s = leer(p)
    s = asegurar_marcadores(
        s, "CCPDF-DESCARGA",
        r'(    <div class="product-hero__actions.*?\n    </div>\n)(?=  </div>\n</header>)')
    s = reemplazar_bloque(s, "CCPDF-DESCARGA", bloque_hero(datos))
    s = reemplazar_bloque(s, "CHANGELOG", render_historial(datos["historial"]))
    s = re.sub(r"<title>CCpdf v[^<]*—", f"<title>CCpdf v{v} —", s)
    s = re.sub(r'(product-hero__version">)[^<]*', rf"\g<1>v{v}", s)
    s = re.sub(r'(product-hero__date">)[^<]*', rf"\g<1>{fecha}", s)
    s = re.sub(r"(Licencia MIT · CCpdf )v[\d.]+", rf"\g<1>v{v}", s)
    s = s.replace("github.com/LeShite/CCpdf-IA", "github.com/LeShite/CCpdf")
    s = s.replace('href="Downloads/">', 'href="Downloads/#ccpdf">')   # menú: directo al apartado de CCpdf
    cambio_ccpdf = escribir(p, s)

    p = os.path.join(directorio, "Downloads", "index.html")
    d = leer(p)
    d = asegurar_marcadores(
        d, "CCPDF-DESCARGAS",
        r"(      <!-- CCpdf · Windows / Linux -->.*?      </article>\n\n      <!-- CCpdf · macOS -->.*?      </article>\n)")
    d = reemplazar_bloque(d, "CCPDF-DESCARGAS", tarjetas_descargas(datos))
    # Selector de producto y cabecera del apartado de CCpdf (si la página los tiene).
    sistemas_sel = " y ".join(NOMBRE_SISTEMA[x] for x in ("windows", "linux", "macos")
                              if x in (datos.get("archivos") or {})) or "Código fuente"
    d = re.sub(r'(data-ccpdf="version">)[^<]*', rf"\g<1>v{v}", d)
    d = re.sub(r'(data-ccpdf="sistemas">)[^<]*', lambda m: m.group(1) + sistemas_sel, d)
    d = d.replace("github.com/LeShite/CCpdf-IA", "github.com/LeShite/CCpdf")
    cambio_desc = escribir(p, d)

    # Portada: solo el bloque CCPDF-RELEASE, y solo si la portada lo tiene.
    p = os.path.join(directorio, "index.html")
    cambio_inicio = False
    if os.path.isfile(p):
        i = leer(p)
        if "<!-- CCPDF-RELEASE:START -->" in i:
            cambio_inicio = escribir(p, reemplazar_bloque(i, "CCPDF-RELEASE", tarjeta_inicio(datos)))

    sistemas = ", ".join(f"{NOMBRE_SISTEMA[s]} {tam(a['tamano'])}" for s, a in (datos.get("archivos") or {}).items())
    return (f"CCpdf: v{v} ({fecha}) desde version.json · {len(datos['historial'])} versiones · "
            f"descargas: {sistemas or 'ninguna'} · "
            f"{'páginas actualizadas' if (cambio_ccpdf or cambio_desc or cambio_inicio) else 'sin cambios'}")


if __name__ == "__main__":
    if "--dir" in sys.argv:
        DIR = sys.argv[sys.argv.index("--dir") + 1]
    print(sync(DIR))
