#**********************************************************************************************
# @Nombre: Estimacion del Pasivo Vacacional
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                             # Manipulacion de datos
import os                                       # Manejo del sistema
import Funciones as fn                          # Funciones ETL
from sqlalchemy import types                    # Manejo de tipos de campos en db
from datetime import datetime                   # Manejo de fechas
from sqlalchemy import create_engine, text      # Conexion base de datos
from pathlib import Path                        # Manejo de rutas de archivos
from dotenv import load_dotenv
load_dotenv()

# Colocar el Id del proceso que esta en el DW
IdProceso = 1172
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Pasivo Vacacional*"
table = "FactPasivoVacacional"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

try:
    # Conectar Kactus -----------------------------------------------------------------------------
    user = os.getenv("DBB_USER_KACTUS")
    password = os.getenv("DBB_PASS_KACTUS")
    server = "10.0.3.63\\RRHHMSSQL"
    database = "KactusGrM"
    con = (create_engine(f"mssql+pyodbc://{user}:{password}@{server}/{database}?driver=SQL+Server")
           .connect())

    #Desarrollo -----------------------------------------------------------------------------------
    # Definir la consulta SQL a Kactus
    query = (Path(os.path.join(os.getenv("PAT_PROJECT"), "00 Querys", "FactPasivoVacacional.sql"))
             .read_text(encoding = "utf-8"))

    # Ejecutar la consulta y cargar los resultados
    pasv = (pd.read_sql(query, con)
            .assign(CodEmpleado = lambda x: x['CodEmpleado'].astype('int64'),
                    Nombre = lambda x: x['Nombre'].str.title(),
                    Apellido = lambda x: x['Apellido'].str.title(),
                    Cargo = lambda x: x['Cargo'].str.title(),
                    CentroCostos = lambda x: x['CentroCostos'].str.strip(),
                    Empresa = lambda x: x['Empresa'].str.strip(),
                    InsertDate = datetime.now())
            .sort_values(by = 'DiasPendientes', ascending = False))

    # Envio de los datos al DW
    sql_types = {'Cedula': types.INTEGER, 'FechaContratacion': types.DATE, 'DiasNoLaborados': types.FLOAT,
                 'DiasDisponibles': types.FLOAT, 'DiasTomados': types.FLOAT, 'DiasPendientes': types.FLOAT,
                 'InsertDate': types.TIMESTAMP}
    
    fn.cona.execute(text(f'TRUNCATE TABLE gh."{table}"'))
    pasv.to_sql(table, schema = 'gh', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datetime.today(), cantidad_registros = len(pasv))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
