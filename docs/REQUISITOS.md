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
| `customtkinter` | ≥ 5.2 | Interfaz gráfica moderna (basada en Tkinter) |
| `thefuzz` | ≥ 0.22 | Búsqueda difusa de texto |
| `pytesseract` | ≥ 0.3.13 | Wrapper Python para Tesseract OCR |
| `pdf2image` | ≥ 1.17 | Conversión de páginas PDF a imágenes (requiere Poppler) |
| `reportlab` | ≥ 4.0 | Generación de la capa de texto invisible sobre el PDF |
| `llama-cpp-python` | ≥ 0.3.36 | Backend de IA local con llama.cpp (opcional, fallback sin Ollama) |

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

### 3.2 Poppler

Necesario para que `pdf2image` pueda convertir PDFs a imágenes. **Obligatorio para OCR.**

| Sistema | Comando de instalación |
|---------|----------------------|
| **Debian / Ubuntu** | `sudo apt install poppler-utils` |
| **Fedora** | `sudo dnf install poppler-utils` |
| **Arch Linux** | `sudo pacman -S poppler` |
| **macOS** | `brew install poppler` |
| **Windows** | Descargar desde: https://github.com/oschwartz10612/poppler-windows/releases — extraer y agregar la carpeta `bin/` al PATH del sistema |

### 3.3 Ghostscript (opcional)

Motor de compresión más potente que el interno. Sin él, el compresor usa solo el motor interno (pypdf).

| Sistema | Comando de instalación |
|---------|----------------------|
| **Debian / Ubuntu** | `sudo apt install ghostscript` |
| **Fedora** | `sudo dnf install ghostscript` |
| **Arch Linux** | `sudo pacman -S ghostscript` |
| **macOS** | `brew install ghostscript` |
| **Windows** | Instalador desde https://ghostscript.com/releases/ |

### 3.4 Tkinter

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

### Opción B: llama-cpp-python (fallback)

Ya se instala con `requirements.txt`. El modelo (**Phi-3.5-mini-instruct**, ~2.4 GB, licencia MIT) **no se descarga solo**: hay que bajarlo una vez desde Hugging Face con:

```bash
python -m Motores.CIPA.descargar_modelo limpieza_llama_cpp
```

---

## 5. Resumen de instalación rápida

### Linux (Debian / Ubuntu)

```bash
# 1. Dependencias del sistema
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-osd poppler-utils python3-tk

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
# 1. Instalar Tesseract y Poppler (ver enlaces arriba), agregar al PATH
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
brew install tesseract tesseract-lang poppler

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
