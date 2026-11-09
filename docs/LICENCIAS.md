# Licencias de terceros — auditoría para venta

Auditoría del 2026-10-23 sobre el código de `main.py`, `Interfaz/` y `Motores/`, el `.venv` del
proyecto y el ejecutable de Linux (`build/ccpdf/PKG-00.toc`). CCpdf es MIT (`LICENSE`).

Este archivo va dentro del ejecutable (`licencias/LICENCIAS.md`) junto con los textos de licencia
de cada paquete (carpetas `*.dist-info`).

Leyenda: ✅ permisiva, se puede vender · ⚠️ se puede vender con condiciones · ❌ problema que hay que
quitar antes de vender.

## Resumen

Todo lo que va dentro del ejecutable es permisivo y se puede vender. Lo que lo impedía se quitó
el 2026-10-23:

| # | Problema | Estado |
|---|---|---|
| 1 | ❌ **GNU readline (GPL-3)** iba dentro del ejecutable de Linux (entraba por `pdb`) | ✅ Excluido en `ccpdf.spec` |
| 2 | ⚠️ **libquadmath (LGPL-2.1+)** y libgfortran iban dentro, con `numpy`, que la app no usa | ✅ `numpy` excluido en `ccpdf.spec` (pytesseract y rapidfuzz lo importan solo si existe) |
| 3 | ⚠️ **Poppler (GPL-2/3)** era obligatorio para el OCR, vía `pdf2image` | ✅ El OCR convierte las páginas con `pypdfium2`; `pdf2image` y Poppler ya no hacen falta |
| 4 | ⚠️ **Ghostscript (AGPL-3)**: el compresor lo usa si el usuario lo tiene instalado | ✅ No va con CCpdf: es una «Mejora extra» que el usuario instala desde el compresor, descargándola de la fuente oficial (Windows) o con el gestor de su sistema (macOS, Linux). **No** incluirlo en un instalador |
| 5 | ⚠️ **Avisos de licencia** que MIT, BSD, Apache, FreeType e IJG exigen entregar | ✅ El `.spec` mete en el ejecutable este archivo y la licencia de cada paquete |
| 6 | ❓ **Logo** (`Interfaz/assets/logo.png`, `logo.ico`) | Pendiente: confirmar que es propio o tiene licencia de uso comercial |

## Paquetes Python (van dentro del ejecutable)

| Paquete | Versión | Licencia | Uso en CCpdf | Venta |
|---|---|---|---|---|
| pypdf | 6.20.1 | BSD-3-Clause | Leer, fusionar, dividir, comprimir; texto del visor | ✅ |
| typing-extensions | 4.16.0 | PSF-2.0 | Dependencia de pypdf | ✅ |
| Pillow | 12.3.0 | MIT-CMU | Imágenes (OCR, visor) | ✅ |
| pypdfium2 (+ PDFium) | 5.14.0 | BSD-3-Clause / Apache-2.0 | Visor y páginas a imagen para el OCR | ✅ |
| customtkinter | 6.0.0 | MIT | Interfaz | ✅ |
| darkdetect | 0.8.0 | BSD-3-Clause | Dependencia de customtkinter | ✅ |
| packaging | 26.3 | Apache-2.0 o BSD-2-Clause | Dependencia de customtkinter | ✅ |
| thefuzz | 0.22.1 | MIT | Búsqueda difusa (Extracción) | ✅ |
| rapidfuzz | 3.14.6 | MIT | Dependencia de thefuzz | ✅ |
| pytesseract | 0.3.13 | Apache-2.0 | Puente con Tesseract | ✅ |
| reportlab | 5.0.1 | BSD | Capa de texto invisible del OCR | ✅ (ver nota) |
| charset-normalizer | 3.5.2 | MIT | Dependencia de reportlab | ✅ |
| tkinterdnd2 (+ tkdnd) | 0.7.0 | MIT (tkdnd: BSD) | Arrastrar y soltar archivos | ✅ |

Nota sobre reportlab: el paquete trae la fuente *DarkGarden* con licencia **GPL**
(`reportlab/fonts/DarkGarden*`). **No** está en el ejecutable actual y el código no la usa; hay que
vigilar que no entre si algún día se añade `collect_data_files("reportlab")` al `.spec`.

## Recursos que van dentro del ejecutable

| Recurso | Licencia | Venta |
|---|---|---|
| Fuente Roboto (de customtkinter) | Apache-2.0 | ✅ |
| `CustomTkinter_shapes_font.otf` | MIT (customtkinter) | ✅ |
| Prompts de CIPA (`Motores/CIPA/prompts/*.txt`) | Propios (MIT) | ✅ |
| Logo `Interfaz/assets/logo.*` | Sin documentar | ❓ ver #6 |

## Librerías nativas dentro del ejecutable de Linux

Comprobado en `build/ccpdf/PKG-00.toc`.

| Librería | Viene de | Licencia | Venta |
|---|---|---|---|
| libpython3.12 | Python | PSF-2.0 | ✅ |
| libtcl8.6, libtk8.6, libBLT | Tkinter | BSD (Tcl/Tk), MIT (BLT) | ✅ |
| libssl, libcrypto | Python (`ssl`) | Apache-2.0 (OpenSSL 3) | ✅ |
| libffi, libexpat, libX11, libXft, libXrender, libXext, libXss, libXau, libXdmcp, libxcb, libfontconfig, libbsd, libmd | Python / Tk / Pillow | MIT / BSD / ISC | ✅ |
| libtinfo | ncurses | MIT-X11 | ✅ |
| libz, libbz2, liblzma, libzstd, libbrotli* | Compresión | zlib / BSD / 0BSD / MIT | ✅ |
| libstdc++, libgcc_s | GCC | GPL-3 **con excepción de runtime** de GCC | ✅ |
| libjpeg | Pillow, PDFium | IJG + BSD | ✅ con crédito (ver Obligaciones) |
| libfreetype | Pillow, PDFium, sistema | FreeType License (FTL) | ✅ con crédito (ver Obligaciones) |
| libharfbuzz, liblcms2, libopenjp2, libpng16, libtiff, libwebp*, libavif, libsharpyuv | Pillow | MIT / BSD / libpng / libtiff | ✅ |
| libpdfium (+ ICU, abseil, agg, fast_float, simdutf, llvm-libc) | pypdfium2 | BSD-3 / Apache-2.0 / Unicode / MIT | ✅ |

Fribidi (LGPL) **no** va dentro: Pillow lo carga del sistema solo si existe.

## Herramientas de build (no se distribuyen)

| Herramienta | Licencia | Venta |
|---|---|---|
| PyInstaller 6.22.3 | GPL-2 **con excepción de bootloader**: permite distribuir ejecutables con cualquier licencia | ✅ |
| pyinstaller-hooks-contrib | GPL-2 / Apache-2.0 | ✅ (solo en build) |
| altgraph, setuptools | MIT | ✅ |

## Programas externos (el usuario los instala; no van en el ejecutable)

| Programa | Licencia | Uso | Venta |
|---|---|---|---|
| Tesseract OCR + datos de idioma (`tessdata`) | Apache-2.0 | OCR | ✅ (incluso se podría incluir en el instalador) |
| Ghostscript | AGPL-3 (o licencia comercial de Artifex) | Compresor, opcional | ✅ si lo instala el usuario; ❌ en el instalador (ver #4) |
| Ollama | MIT | Sirve el modelo de CIPA | ✅ |
| xdg-open, xdg-user-dir | Del sistema | Abrir carpetas, localizar Descargas | ✅ (no se distribuyen) |

## IA (CIPA)

| Componente | Licencia | Venta |
|---|---|---|
| Qwen2.5-1.5B-Instruct (`qwen2.5:1.5b`) | Apache-2.0 (comprobado con `ollama show --license`) | ✅. Ojo: Qwen2.5-**3B** y **72B** NO son Apache (ver BUG-004); no cambiar a esos tamaños |
| Phi-3.5-mini-instruct (GGUF de bartowski) | MIT | ✅ |
| llama-cpp-python 0.3.36 (+ llama.cpp / ggml) | MIT | ✅ (excluido del `.spec`; opcional vía `requirements-ai.txt`) |
| diskcache, Jinja2, MarkupSafe | Apache-2.0 / BSD-3 | ✅ (dependencias de llama-cpp-python) |
| API de DeepSeek / Gemini | No es una licencia: son condiciones de servicio | ✅ el usuario pone su propia clave. Con el plan gratuito de Gemini, Google puede usar los datos enviados (la app ya avisa de privacidad) |

Los pesos de los modelos no se distribuyen con la app: los descarga el usuario (Ollama o
`descargar_modelo`). Si algún día se incluyen en el instalador, hay que acompañarlos de su licencia.

## Instalado en el `.venv` pero no lo usa la app

anyio, click, filelock, fsspec, h11, hf-xet, httpcore2, httpx2, huggingface-hub, idna, numpy, PyYAML,
tqdm (MPL-2.0), truststore. Ninguna entra en el ejecutable.

## Obligaciones al vender

1. **Avisos de licencia**: el ejecutable ya los lleva (`licencias/LICENCIAS.md` y las carpetas
   `*.dist-info` con la licencia de cada paquete, incluidas las de PDFium en
   `pypdfium2-*.dist-info/licenses/`). Si se hace un instalador, conviene copiar también la carpeta
   `licencias/` junto al programa, a la vista del usuario.
2. **Créditos exigidos** (este archivo los cumple al ir dentro del programa):
   - Portions of this software are copyright © The FreeType Project (www.freetype.org). All rights reserved.
   - This software is based in part on the work of the Independent JPEG Group.
3. **No incluir** en el instalador: Ghostscript (AGPL), ni la fuente DarkGarden de reportlab (GPL).
4. Tras cada build, comprobar que sigue limpio (debe salir vacío):
   `grep -oiE 'readline|quadmath|gfortran|DarkGarden|numpy|poppler' build/ccpdf/PKG-00.toc`

## Pendiente de verificar

- Build de **Windows**: no se ha auditado. Las librerías nativas cambian; repetir la comprobación
  del punto 4 sobre su `PKG-00.toc`.
- El ejecutable viejo `dist/CCpdf IA` (16-oct) **lleva readline (GPL)**: no distribuirlo.
