"""Visualización: render de PDF con PDFium (pypdfium2) y motor propio de respaldo."""
from .visor_pdf_motor import (
    DocumentoPDF, abrir_pdf, ErrorVisor, InfoDocumento,
    ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT,
)

__all__ = [
    "DocumentoPDF", "abrir_pdf", "ErrorVisor", "InfoDocumento",
    "ZOOM_MIN", "ZOOM_MAX", "ZOOM_DEFAULT",
]
