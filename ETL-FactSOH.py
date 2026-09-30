#**********************************************************************************************
# @Nombre: Proceso de Cálculo SOH 
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                         # Sistema
import pandas as pd                    # Manipulacion de datos
import numpy as np                     # Manipulacion numerica
import Funciones as fn                 # Funciones ETL
from sqlalchemy import types           # Manejo de tipos de campos en db
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1230
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Calculo SOH*"
table = 'FactSOH'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Descripcion del proceso ---------------------------------------------------------------------
# El proceso para el caluclo del SOH obedece a la siguiente logica:
# @Kilometros: Se obtiene el recorrido en kms de cada bus.
# @Consumo Energetico: Se calculo el consumo energetico para cada bus y para cada mes, de acuerdo
# con los datos generados por el sistema siemens.
# @Ciclo: De acuerdo con alguna teoria, se dice que la bateria pierde la capacidad del 20%
# cuando se completan 3.500 ciclos de carga.
# 
# Calculo del SOH 
# 
# Teniendo el consumo energetico por cada km y los kilometros recorridos, se calculo la cantidad
# de energia carga en el bus hasta la fecha.
# 
# Teniendo la capacidad nominal de la bateria y afectandola por el 20% se obtiene el valor 
# nominal en el limite inferior, el cual se multiplica por la cantidad de ciclos y esto nos da
# un valor en kwh el cual nos indica que cuando la cantidad de energia cargada en el vehiculo
# alcance ese valor entonces la bateria puede presentar en el 80% de vida util.


# Ciclos de carga -----------------------------------------------------------------------------
# La capacidad de las baterias para cada tipologia son:
# @buseton = 282 kwh
# @padron = 383 kwh
# Los ciclos de carga es = 3500

ciclos80pct = 3500

buseton80pct = 282 * 0.8
padron80pct = 383 * 0.8

buseton = buseton80pct * ciclos80pct
padron = padron80pct * ciclos80pct

try:

    # Se procede con el calculo del consumo energetico
    query_km = """
        SELECT dt."FirstDayOfMonth" as "Mes",
               "IdVehiculo",
               SUM("Delta") as "Km",
               MAX(fl."TIPO") as "Tipo"
        FROM ma."FactMeterReading" mr
        LEFT JOIN public."DimDate" dt 
            ON dt."DateKey" = mr."DateKeyReading"
        LEFT JOIN public."DimFlota" fl 
            ON mr."AssetNum" = fl."AssetNum"
        WHERE mr."DateKeyReading" >= 20220101
        GROUP BY dt."FirstDayOfMonth", "IdVehiculo"
        ORDER BY "IdVehiculo", dt."FirstDayOfMonth"
    """

    kmflota = (pd.read_sql(query_km, fn.enginea)
               .assign(Mes = lambda d: pd.to_datetime(d["Mes"]))
               .sort_values(["IdVehiculo", "Mes"])
               .assign(KmCumOdo = lambda d: d.groupby("IdVehiculo")["Km"].cumsum()))

    # Consumo energetico
    query_consumo = """
        SELECT dt."FirstDayOfMonth" as "Mes",
               "IdVehiculo",
               SUM("EnergyDeliveredKWh") as "KWh"
        FROM ma."FactConsumptionSiemens" cm
        LEFT JOIN public."DimDate" dt
            ON dt."Date" = cm."FechaCarga"
        WHERE cm."FechaCarga" >= '2022-09-01'
        GROUP BY dt."FirstDayOfMonth", "IdVehiculo"
        ORDER BY "IdVehiculo", dt."FirstDayOfMonth"
    """

    consumo = (pd.read_sql(query_consumo, fn.enginea)
               .assign(Mes = lambda d: pd.to_datetime(d["Mes"])))

    # Se realiza el calculo del consumo energetico por mes y vehiculo
    dataconsumo = (consumo.merge(kmflota, how = "left", on = ["Mes", "IdVehiculo"])
                   .loc[lambda d: d["Mes"] >= pd.Timestamp("2023-01-01")]
                   .sort_values(["IdVehiculo", "Mes"])
                   .assign(KmCum = lambda d: d.groupby("IdVehiculo")["Km"].cumsum(),
                           KWhCum  =lambda d: d.groupby("IdVehiculo")["KWh"].cumsum())
                   .assign(kwhkm = lambda d: d["KWhCum"] / d["KmCum"])
                   .loc[:, ["Mes", "IdVehiculo", "kwhkm"]])

    # Proceso para el calulo del SOH
    median_kwhkm = dataconsumo["kwhkm"].median(skipna = True)

    soh = (kmflota.merge(dataconsumo, how = "left", on = ["Mes", "IdVehiculo"])
           .assign(kwhkm = lambda d: d["kwhkm"].fillna(median_kwhkm))
           .sort_values(["IdVehiculo", "Mes"])
           .assign(kWhMes = lambda d: d["Km"] * d["kwhkm"],
                   kWhTotal = lambda d: d.groupby("IdVehiculo")["kWhMes"].cumsum(),
                   kwhr4000 = lambda d: np.where(d["Tipo"] == "BUSETON", buseton, padron),
                   Soh = lambda d: 100 - ((d["kWhTotal"] * 0.2 / d["kwhr4000"]) * 100),
                   Ciclos = lambda d: np.where(d["Tipo"] == "BUSETON", np.round(d["kWhTotal"] / buseton80pct, 0), np.round(d["kWhTotal"] / padron80pct, 0)),
                   InsertDate = datetime.now()))

    sql_types = {'Mes': types.DATE, 'IdVehiculo': types.INTEGER, 'Km': types.FLOAT, 'KmCumOdo': types.INTEGER,
                 'kwhkm': types.FLOAT, 'kWhMes': types.FLOAT, 'kWhTotal': types.FLOAT, 'kwhr4000': types.FLOAT,
                 'Soh': types.FLOAT, 'Ciclos': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    # Envio de datos al DW
    soh.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace',index = False, dtype = sql_types)
    
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = soh["Mes"].max(), cantidad_registros = soh.shape[0])
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_SOH')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
