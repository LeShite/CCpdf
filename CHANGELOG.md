# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

- **Web** (`herramientas/web/web_ccpdf.py`): genera también la tarjeta de CCpdf de la portada de
  kodesoft.site (bloque `CCPDF-RELEASE` de `index.html`) desde `version.json`. No cambia la app.

### Cambiado

- **Web** (`herramientas/web/web_ccpdf.py`): la página de descargas de kodesoft.site tiene ahora un
  apartado por producto (`Downloads/#ccpdf`, `#wcp`, `#batocera`). El generador actualiza también la
  versión y los sistemas de CCpdf en el selector de producto (`data-ccpdf="version|sistemas"`), y los
  enlaces de descarga de `ccpdf.html` y de la portada llevan directo a `Downloads/#ccpdf`.

## [1.5.0] - 2026-11-08

### Añadido

- **Arrastrar y soltar**: se pueden soltar PDFs (o carpetas) desde el explorador sobre la ventana.
  Van al módulo abierto: Fusionar, Comprimir, OCR y Metadatos los añaden a la lista; Dividir los toma
  como PDF origen; Extracción usa la carpeta; en el Dashboard, Visor, Asistente o Firmar se abren en el
  Visor. Avisa de los archivos que no son PDF y no acepta nada mientras hay un proceso en curso.
  Nueva dependencia opcional `tkinterdnd2` (MIT, incluye tkdnd BSD): sin ella la app funciona igual.
  Test: `Interfaz/test_arrastrar_soltar.py`.
- **Módulo Metadatos** (Herramientas): muestra lo que revela cada PDF (autor, título, programa
  creador, productor, fechas legibles, claves propias, XMP, PieceInfo) y crea una copia limpia en
  `PDFs_Sin_Metadatos`. Borra `/Info`, XMP del documento y de las páginas y `/PieceInfo`, y elimina
  los objetos huérfanos para que los datos no queden como bytes sueltos dentro del archivo. Nunca
  modifica ni pisa el original; verifica páginas antes de guardar; los PDF protegidos dan un error
  claro. Motor `Motores/Metadatos/`, test `Motores/Metadatos/test_limpieza.py`.
- El contador de módulos del Dashboard se calcula solo (antes estaba fijo en «9 · 7 activos»).
- **Módulo Comparar** (Herramientas): compara dos versiones de un PDF página a página. Texto:
  palabras añadidas y quitadas. Visual: renderiza ambas páginas y marca en rojo las zonas que cambian
  (detecta cambios en imágenes, firmas, sellos y escaneos sin texto). Genera un informe PDF con el
  resumen y las páginas cambiadas marcadas; nunca pisa archivos. No realinea páginas insertadas a
  mitad del documento (lo indica el informe). Motor `Motores/Comparacion/`, test `test_comparar.py`.
- **Historial** (Principal): cada proceso terminado queda registrado en `historial.json` junto a la
  configuración (permisos 600, solo nombres de archivo, nunca sale del equipo), con su detalle y
  botón para abrir la carpeta. Se puede desactivar.
- **Temporales — deshacer acciones**: antes de cada proceso se guarda una copia de los PDFs de
  entrada (almacén por contenido: el mismo PDF ocupa espacio una vez). Desde el historial, en
  cualquier proceso anterior: **Deshacer** retira los archivos generados (se mueven a temporales, no
  se borran), **Rehacer** los devuelve y **Restaurar PDFs de entrada** recupera las versiones
  previas aunque se hayan modificado o borrado; nunca sobrescribe (crea «(restaurado)»). Retención
  configurable de 1 día a 1 año; **1 mes recomendado** (por defecto) y 1 año marcado como no
  recomendado por espacio. Muestra el espacio usado, «Liberar vencidos» y limpieza automática al
  abrir. Tests: `Interfaz/test_historial.py`, `Interfaz/test_historial_ui.py`.

- **Actualizaciones desde kodesoft.site** (sin GitHub): Configuración → Actualizaciones busca en
  `https://kodesoft.site/Downloads/ccpdf/version.json`, muestra versión, fecha, tamaño y novedades, y
  **descarga e instala** la versión nueva (barra de progreso, verificación de tamaño y SHA-256,
  el ejecutable anterior queda como `CCpdf.anterior` y se puede volver a él). Opción de buscar al
  abrir (una vez al día). Desde el código fuente solo muestra las novedades y la página de descarga.
  Ver `docs/ACTUALIZACIONES.md`. Tests: `Interfaz/test_actualizador.py`, `test_actualizador_ui.py`.
- **Datos del usuario entre versiones** (`Interfaz/migracion.py`): `config.json` anota la versión
  que lo escribió; al abrir una versión distinta se respaldan `config.json` e `historial.json`, se
  aplican las migraciones necesarias y se avisa una vez. Respaldo también antes de instalar una
  actualización (se conservan los 10 más recientes).
- **`herramientas/publicar_version.py`**: genera o actualiza `version.json` (la única fuente de
  versiones para la app y la web) a partir del binario y de `CHANGELOG.md`; `--comprobar` lo valida.
- **Ejecutable de Linux** compilado y probado por primera vez (32 MB, `dist/CCpdf`).
- **Ejecutable de Windows** (x64, Windows 10/11 de 64 bits), primero publicado: `CCpdf-1.5.0-windows.exe`
  (29 MB). Lo compila GitHub Actions (`.github/workflows/build-windows.yml`, Python 3.12) en cada push;
  este es el del commit `68c70e8`. Lleva tkdnd para Windows (arrastrar y soltar), `pdfium.dll` y las
  licencias. Se descarga y se actualiza desde kodesoft.site como el de Linux.

### Cambiado

- **Idioma (BUG-019, parcial)**: se aplican las traducciones que existían sin usarse: pestañas de
  Configuración, botones Explorar/Examinar/Cargar .txt, nombres de los temas (`etiqueta_tema`),
  aviso al cambiar de idioma y una línea de ayuda bajo el título de cada módulo (`mod_*_sub`).
  Siguen en español los textos escritos directamente en el código.
- **Menú lateral**: «Configuración» y el usuario quedan fijos abajo y la lista de módulos se
  desplaza con la rueda si no cabe. La ventana se ajusta a la pantalla (máx. 1280×820).
- **Configuración → Carpetas**: añadidas OCR, Metadatos y Comparar (7 en total).
- **Visor**: un hilo de render y otro de búsqueda por documento, con resultados por cola; la
  búsqueda muestra ⏳ y se cancela al abrir otro PDF o buscar otra cosa.
- Nueva dependencia opcional `tkinterdnd2` (arrastrar y soltar) y `requirements-dev.txt` para las
  pruebas.
- **Actualizador**: antes consultaba GitHub Releases (que nunca se publicaron); ahora kodesoft.site.

### Corregido

- **BUG-026 — OCR**: con pypdf 7 no generaba ningún PDF (afectaba a toda instalación nueva).
- **BUG-027**: `numpy` (solo para una prueba) pasa a `requirements-dev.txt`.
- **BUG-011 — Visor**: buscar y abrir otro PDF antes de que terminara mostraba «No se encontró»
  sobre el PDF nuevo (o saltaba a una página del viejo); dos búsquedas seguidas respondían las
  dos; pasar 40 páginas creaba 40 hilos y dibujaba las 40 (ahora 2).
- **BUG-037 — Visor**: la búsqueda contaba como «no está» las páginas cuyo texto no se podía leer;
  ahora avisa.
- **BUG-028 — Configuración**: Actualizaciones decía «Repositorio no publicado todavía»; el
  repositorio se renombró a `LeShite/CCpdf` y lo que falta son Releases.
- **BUG-029 — Interfaz**: en pantallas de 768 px «Configuración» quedaba fuera de la vista.
- **BUG-030 — Dashboard**: el contador de módulos estaba fijo («9 · 7 activos»).
- **BUG-038 — Build**: `ccpdf.spec` exigía la licencia de `typing_extensions`, que pypdf 7 ya no
  instala en Python 3.13: PyInstaller se detenía y no había forma de compilar.

_Corregidos durante el desarrollo de esta versión, antes de publicarla (no afectaron a ninguna
versión publicada):_ BUG-031 (menú de idioma flotante al activar arrastrar y soltar), BUG-032
(el XMP borrado quedaba en el archivo), BUG-033 (fechas ilegibles en Metadatos), BUG-034 (botones
del historial desactivados), BUG-035 (comparación visual lenta) **BUG-036, una regresión
introducida por el primer arreglo de BUG-011** (abrir otro PDF esperaba al render en curso), BUG-039
(la instalación de una actualización dejaba la carpeta temporal de la descarga) y BUG-040 (el aviso
de «datos conservados» podía repetirse).
Detalle de todos en `docs/KNOWN_ISSUES.md`.

_Incluye también los cambios de la rama `release-2026-10-23` (23 oct), que no se habían publicado:_

### Añadido

- **Compresor → Mejoras extras**: si Ghostscript no está instalado, una tarjeta con el botón
  «Descargar e instalar Ghostscript» (Windows: instalador oficial con SHA-256 verificado; macOS:
  Homebrew; Linux: gestor de paquetes vía pkexec). Con Ghostscript instalado la tarjeta no aparece y
  sí la opción de motor «Ghostscript». En macOS (donde hace falta Homebrew) la tarjeta tiene un
  botón «Ocultar» que se recuerda entre sesiones; se vuelve a mostrar en Configuración → Apariencia.
  Tests: `Motores/Compresion/test_instalar_gs.py`, `Interfaz/test_mejoras_extras.py`.
- **Barra lateral ocultable**: botón ☰ en la barra superior para mostrarla u ocultarla con un
  deslizamiento suave (~0,2 s); oculta, el contenido ocupa todo el ancho.
- **Modo híbrido de IA**: Configuración → IA permite elegir «Ollama (Local)» (por defecto, con aviso de
  que puede tardar varios minutos) o «API Externa» (DeepSeek/Gemini, con aviso de privacidad y
  confirmación). Nuevo `Motores/CIPA/backends/api_externa.py` y test `test_api_externa.py`.
- Barra indeterminada y texto animado «Pensando…» mientras trabaja la IA (OCR con CIPA). En el chat el botón pasa a «⏹ Detener».

### Corregido

- **Licencias para venta** (auditoría en `docs/LICENCIAS.md`): el ejecutable ya no lleva GNU readline
  (GPL-3) ni numpy con libquadmath (LGPL), que entraban de rebote sin usarse. El OCR convierte las
  páginas con PDFium en vez de Poppler (GPL): `pdf2image` y Poppler dejan de ser necesarios. El
  ejecutable incluye los avisos de licencia de cada paquete y `licencias/LICENCIAS.md`.
- **BUG-017 — Visor**: las páginas se dibujan con PDFium (`pypdfium2`, BSD-3 / Apache-2.0).
  Se ven los escaneos en blanco y negro (CCITT/JBIG2, antes en blanco), el texto de Word, Chrome y
  LibreOffice (antes basura o cuadros), «“ ” — € …», transparencias y recortes. pypdf sigue para
  texto, búsqueda y metadatos; el motor propio queda de respaldo. Nueva dependencia en
  `requirements.txt`. Test: `Motores/Visualizacion/test_render_pdfium.py`.
- **Arranque de 87 s en Linux**: con ibus por XIM, Tk esperaba al servidor de entrada en cada widget.
  `main.py` fija `XMODIFIERS=@im=none` antes de cargar Tk; ahora abre en ~3 s.
- **Asistente CIPA inventaba archivos**: pedirle «busca un pdf llamado X en descargas» devolvía una ruta
  inventada. Ahora hay una herramienta `buscar_pdf` que busca de verdad (y un atajo que no pasa por el
  modelo), «tráelo» carga el PDF hallado, y cualquier ruta a un PDF que no exista se bloquea en la
  respuesta. «Quién eres», «cómo funcionas» y las preguntas de privacidad tienen respuesta fija
  (la de privacidad distingue modo local y API externa). Test: `Motores/CIPA/test_asistente.py`.
- **BUG-019**: selector de idioma (es/en) en Configuración → Apariencia; traduce la barra lateral,
  el inicio y Configuración (el resto sigue en español).
- **BUG-009**: cerrado; solo quedaba un comentario de `n_threads` desactualizado.
- **Compresión**: un PDF con contraseña ya no se "comprime" a un PDF en blanco con Ghostscript
  (decía "ahorro 100 %"); ahora se reporta como error del archivo, igual que con el motor interno.
- **Visor**: las líneas de texto con "…", CR o los bytes 0x1C-0x1E ya no desaparecen (fallo de
  Pillow con raqm); las fuentes usan el layout básico y la posición del texto avanza aunque un
  dibujo falle.
- Revisión del 2026-10-21 (16 puntos en `docs/KNOWN_ISSUES.md`, sección REV-2026-10-21).
- **Asistente**: el botón «⏹ Detener» no hacía nada (con una petición en curso el campo está vacío y
  se salía antes de comprobarlo). Además, una respuesta que llega después de pulsar Detener ya no se
  muestra ni ejecuta herramientas: se responde «(Cancelado.)».
- **OCR**: si Tesseract no tiene el idioma elegido (p. ej. falta `tesseract-ocr-spa`) ahora se lanza un
  error claro, con el paquete a instalar, en vez de terminar con «OK, 0 palabras» y un PDF sin capa de
  texto. Un fallo de datos de idioma al leer una página tampoco se traga ya como «sin texto».
- **Extracción**: con «Tolerancia ortográfica» los números ya no se toleran: «folio 4587» no coincide con
  «folio 4581» ni «HGZ 51» con «HGZ 5 CHAPALA». Las letras siguen tolerando errores de OCR.
- **Divisor**: ya no puede sobrescribir el PDF de origen. Si la carpeta de salida es la del origen y una
  unidad (o `_PAGINAS_SIN_ASIGNAR`) se llama igual que el PDF, la salida se guarda como «nombre (2).pdf»
  y se avisa en el registro.

### Cambiado

- `llama-cpp-python` pasa de `requirements.txt` a `requirements-ai.txt`: se compila al instalarlo y
  solo hace falta para el fallback de CIPA sin Ollama.

### Documentación

- DOC-001: `REQUISITOS.md`, `README.md`, `Motores/CIPA/README.md`, `requirements.txt` y `.gitignore`
  puestos al día (OSD y Ghostscript, descarga manual del modelo de llama.cpp, sin `huggingface-hub`).

## [1.0.1] - 2026-10-21

### Corregido

- **BUG-001 completo — OCR de escaneos girados y de páginas con orientaciones mezcladas**: cada
  palabra recuerda su orientación y la capa de texto se dibuja girada. Una tabla girada dentro de una
  página con encabezado derecho se lee con la orientación correcta (90° y 270°); las palabras que
  Tesseract lee mal de lado (con confianza alta) se releen por regiones. Una página normal sigue
  costando una sola lectura de OCR.
- **BUG-020**: el compresor ya no usa un atributo privado de pypdf; imports normales de paquete en
  `app.py` (sin `exec()` ni `sys.path` de carpetas de motores); el asistente conoce cómo se usa cada
  módulo; fuentes según el sistema (no solo Segoe UI / Consolas); al cerrar con un proceso en marcha se
  espera al hilo del motor.
- **BUG-022**: si `llama_cpp` está instalado pero su librería nativa falla, CIPA lo avisa y el error
  «sin backend» incluye el motivo.
- **BUG-023**: cierre inmediato (0,1 s) en lugar de desmontar ~1100 widgets de Tk uno a uno (≈7,5 s
  con el gestor de entrada de Linux saturado).

### Añadido

- **BUG-024**: temas conectados. Configuración → Apariencia permite elegir entre siete temas
  (Enterprise —el aspecto de siempre, predeterminado—, Aero, Oscuro, Claro, Rosado, Menta y Atardecer);
  se aplica al reiniciar. Las preferencias pasan a formato 2.
- `Motores/OCR/test_orientaciones_mixtas.py`.

### Cambiado

- `ccpdf.spec` ya no necesita `Interfaz` en `pathex` ni describe el mecanismo `exec()`.

## [1.0.0] - 2026-10-20

### Unificación de CCpdf y CCpdf IA

Los dos proyectos se fusionan en uno solo, **CCpdf 1.0.0**.

- **CCpdf IA Alpha 0.1.0** (carpeta `CCPDF-IA-Alpha-0.1.0`, repo `LeShite/CCpdf-IA`) ya incluía el
  rediseño de interfaz de CCpdf beta 0.8.0 (v0.9.0) y añadía CIPA, OCR y el asistente, además de
  correcciones en el visor, el compresor, el divisor y la rotación. Se tomó como base.
- La carpeta pasó a llamarse `CCPDF` y se conserva su historial de 24 commits.
- La beta (`CCPDFbeta0.8.0`, repo `LeShite/CCPDF`) **no se modificó**. No se migró nada de ella:
  `Interfaz/panel_progreso.py` duplicaba una clase que ya está dentro de `app.py`, y
  `testinterfaz.py`, `utils_historicos/aplicar_confirmacion.py` y `_backups/` son material histórico.

### Cambiado

- Nombre del producto: **CCpdf** (antes «CCpdf IA»). CIPA sigue siendo su módulo de IA local.
- Versión **1.0.0** en la aplicación y en CIPA (antes `v0.1.0-alpha`). Se quitan las etiquetas alpha y beta.
- `ccpdf_ia.spec` → `ccpdf.spec`; el ejecutable pasa a llamarse `CCpdf`. Actualizados
  `build_linux.sh`, `build_windows.bat`, README y documentación.
- `Interfaz/actualizador.py` sigue apuntando a `LeShite/CCpdf-IA` hasta que se renombre el repositorio.

### Corregido

- **OCR de escaneos girados (BUG-001)**: la detección de giro con Tesseract OSD ahora está conectada
  a `aplicar_ocr()` y la capa de texto se dibuja con la orientación y el tamaño correctos en
  escaneos girados 90°, 180° y 270° (antes la fuente salía ≈7× mayor y en horizontal, y la
  selección no coincidía con lo que se ve) y `pypdf` sigue leyendo el texto con sus espacios en los
  cuatro giros. Pendiente: páginas con orientaciones mezcladas.
  Ver `docs/KNOWN_ISSUES.md`.
- **Visor**: los renders obsoletos se descartan con un contador de generación (evita pintar una
  página vieja tras cambiar de página o zoom) y se quitan las trazas de depuración `[VISOR]`.

### Añadido

- `Motores/OCR/test_rotacion.py`: prueba de la detección de giro y del des-rotado de coordenadas.
- `Motores/OCR/test_capa_texto.py`: compara posición, tamaño y dirección de cada palabra de la capa de texto
  de escaneos girados con la página derecha (incluye una página con `/Rotate`).
- `.gitignore`: se ignora `.claude/`.

### Heredado de CCpdf IA Alpha (2026-10-15 a 2026-10-16)

- **CIPA**: IA local con backend Ollama (preferido) o llama.cpp, asistente conversacional con
  tool calling y limpieza opcional del OCR.
- **OCR** con Tesseract: capa de texto invisible, CropBox, escalado y corrección por línea con CIPA.
- Vistas **OCR** y **Asistente** en la interfaz.
- Correcciones de bugs registrados en `docs/KNOWN_ISSUES.md`: bloque 1 (7 críticos), bloque 2
  (5 medios y empaquetado, BUG-005), bloque 5 (BUG-018, 019, 020, 023, 024 y DOC-001), BUG-002
  (consumo de tokens de CIPA reducido 4,9×), BUG-009, BUG-012 y BUG-016.
