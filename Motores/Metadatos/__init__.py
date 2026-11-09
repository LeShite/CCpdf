"""Metadatos: ver y limpiar la información oculta de los PDFs (privacidad)."""
from .pdf_metadatos import (
    leer_metadatos, limpiar_metadatos,
    ErrorMetadatos, InfoMetadatos, ResumenMetadatos, CAMPOS_INFO,
)

__all__ = [
    "leer_metadatos", "limpiar_metadatos",
    "ErrorMetadatos", "InfoMetadatos", "ResumenMetadatos", "CAMPOS_INFO",
]
