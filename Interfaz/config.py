"""
config.py — Preferencias, temas, idiomas y carpetas de CCpdf.

Guarda la configuración en ~/.config/CCpdf/config.json (Linux/macOS) o
%APPDATA%/CCpdf/config.json (Windows). Si el archivo no existe, se usan
los valores por defecto.
"""
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# UBICACIÓN DEL ARCHIVO
# ---------------------------------------------------------------------------
def _ruta_config() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "CCpdf"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "CCpdf"
    else:
        base = Path.home() / ".config" / "CCpdf"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = Path.home() / ".ccpdf"
        base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


# ---------------------------------------------------------------------------
# TEMAS  (sin cambios)
# ---------------------------------------------------------------------------
TEMAS = {
    # El aspecto original de la app (sidebar oscura, superficie clara). Es el
    # tema por defecto para que conectar los temas no cambie la interfaz.
    "enterprise": {
        "etiqueta_es": "Enterprise (predeterminado)", "etiqueta_en": "Enterprise (default)",
        "fondo": "#F8FAFC", "sidebar": "#0F172A", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#F1F5F9", "activo": "#1E293B", "hover_sidebar": "#1E293B",
        "border": "#CBD5E1", "border_suave": "#E2E8F0",
        "acento": "#4F46E5", "acento_hover": "#4338CA", "acento_suave": "#A5B4FC",
        "aqua": "#06B6D4", "lima": "#84CC16",
        "texto": "#0F172A", "texto_suave": "#475569", "texto_tenue": "#94A3B8",
        "texto_blanco": "#FFFFFF",
        "sb_texto": "#94A3B8", "sb_texto_activo": "#F8FAFC", "sb_seccion": "#64748B",
        "ok": "#10B981", "ok_hover": "#059669",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#06B6D4", "color_fusionar": "#10B981",
        "color_dividir": "#F59E0B", "color_comprimir": "#3B82F6",
        "color_visor": "#EC4899", "color_firmar": "#9C27B0",
    },
    "aero": {
        "etiqueta_es": "Aero (cielo)",
        "etiqueta_en": "Aero (sky)",
        "fondo": "#E8F4FC", "sidebar": "#B8DFF5", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#F0F9FF", "activo": "#FFFFFF", "hover_sidebar": "#CFE8F7",
        "border": "#A5D5EF", "border_suave": "#D6EDFA",
        "acento": "#1E88E5", "acento_hover": "#1565C0", "acento_suave": "#64B5F6",
        "aqua": "#00BCD4", "lima": "#8BC34A",
        "texto": "#0D2F4F", "texto_suave": "#4A6B87", "texto_tenue": "#7BA0BC",
        "texto_blanco": "#FFFFFF",
        "ok": "#4CAF50", "ok_hover": "#388E3C",
        "stop": "#EF5350", "stop_hover": "#E53935",
        "color_extraer": "#00BCD4", "color_fusionar": "#4CAF50",
        "color_dividir": "#FF9800", "color_comprimir": "#03A9F4",
        "color_visor": "#E91E63", "color_firmar": "#9C27B0",
    },
    "oscuro": {
        "etiqueta_es": "Oscuro", "etiqueta_en": "Dark",
        "fondo": "#0D1117", "sidebar": "#0B0F16", "tarjeta": "#161B24",
        "tarjeta_hover": "#1E2532", "activo": "#1A2230", "hover_sidebar": "#1A2230",
        "border": "#1F2733", "border_suave": "#222A38",
        "acento": "#4F8EFF", "acento_hover": "#6BA3FF", "acento_suave": "#2E4C8A",
        "aqua": "#22D3EE", "lima": "#A3E635",
        "texto": "#E6EAF2", "texto_suave": "#7A879C", "texto_tenue": "#4B5566",
        "texto_blanco": "#FFFFFF",
        "ok": "#22C55E", "ok_hover": "#16A34A",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#8B5CF6", "color_fusionar": "#22C55E",
        "color_dividir": "#F59E0B", "color_comprimir": "#06B6D4",
        "color_visor": "#EC4899", "color_firmar": "#6366F1",
    },
    "claro": {
        "etiqueta_es": "Claro (limpio)", "etiqueta_en": "Light (clean)",
        "fondo": "#F5F6F8", "sidebar": "#EAECEF", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#F7F8FA", "activo": "#FFFFFF", "hover_sidebar": "#DEE2E7",
        "border": "#D1D6DD", "border_suave": "#E5E8ED",
        "acento": "#3B82F6", "acento_hover": "#2563EB", "acento_suave": "#93C5FD",
        "aqua": "#06B6D4", "lima": "#84CC16",
        "texto": "#111827", "texto_suave": "#4B5563", "texto_tenue": "#9CA3AF",
        "texto_blanco": "#FFFFFF",
        "ok": "#10B981", "ok_hover": "#059669",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#8B5CF6", "color_fusionar": "#10B981",
        "color_dividir": "#F59E0B", "color_comprimir": "#06B6D4",
        "color_visor": "#EC4899", "color_firmar": "#6366F1",
    },
    "rosado": {
        "etiqueta_es": "Rosado", "etiqueta_en": "Pink",
        "fondo": "#FDF2F8", "sidebar": "#FCE7F3", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#FFF7FB", "activo": "#FFFFFF", "hover_sidebar": "#FBCFE8",
        "border": "#F9A8D4", "border_suave": "#FCE7F3",
        "acento": "#EC4899", "acento_hover": "#DB2777", "acento_suave": "#F9A8D4",
        "aqua": "#22D3EE", "lima": "#A3E635",
        "texto": "#500724", "texto_suave": "#9D174D", "texto_tenue": "#DB2777",
        "texto_blanco": "#FFFFFF",
        "ok": "#10B981", "ok_hover": "#059669",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#A855F7", "color_fusionar": "#22C55E",
        "color_dividir": "#F97316", "color_comprimir": "#06B6D4",
        "color_visor": "#8B5CF6", "color_firmar": "#EC4899",
    },
    "menta": {
        "etiqueta_es": "Menta", "etiqueta_en": "Mint",
        "fondo": "#ECFDF5", "sidebar": "#D1FAE5", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#F0FDF9", "activo": "#FFFFFF", "hover_sidebar": "#A7F3D0",
        "border": "#6EE7B7", "border_suave": "#D1FAE5",
        "acento": "#10B981", "acento_hover": "#059669", "acento_suave": "#6EE7B7",
        "aqua": "#06B6D4", "lima": "#84CC16",
        "texto": "#064E3B", "texto_suave": "#047857", "texto_tenue": "#10B981",
        "texto_blanco": "#FFFFFF",
        "ok": "#22C55E", "ok_hover": "#16A34A",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#14B8A6", "color_fusionar": "#22C55E",
        "color_dividir": "#F59E0B", "color_comprimir": "#0EA5E9",
        "color_visor": "#8B5CF6", "color_firmar": "#6366F1",
    },
    "atardecer": {
        "etiqueta_es": "Atardecer", "etiqueta_en": "Sunset",
        "fondo": "#FFF7ED", "sidebar": "#FFEDD5", "tarjeta": "#FFFFFF",
        "tarjeta_hover": "#FFFAF3", "activo": "#FFFFFF", "hover_sidebar": "#FED7AA",
        "border": "#FDBA74", "border_suave": "#FFEDD5",
        "acento": "#F97316", "acento_hover": "#EA580C", "acento_suave": "#FDBA74",
        "aqua": "#06B6D4", "lima": "#84CC16",
        "texto": "#7C2D12", "texto_suave": "#9A3412", "texto_tenue": "#EA580C",
        "texto_blanco": "#FFFFFF",
        "ok": "#22C55E", "ok_hover": "#16A34A",
        "stop": "#EF4444", "stop_hover": "#DC2626",
        "color_extraer": "#EC4899", "color_fusionar": "#22C55E",
        "color_dividir": "#F59E0B", "color_comprimir": "#06B6D4",
        "color_visor": "#8B5CF6", "color_firmar": "#EAB308",
    },
}

TEMAS_POR_DEFECTO = "enterprise"

# Versión del formato del archivo. En la 1 el tema se guardaba aunque nunca se
# podía elegir (siempre "aero"); ese valor no cuenta como elección del usuario.
PREFS_VERSION = 2


# ---------------------------------------------------------------------------
# IDIOMAS  (con las claves nuevas)
# ---------------------------------------------------------------------------
IDIOMAS = {
    "es": {
        "etiqueta": "Español",
        "app_subtitulo": "Suite local de PDF",
        "todo_local": "☁  Todo local, sin nube",
        "todo_local_sub": "Tus PDFs nunca salen de tu equipo",
        "configuracion": "Configuración",
        "config_tema": "Tema",
        "config_idioma": "Idioma",
        "config_cerrar": "Cerrar",
        "config_info": "Los cambios se aplican al instante",
        # --- NUEVAS ---
        "config_apariencia": "Apariencia",
        "config_carpetas": "Carpetas",
        "config_actualizaciones": "Actualizaciones",
        "config_acerca": "Acerca de",
        # --- Módulos ---
        "mod_inicio": "Inicio", "mod_inicio_desc": "Vista general de la suite",
        "mod_extractor": "Extracción Avanzada", "mod_extractor_desc": "Filtra, corta y clasifica PDFs",
        "mod_extractor_sub": "Procesa lotes de PDFs por palabra clave o lista",
        "mod_fusionador": "Fusionador", "mod_fusionador_desc": "Une varios PDFs en uno solo",
        "mod_fusionador_sub": "Combina archivos y añade marcadores por documento",
        "mod_divisor": "Divisor por Unidad", "mod_divisor_desc": "Separa un PDF por unidad médica",
        "mod_divisor_sub": "Cada unidad médica queda en su propio PDF",
        "mod_compresor": "Compresor", "mod_compresor_desc": "Reduce el tamaño de tus PDF",
        "mod_compresor_sub": "Ghostscript cuando está disponible, interno si no",
        "mod_visor": "Visor PDF", "mod_visor_desc": "Abre y explora cualquier PDF",
        "mod_visor_sub": "Navega, hace zoom y busca texto en el documento",
        "mod_firmar": "Firmar / Sellar", "mod_firmar_desc": "Aplica firma o sello a documentos",
        "mod_firmar_sub": "Añade firma visible o sello a cada documento",
        # --- Vistas ---
        "abrir": "Abrir", "explorar": "📂  Explorar",
        "elegir_pdf": "📂  Elegir PDF…", "elegir_destino": "📂  Elegir destino…",
        "cargar_txt": "📄  Cargar .txt", "detener": "⏹  Detener",
        "listo": "Listo.", "iniciando": "Iniciando...",
        "en_desarrollo": "En desarrollo",
        "bienvenida_titulo": "Bienvenido a CCpdf  🌊",
        "bienvenida_texto": ("Herramientas locales para trabajar con PDFs sin subirlos a ningún servidor. "
                             "Elige un módulo para empezar."),
        "clave_inicio": "inicio",
        # --- Barra lateral e inicio (BUG-019) ---
        "sec_principal": "Principal", "sec_procesamiento": "Procesamiento",
        "sec_herramientas": "Herramientas", "sec_inteligencia": "Inteligencia",
        "nav_inicio": "Dashboard", "nav_inicio_desc": "Vista general de la suite",
        "nav_extractor": "Extracción", "nav_extractor_desc": "Corta y clasifica lotes por palabra",
        "nav_fusionador": "Fusionar", "nav_fusionador_desc": "Une varios PDFs en uno solo",
        "nav_divisor": "Dividir", "nav_divisor_desc": "Separa un PDF por unidad",
        "nav_compresor": "Comprimir", "nav_compresor_desc": "Reduce el tamaño de tus PDFs",
        "nav_ocr": "OCR", "nav_ocr_desc": "Añade capa de texto a PDFs escaneados",
        "nav_visor": "Visor", "nav_visor_desc": "Explora cualquier PDF",
        "nav_firmar": "Firmar", "nav_firmar_desc": "Aplica firma o sello",
        "nav_asistente": "Asistente", "nav_asistente_desc": "Chat de ayuda sobre CCpdf",
        "home_bienvenida": "Bienvenido a CCpdf",
        "home_sub": "Suite local de gestión de PDF · Todo se procesa en tu equipo",
        "home_acciones": "Acciones rápidas",
        "home_acciones_sub": "Los flujos más habituales, a un clic.",
        "acc_extractor": "Corta y clasifica", "acc_fusionador": "Une varios en uno",
        "acc_divisor": "Separa por unidad", "acc_compresor": "Reduce el tamaño",
        "config_tema_titulo": "Tema de color",
        "config_idioma_aviso": "Idioma guardado. Cierra y vuelve a abrir CCpdf para aplicarlo.",
        "config_idioma_nota": "Se traduce la barra lateral, el inicio y Configuración; el resto de pantallas sigue en español.",
        "config_mejoras_gs": "Mostrar «Mejoras extras» (Ghostscript) en Comprimir",
    },
    "en": {
        "etiqueta": "English",
        "app_subtitulo": "Local PDF suite",
        "todo_local": "☁  All local, no cloud",
        "todo_local_sub": "Your PDFs never leave your machine",
        "configuracion": "Settings",
        "config_tema": "Theme",
        "config_idioma": "Language",
        "config_cerrar": "Close",
        "config_info": "Changes apply instantly",
        "config_apariencia": "Appearance",
        "config_carpetas": "Folders",
        "config_actualizaciones": "Updates",
        "config_acerca": "About",
        "mod_inicio": "Home", "mod_inicio_desc": "Overview of the suite",
        "mod_extractor": "Advanced Extraction", "mod_extractor_desc": "Filter, cut and classify PDFs",
        "mod_extractor_sub": "Batch process PDFs by keyword or list",
        "mod_fusionador": "Merger", "mod_fusionador_desc": "Join several PDFs into one",
        "mod_fusionador_sub": "Combine files and add bookmarks per document",
        "mod_divisor": "Split by Unit", "mod_divisor_desc": "Split a PDF by medical unit",
        "mod_divisor_sub": "Each medical unit ends up in its own PDF",
        "mod_compresor": "Compressor", "mod_compresor_desc": "Reduce the size of your PDFs",
        "mod_compresor_sub": "Ghostscript when available, internal if not",
        "mod_visor": "PDF Viewer", "mod_visor_desc": "Open and explore any PDF",
        "mod_visor_sub": "Navigate, zoom and search text in the document",
        "mod_firmar": "Sign / Stamp", "mod_firmar_desc": "Apply a signature or stamp",
        "mod_firmar_sub": "Add a visible signature or stamp to each document",
        "abrir": "Open", "explorar": "📂  Browse",
        "elegir_pdf": "📂  Choose PDF…", "elegir_destino": "📂  Choose destination…",
        "cargar_txt": "📄  Load .txt", "detener": "⏹  Stop",
        "listo": "Ready.", "iniciando": "Starting...",
        "en_desarrollo": "In development",
        "bienvenida_titulo": "Welcome to CCpdf  🌊",
        "bienvenida_texto": ("Local tools to work with PDFs without uploading them to any server. "
                             "Pick a module to start."),
        "clave_inicio": "inicio",
        "sec_principal": "Main", "sec_procesamiento": "Processing",
        "sec_herramientas": "Tools", "sec_inteligencia": "Intelligence",
        "nav_inicio": "Dashboard", "nav_inicio_desc": "Overview of the suite",
        "nav_extractor": "Extraction", "nav_extractor_desc": "Cut and classify batches by keyword",
        "nav_fusionador": "Merge", "nav_fusionador_desc": "Join several PDFs into one",
        "nav_divisor": "Split", "nav_divisor_desc": "Separate a PDF by unit",
        "nav_compresor": "Compress", "nav_compresor_desc": "Reduce the size of your PDFs",
        "nav_ocr": "OCR", "nav_ocr_desc": "Add a text layer to scanned PDFs",
        "nav_visor": "Viewer", "nav_visor_desc": "Explore any PDF",
        "nav_firmar": "Sign", "nav_firmar_desc": "Apply a signature or stamp",
        "nav_asistente": "Assistant", "nav_asistente_desc": "Help chat about CCpdf",
        "home_bienvenida": "Welcome to CCpdf",
        "home_sub": "Local PDF management suite · Everything is processed on your machine",
        "home_acciones": "Quick actions",
        "home_acciones_sub": "The most common workflows, one click away.",
        "acc_extractor": "Cut and classify", "acc_fusionador": "Join many into one",
        "acc_divisor": "Separate by unit", "acc_compresor": "Reduce the size",
        "config_tema_titulo": "Color theme",
        "config_idioma_aviso": "Language saved. Close and reopen CCpdf to apply it.",
        "config_idioma_nota": "The sidebar, home and Settings are translated; the other screens stay in Spanish.",
        "config_mejoras_gs": "Show the «Mejoras extras» card (Ghostscript) in Compress",
    },
}

IDIOMA_POR_DEFECTO = "es"


# ---------------------------------------------------------------------------
# CARPETAS DE SALIDA POR MÓDULO  (NUEVO)
# ---------------------------------------------------------------------------
# Cada módulo puede tener una carpeta por defecto donde se guardan los resultados.
# Si está vacía (""), el módulo usa su comportamiento por defecto:
#   - extractor:  "PDFs_Recortados" dentro de la carpeta de origen
#   - fusionador: junto al primer PDF de la lista
#   - divisor:    "<nombre_pdf>_unidades" junto al PDF original
#   - compresor:  "PDFs_Comprimidos" junto al primer PDF

MODULOS_CARPETAS = ("extractor", "fusionador", "divisor", "compresor")

_CARPETAS_POR_DEFECTO = {
    "extractor":  "",
    "fusionador": "",
    "divisor":    "",
    "compresor":  "",
    "ocr":        "",
    "metadatos":  "",
    "comparar":   "",
}


# ---------------------------------------------------------------------------
# PREFERENCIAS  (con "carpetas" añadido)
# ---------------------------------------------------------------------------
def _prefs_vacias() -> dict:
    return {
        "tema": TEMAS_POR_DEFECTO,
        "idioma": IDIOMA_POR_DEFECTO,
        "carpetas": dict(_CARPETAS_POR_DEFECTO),
        "ia_modo": "local",       # "local" (Ollama) o "api" (externa)
        "ia_proveedor": "deepseek",
        "ia_clave": "",           # en claro, en ~/.config/CCpdf (fuera del repo)
        "ocultar_mejoras_gs": False,   # Comprimir → «Mejoras extras» oculta por el usuario
        "historial_activo": True,      # registrar los procesos terminados
        "temporales_activo": True,     # guardar copias para poder deshacer
        "temporales_dias": 30,         # retención de las copias (1–365; 30 recomendado)
    }


def cargar() -> dict:
    ruta = _ruta_config()
    if not ruta.is_file():
        return _prefs_vacias()
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)

        prefs = _prefs_vacias()
        if datos.get("version_prefs", 1) >= 2:
            prefs["tema"] = datos.get("tema", TEMAS_POR_DEFECTO)
        prefs["idioma"] = datos.get("idioma", IDIOMA_POR_DEFECTO)
        for k in ("ia_modo", "ia_proveedor", "ia_clave"):
            if isinstance(datos.get(k), str):
                prefs[k] = datos[k]
        if prefs["ia_modo"] not in ("local", "api"):
            prefs["ia_modo"] = "local"
        if isinstance(datos.get("ocultar_mejoras_gs"), bool):
            prefs["ocultar_mejoras_gs"] = datos["ocultar_mejoras_gs"]
        for k in ("historial_activo", "temporales_activo"):
            if isinstance(datos.get(k), bool):
                prefs[k] = datos[k]
        dias = datos.get("temporales_dias")
        if isinstance(dias, int) and not isinstance(dias, bool):
            prefs["temporales_dias"] = max(1, min(365, dias))

        # Merge de carpetas guardadas (solo las que existen)
        guardadas = datos.get("carpetas") or {}
        for k, v in guardadas.items():
            if k in prefs["carpetas"] and isinstance(v, str):
                prefs["carpetas"][k] = v

        if prefs["tema"] not in TEMAS:
            prefs["tema"] = TEMAS_POR_DEFECTO
        if prefs["idioma"] not in IDIOMAS:
            prefs["idioma"] = IDIOMA_POR_DEFECTO
        return prefs
    except Exception:
        return _prefs_vacias()


def guardar(prefs: dict) -> bool:
    """Guarda las preferencias. Devuelve False si no se pudo escribir."""
    try:
        with open(_ruta_config(), "w", encoding="utf-8") as f:
            json.dump({**prefs, "version_prefs": PREFS_VERSION}, f, ensure_ascii=False, indent=2)
        os.chmod(_ruta_config(), 0o600)  # puede contener la clave de API
        return True
    except Exception:
        return False


def tema(nombre: str) -> dict:
    return TEMAS.get(nombre, TEMAS[TEMAS_POR_DEFECTO])


def idioma(codigo: str) -> dict:
    return IDIOMAS.get(codigo, IDIOMAS[IDIOMA_POR_DEFECTO])


def etiqueta_tema(nombre: str, codigo_idioma: str) -> str:
    t = TEMAS.get(nombre, {})
    clave = f"etiqueta_{codigo_idioma}"
    return t.get(clave, t.get("etiqueta_es", nombre))