"""Comparación: diferencias de texto y visuales entre dos versiones de un PDF."""
from .pdf_comparador import (
    comparar_pdfs, diferencias_texto, mascara_diferencias,
    ErrorComparacion, ResumenComparacion, CambioPagina,
)

__all__ = [
    "comparar_pdfs", "diferencias_texto", "mascara_diferencias",
    "ErrorComparacion", "ResumenComparacion", "CambioPagina",
]
