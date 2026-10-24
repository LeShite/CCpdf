# Problemas conocidos de CCpdf

Registro de bugs pendientes y limitaciones actuales.

Última revisión completa del repositorio: **2026-10-21** (arreglos de la
revisión en [REV-2026-10-21](#rev-2026-10-21); estados anteriores
reconciliados el 2026-10-16).

Estados:

- ✅ **RESUELTO** — fix aplicado y verificado.
- 🟢 **APLICADO** — fix aplicado, sin verificación exhaustiva.
- 🟡 **PARCIAL** — solo se hizo una parte.
- ⏳ **PENDIENTE** — falta el fix.

🔬 = el bug original se reprodujo con un script de prueba; el resto sale de
leer el código.

---

## Índice

| ID | Sev. | Módulo | Estado | Resumen |
|---|---|---|---|---|
| [BUG-001](#bug-001) | 🔴 | OCR | ✅ RESUELTO | Auto-rotación: detección, capa de texto girada y páginas con orientaciones mezcladas |
| [BUG-002](#bug-002) | 🔴 | CIPA | 🟡 PARCIAL | La IA es pesada y consume demasiados tokens |
| [BUG-003](#bug-003) | 🔴 | Visor | ✅ RESUELTO | Cualquier imagen en el PDF hacía que el visor reventara la RAM |
| [BUG-004](#bug-004) | 🔴 | CIPA | ✅ RESUELTO | `qwen2.5:3b` NO era Apache 2.0 (Qwen Research License, no comercial) |
| [BUG-005](#bug-005) | 🔴 | Build | 🟢 APLICADO | Los scripts de build apuntaban a un `.spec` que no existe y el ejecutable no llevaba los prompts |
| [BUG-006](#bug-006) | 🟠 | Visor | ✅ RESUELTO | Páginas con `/Rotate` 90/270 se mostraban giradas 180° |
| [BUG-007](#bug-007) | 🟠 | Interfaz / OCR | ✅ RESUELTO | El OCR no se podía detener (el botón nunca se habilitaba) |
| [BUG-008](#bug-008) | 🟠 | Divisor | ✅ RESUELTO | 🔬 Unidades con «CIUDAD» en el nombre se cortaban |
| [BUG-009](#bug-009) | 🟠 | CIPA | ✅ RESUELTO | Sin Ollama, CIPA nunca funcionaba (el fallback llama.cpp estaba roto) |
| [BUG-010](#bug-010) | 🟠 | Visor | ✅ RESUELTO | Los mensajes de error del render lanzaban `NameError` |
| [BUG-011](#bug-011) | 🟠 | Visor | 🟢 APLICADO | Al abrir otro PDF puede aparecer una página del PDF anterior |
| [BUG-012](#bug-012) | 🟡 | CIPA | ✅ RESUELTO | 🔬 `_postprocesar_correccion` descarta o mutila texto válido |
| [BUG-013](#bug-013) | 🟡 | CIPA | ✅ RESUELTO | `_modelo_existe` daba por instalado un modelo que no lo estaba |
| [BUG-014](#bug-014) | 🟡 | Asistente | ✅ RESUELTO | 🔬 Los atajos secuestraban peticiones combinadas («lee X y resúmelo») |
| [BUG-015](#bug-015) | 🟡 | Compresor | ✅ RESUELTO | Nombres con `%` rompían Ghostscript y dejaban basura `.tmp` |
| [BUG-016](#bug-016) | 🟡 | Asistente | ✅ RESUELTO | El historial puede quedar corrupto (mensajes `tool` huérfanos) |
| [BUG-017](#bug-017) | 🟡 | Visor | ✅ RESUELTO | PDFs escaneados y fuentes modernas se ven en blanco o con basura |
| [BUG-018](#bug-018) | 🟡 | Interfaz | 🟢 APLICADO | Bloqueos de la interfaz por llamadas lentas en el hilo principal |
| [BUG-019](#bug-019) | 🟡 | Configuración | 🟢 APLICADO | Carpetas de Divisor/Fusionador, temas e idiomas se guardan pero no se usan |
| [BUG-020](#bug-020) | ⚪ | Varios | ✅ RESUELTO | Errores menores y detalles |
| [BUG-022](#bug-022) | 🟡 | CIPA | ✅ RESUELTO | 🔬 `llama_cpp` crasheaba con `FileNotFoundError` si falta la lib nativa |
| [BUG-023](#bug-023) | ⚪ | Interfaz | 🟢 APLICADO | Cierre lento del binario empaquetado |
| [BUG-024](#bug-024) | ⚪ | Configuración | ✅ RESUELTO | Sistema de temas desconectado |
| [BUG-025](#bug-025) | 🟡 | OCR / CIPA | ⏳ PENDIENTE | CIPA reescribe todo el texto (oportunidad de optimización) |
| [REV-2026-10-21](#rev-2026-10-21) | 🟠–⚪ | Varios | 🟢 APLICADO | 16 hallazgos de la revisión completa (visor, fusión, OCR, divisor, asistente, build) |
| [DOC-001](#doc-001) | ⚪ | Docs | ✅ RESUELTO | Documentación desactualizada o incorrecta |

Severidad: 🔴 crítico · 🟠 alto · 🟡 medio · ⚪ bajo

---

<a id="bug-001"></a>
## 🔴 BUG-001 — Auto-rotación no funciona correctamente ✅ RESUELTO

**Estado**: Resuelto (actualizado el 2026-10-20)  
**Fecha apertura**: 2026-10-15  
**Módulo**: `Motores/OCR/pdf_ocr.py`

### Actualización 2026-10-20

- ✅ **Punto 1 resuelto.** `aplicar_ocr()` ahora llama a
  `_extraer_palabras_con_osd()`: detecta el giro con Tesseract OSD
  (`--psm 0`, una sola pasada de OCR), hace el OCR sobre la imagen
  enderezada y des-rota las coordenadas con `_desrotar_palabras()`. Si OSD
  falla (página casi vacía) se procesa sin girar. Probado con
  `Motores/OCR/test_rotacion.py` (giros de 90°, 180° y 270°: ángulo
  detectado correcto y coordenadas exactas, desvío 0 px) y con escaneos
  sintéticos a 0°, 90° y 270° (98/98 palabras reconocidas en los tres).
- ✅ **Punto 2 resuelto (2026-10-20).** Cada palabra guarda `rot_texto` (el giro
  que pide OSD) y `_crear_capa_texto()` lo usa: el texto se dibuja girado,
  empieza en la esquina correcta de la caja y toma su ancho y su altura de
  letra de los lados que corresponden. Antes la fuente salía de 78 pt (≈7×
  mayor) y en horizontal; ahora sale de 11,3 pt, igual que en el escaneo
  derecho, y con la dirección exacta (90°, 180° y 270°). Verificado con
  `Motores/OCR/test_capa_texto.py` (≥97 % de las palabras a menos de 3 pt de
  donde estarían en la página derecha, mediana 0,4 pt, ángulo exacto), también
  en una página con `/Rotate`, y de forma independiente con
  `pdftotext -bbox`: las 98 cajas de cada giro caen sobre tinta del escaneo.
  Nota: `pypdf` pega las palabras de texto a 180°/270° (extraía 14 «palabras»,
  una por línea), lo que rompe la búsqueda por palabra completa en el
  extractor y el visor; por eso se escribe un espacio invisible tras cada
  palabra girada 180°/270° (ahora extrae las 98 con sus espacios).
- ✅ **Punto 3 resuelto (2026-10-20).** Páginas con orientaciones mezcladas
  (encabezado derecho y una tabla girada). Hallazgo: Tesseract (`psm 3`) lee
  por sí mismo un bloque girado, pero no dice cómo está girado, y a veces lo
  lee mal con confianza alta («unidad» de lado sale `pepiun` con 89 %). Ahora
  1) la pasada principal marca cada palabra con su orientación; 2) las palabras
  cuya caja no cuadra con ella (alta y estrecha en texto horizontal, o al
  revés) no «tapan» la tinta; 3) la tinta que queda se agrupa en regiones y
  cada una se lee girada a las 4 orientaciones con `psm 6`, quedándose con la
  que lee más texto con confianza ≥75; 4) los bloques que la pasada principal
  sí leyó, pero con orientación dudosa, se comprueban igual sobre su recorte.
  Una página normal sigue costando una sola lectura de OCR. Verificado con
  `Motores/OCR/test_orientaciones_mixtas.py` (tabla girada a 90° y a 270°:
  90/90 palabras, encabezado a 0° y tabla a 90°/270° exactos, todas las cajas
  sobre tinta, sin palabras inventadas). **Límite:** probado con texto limpio y
  grande; en escaneos reales con ruido pueden hacer falta más ajustes.
- Requisito: el paquete `tesseract-ocr-osd` (`osd.traineddata`).

### Descripción

La función `_extraer_palabras_con_auto_rotacion()` elige correctamente la
rotación (270° en el PDF del IMSS), pero las coordenadas de las palabras
**NO quedan bien alineadas** cuando se dibujan sobre la imagen original.

### Síntomas

- Las cajas rojas del test visual aparecen **desplazadas** del texto.
- Mucho texto real queda **sin caja**.
- Aproximadamente solo un 40% de las cajas están en la posición correcta.

### Diagnóstico (2026-10-16)

**`_desrotar_palabras()` es correcta.** ✅ Se probó con una imagen
sintética de 800×1200 y una "palabra" en (100, 300, 340, 330): se rotó con
`PIL.rotate(rot, expand=True)` a 90°, 180° y 270°, se midió la caja en la
imagen rotada y se des-rotó. Las tres veces volvió exactamente a
(100, 300, 340, 330). Las sospechas 1 y 2 de la versión anterior quedan
descartadas.

Los problemas reales son estos:

1. **La auto-rotación no está conectada.** `aplicar_ocr()` llama a
   `_extraer_palabras_con_coords()` (línea ~720), nunca a
   `_extraer_palabras_con_auto_rotacion()`. Tampoco existe ningún
   parámetro `auto_rotar`, así que el workaround anterior ("dejar
   `auto_rotar=False`") no corresponde al código actual.
2. **La capa de texto solo sabe escribir en horizontal.** Tras des-rotar,
   una palabra vertical tiene una caja alta y estrecha (p. ej. 30×240 px).
   `_crear_capa_texto()` usa `h` como tamaño de fuente y escribe en
   horizontal. Cálculo real: caja de 7,2×57,6 pt → fuente de 54,7 pt en
   horizontal. La escala horizontal se queda topada en `ESCALA_H_MIN = 20%`,
   así que la palabra ocupa 41,9 pt de ancho en lugar de 7,2 pt de alto.
   El texto invade las columnas vecinas y la selección/búsqueda no coincide
   con lo que se ve. Hay que guardar en cada palabra la rotación detectada
   y aplicar `c.rotate(rot)` al dibujarla. Los tamaños se calculan en el
   espacio de la imagen rotada: `font_size = h_r`, ancho = `w_r`.
3. **Una sola rotación para toda la página.** En una página con
   encabezado horizontal y tabla girada, se elige la rotación con más
   palabras y se pierde la otra mitad. Esto encaja con el síntoma de
   "~40% de cajas correctas". Hay que combinar palabras de varias
   rotaciones, o recortar por bloques y aplicar OSD a cada bloque.
4. **Coste ×4.** Se hace OCR completo cuatro veces por página. Es mejor
   detectar la orientación con `pytesseract.image_to_osd()` (o con `--psm 0`)
   y hacer un solo OCR.
5. El script de test (`/tmp/test_autorot.py`) ya no existe porque `/tmp` se
   borra al reiniciar. Conviene guardarlo en `tests/` dentro del repo.
   Si las cajas rojas se dibujaban sobre otra imagen (preprocesada, a otro
   DPI o rotada sin `expand=True`), eso también explicaría el desplazamiento.

`CONFIANZA_MINIMA` es **15** en el código, no 30 como decía esta nota.

### Datos del test

PDF de prueba: `OLI_BMI26_237_2449_17JULIO2026.pdf` (página 3, tabla).

Rotación detectada automáticamente: **270°** (con 882 palabras detectadas).

Resultados por rotación (psm=11, dpi=300):
| Rotación | Palabras confiables | Confianza media |
|---|---|---|
| 0° | 272 | 36.9 |
| 90° | 790 | 51.3 |
| 180° | 281 | 38.2 |
| **270°** | **838** | **62.2** |

### Archivos involucrados

- `Motores/OCR/pdf_ocr.py` → `aplicar_ocr()` (no llama a la auto-rotación)
- `Motores/OCR/pdf_ocr.py` → `_crear_capa_texto()` (no rota cada palabra)
- `Motores/OCR/pdf_ocr.py` → `_extraer_palabras_con_auto_rotacion()`

### Workaround actual

Ninguno necesario: hoy el OCR siempre trabaja a 0°. Las tablas giradas
dentro de la página salen con poco texto reconocido.

### Notas

- El PDF tiene `/Rotate=0` en todas las páginas. La tabla está **girada
  dentro** de una página vertical, no es un problema de rotación del PDF.
- pdf2image la renderiza **tal cual** (sin rotar).

---

<a id="bug-002"></a>
## 🔴 BUG-002 — La IA es muy pesada y consume muchos tokens 🟡 PARCIAL

**Estado**: 🟡 Parcial (2026-10-16). Queda el límite de la
salida, ver [BUG-025](#bug-025).  
**Módulo**: `Motores/CIPA/`

### Descripción original

> Es necesario modificar la IA: está siendo muy pesada y consume muchos
> tokens. Se arreglará posteriormente con una IA más pequeña y reduciendo
> el prompt inicial.

### Causas encontradas (2026-10-16)

Medido con el código actual:

| Qué | Tamaño | Cuántas veces se envía |
|---|---|---|
| Prompt de limpieza OCR | ~240 tokens de instrucciones | **Una vez por cada línea** de cada página |
| System prompt del asistente | ~430 tokens | En cada vuelta del bucle de tools (hasta 5 por mensaje) |
| Definición de tools | ~440 tokens | En cada vuelta del bucle |
| Resumen | hasta 9000 car. (~2600 tokens) + 1500 de salida | Por resumen |

1. **OCR + CIPA hace una llamada al modelo por línea**
   (`pdf_ocr._aplicar_cipa_por_linea`). Una página con 50 líneas son 50
   llamadas que repiten las mismas ~240 tokens de instrucciones para
   corregir 5–10 palabras cada vez. Mejor agrupar la página entera (o
   bloques de ~20 líneas) en una sola llamada, con líneas numeradas, y
   pedir la salida con la misma numeración.
2. **Cada llamada hace 2–3 peticiones HTTP extra.**
   `BackendOllama.disponible()` llama a `/api/tags` cada vez, y lo usan
   tanto `CIPA.limpiar_texto()` como `generar()`. Hay que comprobar el
   servidor una vez y cachear el resultado.
3. **El resumen pide "EXACTAMENTE 10 párrafos"** (también en el system
   prompt) con 1500 tokens de salida. Es lo más lento en CPU. Lo razonable
   son 3–5 párrafos y `max_tokens` de 600–800.
4. **No se fija `num_ctx` en Ollama.** Ollama usa por defecto un contexto
   pequeño (2048–4096 tokens según la versión). Un resumen de 9000
   caracteres más 1500 de salida no cabe. Ollama recorta el prompt
   **por el principio**, así que se pierden justo las instrucciones. Hay
   que pasar `"num_ctx": 8192` en `options`, o bajar
   `MAX_CARACTERES_CONTEXTO`.
5. **El system prompt se reconstruye en cada vuelta**, con 4 subprocesos
   `xdg-user-dir`. Se puede calcular una vez en `__init__`.
6. **Modelo**: ver [BUG-004](#bug-004). Si hay que cambiar de modelo por
   licencia, `qwen2.5:1.5b` (Apache 2.0) es más ligero y además legal.

### Aplicado 2026-10-16

1. `pdf_ocr._aplicar_cipa_por_linea` envía las líneas en bloques de 20
   (`CIPA_LINEAS_POR_LLAMADA`), numeradas `[N] texto`, y empareja la
   respuesta por número. Se mantienen las validaciones por línea (mismo
   número de palabras, similitud ≥ 0,6, no tocar palabras con dígitos).
   Prompt nuevo `Motores/CIPA/prompts/limpieza_ocr_lineas.txt` (con
   ejemplo: sin él, `qwen2.5:1.5b` quitaba la numeración y unía líneas) y
   parámetro `nombre_prompt=` en `CIPA.limpiar_texto()`.
2. `BackendOllama.servidor_disponible()` cachea el resultado 5 s por host
   (`TTL_DISPONIBLE`).
3. Resumen de 3–5 párrafos y `max_tokens=800` (prompt del resumen, system
   prompt y descripción de la tool).
4. `num_ctx = 8192` (`NUM_CTX`) en `/api/generate` y `/api/chat`, igual en
   todas las llamadas para que Ollama no recargue el modelo. Comprobado:
   con el valor por defecto (4096) un prompt de 6000 tokens se recortaba
   a 2050. Coste: ~200 MB más de RAM (1,2 → 1,4 GB).
5. El system prompt se calcula una vez en `AsistenteCIPA.__init__` (que
   ya corre en un hilo aparte).

Medido con `OLI_BMI26_237_2449_17JULIO2026.pdf` (4 páginas escaneadas,
1091 palabras, `qwen2.5:1.5b` en CPU):

| Qué | Antes | Después | Mejora |
|---|---|---|---|
| Llamadas al modelo | 115 | 7 | **16× menos** |
| Peticiones `/api/tags` | 233 | 8 | **29× menos** |
| Tokens de entrada | 32 705 | 4 777 | **6,8× menos** |
| Tokens totales | 37 117 | ~7 500 | **4,9× menos** |
| Tiempo OCR + CIPA | 224 s | 131–164 s | **1,5× menos** |
| Cambios de CIPA por PDF | 59 | 5–7 | menos alucinaciones |

- **Tiempo**: el límite ya no está en el código, sino en la CPU generando
  los ~2700 tokens de salida (el texto reescrito). Ver BUG-025.
- **Calidad**: de los 59 cambios de antes, muchos eran alucinaciones
  («Gobierno de CS» → «Gobierno de Colombia», «seguimiento» →
  «segúnimiento», números duplicados, `**` de markdown). Con bloques
  quedan 5–7, pero el modelo aún cuela alguno («Programa» → «Programo»);
  ver BUG-012.
- **Resumen**: en este PDF no cambia (el modelo ya paraba en ~300 tokens);
  el beneficio es el techo para documentos largos.

---

<a id="bug-003"></a>
## 🔴 BUG-003 — El visor revienta la RAM con cualquier imagen ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `Motores/Visualizacion/visor_pdf_motor.py` → `_imagen()` (líneas ~1256-1265)

En PDF, una imagen se dibuja sobre el **cuadrado unidad** (0,0)–(1,1), y
la matriz `cm` la escala al tamaño real. El código calcula la esquina con
`_aplicar(ctm, w, h)`, usando el ancho y alto **en píxeles**, así que el
tamaño se multiplica por la resolución de la imagen.

**Reproducción:** imagen de 1000×500 px dibujada en un recuadro de
200×100 pt. El visor pide `resize((200000, 50000))`, es decir,
**10 gigapíxeles**. En la prueba Linux mató el proceso (exit 137, OOM).
Con un PDF escaneado típico, la app entera se cierra al abrirlo en el visor.

**Solución:** usar `_aplicar(ctm, 1, 1)`. Además, comprobar el tamaño antes
de `resize` (aplicar `MAX_PIXELES_RENDER`) y voltear la imagen si `d > 0`
en la matriz.

**Aplicado:** `p1 = _aplicar(ctm, 1, 1)` en vez de `_aplicar(ctm, w, h)`, y
se añadió un guard `if aw * ah > MAX_PIXELES_RENDER: return` antes del
`resize` como red de seguridad adicional. Verificado con el caso de la
reproducción (imagen 1000×500 px en recuadro de 200×100 pt): antes pedía
un resize de 200000×50000 px, ahora calcula 200×100 px correctamente.

---

<a id="bug-004"></a>
## 🔴 BUG-004 — `qwen2.5:3b` no es Apache 2.0 ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulos**: `Motores/CIPA/config.py` (claves `limpieza` y `extraccion`),
`docs/REQUISITOS.md`

`ollama show qwen2.5:3b` devuelve **"Qwen RESEARCH LICENSE AGREEMENT"**.
Dentro de la familia Qwen2.5, las variantes 3B y 72B usan esa licencia de
investigación, que no permite uso comercial sin permiso. Las variantes
0.5B, 1.5B, 7B, 14B y 32B sí son Apache 2.0.

Esto incumple la "REGLA DE ORO" de `Motores/CIPA/modelos/MODELOS.md`, y en
`config.py` y `REQUISITOS.md` figura como `Apache-2.0`.

**Solución:** cambiar a `qwen2.5:1.5b` o `qwen2.5:7b` (Apache 2.0), o a otro
modelo MIT/Apache, y corregir la licencia en `config.py` y en los docs.
También está el nombre del modelo escrito a mano en `asistente.py:306`
(`self._backend.cargar("qwen2.5:3b")`): debería leerse de `MODELOS`.

**Aplicado:** `config.py` usa ahora `qwen2.5:1.5b` (Apache 2.0) para las
claves `limpieza` y `extraccion`. `asistente.py` importa `MODELOS` de
`.config` y carga `MODELOS["limpieza"]["archivo"]` en vez del nombre
escrito a mano. `docs/REQUISITOS.md` se actualizó (`ollama pull
qwen2.5:1.5b` y el tamaño/licencia del modelo).

---

<a id="bug-005"></a>
## 🔴 BUG-005 — El empaquetado no funciona 🟢 APLICADO

**Estado**: 🟢 Aplicado (commit `759590d`), verificado solo en Linux  
**Módulos**: `build_linux.sh`, `build_windows.bat`, `ccpdf.spec`

1. Los dos scripts ejecutan `PyInstaller ccpdf.spec`, pero el archivo se
   llama **`ccpdf.spec`**, así que el build falla en el paso 3.
2. El bucle del `.spec` que debería añadir archivos de datos no añade nada
   (el `append` está comentado). El ejecutable **no lleva
   `Motores/CIPA/prompts/limpieza_ocr.txt`**, y `CIPA._cargar_prompt()`
   lanzaría "Falta el prompt" en la versión empaquetada.
3. `hiddenimports` no incluye `pytesseract`, `pdf2image`, `reportlab`,
   `thefuzz` ni `llama_cpp`. Los motores se importan con `exec()` desde
   `app.py`, y PyInstaller no ve esos imports.
4. El nombre del ejecutable sigue siendo `CCpdf`, no `CCpdf IA`.

### Verificación 2026-10-16

- ✔ `build_linux.sh` y `build_windows.bat` ejecutan `ccpdf.spec`.
- ✔ El `.spec` añade todos los `.txt` de `Motores/CIPA/prompts/`,
  `hiddenimports` incluye `pytesseract`, `pdf2image`, `reportlab`, `thefuzz`
  y `Motores.*`, y `name="CCpdf IA"`. `llama_cpp` se excluye a propósito
  (BUG-022) en vez de añadirse.
- ✔ Inspeccionado `dist/CCpdf IA` con `pyi-archive_viewer`: lleva
  `limpieza_ocr.txt` y los 4 módulos ocultos.
- ✘ No probado: build en Windows, ni arrancar el binario.
- ⚠ El binario actual es anterior a BUG-002 y no lleva
  `limpieza_ocr_lineas.txt`: hay que recompilar (el `.spec` ya lo recoge).

---

<a id="bug-006"></a>
## 🟠 BUG-006 — El visor gira mal las páginas con /Rotate ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `visor_pdf_motor.py` → `renderizar()` (líneas ~648-653)

`/Rotate` en PDF va en **sentido horario**, pero `Image.ROTATE_90` de PIL
gira en **antihorario**. Prueba: cuadro negro arriba-izquierda en una
página de 400×200.

| /Rotate | Visor propio | Poppler (referencia) |
|---|---|---|
| 90 | abajo-izquierda | arriba-derecha |
| 270 | arriba-derecha | abajo-izquierda |

Las páginas apaisadas guardadas con `/Rotate` se ven boca abajo.
**Solución:** con `rot == 90` usar `ROTATE_270`, y con `rot == 270` usar
`ROTATE_90`.

**Aplicado:** se intercambiaron las dos ramas (`rot == 90` → `ROTATE_270`,
`rot == 270` → `ROTATE_90`). Verificado con el mismo caso de prueba del
reporte (cuadro negro arriba-izquierda, 400×200): tras el fix, `/Rotate=90`
deja el cuadro arriba-derecha y `/Rotate=270` lo deja abajo-izquierda,
igual que Poppler.

---

<a id="bug-007"></a>
## 🟠 BUG-007 — El OCR no se puede detener ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `Interfaz/app.py` → `_set_ejecutando()` (línea ~1711)

`_set_ejecutando` habilita los botones "Detener" de los paneles de
extracción, fusión, división y compresión, pero **no el de `panel_ocr`**.
Tampoco deshabilita `btn_run_ocr`. Durante un OCR largo (minutos por
documento) no hay forma de cancelar.

Además, `_hilo_motor` no incluye `ErrorOCR` en el `except` de errores
conocidos, así que un error normal del OCR (p. ej. "Falta Tesseract") se
muestra como "Error inesperado: …".

**Aplicado:** se añadió `self.btn_run_ocr` a la lista de botones que
`_set_ejecutando` habilita/deshabilita, y `self.panel_ocr` a la lista de
paneles cuyo `btn_stop` se activa. Se añadió `ErrorOCR` a la tupla de
excepciones conocidas en `_hilo_motor` (ya estaba importado a nivel de
módulo), así que un error esperado del OCR ya no se reporta como "Error
inesperado".

---

<a id="bug-008"></a>
## 🟠 BUG-008 — El divisor corta las unidades que contienen «CIUDAD» ✅ RESUELTO

**Estado**: ✅ Resuelto (commit `ab5d552`)  
**Módulo**: `Motores/Division/pdf_divisor.py` → `_RE_UNIDAD` (línea ~120)

La expresión regular deja de leer el valor en cuanto ve `CIUDAD`, `MARCA`,
`MODELO`, etc. (sin `\b` y sin exigir salto de línea), aunque esa palabra
forme parte del nombre de la unidad:

```
"UNIDAD MEDICA: HGZ 6 CIUDAD JUAREZ CHIHUAHUA"  →  "HGZ 6"
```

Si la lista tiene dos unidades que empiezan igual (`HGZ 6 CIUDAD JUAREZ` y
`HGZ 6 CIUDAD DELICIAS`), las páginas acaban como **ambiguas** y van a
`_PAGINAS_SIN_ASIGNAR.pdf`. Con «CD.» sí funciona, porque se expande
después de extraer el valor.

**Solución:** cortar en el salto de línea y exigir que las palabras de
corte vayan seguidas de `:` (`CIUDAD\s*:`), que es como aparecen como
nombre de campo.

### Verificación 2026-10-16

`_RE_UNIDAD` corta en `\n` o en `CIUDAD:`, `MARCA:`, etc. (con `:`).
Probado con `extraer_unidad_pagina`/`_RE_UNIDAD`:

- `"HGZ 6 CIUDAD JUAREZ CHIHUAHUA"` → completo ✔
- `"HGZ 6 CIUDAD DELICIAS\nMARCA: X"` → `HGZ 6 CIUDAD DELICIAS` ✔
- `"UMF 12 CIUDAD: SALTILLO"` → `UMF 12` ✔
- `"HGR 1 MARCA: ACME MODELO: Z"` → `HGR 1` ✔

Efecto secundario menor: `DATOS DEL` sin `:` en la misma línea ya no corta
(`"HGZ 2 DATOS DEL EQUIPO"` → valor completo).

---

<a id="bug-009"></a>
## 🟠 BUG-009 — Sin Ollama, CIPA nunca funciona ✅ RESUELTO

**Estado**: 🟡 Parcial (commit `ab5d552`)  
**Módulos**: `Motores/CIPA/nucleo.py`, `config.py`, `descargar_modelo.py`

- `aplicar_ocr` siempre carga la clave `"limpieza"`, que es un modelo de
  Ollama. Si el backend activo es llama.cpp, `ruta_modelo()` devuelve
  `None` y salta `ErrorCIPA`. El modelo previsto para ese caso,
  `limpieza_llama_cpp`, no se usa nunca.
- `REQUISITOS.md` dice que el modelo de llama.cpp "se descarga
  automáticamente la primera vez". **No es así:** solo se descarga a mano
  con `python -m Motores.CIPA.descargar_modelo limpieza_llama_cpp`.
- `descargar_modelo.py limpieza` intenta descargar la URL `ollama://…` con
  urllib y falla. Además, el nombre de archivo `qwen2.5:3b` lleva `:`, que
  no es válido en Windows. `--listar` marca los modelos de Ollama como
  "falta" aunque estén instalados.
- El backend se elige **una sola vez** en `CIPA.__init__`. Si Ollama
  arranca después de abrir la app, el asistente sigue diciendo "necesita
  Ollama activo" hasta reiniciar, porque `AsistenteCIPA` se crea una vez y
  se reutiliza.
- `PARAMETROS_DEFECTO["n_threads"] = 6` está fijado para "el OptiPlex".
  Se ignora en la carga, que usa `os.cpu_count()`, pero el comentario
  confunde.

### Resolución 2026-10-21

- ✔ `config.py`: el comentario de `n_threads` ya no menciona el OptiPlex.
- ✔ `_actualizar_backend()` ya usa `_servidor_activo()`, que respeta el host
  (comprobado en el código).
- ✔ `REQUISITOS.md` corregido (ver [DOC-001](#doc-001)).

### Verificación 2026-10-16

- ✔ Sin Ollama, `cargar_modelo("limpieza")` usa `limpieza_llama_cpp`
  (probado: carga Phi-3.5).
- ✔ `descargar_modelo.py` usa `ollama pull` para los modelos de Ollama, y
  `--listar` pregunta al servidor (probado: marca `✓ listo`).
- ✔ El backend se re-evalúa: si Ollama arranca más tarde, se pasa a Ollama
  (probado simulando el servidor caído y luego activo). Se usa `_servidor_activo()` (respeta `self._host`).
- ✘ `docs/REQUISITOS.md:101` sigue diciendo que el modelo de llama.cpp «se
  descarga automáticamente la primera vez»; el código no lo hace.
- ✘ `config.py:118` mantiene `# núcleos físicos del OptiPlex`.
- ⚠ Nuevo: `_actualizar_backend()` llama a `servidor_disponible()` sin
  pasarle `self._host`, así que siempre consulta `127.0.0.1:11434` aunque
  `BackendOllama` se cree con otro host.

---

<a id="bug-010"></a>
## 🟠 BUG-010 — Los errores del render del visor lanzan NameError ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `Interfaz/visor_pdf.py` → `_render()` (líneas ~314 y ~318)

```python
except ErrorVisor as e:
    self.after(0, lambda: messagebox.showerror("Error de render", str(e)))
```

En Python 3, `e` se borra al salir del bloque `except`. Cuando `after`
ejecuta la lambda, `e` ya no existe y salta
`NameError: name 'e' is not defined`. Reproducido: el usuario nunca ve el
mensaje de error. **Solución:** `msg = str(e)` antes de la lambda, y usar
`lambda m=msg: …`.

**Aplicado:** en ambos `except` (`ErrorVisor` y `Exception`) se guarda
`msg = str(e)` antes de encolar el `after(0, ...)`, y la lambda recibe el
mensaje por defecto (`lambda m=msg: messagebox.showerror(...)`), evitando
la referencia tardía a `e`.

---

<a id="bug-011"></a>
## 🟠 BUG-011 — El visor puede mostrar una página del PDF anterior 🟢 APLICADO

**Módulo**: `Interfaz/visor_pdf.py` → `_render()` / `_recibir_render()`

- La clave de la caché es `(página, zoom)`, sin el documento. Si se abre
  otro PDF mientras se renderiza el anterior, el render viejo llega con la
  misma clave (página 0, mismo zoom) y se pinta y cachea como si fuera del
  nuevo documento.
- Cada cambio de página lanza un hilo nuevo, y varios hilos usan a la vez
  el mismo `PdfReader`, que no es thread-safe. Si se cierra el documento
  durante un render, `self._doc` pasa a `None` dentro del hilo.
- `self.after()` se llama desde hilos secundarios. Tkinter no garantiza
  que eso funcione; lo seguro es la cola que ya usa `app.py`.
- Quedan muchos `print("[VISOR] …")` de depuración.

**Solución:** incluir un id de documento en la clave, usar un solo hilo de
render con un token de "petición actual", y pasar los resultados por cola.

### Resolución 2026-10-21

- 🟢 `_render_gen` (token de petición) se incrementa al cargar, cerrar o
  vaciar la caché; el hilo usa el documento capturado y los errores se
  filtran por generación. Quitados los `print("[VISOR] …")`.
- ⏳ No se cambió a un solo hilo ni a cola. Solo compilado, sin probar en GUI.

---

<a id="bug-012"></a>
## 🟡 BUG-012 — `_postprocesar_correccion` descarta o mutila texto válido ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16; parcial en `ab5d552`)  
**Módulo**: `Motores/CIPA/nucleo.py` (líneas ~256-310)

- El marcador `"A continuación"` va **sin `\n`**: cualquier texto que
  contenga esa frase (muy común en documentos) se corta ahí. Si está al
  principio, el resultado queda vacío y se descarta la corrección entera.
  Probado: una corrección válida de un texto que empieza por "A
  continuación…" se perdió.
- Pasa lo mismo con `"\nCambios"`, `"\nCorrecciones"` y `"\nNotas:"` si el
  documento tiene líneas que empiezan así.
- `limpio.strip("-= \t")` quita el guion de la primera viñeta. Probado:
  `"- Monitor\n- Teclado"` pasa a `"Monitor\n- Teclado"`, y el cambio se
  **acepta** porque la similitud sigue siendo alta.

### Verificación 2026-10-16

Probado con correcciones reales (original con erratas):

- ✔ `"A continuacion se detalan…"` (al principio) → corrección aceptada.
- ✔ `"- Monitr\n- Teclado"` → viñeta conservada.
- ✘ `"…\nCambios …"`, `"…\nCorrecciones …"` y `"…\nA continuacion …"` (a
  mitad de texto) → corrección **descartada**.
- ✘ `"Oficio de liberacion\nNotas: revisr"` → se **acepta** el texto
  recortado `"Oficio de liberación"`: se pierde una línea.

Desde BUG-002, el OCR envía las líneas como `[N] texto` y estos marcadores
ya no coinciden en ese camino; el fallo sigue en `limpiar_texto()` con
texto libre.

**Aplicado:** un marcador de corte solo se aplica si **no** aparece ya en
el original (`nucleo.py`, paso 2). Verificado: `"Oficio de liberacion\nNotas:
revisr"` → `"Oficio de liberación\nNotas: revisar"`; `"\nCambios …"` a mitad
de texto se conserva; una `Nota:` añadida por el modelo sigue cortándose.

---

<a id="bug-013"></a>
## 🟡 BUG-013 — `_modelo_existe` da falsos positivos ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `Motores/CIPA/backends/ollama.py` (líneas ~222-231)

Compara solo el nombre base: con `qwen2.5:7b` instalado, responde que
`qwen2.5:3b` **existe**. Después `generar()` falla con un 404 de Ollama y
CIPA devuelve el texto sin corregir sin avisar a nadie. La comparación por
base solo debería usarse cuando no se indica etiqueta (`qwen2.5` →
`qwen2.5:latest`).

**Aplicado:** si `nombre` incluye `:` (etiqueta explícita), ahora exige
coincidencia exacta con la lista de instalados y ya no acepta otra
etiqueta del mismo modelo base. La comparación por nombre base solo se
usa cuando no se pide etiqueta. Verificado: con `qwen2.5:7b` instalado,
`_modelo_existe("qwen2.5:3b")` devuelve `False` (antes daba `True`);
`_modelo_existe("qwen2.5:7b")` sigue devolviendo `True`, y
`_modelo_existe("llama3.2")` (sin etiqueta) resuelve correctamente a
`llama3.2:latest`.

---

<a id="bug-014"></a>
## 🟡 BUG-014 — Los atajos del asistente secuestran peticiones ✅ RESUELTO

**Estado**: ✅ Resuelto (commit `ab5d552`)  
**Módulo**: `Motores/CIPA/asistente.py` → `_detectar_atajo()` (líneas ~521-545)

- "lee el PDF informe.pdf y hazme un resumen" contiene "resumen", así que
  se ejecuta el atajo de resumen **sin pasar por el modelo**, y el usuario
  recibe: *"No hay documento cargado. Llama primero a leer_pdf."*
- `"resume"` se busca como subcadena: también salta con "resumidamente",
  "presume", etc.
- Los atajos solo deberían activarse si **ya hay un documento cargado** y
  el mensaje no menciona una ruta o un `.pdf`.

### Verificación 2026-10-16

Probado `_detectar_atajo()`: sin documento cargado nunca hay atajo; con
documento, `"lee el PDF informe.pdf y hazme un resumen"`, `"léelo
resumidamente"`, `"presume de algo"` y `"resume ~/Escritorio/x"` → sin
atajo ✔; `"dame un resumen"` → atajo ✔.

---

<a id="bug-015"></a>
## 🟡 BUG-015 — Nombres con `%` rompen Ghostscript ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16)
**Módulo**: `Motores/Compresion/pdf_compresor.py` → `_comprimir_gs()` (línea ~226)

Ghostscript interpreta `%d` en `-sOutputFile` como "una salida por página".
Con el archivo `Reporte 100%d.pdf`, Ghostscript escribió
`Reporte 1001_comprimido.pdf.tmp` y `Reporte 1002_comprimido.pdf.tmp`.
El motor interno tomó el relevo (el resumen dice `[interno-fallback]`),
pero **los `.tmp` se quedan en la carpeta de salida**. Solución: escapar
`%` → `%%` en la ruta de salida.

**Aplicado:** se construye `ruta_out_gs = ruta_out.replace("%", "%%")` y
se usa esa ruta escapada en `-sOutputFile`; la comprobación de existencia
del archivo sigue usando `ruta_out` (la ruta real, sin escapar). Verificado:
`"Reporte 100%d.pdf"` pasa a `"Reporte 100%%d.pdf"` en el argumento de
Ghostscript, que ya no lo interpreta como patrón de página.

---

<a id="bug-016"></a>
## 🟡 BUG-016 — El historial del asistente puede quedar corrupto ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-16; parcial en `ab5d552`)  
**Módulo**: `Motores/CIPA/asistente.py`

- `_recortar_historial()` corta por número de mensajes sin respetar los
  grupos `assistant(tool_calls) → tool → …`. Pueden quedar mensajes
  `role: tool` sin su llamada, y el modelo se confunde.
- Si el bucle llega a 5 iteraciones, el historial se queda con llamadas y
  resultados de tools pero **sin respuesta final**, y no se recorta. El
  siguiente mensaje arrastra todo eso (más tokens, ver BUG-002).
- `MAX_TURNOS_HISTORIAL = 10` dice "últimos N mensajes", pero en realidad
  guarda 20.

### Verificación 2026-10-16

- ✔ `_recortar_historial()` quita los `tool` huérfanos del principio
  (probado con un corte que caía en `tool`).
- ✔ La constante es ahora `MAX_MENSAJES_HISTORIAL = 10` y guarda 10.
- ✔ (corregido) Si el bucle llega a 5 iteraciones, `enviar()` ya llama a
  `_recortar_historial()` antes de devolver el fallback.

---

<a id="bug-017"></a>
## 🟡 BUG-017 — El visor no muestra bien escaneos ni fuentes modernas ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-23). El visor dibuja con PDFium (`pypdfium2`, BSD-3 / Apache-2.0,
el motor de PDF de Chrome). Verificado con un PDF de Chromium (Type0/Identity-H), uno de
LibreOffice (comillas, «—», «€», «…») y un escaneo CCITT G4: los tres se ven bien; con el motor
propio salían basura, cuadros y en blanco. Test: `Motores/Visualizacion/test_render_pdfium.py`.
El motor propio queda de respaldo si PDFium no está instalado o falla en una página; lo de
abajo describe sus limitaciones.

**Módulo**: `visor_pdf_motor.py` (limitaciones del motor propio)

- **Imágenes que no se dibujan** (además de BUG-003): espacio de color
  `/ICCBased` (muy común) o `/Indexed`, imágenes de 1 bit, `CCITTFaxDecode`
  y `JBIG2Decode`. Los dos últimos son el formato típico de los escaneos en
  blanco y negro, que se ven **en blanco**. También se ignoran `/SMask` y
  `/Decode`.
- **Texto con fuentes Type0 / Identity-H** (Word, LibreOffice y la mayoría
  de generadores actuales): los bytes se decodifican como latin-1 sin
  `/ToUnicode` ni `/Encoding`, y se dibujan caracteres basura.
- Recorte (`W`/`W*`) no aplicado, relleno par-impar ignorado, grosor de
  línea que no escala con el zoom, texto girado (Tm con rotación) dibujado
  en horizontal y sin soporte de imágenes en línea (`BI … ID … EI`).

Dado que el OCR ya depende de Poppler, puede valer la pena usar
`pdf2image`/`pdftoppm` (o PyMuPDF, ojo que es AGPL) como renderizador del
visor y dejar el motor propio como respaldo.

---

<a id="bug-018"></a>
## 🟡 BUG-018 — Bloqueos de la interfaz 🟢 APLICADO

**Estado**: 🟢 Aplicado (commit `4bd88db`)

- `CIPA()` hace una petición HTTP con 3 s de timeout en el constructor. Hoy
  se llama desde hilos, pero cualquier uso en el hilo principal congela la
  ventana.
- La búsqueda del visor (`VisorPDF._buscar`) extrae el texto de **todas**
  las páginas en el hilo principal. Con un PDF grande, la ventana se queda
  congelada.
- `Interfaz/app.py` importa `Motores.CIPA` al arrancar. Si falla
  `RUTA_CACHE.mkdir()` (permisos), lanza una excepción que no es
  `ImportError` y **la app no abre**.

### Verificación 2026-10-16

- ✔ `CIPA()` ya no hace peticiones en el constructor (medido: 0,000 s).
- 🟢 `VisorPDF._buscar` lanza `doc.buscar()` en un hilo. No probado en la
  interfaz; además el resultado vuelve con `self.after()` desde el hilo,
  el mismo patrón que señala BUG-011.
- 🟢 `app.py` importa `Motores.CIPA` con `except Exception`. No probado
  forzando el fallo de `mkdir`.

---

<a id="bug-019"></a>
## 🟡 BUG-019 — Opciones de configuración que no hacen nada 🟢 APLICADO

**Estado**: 🟡 Parcial (commit `4bd88db`)  
**Módulos**: `Interfaz/app.py`, `Interfaz/config.py`

- En Configuración → Carpetas se pueden guardar carpetas para **Divisor** y
  **Fusionador**, pero `_iniciar_division` y `_resolver_salida_fusion` no
  llaman a `_carpeta_defecto()`. Solo funcionan las de Extracción y
  Compresor.
- `config.py` define 6 temas y 2 idiomas, pero la interfaz usa la paleta
  fija `P` y casi todos los textos están escritos en el código. No hay
  pestaña de Apariencia.

### Resolución 2026-10-21

- ✔ Carpetas de Divisor y Fusionador: ya se usan (verificado en el código el 16-10).
- ✔ Temas: ver [BUG-024](#bug-024).
- 🟢 Idioma: nuevo selector en Configuración → Apariencia (se aplica al reiniciar).
  Traduce (es/en) la barra lateral, el inicio y Configuración. El resto de pantallas
  (formularios, mensajes del OCR, diálogos) **sigue en español**: traducirlo
  entero son cientos de textos. Probado: arranque y recorrido de las 9 vistas en
  `es` y `en`, y apertura de Configuración, sin errores; no vi el resultado en pantalla.

### Verificación 2026-10-16

- ✔ `_carpeta_base_fusion` y `_iniciar_division` usan
  `_carpeta_defecto("fusionador")` / `("divisor")` (leído en el código, no
  probado en la interfaz).
- ✘ Temas: siguen sin conectarse (ver [BUG-024](#bug-024)). El commit dice
  «temas recuperados», pero `app.py` no usa `TEMAS` ni `tema()`.
- ✘ Idiomas: `IDIOMAS` tampoco se usa en `app.py`.

---

<a id="bug-020"></a>
## ⚪ BUG-020 — Errores menores ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-20; parcial desde el commit `4bd88db`)

- **Fusionar → mover arriba/abajo** con varias filas seleccionadas en el
  borde (p. ej. filas 0 y 1 hacia arriba) desordena la lista: la fila 1 se
  intercambia con la 0, que estaba seleccionada.
- **Actualizador**: `REPO = "tu-usuario/CCpdf"` es un marcador de posición,
  así que siempre responde "Repositorio no publicado todavía".
- **Ghostscript en Windows**: `sorted(glob(...))` ordena por texto, así que
  `gs9.x` va después de `gs10.x` y elige la versión más antigua.
- **Compresor**: `obj._data` es un atributo privado de pypdf y puede
  desaparecer en una actualización.
- **Imports duplicados**: `app.py` mete cada carpeta de `Motores/` en
  `sys.path` e importa `pdf_motor` como módulo suelto. El mismo archivo
  queda cargado dos veces (`pdf_motor` y `Motores.Extraccion.pdf_motor`),
  con clases de excepción distintas. Los `exec()` de `_try_import` también
  impiden que PyInstaller y Pyright vean los imports.
- **Dashboard**: la tarjeta "Módulos: 7, 5 activos" no coincide (hay 9
  módulos).
- **Asistente**: la interfaz invita a preguntar "¿Cómo divido un PDF por
  unidad médica?", pero el system prompt no incluye cómo se usa cada
  módulo, así que el modelo se lo inventará.
- **Fuentes**: `Segoe UI` y `Consolas` no existen en Linux, y Tk usa una
  fuente sustituta.
- Al cerrar la app con un proceso en marcha, el hilo daemon muere a mitad
  de escritura y pueden quedar archivos `.tmp`.

### Verificación 2026-10-16

- ✔ Fusionar → mover: probado `_fusion_mover` con filas `[0,1]↑`, `[1,2]↑`,
  `[2,3]↓`, `[0,2]↓` y `[0,3]↑`; orden y selección correctos.
- ✔ Actualizador: `REPO = "LeShite/CCpdf-IA"`.
- ✔ Ghostscript en Windows: se ordena por versión numérica
  (`_clave_version_gs`). No probado en Windows.
- ✔ Dashboard: «9 / 7 activos».
- ✘ Compresor: sigue usando `obj._data` (`pdf_compresor.py:299`).
- ✘ Imports duplicados: siguen el `sys.path.insert` y el `exec()` de
  `_try_import` en `app.py`.
- ✘ Asistente: el system prompt sigue sin explicar cómo se usa cada módulo.
- ✘ Fuentes: siguen `Segoe UI` y `Consolas` fijas.
- ✘ Cierre con proceso en marcha: `_al_cerrar` activa la cancelación pero
  no espera al hilo antes de `destroy()`.


### Resolución 2026-10-20

- ✔ **Compresor**: ya no usa `obj._data`; el tamaño del stream sale de
  `/Length` (API pública de pypdf), y si falta, de `get_data()`. Comprobado:
  PDF de 6560 KB con una imagen grande → 103 KB con el motor interno.
- ✔ **Imports duplicados**: `app.py` importa todo como paquete
  (`Interfaz.*`, `Motores.*`); desaparecen `_preparar_path`, `_try_import` y
  los `exec()`. Cada motor se carga una sola vez (una única clase de
  excepción) y PyInstaller y Pyright pueden seguir los imports. `ccpdf.spec`
  ya no necesita `Interfaz` en `pathex`.
- ✔ **Asistente**: el system prompt explica cómo se usa cada módulo
  (Extracción, Fusionar, Dividir, Comprimir, OCR, Visor, Firmar).
- ✔ **Fuentes**: se usa la primera familia instalada de cada lista
  (`Segoe UI` → `Helvetica Neue` → `Noto Sans` → `DejaVu Sans`; `Consolas` →
  `Menlo` → `DejaVu Sans Mono`). En este equipo Linux: Noto Sans y DejaVu
  Sans Mono. No probado en Windows ni en macOS.
- ✔ **Cierre con un proceso en marcha**: `_al_cerrar` activa la cancelación y
  espera hasta 8 s al hilo del motor antes de salir. Comprobado con un hilo
  que tarda 1 s en cerrar: la ventana espera 1,0 s.

---

<a id="bug-022"></a>
## 🟡 BUG-022 — `llama_cpp` crashea con `FileNotFoundError` si falta la lib nativa ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-20; el crash, desde el commit `759590d`)  
**Módulo**: `Motores/CIPA/backends/llama_cpp.py`

El `except` solo atrapa `ImportError`, pero la lib nativa lanza
`FileNotFoundError`/`OSError`.

**Fix aplicado**: ampliar el `except` a
`(ImportError, OSError, FileNotFoundError)`.

**Pendiente**: mejorar el mensaje de degradación.

### Verificación 2026-10-16

- ✔ Simulado un `FileNotFoundError` al importar `llama_cpp`: el módulo
  carga con `HAY_LLAMA_CPP = False` y CIPA sigue funcionando con Ollama.
- ✘ La degradación es silenciosa: no se registra ni se muestra ningún aviso.


### Resolución 2026-10-20

- ✔ Si `llama_cpp` está instalado pero su librería nativa falla
  (`OSError`/`FileNotFoundError`), se guarda el motivo en `ERROR_LLAMA_CPP`
  y se registra un aviso en el logger `CIPA`. Si simplemente no está
  instalado (lo normal con Ollama) no se avisa.
- ✔ El error «no hay ningún backend de CIPA disponible» ahora incluye el
  motivo (`(llama-cpp-python: FileNotFoundError: …)`) y `estado()` lo expone
  como `llama_cpp_error`. Comprobado simulando una librería nativa rota.

---

<a id="bug-023"></a>
## ⚪ BUG-023 — Cierre lento del binario empaquetado 🟢 APLICADO

**Estado**: 🟢 Aplicado (2026-10-20); sin verificar en Windows  
**Módulo**: `main.py` / `Interfaz/app.py`

El binario empaquetado (PyInstaller) tarda varios segundos en cerrarse tras
pulsar salir o cerrar la ventana. Probablemente algún hilo daemon (render del
visor, motor en ejecución, etc.) sigue vivo y retrasa la salida del proceso,
o el runtime de PyInstaller tarda en desmontar el entorno empaquetado.

Relacionado con la nota de BUG-020 sobre hilos daemon que mueren a mitad de
escritura al cerrar con un proceso en marcha.

### Pendiente

Reproducir con el binario empaquetado (no se reproduce necesariamente
ejecutando desde código fuente) y diagnosticar qué mantiene el proceso vivo.


### Diagnóstico y fix 2026-10-20

- **Se reproduce desde el código fuente**, no solo empaquetado. `destroy()` de
  la ventana principal desmonta una a una unas 1100 piezas de Tk justo antes de
  que el proceso termine. En un equipo Linux con el gestor de entrada
  (`ibus-daemon`) saturado tardó ≈7,5 s (el proceso entero, ≈9,9 s); con el
  gestor sano, 0,04 s. La saturación de `ibus` también hacía lento el arranque
  (30–57 s frente a 4 s), con el mismo código antes y después de los cambios.
- **Fix**: `_al_cerrar` espera al hilo del motor, oculta la ventana
  (`withdraw()`) y sale del `mainloop` (`quit()`) en lugar de `destroy()`.
  Cierre medido: 0,16 s desde el código fuente y 0,11 s con un binario de
  PyInstaller en Linux (la limpieza de la carpeta temporal del `onefile` son
  0,02 s). Con `ibus` saturado: `destroy` 7,5 s frente a `quit` 0,08 s.
- **Sin verificar**: Windows; y el binario construido tras los últimos cambios
  solo se comprobó que arranca y se mantiene vivo, no su tiempo de cierre.

---

<a id="bug-024"></a>
## ⚪ BUG-024 — Sistema de temas desconectado ✅ RESUELTO

**Estado**: ✅ Resuelto (2026-10-20)  
**Módulo**: `Interfaz/config.py` + `Interfaz/app.py`

Los 6 temas están definidos en `config.py` pero la interfaz usa la paleta
`P` fija y no tiene sección en Configuración para aplicarlos.

**Pendiente**: conectar la selección de tema en Configuración → Apariencia.


### Resolución 2026-10-20

- ✔ La paleta `P` se rellena al arrancar con el tema elegido
  (`_aplicar_tema`, antes de crear ningún widget); los colores de los módulos
  y de las tarjetas del Dashboard salen también del tema. El modo claro/oscuro
  de CustomTkinter se decide por la luminancia del fondo.
- ✔ Configuración → **Apariencia**: selector de tema con vista previa de
  colores. El cambio se aplica al reiniciar CCpdf (la interfaz entera se
  construye con la paleta al abrirse).
- ✔ Siete temas: los seis de `config.py` y **Enterprise**, el aspecto original
  de la app, que pasa a ser el predeterminado para que conectar los temas no
  cambie la interfaz. Los archivos de preferencias antiguos (formato 1)
  guardaban `"tema": "aero"` sin que se pudiera elegir; ese valor se ignora
  (`version_prefs` = 2).
- ✔ Comprobado: los siete temas arrancan y recorren las 9 vistas sin errores;
  la selección se guarda; el archivo antiguo se migra.
- ⏳ **Sin verificar el aspecto visual** (contraste, legibilidad) de cada tema:
  la sesión estaba bloqueada y no se pudo capturar la ventana.
- ⏳ Quedan colores fijos en `dialogo_confirmar.py` (7) y `visor_pdf.py` (3), que
  no usan la paleta; y el idioma (BUG-019) sigue sin aplicarse.

---

<a id="bug-025"></a>
## 🟡 BUG-025 — CIPA reescribe todo el texto (oportunidad de optimización) ⏳ PENDIENTE

**Estado**: ⏳ Pendiente, no urgente  
**Módulo**: `Motores/OCR/pdf_ocr.py`

Tras [BUG-002](#bug-002), el tiempo de CIPA está dominado por la generación
de tokens de salida: el modelo devuelve el texto completo reescrito
(~2700 tokens para un PDF de 4 páginas, ~675 por página). En CPU, esto
marca el límite.

**Idea**: enviar al modelo SOLO las líneas sospechosas (palabras fuera de
diccionario, confianza baja de Tesseract, caracteres raros), no todo el
texto. Debería reducir la salida a ~200–500 tokens por PDF → 5–10× más
rápido.

---

<a id="doc-001"></a>
## ⚪ DOC-001 — Documentación desactualizada ✅ RESUELTO

**Estado**: 🟡 Parcial (commit `4bd88db`)

- `README.md` dice que el OCR usa "Tesseract + IA", pero la IA solo actúa si
  se marca "Usar CIPA" y sufre BUG-002/BUG-009.
- `Motores/CIPA/README.md` y `Motores/CIPA/modelos/MODELOS.md` hablan de
  Qwen2.5-**1.5B** y de llama.cpp como único runtime. El código usa
  Qwen2.5-**3B** vía Ollama.
- `docs/REQUISITOS.md`: licencia de Qwen incorrecta (BUG-004) y "descarga
  automática" que no existe (BUG-009).
- `requirements.txt` repite `llama-cpp-python` y `huggingface-hub` en un
  bloque comentado de "descomentar cuando implementemos". `huggingface-hub`
  no se importa en ningún sitio (la descarga usa `urllib`).
- `pdf_ocr.py`: el comentario de `CONFIANZA_MINIMA` dice "30", pero el
  valor es 15.
- `.gitignore` ignora `*.pdf`, así que los PDFs de prueba de BUG-001 no
  pueden versionarse sin la excepción `!tests/samples/*.pdf`.

### Verificación 2026-10-16

- ✔ `README.md`: el OCR aparece como Tesseract + CIPA opcional.
- ✔ `Motores/CIPA/README.md` y `MODELOS.md`: Qwen2.5-1.5B vía Ollama y
  Phi-3.5 vía llama.cpp como fallback.
- ✔ `REQUISITOS.md`: licencia de Qwen correcta (BUG-004).
- ✘ `REQUISITOS.md:101`: sigue la «descarga automática» (BUG-009).
- 🟡 `requirements.txt`: se quitó el bloque duplicado, pero
  `huggingface-hub` sigue listado y no se importa en ningún sitio.
- ✔ `pdf_ocr.py`: el comentario de `CONFIANZA_MINIMA` dice 15.
- ✘ `.gitignore`: `!tests/samples/*.pdf` sigue comentado.

### Resolución 2026-10-21

- ✔ `REQUISITOS.md`: sin «descarga automática» (el modelo de llama.cpp se baja con
  `python -m Motores.CIPA.descargar_modelo limpieza_llama_cpp`); añadidos los datos
  OSD de Tesseract (necesarios para detectar páginas giradas) y Ghostscript (opcional).
- ✔ `requirements.txt` y `REQUISITOS.md`: quitado `huggingface-hub` (no se importa).
- ✔ `Motores/CIPA/README.md`: completada la sección «Estructura» y añadidos los backends.
- ✔ `README.md`: características actuales (orientación, visor, temas) e instalación.
- ✔ `.gitignore`: activada la excepción `!tests/samples/*.pdf`.

---

<a id="rev-2026-10-21"></a>
## 🟠 REV-2026-10-21 — Hallazgos de la revisión completa 🟢 APLICADO

Informe completo: `REVISION-CCpdf.md`. 🔬 = reproducido con un script de prueba.
**Todos los arreglos solo se compilaron (`py_compile`); no se probaron en GUI,
ni con pypdf ni con Tesseract.**

| # | Módulo | Problema | Arreglo |
|---|---|---|---|
| 1 🔬 | Visor | Curvas Bézier con doble transformación | `_bezier` ya no transforma dos veces |
| 2 | Visor | Ver BUG-011 | Ver BUG-011 |
| 3 🔬 | Fusión | PDF fusionado con permisos 600 | chmod según umask antes de reemplazar |
| 4 | Fusión | Pisaba `fusionado.pdf` sin avisar | Pregunta antes de reemplazar |
| 5 | CIPA | El prompt pedía unir/separar palabras y el código lo descartaba | Prompt: solo corrección dentro de cada palabra |
| 6 | OCR | Sin progreso por página; Detener decía "archivo"; lecturas extra costosas | Progreso por página; "página actual"; `MAX_REGIONES` 12→6 |
| 7 | OCR | Pisaba entradas (`a_ocr.pdf`) | Las entradas cuentan como rutas usadas (solo con destino absoluto; con destino relativo aún puede pisarlas) |
| 8 | OCR | `_pagina_tiene_imagen` no miraba Form XObjects | Mira dentro de los Forms |
| 9 | Divisor | Progreso no monótono | Lectura 0-50 %, escritura 50-100 % |
| 10 🔬 | Divisor | Unidad en dos renglones; nombres reservados de Windows | Regex y saneado de nombres |
| 11 | — | Ya estaba resuelto | — |
| 12 | Fusión | Conteo con páginas parciales | Cuenta páginas parciales |
| 13 | Asistente | Historial al fallar, «busca», «/» y «~», truncado sin aviso | Corregidos, con aviso de truncado |
| 14 | CIPA | `descargar_modelo.py` sin mensaje de error y `.gguf` truncado válido | Imprime el error; descarga a `.part` |
| 15 | Build | `build_linux.sh` mostraba `CCpdf\ IA` | Ahora `./dist/CCpdf` |
| 16 | Varios | `guardar()` ocultaba errores; imports sin usar | Devuelve `bool` y la UI avisa; imports quitados |

### Sigue pendiente

- Coste real del OCR: medir con un escaneo con logos o firmas (el recorte de
  `MAX_REGIONES` es una estimación).
- Del #16: nombres de tema siempre en español, "v1.0.1" repetida en `app.py`,
  `asistente.py` y `README.md`, y las funciones sin uso
  `_extraer_palabras_con_auto_rotacion` y `renderizar_miniatura`.
- Auditoría 2 (2026-10-21, `AUDITORIA-2-CCpdf.md`): corregidos el PDF en blanco de Ghostscript con
  contraseña, las líneas con "…" que desaparecían del visor, `llama-cpp-python` (ahora en
  `requirements-ai.txt`), el botón Detener del asistente, el «OK, 0 palabras» con un idioma de
  Tesseract sin instalar, la tolerancia ortográfica con números y el divisor que podía pisar el PDF
  de origen. Siguen pendientes, entre otros: destino relativo del OCR (el arreglo #7 solo vale con
  rutas absolutas). Las comillas, guiones y «€» del visor se resolvieron con BUG-017 (PDFium).
