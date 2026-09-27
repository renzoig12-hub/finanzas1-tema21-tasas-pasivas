# Tasas pasivas comparadas entre banca, cajas y financieras: valor futuro de un depósito

| Dato | Detalle |
|---|---|
| Autor | Renzo Jhonel Ignacio Paucar |
| Código de matrícula | 2024200504J |
| Curso | Finanzas I (055D) · UNCP · 2026-II · Dr. Ciro Iván Machacuay Meza |
| Tema del temario | N.° 21 (Unidad I) |
| Periodo | FECHA_INICIO = 2023-01 · FECHA_CORTE = 2025-12 (36 meses) |
| Fecha de extracción | 24 y 25 de septiembre de 2026 |
| Lenguaje | Python 3.13.15 (Google Colab) |
| Repositorio | https://github.com/renzoig12-hub/finanzas1-tema21-tasas-pasivas |

## Fuentes y vías de extracción

| Vía | Fuente | Endpoint / URL | Script |
|---|---|---|---|
| 1. API | BCRPData | `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigo}/json/2023-1/2025-12` (PN07812NM a PN07816NM, PD04722MM) | 01_extraccion_api.py |
| 2. Scraping (formularios ASP.NET) | SBS, tasas pasivas por empresa | `https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIPasivaDepositoEmpresa.aspx?tip={B,F,C}` | 02_scraping_web.py (parte A) |
| 2. Descarga programática | SBS, Indicadores Financieros | `https://www.sbs.gob.pe/app/stats_net/stats/EstadisticaSistemaFinancieroResultados.aspx?c={B-2401,B-3301,C-1301}` | 02_scraping_web.py (parte B) |

Ninguna fuente requiere clave. El scraping respeta robots.txt (la ruta /app/ no está restringida), usa User-Agent identificable y pausas de 1.5 s.

## Orden de ejecución

~~~
pip install -r requirements.txt
python codigo/01_extraccion_api.py    # API del BCRP (~10 s)
python codigo/02_scraping_web.py      # SBS: tasas + indicadores (~25 min)
python codigo/03_limpieza_datos.py    # unión y limpieza (~5 s)
python codigo/04_analisis.py          # tablas y figuras en /salidas (~10 s)
~~~

## Base de datos

- `datos_procesados/datos_procesados_2024200504J.csv`: 1 355 filas (41 entidades x 36 meses), 23 columnas.
- **SHA-256:** `9bbc1f95cddf41db0ffa8e942ddadc6d41376ee6da35b5aec20ec4d006fa079c`
- Muestra de análisis (04_analisis.py): 32 entidades con al menos 24 meses de tasa, 1 106 observaciones completas.

## Estructura

~~~
codigo/            01 a 04
datos_crudos/      archivos tal como salen de la fuente (no se editan)
datos_procesados/  base unida y limpia + hash
salidas/           tablas (CSV) y figuras (PNG) del artículo
log_ejecucion.txt  fecha, hora, código HTTP y filas de cada extracción
diccionario_variables.md, requirements.txt, .env.example, bitacora_ia.md
~~~

## Verificación de reproducibilidad

El 25 de setiembre de 2026 se clonó el repositorio en una carpeta limpia de Google Colab, se instalaron las librerías de requirements.txt y se ejecutaron 01_extraccion_api.py, 03_limpieza_datos.py y 04_analisis.py. El hash SHA-256 del archivo procesado regenerado coincidió exactamente con el declarado, y 04_analisis.py produjo las mismas tablas y figuras. El 26 de setiembre de 2026 se ajustaron las figuras al formato APA 7 (título y nota fuera de la imagen, en el artículo).
