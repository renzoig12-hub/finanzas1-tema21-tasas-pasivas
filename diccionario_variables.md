# Diccionario de variables
Autor: Renzo Jhonel Ignacio Paucar · 2024200504J · Tema N.° 21 · Archivo: datos_procesados/datos_procesados_2024200504J.csv

| Variable | Rol | Definición | Unidad | Frecuencia | Fuente | URL / endpoint |
|---|---|---|---|---|---|---|
| periodo | Llave | Mes de referencia (AAAA-MM) | fecha | mensual | — | — |
| tipo_entidad | Llave | B = banco, F = financiera, C = caja municipal | código | — | SBS | — |
| entidad | Llave | Nombre de la entidad (normalizado con tabla de equivalencias) | texto | — | SBS | — |
| plazo_181_360d | **Y** | Tasa pasiva de depósitos a plazo de 181 a 360 días, MN | % TEA | mensual | SBS | https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIPasivaDepositoEmpresa.aspx?tip={B,F,C} |
| plazo_promedio | Robustez | Tasa pasiva promedio de depósitos a plazo, MN | % TEA | mensual | SBS | ídem |
| tasa_ahorro, plazo_30d, plazo_31_90d, plazo_91_180d, plazo_mas360d, tasa_cts | Complementarias | Tasas pasivas por tipo de depósito y plazo, MN | % TEA | mensual | SBS | ídem |
| morosidad | **X1** | Créditos atrasados (criterio SBS) / créditos directos | % | mensual | SBS, Indicadores Financieros | https://www.sbs.gob.pe/app/stats_net/stats/EstadisticaSistemaFinancieroResultados.aspx?c={B-2401, B-3301, C-1301} |
| ratio_capital_global | **X2** | Patrimonio efectivo / activos y contingentes ponderados por riesgo | % | mensual | SBS, Indicadores Financieros | ídem |
| capital_al | Control | Fecha a la que corresponde el ratio de capital (rezago de publicación) | texto | mensual | SBS | ídem |
| tipo_entidad_nombre | **X3** | Tipo de entidad (dummies en la regresión; referencia = banco) | categoría | — | SBS | — |
| tasa_referencia_bcrp | **X4** | Tasa de referencia de la política monetaria (PD04722MM) | % | mensual | BCRP | https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04722MM/json/2023-1/2025-12 |
| tipmn_banca | Complementaria | Tasa pasiva promedio de la banca en MN, TIPMN (PN07816NM) | % | mensual | BCRP | https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN07816NM/json/2023-1/2025-12 |
| tasa_plazo_30d/180d/360d/mas360 | Complementarias | Tasas pasivas de la banca por plazo (PN07812NM a PN07815NM) | % | mensual | BCRP | API BCRPData |
| fecha_consultada | Control | Día hábil usado para bancos y financieras (último día hábil del mes) | fecha | mensual | propio | — |
| atipico_plazo_181_360d | Control | Marca de valor atípico (regla IQR por tipo de entidad) | booleano | mensual | propio | — |

**Variables construidas en 04_analisis.py:** `morosidad_w` y `ratio_capital_global_w` (winsorizadas en los percentiles 1 y 99); `vf` = 10 000 × (1 + TEA)^(360/360); `intereses` = vf − 10 000; `diferencial` = tasa − tasa BCRP.
