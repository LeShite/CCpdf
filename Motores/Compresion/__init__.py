"""Compresión: reducir el tamaño de los PDFs."""
from .pdf_compresor import (
    comprimir_pdfs, info_motor, buscar_ghostscript,
    ErrorCompresion, ResumenCompresion, NIVELES,
)
from .instalar_gs import instalar_ghostscript

__all__ = [
    "comprimir_pdfs", "info_motor", "buscar_ghostscript", "instalar_ghostscript",
    "ErrorCompresion", "ResumenCompresion", "NIVELES",
]
