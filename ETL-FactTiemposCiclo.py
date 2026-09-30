#**********************************************************************************************
# @Nombre: Proceso para el calculo de los tiempos de ciclo
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import re                              # Manejo de expresiones regulares
import pyarrow.parquet as pq           # Manejo de archivos parquet
import Funciones as fn                 # Funciones personalizadas
import subprocess                      # Controlador de scripts
import sys                             # Interprete python
from sqlalchemy import types           # Manejo de tipos de campos en db
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1160
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Calculo Tiempo ciclo*"
table = "FactViajesTiempos"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#----------------------------------------------------------------------------------------------
def zscore_mad(series):
    med = series.median()
    mad = (series - med).abs().median()
    return (series - med).abs() <= 2 * mad

def to_seconds(col):
    s = pd.to_datetime(col, errors = "coerce")
    base = pd.Timestamp("1900-01-01")
    return (s - base).dt.total_seconds()

try:
    # Calendario
    dimcalendario = pd.read_sql_query(''' SELECT "Date", "DateType"
                                          FROM public."DimDate"
                                          WHERE "DateKey" BETWEEN 20220401 AND 20231231 ''', con = fn.enginea)

    # Paths
    userpc = os.getenv("PAT_NAS")
    rut = "02 Datos/12 viajes_desglosados"
    ruta_destino = os.path.join(userpc, rut)

    pathfiles = [os.path.join(ruta_destino, f)
                 for f in os.listdir(ruta_destino)
                 if f.endswith(".parquet")
                 and int(re.search(r"^\d{8}", f).group()) >= 20250601]

    ruta_base = os.getenv("PAT_GESTION_INFO")
    ruta_origen = os.path.join(ruta_base, "01 Viajes_Desglosados")
    carpeta_procesados = os.path.join(ruta_origen, "procesados")
    os.makedirs(carpeta_procesados, exist_ok = True)

    # Consolidación parquet por fecha
    archivos_origen = [os.path.join(ruta_origen, f)
                       for f in os.listdir(ruta_origen)
                       if f.endswith(".parquet")]

    df_archivos = (pd.DataFrame({"path": archivos_origen})
                   .assign(fecha = lambda d: d["path"].apply(lambda x: os.path.basename(x)[:8])))

    for fecha, grupo in df_archivos.groupby("fecha"):
        archivo_salida = os.path.join(ruta_destino, f"{fecha}_viajes_desglosado.parquet")

        if not os.path.exists(archivo_salida):
            tablas = [pq.read_table(p).to_pandas()
                      for p in grupo["path"]]
            pd.concat(tablas, ignore_index = True).to_parquet(archivo_salida)

            for p in grupo["path"]:
                try:
                    os.rename(p, os.path.join(carpeta_procesados, os.path.basename(p)))
                except Exception:
                    print(f"No se pudo mover: {p}")

    #------------------------------------------------------------------------------------------
    columnas = ["Fecha", "Linea", "Sentido", "Vehiculo", "Cumplimiento", "DHoraReal", "DurTeor", 
                "DurReal", "LongitudRuta", "DistanciaComputable"]

    dimrutas = pd.DataFrame({"Ruta": ["KA324","KB326","KH308","KH317","KL312","KL328","KL329",
                                      "KA332","KB314","KG311","KH318","KH327","KL325","KL331"],
                             "UF":   ["UF06"]*7 + ["UF17"]*7})

    # Transformación principal
    datafinal = (pd.concat([pd.read_parquet(p, columns = columnas) for p in pathfiles], ignore_index = True)
                 .assign(DurReal = lambda d: d["DurReal"].astype(str),
                         LongitudRuta = lambda d: d["LongitudRuta"].astype(str),
                         DistanciaComputable = lambda d: d["DistanciaComputable"].astype(str))
                 .query("DurReal != ''")
                 .assign(DistanciaComputable = lambda d: pd.to_numeric(d["DistanciaComputable"].str.replace(r"[^\d.]", "", regex = True), errors = "coerce"),
                         LongitudRuta = lambda d: pd.to_numeric(d["LongitudRuta"].str.replace(r"[^\d.]", "", regex = True), errors = "coerce"))
                 .dropna(subset = ["DistanciaComputable", "LongitudRuta"])
                 .assign(Var = lambda d: (d["DistanciaComputable"] / d["LongitudRuta"]).round(2))
                 .query("Var > 0.9")
                 .drop(columns = ["LongitudRuta"])
                 .assign(LineaSae = lambda d: d["Linea"].str.split().str[0],
                         Ruta = lambda d: d["Linea"].str.split().str[1])
                 .merge(dimrutas, on = "Ruta", how = "left")
                 .assign(Ruta = lambda d: d["Ruta"] + "-" + d["Sentido"].str[0],
                         Fecha = lambda d: pd.to_datetime(d["Fecha"], dayfirst = True),
                         DHoraReal = lambda d: pd.to_datetime(d["DHoraReal"], errors = "coerce").dt.hour,
                         DurTeorSec = lambda d: to_seconds(d["DurTeor"]),
                         DurRealSec = lambda d: to_seconds(d["DurReal"]),
                         TimeTraveled = lambda d: ((d["DistanciaComputable"] / 1000) / (d["DurRealSec"] / 3600)).round(2),
                         InsertDate = datetime.now()))

    #------------------------------------------------------------------------------------------
    factviajes = datafinal[["Fecha", "Ruta", "UF", "DHoraReal", "DurTeorSec", "DurRealSec",
                            "DistanciaComputable", "TimeTraveled", "InsertDate"]]

    #------------------------------------------------------------------------------------------
    sql_types = {"Fecha": types.DATE, "Ruta": types.TEXT, "UF": types.TEXT, "DHoraReal": types.INTEGER,
                 "DurTeorSec": types.INTEGER, "DurRealSec": types.INTEGER, "DistanciaComputable": types.INTEGER,
                 "TimeTraveled": types.FLOAT, "InsertDate": types.TIMESTAMP}

    # Cargue al DW
    factviajes.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    #------------------------------------------------------------------------------------------
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = factviajes["Fecha"].max(), cantidad_registros = len(factviajes))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

#----------------------------------------------------------------------------------------------
# Power BI
path = os.getenv("PAT_PBI_REFRESH")
os.system(f'python "{path}" {os.getenv("PBI_RUTAS")}')

#----------------------------------------------------------------------------------------------
# Desencadenar el proceso para el consumo de ruta
subprocess.run([sys.executable, r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\ETL-FactConsumoRuta.py"])
