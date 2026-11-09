# CCpdf

Suite local de gestión de PDF con inteligencia artificial integrada.

## Características

- **Local por defecto** — ningún dato sale de tu equipo. Opcionalmente, la IA puede usar una API
  externa (DeepSeek/Gemini) si tú lo eliges en Configuración → IA; entonces el texto sí se envía al proveedor.
- **CIPA** — Capa de Inteligencia de Procesamiento Aumentado (IA local).
- **OCR** con Tesseract para PDFs escaneados, con limpieza opcional vía CIPA
  (IA local, activable con "Usar CIPA"; ver limitaciones en
  `docs/KNOWN_ISSUES.md`).
  El OCR detecta páginas giradas y bloques en otras orientaciones, y conserva
  la orientación en la capa de texto.
- **Extracción**, **fusión**, **división** y **compresión** de PDFs
  (compresión con motor interno o Ghostscript).
- **Visor** de PDF integrado.
- **Metadatos**: ve y borra la información oculta (autor, programa, fechas, XMP).
- **Arrastrar y soltar** PDFs y carpetas sobre la ventana.
- **Comparar** dos versiones de un PDF (texto y visual) con informe.
- **Historial** con **deshacer / rehacer** y copias temporales (1 día a 1 año; 1 mes recomendado).
- **Actualizaciones** desde kodesoft.site, conservando tus datos (ver `docs/ACTUALIZACIONES.md`).
- **Temas**: 7 aspectos elegibles en Configuración → Apariencia (se aplican al reiniciar).
- **Licencia MIT** — código abierto.

## Estado

Versión **1.5.0**. Ver `CHANGELOG.md` y `docs/KNOWN_ISSUES.md`.

## Instalación

Requisitos y pasos en `docs/REQUISITOS.md`. Resumen:

```bash
pip install -r requirements.txt
python3 main.py
```

Necesita Tesseract en el sistema para el OCR.
La IA local con llama.cpp (sin Ollama) es opcional: `pip install -r requirements-ai.txt`.

Desarrollado por Iker · Kodesoft