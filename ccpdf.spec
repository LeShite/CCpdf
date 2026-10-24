# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller para CCpdf.
Empaqueta la app + todos los recursos de CustomTkinter + los motores.
"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Recursos de CustomTkinter (fuentes, temas JSON)
datas = collect_data_files("customtkinter")

# Módulos ocultos que PyInstaller no detecta solo:
# - customtkinter/pypdf/PIL: submódulos cargados dinámicamente.
# - pytesseract/pypdfium2/reportlab/thefuzz: los usan los motores de
#   OCR/Compresión, pero no aparecen en ningún import de nivel superior
#   que PyInstaller pueda seguir sin ayuda.
# - Motores.*: app.py ya los importa de forma estática, pero se listan todos
#   igualmente para no depender de que un import condicional (como el de
#   Motores.CIPA, dentro de un try) sea detectado.
hiddenimports = (
    collect_submodules("customtkinter")
    + collect_submodules("pypdf")
    + collect_submodules("PIL")
    + [
        "pytesseract",
        "pypdfium2",
        "reportlab",
        "thefuzz",
        "customtkinter",
    ]
    + collect_submodules("Motores")
)

# Añadir nuestros assets (logo)
assets_dir = os.path.join("Interfaz", "assets")
if os.path.isdir(assets_dir):
    for archivo in os.listdir(assets_dir):
        datas.append((os.path.join(assets_dir, archivo), "Interfaz/assets"))

# Prompts de CIPA: texto plano que se lee en tiempo de ejecución
# (CIPA._cargar_prompt), no se puede empaquetar como bytecode.
prompts_dir = os.path.join("Motores", "CIPA", "prompts")
if os.path.isdir(prompts_dir):
    for archivo in os.listdir(prompts_dir):
        if archivo.endswith(".txt"):
            datas.append((os.path.join(prompts_dir, archivo), prompts_dir))

# Avisos de licencia (MIT/BSD/Apache exigen entregarlos con el programa): la carpeta
# .dist-info de cada paquete que va dentro trae sus textos de licencia. Ver docs/LICENCIAS.md.
for paquete in ("pypdf", "typing_extensions", "pillow", "pypdfium2", "customtkinter",
                "darkdetect", "packaging", "thefuzz", "rapidfuzz", "pytesseract",
                "reportlab", "charset_normalizer", "pyinstaller"):
    datas += copy_metadata(paquete)
datas.append(("docs/LICENCIAS.md", "licencias"))

a = Analysis(
    ["main.py"],
    # Todo se importa como paquete (Interfaz.*, Motores.*) desde la raíz.
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # llama_cpp: su .so nativo no se empaqueta bien en onefile (ver
    # BUG-022 en docs/KNOWN_ISSUES.md). CIPA ya degrada con gracia sin
    # él; el ejecutable usa Ollama como backend de IA.
    # readline (GNU readline, GPL-3) y numpy (trae libquadmath, LGPL): ninguno lo usa
    # la app; entraban de rebote por pdb y por los imports opcionales de pytesseract y
    # rapidfuzz. Excluirlos es lo que permite vender el ejecutable (docs/LICENCIAS.md).
    excludes=["tkinter.test", "test", "llama_cpp", "readline", "numpy"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CCpdf",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # sin consola en Windows
    icon="Interfaz/assets/logo.ico",   # ← Windows usa .ico
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# En macOS generarías un .app aquí con BUNDLE(...)
