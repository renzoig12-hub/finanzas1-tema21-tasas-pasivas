# Autor: Renzo Jhonel Ignacio Paucar
# Código de matrícula: 2024200504J
# Tema N.° 21 (Unidad I): Tasas pasivas comparadas entre banca, cajas y financieras: valor futuro de un depósito
# Fecha de extracción: 2026-09-24

"""
VÍA 1 - API REST del BCRP (BCRPData).
Descarga tasas pasivas de la banca y la tasa de referencia del BCRP,
y las guarda sin modificar en datos_crudos/. Registra cada pedido en log_ejecucion.txt.
Ejecutar desde la carpeta principal:  python codigo/01_extraccion_api.py
"""

import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ---------- 1. Parámetros congelados ----------
CODIGO_MATRICULA = "2024200504J"
FECHA_INICIO = "2023-1"     # enero 2023
FECHA_CORTE = "2025-12"     # diciembre 2025 -> 36 meses

SERIES = {
    "PN07816NM": "tipmn_banca",           # TIPMN
    "PN07812NM": "tasa_plazo_30d",        # plazo hasta 30 días
    "PN07813NM": "tasa_plazo_180d",       # 31 a 180 días
    "PN07814NM": "tasa_plazo_360d",       # 181 a 360 días
    "PN07815NM": "tasa_plazo_mas360",     # más de 360 días
    "PD04722MM": "tasa_referencia_bcrp",  # tasa de referencia (X4)
}
URL_BASE = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
CABECERAS = {"User-Agent": f"UNCP-Finanzas1-Tema21 (estudiante {CODIGO_MATRICULA}; uso academico)"}

# ---------- 2. Rutas relativas (nada de C:\Users\...) ----------
PROYECTO = Path(__file__).resolve().parent.parent   # carpeta que contiene a /codigo
CRUDOS = PROYECTO / "datos_crudos"
LOG = PROYECTO / "log_ejecucion.txt"
CRUDOS.mkdir(exist_ok=True)


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en pantalla y en el log."""
    ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ahora}] {mensaje}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ---------- 3. Descarga, una serie por pedido ----------
escribir_log("=== Inicio 01_extraccion_api.py (BCRP API) ===")
filas = []
for codigo, nombre in SERIES.items():
    url = f"{URL_BASE}/{codigo}/json/{FECHA_INICIO}/{FECHA_CORTE}"
    respuesta = requests.get(url, headers=CABECERAS, timeout=60)
    try:
        datos = respuesta.json()
    except ValueError:
        escribir_log(f"ERROR {codigo}: HTTP {respuesta.status_code}, no devolvió JSON -> {respuesta.text[:150]}")
        continue
    for periodo in datos["periods"]:
        filas.append({
            "periodo": periodo["name"],
            "codigo_serie": codigo,
            "nombre_corto": nombre,
            "valor": periodo["values"][0],   # texto tal cual
        })
    escribir_log(f"{codigo} ({nombre}) | HTTP {respuesta.status_code} | {len(datos['periods'])} meses | {url}")
    time.sleep(1)   # pausa entre pedidos

# ---------- 4. Guardar crudos sin modificar ----------
tabla = pd.DataFrame(filas)
archivo = CRUDOS / f"datos_crudos_bcrp_{CODIGO_MATRICULA}.csv"
tabla.to_csv(archivo, index=False, encoding="utf-8")
escribir_log(f"Guardado {archivo.name} | filas: {len(tabla)}")
escribir_log("=== Fin 01_extraccion_api.py ===")
