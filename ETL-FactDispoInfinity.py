#**********************************************************************************************
# @Nombre: ETL para extraer la disponibilidad de API de infinity
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                               # Manejo del sistema
import requests                         # Hacer consultas en API's
import pandas as pd                     # Manipulacion de datos
from sqlalchemy import types            # Definir tipos de datos SQL
import Funciones as fn                  # Funciones ETL
from skimpy import clean_columns        # Limpieza de nombres de columnas
from datetime import datetime           # Manipulacion de fechas
import infinity as inf                  # Creación del Token Api Infinity
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1113
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Disponibilidad Infinity *"
table = 'FactDisponibilidadInfinity'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Conectar Data Warehouse ---------------------------------------------------------------------
hook = os.getenv('TOK_SLACK')

# *********************************************************************************************
# ********************************* Infinity **************************************************
# *********************************************************************************************
# Datos para la solicitud GET
url_dashboard = "https://w26670ug8k.execute-api.us-east-1.amazonaws.com/prod/availability"

try:
    # API para obtener los datos de las transacciones ---------------------------------------------
    response_get = requests.get(url_dashboard, headers = inf.iniinfinity())

    datat = response_get.json()

    def get_kpis(empresa):

        dataframes_temporales = []
        for empresas in empresa:

            fuunkp = (
                clean_columns(pd.DataFrame(pd.json_normalize(datat['fuunkpis'][empresas])), case = 'pascal')
                .drop(columns = ["IdUnit", "UnitDescription", "UnavailableChargers", "ChargingConnectors", 
                            "InactiveConnectors", "PowerUsed", 
                            "PowerUsedString", "PorcentageUsed", "Limite", "LimiteString", "PowerMax", 
                            "PowerMaxString"])
                .assign(
                    InsertDate = datetime.now(),
                    DateStart = lambda x: (x['InsertDate']).apply(lambda x: x.strftime("%Y-%m-%d")),
                    HoraDisponibilidad = lambda x: (x['InsertDate']).apply(lambda x: x.hour))
                .rename(columns = {'UnitName': 'Empresa'})
                .loc[:, ["DateStart", "HoraDisponibilidad", "Empresa", "TotalChargers", 
                         "AvailableChargers", "PercentageChargers", "TotalConnectors", 
                         "AvailableConnectors", "ErrorConnectors", "OfflineConnectors", 
                         "PercentageConnectors","InsertDate"]]
            )

            dataframes_temporales.append(fuunkp)

        # Concatena los DataFrames en la lista en un solo DataFrame
        resultado = pd.concat(dataframes_temporales, ignore_index = True)

        return resultado

    # se consolida los datos de los kpis
    datos = get_kpis(['fuunkpi1', 'fuunkpi2'])

    # Envio de los datos al DW
    sql_types = {
        'DateStart': types.DATE,
        'HoraDisponibilidad': types.INTEGER,
        'TotalChargers': types.INTEGER,
        "AvailableChargers": types.INTEGER,
        "PercentageChargers": types.INTEGER,
        "TotalConnectors": types.INTEGER,
        "AvailableConnectors": types.INTEGER,
        "PercentageConnectors": types.INTEGER,
        "ErrorConnectors": types.INTEGER, 
        "OfflineConnectors": types.INTEGER,
        'InsertDate': types.TIMESTAMP
    }
    
    datos.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # validacion de hora para notificar al proceso de ETL
    hora_actual = datetime.now().hour

    if hora_actual == 6:
          #  Actualiza Energia subestaciones
          file_phyton = os.getenv('PAT_PBI_REFRESH')
          datasetid = os.getenv('PBI_CARGADORES')
          command = f'python "{file_phyton}" "{datasetid}"'
          os.system(command)
          # Registro de la ejecucion del proceso
          fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datos['DateStart'].max(), cantidad_registros = len(datos))
          fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    if hora_actual == 6:
        # registro de la ejecucion del proceso con error
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))