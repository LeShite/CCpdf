# CIPA — Capa de Inteligencia de Procesamiento Aumentado

CIPA es la capa de IA local de **CCpdf**. Procesa documentos
**sin enviar nada a la nube**.

## Filosofía

- 🌐 **100% local** — ningún dato sale del equipo.
- 🧩 **Modular** — cada tarea usa el modelo que mejor le conviene.
- ⚙️ **Opcional** — si no está instalada, CCpdf funciona sin ella.
- ⚖️ **Licencia limpia** — solo MIT y Apache 2.0. Comercializable.
- 💻 **CPU-first** — corre en portátiles modestos, sin GPU.

## Tareas soportadas

| Tarea | Modelo | Runtime | Licencia | Tamaño |
|---|---|---|---|---|
| Limpieza OCR | Qwen2.5-1.5B-instruct | Ollama (preferido) | Apache 2.0 | ~1.0 GB |
| Limpieza OCR (sin Ollama) | Phi-3.5-mini-instruct | llama.cpp (fallback) | MIT | ~2.4 GB |
| Extracción de campos / Clasificación | Qwen2.5-1.5B-instruct | Ollama | Apache 2.0 | ~1.0 GB |

## Estructura

```
CIPA/
├── nucleo.py           # API pública: CIPA, estado(), aplicar_ocr()
├── asistente.py        # asistente conversacional (usa el system prompt de cada módulo)
├── config.py           # catálogo de modelos y rutas
├── descargar_modelo.py # descarga de modelos (ollama pull / .gguf por HTTP)
├── backends/           # ollama.py, llama_cpp.py (base.py define la interfaz)
├── prompts/            # prompts de limpieza OCR
└── modelos/            # MODELOS.md y caché de .gguf
```

## Backends

- **Ollama** (preferido): servidor local; el modelo se baja con `ollama pull qwen2.5:1.5b`.
- **API externa** (opcional, `backends/api_externa.py`): DeepSeek o Gemini por su endpoint compatible
  con OpenAI. Se activa con `configurar_modo("api", proveedor, clave)`; **envía el texto al proveedor**.
- **llama.cpp** (fallback): requiere `llama-cpp-python` y bajar el modelo a mano con
  `python -m Motores.CIPA.descargar_modelo limpieza_llama_cpp`. Si está instalado pero su
  librería nativa falla, CIPA lo registra en el logger `CIPA` y lo indica en `estado()`.
