# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

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

- **OCR de escaneos girados (BUG-001, parcial)**: la detección de giro con Tesseract OSD ahora está
  conectada a `aplicar_ocr()` y los escaneos a 90°, 180° y 270° se reconocen. Pendiente: la capa de texto
  de esas páginas queda mal colocada. Ver `docs/KNOWN_ISSUES.md`.
- **Visor**: los renders obsoletos se descartan con un contador de generación (evita pintar una
  página vieja tras cambiar de página o zoom) y se quitan las trazas de depuración `[VISOR]`.

### Añadido

- `Motores/OCR/test_rotacion.py`: prueba de la detección de giro y del des-rotado de coordenadas.
- `.gitignore`: se ignora `.claude/`.

### Heredado de CCpdf IA Alpha (2026-10-15 a 2026-10-16)

- **CIPA**: IA local con backend Ollama (preferido) o llama.cpp, asistente conversacional con
  tool calling y limpieza opcional del OCR.
- **OCR** con Tesseract: capa de texto invisible, CropBox, escalado y corrección por línea con CIPA.
- Vistas **OCR** y **Asistente** en la interfaz.
- Correcciones de bugs registrados en `docs/KNOWN_ISSUES.md`: bloque 1 (7 críticos), bloque 2
  (5 medios y empaquetado, BUG-005), bloque 5 (BUG-018, 019, 020, 023, 024 y DOC-001), BUG-002
  (consumo de tokens de CIPA reducido 4,9×), BUG-009, BUG-012 y BUG-016.
