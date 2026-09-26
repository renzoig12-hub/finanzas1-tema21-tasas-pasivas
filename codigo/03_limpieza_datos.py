# Autor: Renzo Jhonel Ignacio Paucar
# Código de matrícula: 2024200504J
# Tema N.° 21 (Unidad I): Tasas pasivas comparadas entre banca, cajas y financieras: valor futuro de un depósito
# Fecha de extracción: 2026-09-25

"""
03_limpieza_datos.py
Une y limpia las tres bases crudas:
  - datos_crudos_sbs_...csv              (tasas pasivas por entidad: variable Y)
  - datos_crudos_sbs_indicadores_...csv  (morosidad X1 y ratio de capital X2)
  - datos_crudos_bcrp_...csv             (tasa de referencia X4 y tasas del sistema)
Pasos:
  1) normaliza los nombres de las entidades con una tabla de equivalencias,
  2) convierte "-" en faltante y el texto en número,
  3) verifica que no haya duplicados,
  4) une SBS-tasas + SBS-indicadores por (periodo, tipo_entidad, entidad)
     y agrega el BCRP por periodo,
  5) marca valores atípicos (no los borra) y guarda datos_procesados_<codigo>.csv
     con su hash SHA-256.
No descarga nada: trabaja solo con los archivos de datos_crudos/.
Ejecutar desde la carpeta principal:  python codigo/03_limpieza_datos.py
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

CODIGO_MATRICULA = "2024200504J"

# ---------- 1. Rutas ----------
PROYECTO = Path(__file__).resolve().parent.parent
CRUDOS = PROYECTO / "datos_crudos"
PROCESADOS = PROYECTO / "datos_procesados"
LOG = PROYECTO / "log_ejecucion.txt"
PROCESADOS.mkdir(exist_ok=True)

ARCHIVO_TASAS = CRUDOS / f"datos_crudos_sbs_{CODIGO_MATRICULA}.csv"
ARCHIVO_INDIC = CRUDOS / f"datos_crudos_sbs_indicadores_{CODIGO_MATRICULA}.csv"
ARCHIVO_BCRP = CRUDOS / f"datos_crudos_bcrp_{CODIGO_MATRICULA}.csv"
ARCHIVO_SALIDA = PROCESADOS / f"datos_procesados_{CODIGO_MATRICULA}.csv"

NOMBRE_TIPO = {"B": "Banco", "F": "Financiera", "C": "Caja municipal"}

# ---------- 2. Tabla de equivalencias de nombres ----------
# Nombre en "Indicadores Financieros" (ya sin asteriscos ni notas)  ->  nombre en "Tasas"
# Verificado por periodos de aparición (ver bitácora / artículo):
#   B. De Comercio -> BANCOM (cambio de nombre), B. China Perú -> Bank of China,
#   HSBC Bank Perú = Banco GNB (etiqueta antigua en el cuadro B-2401).
EQUIVALENCIAS = {
    "B": {
        "Alfin Banco": "Alfin",
        "B. BBVA Perú": "BBVA",
        "B. BCI Perú": "BCI",
        "B. China Perú": "Bank of China",
        "Bank of China": "Bank of China",
        "B. De Comercio": "Bancom",
        "BANCOM": "Bancom",
        "B. De Crédito del Perú (con sucursales en el exterior)": "Crédito",
        "B. Falabella Perú": "Falabella",
        "B. ICBC": "ICBC",
        "B. Interamericano de Finanzas": "BIF",
        "B. Pichincha": "Pichincha",
        "B. Ripley": "Ripley",
        "B. Santander Perú": "Santander",
        "Citibank": "Citibank",
        "Compartamos Banco": "Compartamos",
        "HSBC Bank Perú": "GNB",
        "Interbank": "Interbank",
        "Mibanco": "Mibanco",
        "Santander Consumer Bank": "Santander Cons. Bank",
        "Scotiabank Perú": "Scotiabank",
    },
    "F": {
        "Compartamos Financiera": "Compartamos",
        "Crediscotia Financiera": "Crediscotia",
        "Financiera Confianza": "Confianza",
        "Financiera Credinka": "Credinka",
        "Financiera Efectiva": "Efectiva",
        "Financiera Oh!": "Oh!",
        "Financiera Proempresa": "Proempresa",
        "Financiera Qapaq": "Qapaq",
        "Financiera Surgir": "Surgir",
        "Mitsui Auto Finance": "Mitsui",
        # "Financiera Santander Consumer" (mar-may 2025) no tiene tasas como financiera: queda fuera
    },
    "C": {
        "CMAC Del Santa": "CMAC del Santa",   # solo cambia la mayúscula
    },
}
# En la base de tasas, el Banco de Comercio también cambió de nombre
EQUIVALENCIAS_TASAS = {"B": {"Comercio": "Bancom"}}

COLUMNAS_TASAS = ["tasa_ahorro", "plazo_30d", "plazo_31_90d", "plazo_91_180d",
                  "plazo_181_360d", "plazo_mas360d", "plazo_promedio", "tasa_cts"]

MESES_BCRP = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7,
              "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def escribir_log(mensaje):
    ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ahora}] {mensaje}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def limpiar_nombre(nombre):
    """Quita espacios repetidos y marcas de notas al pie: 'Citibank***' -> 'Citibank', 'CMAC Sullana1/' -> 'CMAC Sullana'."""
    nombre = " ".join(str(nombre).split())
    nombre = re.sub(r"(\*+|\d+/)$", "", nombre).strip()
    return nombre


def a_numero(serie):
    """Convierte texto a número; '-' y vacíos pasan a faltante (NaN)."""
    return pd.to_numeric(serie.replace({"-": np.nan, "": np.nan}), errors="coerce")


def verificar_duplicados(tabla, llaves, nombre):
    dup = tabla.duplicated(subset=llaves, keep=False)
    if dup.any():
        print(tabla[dup].sort_values(llaves).to_string())
        raise ValueError(f"{nombre}: hay {dup.sum()} filas duplicadas en {llaves}. Revisar equivalencias.")


escribir_log("=== Inicio 03_limpieza_datos.py ===")

# ---------- 3. Tasas pasivas (Y) ----------
tasas = pd.read_csv(ARCHIVO_TASAS, dtype=str)
tasas["entidad"] = tasas["entidad"].map(limpiar_nombre)
for tipo, eq in EQUIVALENCIAS_TASAS.items():
    filtro = tasas["tipo_entidad"] == tipo
    tasas.loc[filtro, "entidad"] = tasas.loc[filtro, "entidad"].replace(eq)
for col in COLUMNAS_TASAS:
    tasas[col] = a_numero(tasas[col])
tasas = tasas[["periodo", "tipo_entidad", "entidad", *COLUMNAS_TASAS, "fecha_consultada"]]
verificar_duplicados(tasas, ["periodo", "tipo_entidad", "entidad"], "Tasas")
escribir_log(f"Tasas: {len(tasas)} filas, {tasas['entidad'].nunique()} entidades")

# ---------- 4. Indicadores (X1 morosidad, X2 capital) ----------
indic = pd.read_csv(ARCHIVO_INDIC, dtype=str)
indic["entidad"] = indic["entidad_indicadores"].map(limpiar_nombre)
for tipo, eq in EQUIVALENCIAS.items():
    filtro = indic["tipo_entidad"] == tipo
    indic.loc[filtro, "entidad"] = indic.loc[filtro, "entidad"].replace(eq)
indic["morosidad"] = a_numero(indic["morosidad"])
indic["ratio_capital_global"] = a_numero(indic["ratio_capital_global"])
indic = indic[["periodo", "tipo_entidad", "entidad", "morosidad", "ratio_capital_global", "capital_al"]]
verificar_duplicados(indic, ["periodo", "tipo_entidad", "entidad"], "Indicadores")
escribir_log(f"Indicadores: {len(indic)} filas, {indic['entidad'].nunique()} entidades")

# ---------- 5. BCRP (X4 y tasas del sistema) ----------
bcrp = pd.read_csv(ARCHIVO_BCRP, dtype=str)
mes_txt = bcrp["periodo"].str.split(".").str[0]
anio_txt = bcrp["periodo"].str.split(".").str[1]
bcrp["periodo"] = anio_txt + "-" + mes_txt.map(MESES_BCRP).map("{:02d}".format)
bcrp["valor"] = a_numero(bcrp["valor"])
bcrp = bcrp.pivot(index="periodo", columns="nombre_corto", values="valor").reset_index()
bcrp.columns.name = None
escribir_log(f"BCRP: {len(bcrp)} meses, series: {[c for c in bcrp.columns if c != 'periodo']}")

# ---------- 6. Unión de las fuentes ----------
llaves = ["periodo", "tipo_entidad", "entidad"]
base = tasas.merge(indic, on=llaves, how="left", indicator="union_sbs")
sin_indicadores = base[base["union_sbs"] == "left_only"]
if len(sin_indicadores):
    escribir_log(f"AVISO: {len(sin_indicadores)} filas de tasas sin indicadores: "
                 f"{sorted(sin_indicadores['entidad'].unique())}")
base = base.drop(columns="union_sbs")

solo_indic = indic.merge(tasas[llaves], on=llaves, how="left", indicator=True)
solo_indic = solo_indic[solo_indic["_merge"] == "left_only"]
if len(solo_indic):
    escribir_log(f"Indicadores sin tasas (quedan fuera, no tienen Y): "
                 f"{sorted((solo_indic['tipo_entidad'] + ':' + solo_indic['entidad']).unique())}")

base = base.merge(bcrp, on="periodo", how="left")
base.insert(2, "tipo_entidad_nombre", base["tipo_entidad"].map(NOMBRE_TIPO))
base = base.sort_values(llaves).reset_index(drop=True)

# ---------- 7. Valores atípicos (se marcan, no se borran) ----------
# Regla IQR dentro de cada tipo de entidad sobre la tasa de plazo 181-360 días
def marcar_atipicos(grupo):
    q1, q3 = grupo.quantile(0.25), grupo.quantile(0.75)
    rango = q3 - q1
    return (grupo < q1 - 1.5 * rango) | (grupo > q3 + 1.5 * rango)

base["atipico_plazo_181_360d"] = base.groupby("tipo_entidad")["plazo_181_360d"].transform(marcar_atipicos)
escribir_log(f"Valores atípicos marcados en plazo_181_360d: {int(base['atipico_plazo_181_360d'].sum())}")

# ---------- 8. Guardar y resumir ----------
base.to_csv(ARCHIVO_SALIDA, index=False, encoding="utf-8")
hash_sha = hashlib.sha256(ARCHIVO_SALIDA.read_bytes()).hexdigest()
(PROCESADOS / "hash_sha256.txt").write_text(f"{ARCHIVO_SALIDA.name}  {hash_sha}\n", encoding="utf-8")

escribir_log(f"Guardado {ARCHIVO_SALIDA.name} | filas: {len(base)} | columnas: {base.shape[1]}")
escribir_log(f"SHA-256: {hash_sha}")
for tipo, nombre in NOMBRE_TIPO.items():
    parte = base[base["tipo_entidad"] == tipo]
    escribir_log(f"   {nombre}: {parte['entidad'].nunique()} entidades, {len(parte)} filas")
escribir_log("Datos disponibles (no faltantes) por variable principal:")
for col in ["plazo_181_360d", "plazo_promedio", "morosidad", "ratio_capital_global", "tasa_referencia_bcrp"]:
    escribir_log(f"   {col}: {base[col].notna().sum()} de {len(base)}")
escribir_log("=== Fin 03_limpieza_datos.py ===")
