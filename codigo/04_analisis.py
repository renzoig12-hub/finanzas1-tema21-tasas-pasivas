# Autor: Renzo Jhonel Ignacio Paucar
# Código de matrícula: 2024200504J
# Tema N.° 21 (Unidad I): Tasas pasivas comparadas entre banca, cajas y financieras: valor futuro de un depósito
# Fecha de extracción: 2026-09-25

"""
04_analisis.py
Genera todas las tablas y figuras del artículo a partir de
datos_procesados/datos_procesados_<codigo>.csv y las guarda en /salidas.

  Bloque 1  Muestra de análisis: regla de inclusión (>= 24 meses con tasa) y filas completas
  Bloque 2  Winsorización (percentiles 1 y 99) de morosidad y ratio de capital
  Tabla 1   Estadísticas descriptivas por tipo de entidad
  Tabla 2   Valor futuro de S/ 10 000 a 360 días por tipo de entidad
  Tabla 3   Ranking de entidades por valor futuro
  Tabla 4   Regresión MCO con errores agrupados por entidad + robustez
  Figura 1  Tasa pasiva 181-360 días por tipo vs tasa de referencia BCRP
  Figura 2  Diferencial (tasa - tasa BCRP) vs morosidad
  Figura 3  Intereses de un depósito de S/ 10 000 a un año, por tipo

Fórmula del valor futuro (interés compuesto con TEA):  VF = P x (1 + TEA)^(n/360)
No usa aleatoriedad (no requiere semilla).
Ejecutar desde la carpeta principal:  python codigo/04_analisis.py
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")                       # dibuja sin abrir ventanas (sirve en cualquier computadora)
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf

# ---------- 0. Parámetros ----------
CODIGO_MATRICULA = "2024200504J"
MINIMO_MESES = 24                  # regla de inclusión: al menos 24 de 36 meses con tasa
Y = "plazo_181_360d"               # variable endógena: tasa de depósitos a plazo 181-360 días (TEA %)
Y_ROBUSTEZ = "plazo_promedio"      # tasa promedio de depósitos a plazo (prueba de robustez)
P = 10_000                         # capital inicial del depósito (S/)
N_DIAS = 360                       # plazo del depósito (días)
VARIABLES_MODELO = [Y, "morosidad", "ratio_capital_global", "tipo_entidad_nombre", "tasa_referencia_bcrp"]
LLAVE = ["tipo_entidad", "entidad"]   # tipo + nombre ("Compartamos" banco ≠ "Compartamos" financiera)

ORDEN = ["Banco", "Caja municipal", "Financiera"]
COLOR = {"Banco": "#2a78d6", "Caja municipal": "#1baf7a", "Financiera": "#eb6834"}   # paleta apta para daltonismo
MARCA = {"Banco": "o", "Caja municipal": "s", "Financiera": "^"}                    # forma distinta por tipo

PROYECTO = Path(__file__).resolve().parent.parent
SALIDAS = PROYECTO / "salidas"
LOG = PROYECTO / "log_ejecucion.txt"
SALIDAS.mkdir(exist_ok=True)


def escribir_log(mensaje):
    ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ahora}] {mensaje}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def estilo(ax):
    """Estilo limpio para las figuras: sin bordes arriba/derecha, cuadrícula suave detrás."""
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


escribir_log("=== Inicio 04_analisis.py ===")
base = pd.read_csv(PROYECTO / "datos_procesados" / f"datos_procesados_{CODIGO_MATRICULA}.csv")

# ---------- Bloque 1. Muestra de análisis ----------
meses_con_y = base.groupby(LLAVE)[Y].transform(lambda s: s.notna().sum())
base_incl = base[meses_con_y >= MINIMO_MESES]

todas = set(zip(base["tipo_entidad_nombre"], base["entidad"]))
incluidas = set(zip(base_incl["tipo_entidad_nombre"], base_incl["entidad"]))
excluidas = sorted(todas - incluidas)
pd.DataFrame(excluidas, columns=["tipo_entidad", "entidad_excluida"]).to_csv(SALIDAS / "entidades_excluidas.csv", index=False)

base_analisis = base_incl.dropna(subset=VARIABLES_MODELO).copy()     # filas completas, no se imputa nada
escribir_log(f"Excluidas {len(excluidas)} entidades (< {MINIMO_MESES} meses con tasa). "
             f"Muestra: {base_analisis.groupby(LLAVE).ngroups} entidades, {len(base_analisis)} observaciones")

# ---------- Bloque 2. Winsorización ----------
def winsorizar(serie, inferior=0.01, superior=0.99):
    """Recorta los valores extremos a los percentiles 1 y 99 (no borra filas)."""
    return serie.clip(lower=serie.quantile(inferior), upper=serie.quantile(superior))

for var in ["ratio_capital_global", "morosidad"]:
    base_analisis[var + "_w"] = winsorizar(base_analisis[var])
    escribir_log(f"Winsorización {var}: máximo {base_analisis[var].max():.2f} -> {base_analisis[var + '_w'].max():.2f}")

# Variables derivadas
base_analisis["vf"] = P * (1 + base_analisis[Y] / 100) ** (N_DIAS / 360)       # valor futuro
base_analisis["intereses"] = base_analisis["vf"] - P
base_analisis["diferencial"] = base_analisis[Y] - base_analisis["tasa_referencia_bcrp"]
base_analisis["fecha"] = pd.to_datetime(base_analisis["periodo"] + "-01")
base_analisis["grupo"] = base_analisis["tipo_entidad"] + "_" + base_analisis["entidad"]

# ---------- Tabla 1. Descriptivos ----------
variables = [Y, "morosidad", "ratio_capital_global", "tasa_referencia_bcrp"]
tabla1 = (base_analisis.groupby("tipo_entidad_nombre")[variables]
          .agg(["count", "mean", "std", "min", "max"]).round(2).T)
tabla1.to_csv(SALIDAS / "tabla1_descriptivos.csv")

# ---------- Tabla 2. Valor futuro por tipo ----------
tabla2 = (base_analisis.groupby("tipo_entidad_nombre")
          .agg(TEA_media=(Y, "mean"), VF_medio=("vf", "mean"), Intereses=("intereses", "mean"),
               VF_minimo=("vf", "min"), VF_maximo=("vf", "max"))
          .reindex(ORDEN).round(2))
tabla2["Ganancia_extra_vs_banco"] = (tabla2["Intereses"] - tabla2.loc["Banco", "Intereses"]).round(2)
tabla2.to_csv(SALIDAS / "tabla2_valor_futuro.csv")

# ---------- Tabla 3. Ranking de entidades ----------
tabla3 = (base_analisis.groupby(["tipo_entidad_nombre", "entidad"])
          .agg(TEA_media=(Y, "mean"), VF_medio=("vf", "mean"), Morosidad_media=("morosidad", "mean"),
               Capital_medio=("ratio_capital_global_w", "mean"), Meses=("vf", "size"))
          .round(2).sort_values("VF_medio", ascending=False).reset_index())
tabla3.insert(0, "Puesto", range(1, len(tabla3) + 1))
tabla3.to_csv(SALIDAS / "tabla3_ranking_entidades.csv", index=False)
escribir_log("Tablas 1, 2 y 3 guardadas en salidas/")

# ---------- Tabla 4. Regresión y robustez ----------
FORMULA_X = (" ~ morosidad_w + ratio_capital_global_w"
             " + C(tipo_entidad_nombre, Treatment('Banco')) + tasa_referencia_bcrp")

def estimar(datos, y):
    """MCO con errores estándar agrupados por entidad."""
    datos = datos.dropna(subset=[y]).copy()
    return smf.ols(y + FORMULA_X, data=datos).fit(cov_type="cluster", cov_kwds={"groups": datos["grupo"]})

modelos = {
    "(1) Principal": estimar(base_analisis, Y),
    "(2) Sin BCI": estimar(base_analisis[base_analisis["entidad"] != "BCI"], Y),
    "(3) Y promedio": estimar(base_analisis, Y_ROBUSTEZ),
}

def estrellas(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""

nombres = {
    "C(tipo_entidad_nombre, Treatment('Banco'))[T.Financiera]": "Financiera (vs banco)",
    "C(tipo_entidad_nombre, Treatment('Banco'))[T.Caja municipal]": "Caja municipal (vs banco)",
    "morosidad_w": "Morosidad",
    "ratio_capital_global_w": "Ratio de capital global",
    "tasa_referencia_bcrp": "Tasa de referencia BCRP",
    "Intercept": "Constante",
}
filas = []
for var, etiqueta in nombres.items():
    filas.append({"Variable": etiqueta, **{k: f"{m.params[var]:.3f}{estrellas(m.pvalues[var])}" for k, m in modelos.items()}})
    filas.append({"Variable": "", **{k: f"({m.bse[var]:.3f})" for k, m in modelos.items()}})
filas.append({"Variable": "Observaciones", **{k: int(m.nobs) for k, m in modelos.items()}})
filas.append({"Variable": "R²", **{k: f"{m.rsquared:.3f}" for k, m in modelos.items()}})
tabla4 = pd.DataFrame(filas)
tabla4.to_csv(SALIDAS / "tabla4_regresion.csv", index=False)
with open(SALIDAS / "tabla4_regresion_detalle.txt", "w", encoding="utf-8") as f:
    for nombre_m, m in modelos.items():
        f.write(f"===== {nombre_m} =====\n{m.summary()}\n\n")
escribir_log("Tabla 4 (regresión y robustez) guardada en salidas/")

# ---------- Figura 1. Tasas en el tiempo ----------
mensual = base_analisis.groupby(["fecha", "tipo_entidad_nombre"])[Y].mean().unstack()
referencia = base_analisis.groupby("fecha")["tasa_referencia_bcrp"].first()
fig, ax = plt.subplots(figsize=(9, 4.5))
for tipo in ORDEN:
    ax.plot(mensual.index, mensual[tipo], color=COLOR[tipo], marker=MARCA[tipo], markevery=3, linewidth=2, label=tipo)
ax.plot(referencia.index, referencia, color="gray", linestyle="--", linewidth=2, label="Tasa de referencia BCRP")
ax.set_ylabel("Tasa efectiva anual (%)")
ax.set_title("Figura 1. Tasa pasiva a 181-360 días por tipo de entidad, 2023-2025", loc="left")
ax.legend(frameon=False)
estilo(ax)
fig.text(0.01, -0.02, "Fuente: SBS y BCRP. Elaboración propia.", fontsize=8, color="gray")
fig.savefig(SALIDAS / "figura1_tasas_en_el_tiempo.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------- Figura 2. Diferencial vs morosidad ----------
fig, ax = plt.subplots(figsize=(8, 5))
for tipo in ORDEN:
    p = base_analisis[base_analisis["tipo_entidad_nombre"] == tipo]
    ax.scatter(p["morosidad_w"], p["diferencial"], color=COLOR[tipo], marker=MARCA[tipo],
               s=20, alpha=0.6, edgecolors="white", linewidths=0.5, label=tipo)
ax.axhline(0, color="gray", linestyle="--", linewidth=1)
ax.set_xlabel("Morosidad (%)")
ax.set_ylabel("Diferencial: tasa de la entidad − tasa BCRP (p.p.)")
ax.set_title("Figura 2. Diferencial de la tasa pasiva y morosidad", loc="left")
ax.legend(frameon=False)
estilo(ax)
fig.text(0.01, -0.02, "Fuente: SBS y BCRP. Cada punto es una entidad en un mes.", fontsize=8, color="gray")
fig.savefig(SALIDAS / "figura2_diferencial_vs_morosidad.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------- Figura 3. Intereses por tipo ----------
intereses = tabla2.loc[ORDEN, "Intereses"]
fig, ax = plt.subplots(figsize=(7, 4.2))
barras = ax.bar(ORDEN, intereses, color=[COLOR[t] for t in ORDEN], width=0.55)
for barra, valor in zip(barras, intereses):
    ax.text(barra.get_x() + barra.get_width() / 2, valor + 10, f"S/ {valor:,.2f}", ha="center", fontsize=10)
ax.set_ylabel("Intereses ganados en un año (S/)")
ax.set_ylim(0, intereses.max() * 1.18)
ax.set_title(f"Figura 3. Intereses de un depósito de S/ {P:,} a {N_DIAS} días".replace(",", " "), loc="left")
estilo(ax)
ax.grid(axis="x", visible=False)
fig.text(0.01, -0.02, "VF = P(1 + TEA)^(n/360). Fuente: SBS, 2023-2025. Elaboración propia.", fontsize=8, color="gray")
fig.savefig(SALIDAS / "figura3_intereses_por_tipo.png", dpi=300, bbox_inches="tight")
plt.close(fig)
escribir_log("Figuras 1, 2 y 3 guardadas en salidas/")

# ---------- Resumen en pantalla ----------
print("\n", tabla2.to_string())
print("\n", tabla4.to_string(index=False))
print("\n*** p<0.01, ** p<0.05, * p<0.10. Errores estándar agrupados por entidad entre paréntesis.")
escribir_log("=== Fin 04_analisis.py ===")
