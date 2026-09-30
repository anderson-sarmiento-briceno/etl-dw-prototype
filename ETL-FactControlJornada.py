#**********************************************************************************************
# @Nombre: Proceso de transformacion de control de jornada de Mantenimiento
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import os                                   # Manejo del sistema
import requests                             # Hacer consultas en API's
import Funciones as fn                      # Funciones ETL
from sqlalchemy import types                # Definir tipos de datos para sql
from skimpy import clean_columns            # Limpieza de nombres de columnas
from datetime import datetime, timedelta    # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1080
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Control Jornada Mtto*"
table = "FactJornadaMtto"

# Parámetros
pass_rigel = os.getenv("API_PASS_RIGEL")

desde = "2022-04-01"
hasta = (datetime.today() - timedelta(days = 1)).date()

url_jornada_rigel = (f"http://rigel.greenmovil.com.co:8080/RigelpbWS/controlJornada/detallado"
                     f"?desde={desde}&hasta={hasta}&key={pass_rigel}")

try:
    # Consulta de API de Rigel
    response = requests.get(url_jornada_rigel)

    # Transformación de los datos
    jornada = (pd.DataFrame(response.json()["data"])
               .pipe(clean_columns, case = "pascal")
               .assign(Nombre = lambda df: df["Nombre"].str.title(),
                       InsertDate = datetime.now()))

    # Envio de los datos al DW
    sql_types = {'Fecha': types.DATE, 'Identificacion': types.INTEGER, 'Diurnas': types.FLOAT,
                 'Nocturnas': types.FLOAT, 'ExtraDiurna': types.FLOAT, 'FestivoDiurno': types.FLOAT,
                 'FestivoNocturno': types.FLOAT, 'FestivoExtraDiurno': types.FLOAT, 'FestivoExtraNocturno': types.FLOAT,
                 'ExtraNocturna': types.FLOAT, 'DominicalCompDiurnas': types.FLOAT, 'DominicalCompNocturnas': types.FLOAT,
                 'DominicalCompDiurnaExtra': types.FLOAT, 'DominicalCompNocturnaExtra': types.FLOAT,
                 'InsertDate': types.TIMESTAMP}
    
    # Carga a tabla
    jornada.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = jornada["Fecha"].max(), cantidad_registros = len(jornada))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
