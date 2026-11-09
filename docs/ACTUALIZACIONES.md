# Actualizaciones de CCpdf (kodesoft.site)

CCpdf ya **no consulta GitHub**. Todo sale de un único archivo en la web de Kodesoft:

```
https://kodesoft.site/Downloads/ccpdf/version.json
```

Ese JSON es la **única fuente** de la información de versiones:

| Quién lo lee | Para qué |
|---|---|
| La app (`Interfaz/actualizador.py`) | Saber si hay versión nueva, mostrar las novedades, descargar e instalar |
| La web (`web_ccpdf.py`, lo ejecuta el cron cada hora) | Regenerar `ccpdf.html` (versión, fecha, botones de descarga, tamaños, SHA-256 e historial) y las tarjetas de CCpdf en `Downloads/index.html` |

Se **edita a mano** en cada versión (o se genera con `herramientas/publicar_version.py`, ver abajo).
Al guardarlo, en la siguiente hora la web queda actualizada y las apps instaladas lo ven.

---

## 1. Formato de `version.json`

```json
{
  "producto": "CCpdf",
  "version": "1.5.0",
  "fecha": "2026-11-08",
  "notas": ["Arrastrar y soltar", "Módulo Metadatos", "Módulo Comparar"],
  "pagina": "https://kodesoft.site/ccpdf.html",
  "archivos": {
    "linux": {
      "nombre": "CCpdf-1.5.0-linux",
      "url": "CCpdf-1.5.0-linux",
      "sha256": "fc8b5258…(64 caracteres hex)",
      "tamano": 33717408
    }
  },
  "historial": [
    {
      "version": "1.5.0",
      "fecha": "2026-11-08",
      "secciones": {
        "Añadido":   ["**Arrastrar y soltar**: …", "…"],
        "Cambiado":  ["…"],
        "Corregido": ["**BUG-026 — OCR**: …"]
      }
    },
    { "version": "1.0.1", "fecha": "2026-10-21", "secciones": { "…": [] } }
  ]
}
```

| Campo | Obligatorio | Qué es |
|---|---|---|
| `producto` | sí | Siempre `"CCpdf"` |
| `version` | sí | `MAYOR.MENOR.PARCHE` sin «v» (la app la compara con su `APP_VERSION`) |
| `fecha` | sí | `AAAA-MM-DD` |
| `notas` | sí | Lista corta (≤ 8) que la app muestra en «Novedades». Texto plano |
| `pagina` | no | Página de descarga que abre el botón «Abrir página de descarga» (solo se acepta kodesoft.site) |
| `archivos` | no | Uno por sistema: `linux`, `windows`, `macos`. Si falta un sistema, la app de ese sistema no ofrece instalar (solo la página) y la web lo muestra como «Próximamente» |
| `archivos.*.nombre` | sí | Nombre del archivo dentro de `Downloads/ccpdf/` |
| `archivos.*.url` | sí | **Relativa al JSON** (lo normal: igual que `nombre`). Así el mismo JSON vale en QA y en producción. Si es absoluta, solo se acepta `https://*.kodesoft.site` |
| `archivos.*.sha256` | sí | SHA-256 del archivo (`sha256sum archivo`). La app **rechaza** la descarga si no coincide |
| `archivos.*.tamano` | sí | Tamaño en bytes (`stat -c %s archivo`). La app rechaza descargas incompletas |
| `historial` | sí | Todas las versiones, **la más reciente primero**; la primera debe ser `version`. Cada entrada: `version`, `fecha` y `secciones` (nombre → lista de textos). Admite `**negrita**`, `` `código` ``, `_cursiva_` y `[enlace](https://…)` |

---

## 2. Publicar una versión nueva

### Opción A — con la herramienta (recomendado)

En pcprod, desde la raíz del repo, con la versión ya en `APP_VERSION` y su sección en `CHANGELOG.md`:

```bash
bash build_linux.sh                                   # → dist/CCpdf
python -m herramientas.publicar_version --salida /tmp/ccpdf-web \
       --binario linux=dist/CCpdf                     # copia el binario y genera/actualiza version.json
python -m herramientas.publicar_version --salida /tmp/ccpdf-web --comprobar
```

- Si `version.json` ya existía en la carpeta, conserva el historial anterior y lo editado a mano.
- Añade al historial la sección `[x.y.z] - fecha` de `CHANGELOG.md` si aún no estaba.
- `--historial-completo` reconstruye todo el historial desde `CHANGELOG.md`.
- Nunca borra binarios de versiones anteriores (avisa de cuáles hay).

### Opción B — a mano

1. Copiar el binario a `Downloads/ccpdf/` con el nombre `CCpdf-<versión>-<sistema>[.exe]`.
2. `sha256sum` y `stat -c %s` del binario.
3. En `version.json`: cambiar `version`, `fecha`, `notas`, el bloque de `archivos` y **añadir arriba** la entrada nueva de `historial`.
4. Validar el JSON (por ejemplo `python3 -m json.tool version.json`).

### Subir a QA y luego a producción

1. **QA**: copiar `version.json` y el binario a `qa@192.168.1.5:kodesoft-web/Downloads/ccpdf/` y, si no se quiere esperar al cron, `python3 ~/kodesoft-server/update_changelog.py`. Comprobar `https://qa-web.kodesoft.site/ccpdf.html` y que la app actualiza contra QA (ver §5).
2. **Producción**: lo mismo en la web de producción (ver «Pendiente en producción» en `~/Bitacora-Cambios.md`).

---

## 3. Qué hace la app

Configuración → **Actualizaciones**:

1. **Buscar actualizaciones** (y, si está marcado, una vez al día al abrir CCpdf).
2. Muestra versión, fecha, tamaño y **novedades** (`notas`).
3. **Descargar e instalar** (solo si CCpdf corre como ejecutable y hay archivo para el sistema):
   - respalda los datos del usuario,
   - descarga con barra de progreso, verifica **tamaño y SHA-256**,
   - sustituye el ejecutable y guarda el anterior como `CCpdf.anterior`,
   - ofrece **Reiniciar ahora**.
4. **Volver a la versión anterior**: aparece si existe `CCpdf.anterior`.
5. Desde el código fuente (`python3 main.py`) no instala: muestra las novedades y la página de descarga.

Solo se aceptan manifiestos y descargas de `kodesoft.site` (y subdominios) por HTTPS, o de la red local
para pruebas.

---

## 4. Datos del usuario entre versiones

Los datos viven **fuera del programa** y no se tocan al cambiar el ejecutable:

| Sistema | Carpeta |
|---|---|
| Linux | `~/.config/CCpdf/` |
| Windows | `%APPDATA%\CCpdf\` |
| macOS | `~/Library/Application Support/CCpdf/` |

Contiene `config.json` (tema, idioma, carpetas, IA…), `historial.json`, `temporales/` y `respaldos/`.

- `config.json` guarda `app_version`: la versión que escribió los datos.
- Al abrir una versión distinta, `Interfaz/migracion.py` **respalda** `config.json` e
  `historial.json` en `respaldos/<fecha>_<versión>_antes-de-migrar/`, aplica las migraciones que
  correspondan (lista `MIGRACIONES`) y anota la versión nueva. La app avisa una vez: «Tu
  configuración, carpetas e historial se conservaron».
- Antes de instalar una actualización también se hace un respaldo (`…_antes-de-actualizar`).
- Se conservan los 10 respaldos más recientes. Botón **Respaldos** en la pestaña para abrirlos.
- Cuando una versión nueva cambie el formato de los datos, añadir una función a `MIGRACIONES`
  (versión mínima → función que transforma el `dict` de `config.json`).

---

## 5. Probar contra QA

```bash
CCPDF_URL_ACTUALIZACIONES=https://qa-web.kodesoft.site/Downloads/ccpdf/version.json ./dist/CCpdf
```

Pruebas automáticas: `Interfaz/test_actualizador.py` (motor y migración) e
`Interfaz/test_actualizador_ui.py` (pestaña de punta a punta con un servidor local).

---

## 6. La web

- Generador: `~/kodesoft-server/web_ccpdf.py` en el servidor de la web (copia de referencia en
  `herramientas/web/web_ccpdf.py` de este repo). Lo llama `update_changelog.py` (cron cada hora).
- Regenera los bloques entre marcadores `<!-- CHANGELOG:START/END -->` y
  `<!-- CCPDF-DESCARGA:START/END -->` de `ccpdf.html`, y `<!-- CCPDF-DESCARGAS:START/END -->` de
  `Downloads/index.html`. Si faltan, los crea la primera vez.
- nginx bloquea los `.json`; hay una excepción **solo** para `/Downloads/ccpdf/version.json`
  (`location = …`, sin caché). En QA hubo que poner `root` dentro de esa excepción porque su
  `default.conf` solo define `root` en `location /` (en producción `root` es global).
