#**********************************************************************************************
# @Nombre: Proceso de Extraccion historico Disponibilidad
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import numpy as np                     # Manipulacion numerica
import os                              # Manejo del sistema
import requests                        # Solicitud a API
import Funciones as fn                 # Funciones ETL
from sqlalchemy import types           # Manejo de tipos de campos en db
from skimpy import clean_columns       # Limpieza de nombres de columnas
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1040
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Disponibilidad Historica*"
table1 = "FactDisponibilidadHistorico"
table2 = "FactDisponibilidadCorte"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

pass_rigel = os.getenv("API_PASS_RIGEL")

inicio_total = pd.to_datetime("2022-04-01")
fin_total = pd.Timestamp.today().normalize() - pd.Timedelta(days = 1)

anios = list(range(inicio_total.year, fin_total.year + 1))

# Funcion de particion por años

def procesar_anio(anio, pass_rigel, inicio_total, fin_total):

    print(f"Procesando año {anio} ...")

    desde = inicio_total if anio == inicio_total.year else pd.to_datetime(f"{anio}-01-01")
    hasta = fin_total if anio == fin_total.year else pd.to_datetime(f"{anio}-12-31")

    url = (f"http://rigel.greenmovil.com.co:8080/"
           f"RigelpbWS/disponibilidadFlota/historial?"
           f"key={pass_rigel}&desde={desde.date()}&hasta={hasta.date()}")

    response = requests.get(url, timeout = 120)
    response.raise_for_status()

    data = response.json()["data"]

    if not data:
        return pd.DataFrame(), pd.DataFrame()
    
    dispo_h = (clean_columns(pd.DataFrame(data), case = 'pascal')
               .drop(columns = ["DateCreatedMilliseconds", "UfCode", "DateOnMilliseconds",
                                "IssueDateMilliseconds", "IssueStatus", "IssueDate", "DateOn"], errors = "ignore")
               .loc[lambda df: df["SystemName"] != ""]
               .assign(DateCreated = lambda df: pd.to_datetime(df["DateCreated"]),
                       IssueDateClosed = lambda df: pd.to_datetime(df["IssueDateClosed"]))
               .assign(TimeUnavailableSec = lambda df: (df["IssueDateClosed"] - df["DateCreated"]).dt.total_seconds())
               .assign(IssueTime = lambda x: pd.to_datetime(x["IssueTime"], format = "%H:%M:%S", errors = "coerce").dt.time,
                       InsertDate = datetime.now(),
                       DateKeyCreated = lambda df: df["DateCreated"].dt.strftime("%Y%m%d"),
                       IssueTypeDet = lambda df: (df["IssueTypeDet"].str.replace(".*TM0.*", "Accidente", regex = True)
                                                                    .str.replace(".*TM1.*", "Accidente", regex = True)
                                                                    .str.replace(".*Móvil en URI.*", "Accidente", regex = True))))

    # Proceso de corte 5:30
    fechas_df = (pd.DataFrame({"DateCorteAM": pd.date_range(start = f"{anio}-01-01 05:30", end = f"{anio}-12-31 05:30", freq = "D")})
                 .assign(key = 1))

    columns_corte = ["DateKeyCreated", "DateCreated", "VehiclePlate", "IssueDateClosed",
                     "IssueType", "IssueTypeDet", "SystemName", "CurrentStatus"]
    dispo_corte = (dispo_h[columns_corte]
                   .copy()
                   .assign(FechaNext = lambda df: df["DateCreated"].dt.normalize() + pd.Timedelta(hours = 5, minutes = 30),
                           FechaHasta = lambda df: df["DateCreated"].dt.normalize() + pd.Timedelta(hours = 5, minutes = 30) + pd.Timedelta(days = 1))
                   .assign(Valida = lambda df: ~(df["IssueDateClosed"].between(df["FechaNext"], df["FechaHasta"]) & (df["DateCreated"] > df["FechaNext"])))
                   .loc[lambda df: df["Valida"]]
                   .assign(key = 1)
                   .merge(fechas_df, on = "key")
                   .drop(columns = "key")
                   .assign(Inop = lambda df: ((df["DateCorteAM"] >= df["DateCreated"]) & (df["DateCorteAM"] <= df["IssueDateClosed"])))
                   .loc[lambda df: df["Inop"]]
                   .sort_values(["VehiclePlate", "DateCreated", "DateCorteAM"])
                   .assign(Lagdate = lambda df: df.groupby(["DateCreated", "VehiclePlate"])["DateCorteAM"].shift(1),
                           rownum = lambda df: df.groupby(["DateCreated", "VehiclePlate"]).cumcount(),
                           nrows = lambda df: df.groupby(["DateCreated", "VehiclePlate"])["DateCorteAM"].transform("count"))
                   .assign(IsLast = lambda df: np.where(df["rownum"] == 0, "F", np.where(df["rownum"] == df["nrows"] - 1, "L", "M")),
                           TimeToCalculate = lambda df: np.where(df["rownum"] == 0, df["DateCreated"], df["Lagdate"]))
                   .assign(DayTimeUnavailableSec = lambda df: np.where(df["IsLast"] == "L", ((df["DateCorteAM"] - df["TimeToCalculate"]).dt.total_seconds() + (df["IssueDateClosed"] - df["DateCorteAM"]).dt.total_seconds()),
                                                                       (df["DateCorteAM"] - df["TimeToCalculate"]).dt.total_seconds()),
                           InsertDate = datetime.now())
                   .drop(columns = ["FechaNext", "FechaHasta", "Valida", "Inop", "Lagdate", 
                                    "rownum", "nrows", "IsLast", "TimeToCalculate"]))

    return dispo_h, dispo_corte


# Solicitud de proceso

lista_dispo_h = []
lista_dispo_corte = []

try:
    for anio in anios:
        dh, dc = procesar_anio(anio, pass_rigel, inicio_total, fin_total)
        lista_dispo_h.append(dh)
        lista_dispo_corte.append(dc)
        print(f"Año {anio} procesado correctamente")

    dispo_h = pd.concat(lista_dispo_h, ignore_index = True)
    dispo_corte = pd.concat(lista_dispo_corte, ignore_index = True)

    sql_types = {'DateKeyCreated': types.INTEGER, 'DateCreated': types.TIMESTAMP, 'IssueDateClosed': types.TIMESTAMP,
                 'IssueTime': types.TIME, 'DaysOff': types.INTEGER, 'IsInmovilizedVehicle': types.BOOLEAN,
                 'TimeUnavailableSec': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    dispo_h.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    sql_types = {'DateKeyCreated': types.INTEGER, 'DateCreated': types.TIMESTAMP, 'IssueDateClosed': types.TIMESTAMP,
                 'DateCorteAM': types.TIMESTAMP, 'DayTimeUnavailableSec': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    dispo_corte.to_sql(table2, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = dispo_h['DateCreated'].max(), cantidad_registros = len(dispo_h))
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = dispo_corte['DateCreated'].max(), cantidad_registros = len(dispo_corte))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))
