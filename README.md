# CCpdf

Suite local de gestión de PDF con inteligencia artificial integrada.

## Características

- **100% local** — ningún dato sale de tu equipo.
- **CIPA** — Capa de Inteligencia de Procesamiento Aumentado (IA local).
- **OCR** con Tesseract para PDFs escaneados, con limpieza opcional vía CIPA
  (IA local, activable con "Usar CIPA"; ver limitaciones en
  `docs/KNOWN_ISSUES.md`).
  El OCR detecta páginas giradas y bloques en otras orientaciones, y conserva
  la orientación en la capa de texto.
- **Extracción**, **fusión**, **división** y **compresión** de PDFs
  (compresión con motor interno o Ghostscript).
- **Visor** de PDF integrado.
- **Temas**: 7 aspectos elegibles en Configuración → Apariencia (se aplican al reiniciar).
- **Licencia MIT** — código abierto.

## Estado

Versión **1.0.1**. Ver `CHANGELOG.md` y `docs/KNOWN_ISSUES.md`.

## Instalación

Requisitos y pasos en `docs/REQUISITOS.md`. Resumen:

```bash
pip install -r requirements.txt
python3 main.py
```

Necesita Tesseract y Poppler en el sistema para el OCR.

Desarrollado por Iker · Kodesoft