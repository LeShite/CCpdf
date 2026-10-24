"""Motores de CCpdf: lógica pura sin dependencias de GUI."""
import threading

# PDFium (pypdfium2) no es thread-safe ni entre documentos distintos, y lo usan el
# visor y el OCR desde hilos distintos: toda llamada a PDFium va bajo este lock.
LOCK_PDFIUM = threading.Lock()
