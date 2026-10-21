"""
CIPA — Capa de Inteligencia de Procesamiento Aumentado.

IA para CCpdf. Local por defecto (nada sale del equipo); opcionalmente API externa
(`configurar_modo("api", ...)`), que sí envía el texto al proveedor.

Uso:
    from Motores.CIPA import CIPA, AsistenteCIPA

    # Para tareas puntuales (limpieza OCR, etc.)
    cipa = CIPA()

    # Para chat conversacional con tool calling
    asistente = AsistenteCIPA()
    respuesta = asistente.enviar("lee el PDF de mi escritorio")
"""
from .nucleo import CIPA, ErrorCIPA, configurar_modo
from .asistente import AsistenteCIPA

__all__ = ["CIPA", "ErrorCIPA", "AsistenteCIPA", "configurar_modo"]
__version__ = "1.0.0"