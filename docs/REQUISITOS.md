# Requisitos para ejecutar CCpdf

Guía completa de todo lo necesario para correr el proyecto.

---

## 1. Python

- **Python 3.10 o superior** (recomendado 3.12).
- Descarga: https://www.python.org/downloads/

---

## 2. Dependencias Python (pip)

Archivo: `requirements.txt` en la raíz del proyecto.

```bash
pip install -r requirements.txt
```

| Paquete | Versión mínima | Propósito |
|---------|---------------|-----------|
| `pypdf` | ≥ 4.0 | Manipulación de PDFs (extraer, fusionar, dividir, comprimir) |
| `Pillow` | ≥ 10.0 | Procesamiento de imágenes |
| `pypdfium2` | ≥ 4.30 | Dibujo de páginas en el visor y páginas a imagen para el OCR (PDFium; BSD-3 / Apache-2.0) |
| `customtkinter` | ≥ 5.2 | Interfaz gráfica moderna (basada en Tkinter) |
| `thefuzz` | ≥ 0.22 | Búsqueda difusa de texto |
| `pytesseract` | ≥ 0.3.13 | Wrapper Python para Tesseract OCR |
| `reportlab` | ≥ 4.0 | Generación de la capa de texto invisible sobre el PDF |

Opcional, en `requirements-ai.txt` (no se instala con el anterior porque se compila y necesita
un compilador de C/C++ y CMake):

| Paquete | Versión mínima | Propósito |
|---------|---------------|-----------|
| `llama-cpp-python` | ≥ 0.3.36 | Backend de IA local con llama.cpp (fallback sin Ollama) |

```bash
pip install -r requirements-ai.txt
```

---

## 3. Dependencias del sistema operativo

Estas NO se instalan con pip. Se instalan con el gestor de paquetes del SO.

### 3.1 Tesseract OCR

Motor de reconocimiento óptico de caracteres. **Obligatorio para la función OCR.**

| Sistema | Comando de instalación |
|---------|----------------------|
| **Debian / Ubuntu** | `sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-osd` |
| **Fedora** | `sudo dnf install tesseract tesseract-langpack-spa tesseract-langpack-osd` |
| **Arch Linux** | `sudo pacman -S tesseract tesseract-data-spa tesseract-data-osd` |
| **macOS** | `brew install tesseract tesseract-lang` |
| **Windows** | Descargar instalador desde: https://github.com/UB-Mannheim/tesseract/wiki — marcar el idioma español y los datos de orientación (OSD) durante la instalación y agregar al PATH |

Los datos de orientación (`osd`) permiten al OCR detectar páginas escaneadas giradas. Sin ellos el OCR funciona, pero asume que todas las páginas están derechas.

### 3.2 Ghostscript (opcional)

Motor de compresión más potente que el interno. Sin él, el compresor usa solo el motor interno (pypdf).
Su licencia es AGPL-3: el usuario lo instala aparte; **no** debe incluirse en el instalador de CCpdf
(ver `docs/LICENCIAS.md`).

**Desde la app**: Comprimir → «Mejoras extras» → «Descargar e instalar Ghostscript». La tarjeta solo
aparece si no está instalado.

| Sistema | Qué hace el botón |
|---------|-------------------|
| **Windows** | Descarga el instalador oficial de Artifex (versión fija, SHA-256 verificado) y lo instala en silencio; Windows pide permiso de administrador |
| **macOS** | `brew install ghostscript` (hace falta [Homebrew](https://brew.sh); si no está, lo explica). Si no lo quieres, «Ocultar» quita la tarjeta para siempre; se recupera en Configuración → Apariencia |
| **Linux** | apt-get, dnf, zypper o pacman vía `pkexec` (pide la contraseña) |

A mano:

| Sistema | Comando de instalación |
|---------|----------------------|
| **Debian / Ubuntu** | `sudo apt install ghostscript` |
| **Fedora** | `sudo dnf install ghostscript` |
| **Arch Linux** | `sudo pacman -S ghostscript` |
| **macOS** | `brew install ghostscript` |
| **Windows** | Instalador desde https://ghostscript.com/releases/ |

### 3.3 Tkinter

Normalmente viene incluido con Python, pero en algunas distros Linux hay que instalarlo aparte.

| Sistema | Comando de instalación |
|---------|----------------------|
| **Debian / Ubuntu** | `sudo apt install python3-tk` |
| **Fedora** | `sudo dnf install python3-tkinter` |
| **Arch Linux** | `sudo pacman -S tk` |
| **macOS / Windows** | Incluido con Python |

---

## 4. IA local (CIPA) — Opcional

La inteligencia artificial funciona con dos backends posibles. **Sin ninguno de los dos, la app funciona igual**, solo que sin asistente conversacional ni limpieza OCR inteligente.

### Opción A: Ollama ⭐ (recomendada)

Más rápido y eficiente. Corre como servicio local en `localhost:11434`.

| Sistema | Instalación |
|---------|-------------|
| **Linux** | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **macOS** | `brew install ollama` |
| **Windows** | Descargar desde: https://ollama.com/download |

Después de instalar Ollama, descargar el modelo:

```bash
ollama pull qwen2.5:1.5b
```

Modelo usado: **Qwen2.5-1.5B-instruct** (~1.0 GB, licencia Apache 2.0).

**Rendimiento medido** (Ollama, `qwen2.5:1.5b`, equipo de 12 hilos y 11,7 GB de RAM, sin GPU):

| Medida | Resultado |
|---|---|
| Velocidad de generación | ≈ 22 tokens/s |
| Carga del modelo en frío | ≈ 4 s |
| Respuesta de ~200 tokens | ≈ 11–13 s |
| RAM del modelo cargado | ≈ 1,2 GB |
| CPU mientras genera | ≈ 420 % (unos 4 núcleos) |
| CPU en reposo | 0 % (Ollama descarga el modelo a los 5 min sin uso) |

**Para IA local se recomiendan 8 GB de RAM y una CPU de 4 núcleos (quad-core) o más.**
La limpieza OCR con CIPA genera mucho texto (≈ 2700 tokens para un PDF de 4 páginas): con estas
cifras, **el procesamiento puede tardar varios minutos por lote**. CCpdf lo avisa en pantalla y la
interfaz sigue respondiendo mientras tanto (el motor corre en un hilo aparte).

### Opción B: llama-cpp-python (fallback)

Se instala aparte con `pip install -r requirements-ai.txt` (necesita compilador de C/C++ y CMake). El modelo (**Phi-3.5-mini-instruct**, ~2.4 GB, licencia MIT) **no se descarga solo**: hay que bajarlo una vez desde Hugging Face con:

```bash
python -m Motores.CIPA.descargar_modelo limpieza_llama_cpp
```

### Opción C: API externa (DeepSeek / Gemini) — modo híbrido

Para ir más rápido sin hardware potente. Se elige en **Configuración → IA → API Externa**, con tu propia clave
de API (también se lee de la variable de entorno `CCPDF_API_KEY`).

> ⚠ **Privacidad:** con este modo el texto de tus documentos **se envía al proveedor**. Por defecto
> CCpdf usa siempre el modo local, y la interfaz pide confirmación al activar la API. La clave se
> guarda en claro en `~/.config/CCpdf/config.json` (permisos 600, fuera del repositorio).

---

## 5. Resumen de instalación rápida

### Linux (Debian / Ubuntu)

```bash
# 1. Dependencias del sistema
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-osd python3-tk

# 2. Dependencias Python
pip install -r requirements.txt

# 3. IA local (opcional)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:1.5b

# 4. Ejecutar
python3 main.py
```

### Windows

```powershell
# 1. Instalar Tesseract (ver enlace arriba), agregar al PATH
# 2. Dependencias Python
pip install -r requirements.txt

# 3. IA local (opcional): instalar Ollama desde https://ollama.com/download
ollama pull qwen2.5:1.5b

# 4. Ejecutar
python main.py
```

### macOS

```bash
# 1. Dependencias del sistema
brew install tesseract tesseract-lang

# 2. Dependencias Python
pip install -r requirements.txt

# 3. IA local (opcional)
brew install ollama
ollama pull qwen2.5:1.5b

# 4. Ejecutar
python3 main.py
```

---

## 6. Hardware recomendado

| Componente | Mínimo (sin IA) | Recomendado (con IA) |
|------------|-----------------|---------------------|
| **RAM** | 2 GB | 8 GB |
| **CPU** | Dual-core | Quad-core o superior |
| **Disco** | 500 MB | 5 GB (modelos IA) |
| **GPU** | No necesaria | No necesaria (todo corre en CPU) |

---

Desarrollado por Iker · Kodesoft
