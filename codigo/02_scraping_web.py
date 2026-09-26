# Autor: Renzo Jhonel Ignacio Paucar
# Código de matrícula: 2024200504J
# Tema N.° 21 (Unidad I): Tasas pasivas comparadas entre banca, cajas y financieras: valor futuro de un depósito
# Fecha de extracción: 2026-09-24

"""
VÍA 2 - Scraping / descarga programática de la SBS.
Para cada mes y tipo de entidad (Bancos, Financieras, Cajas municipales):
  1) abre la página de tasas pasivas por empresa,
  2) llena el formulario con el periodo (calendario o menús año/mes).
     Bancos y financieras: último día HÁBIL del mes (la SBS no publica sábados,
     domingos ni feriados: si el día no tiene datos, se retrocede un día).
     Cajas municipales: el mes completo.
  3) aprieta "Exportar" y guarda el Excel oficial SIN modificar en datos_crudos/sbs/,
  4) lee la tabla (una fila por entidad) y la junta en datos_crudos_sbs_<codigo>.csv.
Además (parte B) descarga los "Indicadores Financieros" mensuales por empresa
(B-2401 bancos, B-3301 financieras, C-1301 cajas municipales) tomando los enlaces
directamente de la página del Boletín Estadístico, y extrae el Ratio de Capital
Global y la Morosidad (Créditos Atrasados / Créditos Directos) de cada entidad.
Respeta robots.txt (la ruta /app/ no está prohibida), usa User-Agent identificable
y pausa de 1.5 s entre solicitudes.
Ejecutar desde la carpeta principal:  python codigo/02_scraping_web.py
"""

import calendar
import json
import re
import time
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------- 1. Parámetros congelados ----------
CODIGO_MATRICULA = "2024200504J"
ANIO_INICIO, MES_INICIO = 2023, 1     # enero 2023
ANIO_CORTE, MES_CORTE = 2025, 12      # diciembre 2025 -> 36 meses

TIPOS = {"B": "Banco", "F": "Financiera", "C": "Caja municipal"}
URL_TASAS = "https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIPasivaDepositoEmpresa.aspx?tip={tipo}"
CABECERAS = {"User-Agent": f"UNCP-Finanzas1-Tema21 (estudiante {CODIGO_MATRICULA}; uso academico)"}
PAUSA = 1.5   # segundos entre solicitudes

# Qué partes ejecutar (ambas en True para reproducir todo desde cero)
DESCARGAR_TASAS = True         # parte A: tasas pasivas por empresa (formularios)
DESCARGAR_INDICADORES = True   # parte B: morosidad y capital (Boletín Estadístico)

# Parte B: códigos de reporte "Indicadores Financieros" por tipo de entidad
REPORTES_INDICADORES = {"B": "B-2401", "F": "B-3301", "C": "C-1301"}
URL_BOLETIN = "https://www.sbs.gob.pe/app/stats_net/stats/EstadisticaSistemaFinancieroResultados.aspx?c={codigo}"
NUMERO_MES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
              "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

# Opciones de los menús de cajas (tal como aparecen en la página)
ANIOS = ['2026', '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018',
         '2017', '2016', '2015', '2014', '2013', '2012']
MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
         'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']

# Columnas del Excel de la SBS (columna 1 a 9)
COLUMNAS_SBS = ["entidad", "tasa_ahorro", "plazo_30d", "plazo_31_90d", "plazo_91_180d",
                "plazo_181_360d", "plazo_mas360d", "plazo_promedio", "tasa_cts"]

# ---------- 2. Rutas relativas ----------
PROYECTO = Path(__file__).resolve().parent.parent
CRUDOS = PROYECTO / "datos_crudos"
CRUDOS_SBS = CRUDOS / "sbs"
LOG = PROYECTO / "log_ejecucion.txt"
CRUDOS_SBS.mkdir(parents=True, exist_ok=True)


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en pantalla y en el log."""
    ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ahora}] {mensaje}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def campos_ocultos(html):
    """Toma los campos ocultos del formulario (__VIEWSTATE, etc.) para devolverlos."""
    sopa = BeautifulSoup(html, "html.parser")
    return {c.get("name"): c.get("value", "") for c in sopa.find_all("input", type="hidden") if c.get("name")}


def formulario_calendario(html, fecha, boton):
    """Bancos y financieras: calendario con fecha 'AAAA-MM-DD'."""
    anio, mes, dia = fecha.split("-")
    f = campos_ocultos(html)
    f["ctl00$cphContent$rdpDate"] = fecha
    f["ctl00$cphContent$rdpDate$dateInput"] = f"{dia}/{mes}/{anio}"
    f["ctl00_cphContent_rdpDate_dateInput_ClientState"] = json.dumps({
        "enabled": True, "emptyMessage": "",
        "validationText": f"{fecha}-00-00-00", "valueAsString": f"{fecha}-00-00-00",
        "minDateStr": "1000-01-01-00-00-00", "maxDateStr": "2099-12-31-00-00-00",
        "lastSetTextBoxValue": f"{dia}/{mes}/{anio}"})
    f["ctl00_cphContent_rdpDate_calendar_SD"] = f"[[{int(anio)},{int(mes)},{int(dia)}]]"
    f[f"ctl00$cphContent${boton}"] = "Consultar" if boton == "btnConsultar" else "Exportar"
    return f


def estado_menu(texto, posicion):
    """ClientState de un menú Telerik: texto elegido y su posición en la lista."""
    return json.dumps({"enabled": True, "logEntries": [], "selectedIndex": posicion,
                       "selectedText": texto, "selectedValue": texto, "text": texto, "value": texto})


def formulario_mensual(html, anio, mes, boton):
    """Cajas municipales: menús de año y mes."""
    texto_anio, texto_mes = str(anio), MESES[mes - 1]
    f = campos_ocultos(html)
    f["ctl00_cphContent_rAnio_ClientState"] = estado_menu(texto_anio, ANIOS.index(texto_anio))
    f["ctl00_cphContent_rMes_ClientState"] = estado_menu(texto_mes, mes - 1)
    f["ctl00$cphContent$rAnio"] = texto_anio
    f["ctl00$cphContent$rMes"] = texto_mes
    f[f"ctl00$cphContent${boton}"] = "Consultar" if boton == "btnConsultaMensual" else "Exportar"
    return f


def ultimo_dia_habil(anio, mes, retroceso):
    """Último día del mes menos 'retroceso' días (para saltar fines de semana y feriados)."""
    fecha = date(anio, mes, calendar.monthrange(anio, mes)[1]) - timedelta(days=retroceso)
    return fecha.strftime("%Y-%m-%d")


def descargar_excel_bf(sesion, tipo, fecha):
    """Bancos y financieras: abre, consulta la fecha exacta y exporta."""
    url = URL_TASAS.format(tipo=tipo)
    r0 = sesion.get(url, headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    r1 = sesion.post(url, data=formulario_calendario(r0.text, fecha, "btnConsultar"), headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    r2 = sesion.post(url, data=formulario_calendario(r1.text, fecha, "btnExportar"), headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    return r2


def descargar_excel_c(sesion, anio, mes):
    """Cajas: abre, consulta año y mes, y exporta."""
    url = URL_TASAS.format(tipo="C")
    r0 = sesion.get(url, headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    r1 = sesion.post(url, data=formulario_mensual(r0.text, anio, mes, "btnConsultaMensual"), headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    r2 = sesion.post(url, data=formulario_mensual(r1.text, anio, mes, "btnExportarM"), headers=CABECERAS, timeout=60)
    time.sleep(PAUSA)
    return r2


def leer_excel_sbs(contenido, periodo, tipo):
    """Convierte el Excel de la SBS en una tabla: una fila por entidad (valores tal cual)."""
    hoja = pd.read_excel(BytesIO(contenido), header=None)
    fila_titulos = hoja.index[hoja[1] == "Tasa Anual (%)"][0]
    filas = []
    for i in range(fila_titulos + 2, len(hoja)):
        nombre = hoja.iloc[i, 1]
        if pd.isna(nombre) or nombre == "Promedio":
            break
        filas.append(dict(zip(COLUMNAS_SBS, hoja.iloc[i, 1:10])))
    tabla = pd.DataFrame(filas)
    tabla.insert(0, "periodo", periodo)
    tabla.insert(1, "tipo_entidad", tipo)
    tabla["subtitulo_sbs"] = str(hoja.iloc[fila_titulos - 2, 1])   # para verificar el periodo
    return tabla


def periodo_correcto(subtitulo, tipo, anio, mes, fecha=None):
    """Comprueba que el Excel sea del periodo pedido, leyendo su subtítulo."""
    if tipo == "C":
        # El menú dice "Setiembre" pero el Excel dice "Septiembre": aceptamos ambos
        nombres = [MESES[mes - 1]] + (["Septiembre"] if mes == 9 else [])
        return any(f"{n} del {anio}" in subtitulo for n in nombres)
    a, m, d = fecha.split("-")
    return f"{d}/{m}/{a}" in subtitulo


def lista_de_meses():
    """Genera (año, mes) desde el inicio hasta el corte."""
    anio, mes = ANIO_INICIO, MES_INICIO
    while (anio, mes) <= (ANIO_CORTE, MES_CORTE):
        yield anio, mes
        mes += 1
        if mes == 13:
            anio, mes = anio + 1, 1


# ---------- 3. PARTE A: tasas pasivas por empresa ----------
escribir_log("=== Inicio 02_scraping_web.py (SBS) ===")

if DESCARGAR_TASAS:
    sesion = requests.Session()
    todas = []
    fallas = []

    def intentar(tipo, anio, mes, fecha=None):
        """Descarga, verifica y guarda un periodo. Devuelve True si salió bien."""
        periodo = f"{anio}-{mes:02d}"
        etiqueta = f"{tipo} {periodo}" + (f" (fecha {fecha})" if fecha else "")
        try:
            r = descargar_excel_c(sesion, anio, mes) if tipo == "C" else descargar_excel_bf(sesion, tipo, fecha)
            if r.content[:2] != b"PK":
                escribir_log(f"{etiqueta} | HTTP {r.status_code} | sin Excel")
                return False
            tabla = leer_excel_sbs(r.content, periodo, tipo)
            subtitulo = tabla["subtitulo_sbs"].iloc[0]
            if not periodo_correcto(subtitulo, tipo, anio, mes, fecha):
                escribir_log(f"{etiqueta} | periodo distinto al pedido: '{subtitulo[-30:]}'")
                return False
            tabla["fecha_consultada"] = fecha if fecha else periodo
            archivo = CRUDOS_SBS / f"sbs_{tipo}_{periodo}.xlsx"
            archivo.write_bytes(r.content)                   # Excel original, sin tocar
            todas.append(tabla)
            escribir_log(f"{etiqueta} | HTTP {r.status_code} | {len(tabla)} entidades | {archivo.name}")
            return True
        except Exception as error:
            escribir_log(f"{etiqueta} | ERROR: {error}")
            return False


    for tipo in TIPOS:
        for anio, mes in lista_de_meses():
            if tipo == "C":
                exito = intentar("C", anio, mes) or intentar("C", anio, mes)   # 2 intentos
            else:
                exito = False
                for retroceso in range(0, 6):     # último día, y si no hay datos, 1..5 días antes
                    if intentar(tipo, anio, mes, ultimo_dia_habil(anio, mes, retroceso)):
                        exito = True
                        break
            if not exito:
                fallas.append(f"{tipo} {anio}-{mes:02d}")

    # Juntar todo en un CSV crudo
    crudo = pd.concat(todas, ignore_index=True)
    archivo_csv = CRUDOS / f"datos_crudos_sbs_{CODIGO_MATRICULA}.csv"
    crudo.to_csv(archivo_csv, index=False, encoding="utf-8")

    escribir_log(f"Guardado {archivo_csv.name} | filas: {len(crudo)}")
    for tipo in TIPOS:
        parte = crudo[crudo["tipo_entidad"] == tipo]
        escribir_log(f"   {TIPOS[tipo]}: {parte['periodo'].nunique()} meses, {len(parte)} filas")
    escribir_log(f"Periodos que fallaron: {fallas if fallas else 'ninguno'}")

# ---------- 4. PARTE B: morosidad y ratio de capital (Indicadores Financieros) ----------
def enlaces_del_boletin(codigo):
    """Lee la página del Boletín y devuelve {periodo 'AAAA-MM': url del Excel} para el rango pedido."""
    r = requests.get(URL_BOLETIN.format(codigo=codigo), headers=CABECERAS, timeout=60)
    sopa = BeautifulSoup(r.text, "html.parser")
    enlaces = {}
    for a in sopa.find_all("a"):
        href = a.get("href") or ""
        # ejemplo: https://intranet2.sbs.gob.pe/estadistica/financiera/2025/Enero/B-2401-en2025.XLS
        m = re.search(r"/(\d{4})/([A-Za-z]+)/" + re.escape(codigo) + r"-[a-z]{2}\d{4}\.xlsx?$", href, re.I)
        if not m:
            continue
        anio, mes = int(m.group(1)), NUMERO_MES.get(m.group(2).lower())
        if mes and (ANIO_INICIO, MES_INICIO) <= (anio, mes) <= (ANIO_CORTE, MES_CORTE):
            enlaces[f"{anio}-{mes:02d}"] = href
    escribir_log(f"Boletín {codigo} | HTTP {r.status_code} | {len(enlaces)} meses encontrados en el rango")
    return enlaces


def es_numero(valor):
    return isinstance(valor, (int, float)) and not pd.isna(valor)


def leer_indicadores(contenido, periodo, tipo):
    """
    Extrae Ratio de Capital Global y Morosidad de cada entidad.
    Busca por CONTENIDO (no por posición fija) porque el formato cambia entre
    bancos/financieras (un bloque) y cajas (dos bloques lado a lado).
    """
    hoja = pd.read_excel(BytesIO(contenido), header=None)
    texto = hoja.map(lambda v: " ".join(str(v).split()) if isinstance(v, str) else v)

    def buscar_fila(patron):
        for i in range(len(texto)):
            for v in texto.iloc[i]:
                if isinstance(v, str) and re.search(patron, v):
                    return i, v
        raise ValueError(f"No se encontró la fila: {patron}")

    fila_cap, etiqueta_cap = buscar_fila(r"^Ratio de Capital Global")
    fila_mor, _ = buscar_fila(r"^Créditos Atrasados \(criterio SBS\)\*+ ?/ ?Créditos Directos$")
    fecha_cap = re.search(r"al (\d{2}/\d{2}/\d{4})", etiqueta_cap)

    # Fecha del reporte (celda tipo fecha en las primeras filas) para verificar el periodo
    fecha_reporte = next((v for v in hoja.iloc[:6].values.ravel() if isinstance(v, (pd.Timestamp, datetime))), None)

    filas = []
    for j in range(hoja.shape[1]):
        capital = hoja.iloc[fila_cap, j]
        if not es_numero(capital):
            continue
        nombre = None
        for i in range(fila_cap - 1, -1, -1):          # subir por la columna hasta hallar el nombre
            if isinstance(texto.iloc[i, j], str):
                nombre = texto.iloc[i, j]
                break
        if nombre is None or nombre.upper().startswith("TOTAL"):
            continue
        filas.append({
            "periodo": periodo,
            "tipo_entidad": tipo,
            "entidad_indicadores": nombre,
            "ratio_capital_global": capital,
            "morosidad": hoja.iloc[fila_mor, j],
            "capital_al": fecha_cap.group(1) if fecha_cap else "mismo mes",
            "fecha_reporte": pd.Timestamp(fecha_reporte).strftime("%Y-%m") if fecha_reporte is not None else None,
        })
    return pd.DataFrame(filas)


if DESCARGAR_INDICADORES:
    CRUDOS_IND = CRUDOS / "sbs_indicadores"
    CRUDOS_IND.mkdir(parents=True, exist_ok=True)
    indicadores = []
    fallas_ind = []
    for tipo, codigo in REPORTES_INDICADORES.items():
        enlaces = enlaces_del_boletin(codigo)
        time.sleep(PAUSA)
        for anio, mes in lista_de_meses():
            periodo = f"{anio}-{mes:02d}"
            url = enlaces.get(periodo)
            if not url:
                escribir_log(f"{codigo} {periodo} | sin enlace en el Boletín")
                fallas_ind.append(f"{codigo} {periodo}")
                continue
            try:
                r = requests.get(url, headers=CABECERAS, timeout=60)
                tabla = leer_indicadores(r.content, periodo, tipo)
                if tabla["fecha_reporte"].iloc[0] not in (None, periodo):
                    raise ValueError(f"el archivo es de {tabla['fecha_reporte'].iloc[0]}")
                (CRUDOS_IND / url.split("/")[-1]).write_bytes(r.content)   # archivo original, sin tocar
                indicadores.append(tabla)
                escribir_log(f"{codigo} {periodo} | HTTP {r.status_code} | {len(tabla)} entidades | {url.split('/')[-1]}")
            except Exception as error:
                escribir_log(f"{codigo} {periodo} | ERROR: {error}")
                fallas_ind.append(f"{codigo} {periodo}")
            time.sleep(PAUSA)

    crudo_ind = pd.concat(indicadores, ignore_index=True)
    archivo_ind = CRUDOS / f"datos_crudos_sbs_indicadores_{CODIGO_MATRICULA}.csv"
    crudo_ind.to_csv(archivo_ind, index=False, encoding="utf-8")
    escribir_log(f"Guardado {archivo_ind.name} | filas: {len(crudo_ind)}")
    for tipo in REPORTES_INDICADORES:
        parte = crudo_ind[crudo_ind["tipo_entidad"] == tipo]
        escribir_log(f"   {TIPOS[tipo]}: {parte['periodo'].nunique()} meses, {len(parte)} filas")
    escribir_log(f"Indicadores que fallaron: {fallas_ind if fallas_ind else 'ninguno'}")

escribir_log("=== Fin 02_scraping_web.py ===")
