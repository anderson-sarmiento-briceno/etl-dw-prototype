#**********************************************************************************************
# @Nombre: ETL para extraer los datos del API de infinity
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                                # Manejo del sistema
import requests                                          # Hacer consultas en API's
import subprocess                                        # Llamar procesos externos
import pandas as pd                                      # Manipulacion de datos
import infinity as inf                                   # Creación del Token Api Infinity
import Funciones as fn                                   # Funciones ETL
import sys                                               # Interprete python
from sqlalchemy import types                             # Definir tipos de datos para sql
from skimpy import clean_columns                         # Limpieza de nombres de columnas
from datetime import date, timedelta, datetime           # Manipulacion de fechas
import numpy as np                                       # Manejo de datos numericos
from concurrent.futures import ThreadPoolExecutor        # Ejecucion paralela de solicitudes
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1115
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Infinity *"
table1 = 'FactConsumoEnergy'
table2 = 'DimModulesVehicles'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

headers = inf.iniinfinity()
def fetch_page(page_num):
    params = {'startDate': startdate, 'endDate': enddate, 'page': page_num}
    response = requests.get(url_get, headers = headers, params = params)
    return pd.DataFrame(response.json()["data"])

try:
    # *********************************************************************************************
    # ********************************* Infinity **************************************************
    # *********************************************************************************************
    # Se lee la tabla Energy del DW y se extraen los Id de las Tx de Infinity ---------------------
    idInfinity = pd.read_sql_query('''
                                      SELECT "TransactionId"
                                      FROM ma."FactConsumoEnergy" 
                                      WHERE "Source" = 'EasyChargEV'
                                      ''', con = fn.enginea)

    # Se crea lista de Ids Existentes en la tabla -------------------------------------------------
    idInfinity_lista = idInfinity['TransactionId'].tolist()

    # Seleccionador rango de fechas del request 
    startdate = (date.today() - timedelta(days = 15)).strftime("%Y-%m-%d")
    enddate = (date.today() - timedelta(days = 1)).strftime("%Y-%m-%d")

    # Datos para la solicitud GET
    url_get = 'https://w26670ug8k.execute-api.us-east-1.amazonaws.com/prod/transactions'
    initial_res = requests.get(url_get, headers = headers, 
                               params={'startDate': startdate, 'endDate': enddate, 'page': 0})
    first_df = pd.DataFrame(initial_res.json()["data"])
    total_pages = initial_res.json()["pagination"]["total_pages"]

    # Descarga paralela del resto de paginas
    with ThreadPoolExecutor(max_workers = 10) as executor:
        # Creamos una lista de futuros para las paginas restantes (de 1 a total_pages-1)
        results = list(executor.map(fetch_page, range(1, total_pages)))

    # Consolidacion final
    list_response = [first_df] + results
    df_final = pd.concat(list_response, ignore_index = True)

    datatransa = clean_columns(df_final, case = 'pascal')

    # Se filtran los Id existentes ----------------------------------------------------------------
    dataenergy = datatransa[~datatransa['Id'].isin(idInfinity_lista)]

    dataenergy = (
        dataenergy.assign(
        StartEventTimestamp = lambda x: pd.to_datetime(x['StartEventTimestamp'], utc = True)
                                                        .dt.tz_convert('America/Bogota')
                                                        .dt.tz_localize(None),
        StopEventTimestamp  = lambda x: pd.to_datetime(x['StopEventTimestamp'], utc = True)
                                                        .dt.tz_convert('America/Bogota')
                                                        .dt.tz_localize(None),
        DateStart = lambda x: x['StartEventTimestamp'].dt.date,
        StopValue = lambda x: pd.to_numeric(x['StopValue'], errors = 'coerce'),
        StartValue = lambda x: pd.to_numeric(x['StartValue'], errors = 'coerce'),
        InsertDate = datetime.now(),
        PercentCharged = lambda x: x['StopValue'] - x['StartValue'],
        TiempoCargaSec = lambda x: (x['StopEventTimestamp'] - x['StartEventTimestamp']).dt.total_seconds(),
        Source = "EasyChargEV",
        VehicleInfo = lambda x: x["VehicleInfo"].replace('UNKNOWN', np.nan))
        .drop(columns = ['IdTag', 'ConnectorPk', 'FunctionalName', 'StartTimestamp', 'StopTimestamp',
                         'StopEventActor', 'FunctionalUnitName', 'Placa', 'ConnectorId'])
        .rename(columns = {'Id': 'TransactionId', 
                           'ChargeBoxName': 'ChargerName', 
                           'TotalValue': 'EnergyDeliveredKWh', 
                           'StopReason': 'Reason', 
                           'StartEventTimestamp': 'StartAt', 
                           'StopEventTimestamp': 'EndAt',
                           'StartValue': 'InitialSoCPercent',
                           'StopValue': 'EndSoCPercent',
                           'Moduleid': 'ModuleId'})
        .loc[:, ["DateStart", "TransactionId", "ChargerName", "ConnectorName", "EnergyDeliveredKWh",
                  "Reason", "StartAt", "EndAt", "InitialSoCPercent", "EndSoCPercent", "ModuleId", 
                  "TiempoCargaSec", "PercentCharged", "VehicleInfo", "Source", "InsertDate"]]    
    )

    # Envio de los datos al DW
    sql_types = {
        'DateStart': types.DATE,
        'TransactionId': types.BIGINT,
        'EnergyDeliveredKWh': types.INTEGER,
        'StartAt': types.TIMESTAMP,
        'EndAt': types.TIMESTAMP,
        'InitialSoCPercent': types.INTEGER,
        'EndSoCPercent': types.INTEGER,
        'PercentCharged': types.INTEGER,
        'TiempoCargaSec': types.INTEGER,
        'InsertDate': types.TIMESTAMP
    }

    dataenergy.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = dataenergy["DateStart"].max(), cantidad_registros = len(dataenergy))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

# *********************************************************************************************
# ************************* Refresh dataset power bi service **********************************
# *********************************************************************************************
# Actualiza Energia subestaciones
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_ENERGSUB')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Actualizacion de Proceso de Carga
datasetid = os.getenv('PBI_CARGA')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# *********************************************************************************************
# ***************************** Modulos Vehicles **********************************************
# *********************************************************************************************
try:
    # API para obtener los datos de los modulos ---------------------------------------------------
    url_vehicles = "https://w26670ug8k.execute-api.us-east-1.amazonaws.com/prod/vehicles"

    vehicles_get = requests.get(url_vehicles, headers = headers)

    datavehicles = (
        clean_columns(pd.DataFrame(vehicles_get.json()), case = 'pascal')
        .drop(columns = ['BateryMaxCap'])
        .rename(columns = {'Id': 'VehicleId'}))

    df_modulos = clean_columns(pd.json_normalize(datavehicles['Modules'].explode()), case = 'pascal')

    df_vehicles = (
        pd.merge(df_modulos, datavehicles[['VehicleId', 'Alias', 'Placa', 'ChargeMaxCap', 'SiteId']], on = 'VehicleId', how = 'left')
        .rename(columns = {'Id': 'ModuleId', 
                           'Alias': 'NumeroTM', 
                           'Placa': 'AssetNum'})
        .assign(
            InsertDate = datetime.now())
        .dropna()
        )

    sql_types_veh = {
        'ModuleId': types.VARCHAR(50),
        'VehicleId': types.VARCHAR(50),
        'ChargeMaxCap': types.INTEGER,
        'InsertDate': types.TIMESTAMP
    }

    df_vehicles.to_sql(table2, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types_veh)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = datetime.today(), cantidad_registros = len(df_vehicles))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))
    
# *********************************************************************************************
# ***************************** Invocan Otros Procesos ****************************************
# *********************************************************************************************
# Desencadenar el proceso de para el calculo de la durabilidad de las llantas
subprocess.run([sys.executable, r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\ETL-FactRendimientoSiemens.py"])