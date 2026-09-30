#**********************************************************************************************
# @Nombre: Historico General de Incapacidades y Ausencias
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                   # Manipulacion de datos
import os                             # Manejo del sistema
import Funciones as fn                # Funciones ETL
from sqlalchemy import types, text    # Manejo de tipos de campos en db
from datetime import datetime         # Manejo de fechas
from sqlalchemy import create_engine  # Conexion base de datos
from dotenv import load_dotenv
load_dotenv()

# Colocar el Id del proceso que esta en el DW
IdProceso = 1171
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Historico de Ausentismo*"
table = 'FactHistoricoAusentismo'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Conectar Kactus -----------------------------------------------------------------------------
user = os.getenv("DBB_USER_KACTUS")
password = os.getenv("DBB_PASS_KACTUS")
server = "10.0.3.63\\RRHHMSSQL"
database = "KactusGrM"
con = (create_engine(f"mssql+pyodbc://{user}:{password}@{server}/{database}?driver=SQL+Server")
       .connect())

#Desarrollo -----------------------------------------------------------------------------------
try:
    # Definir la consulta SQL a Kactus
    query = """ SELECT aus.[cod_empl] as "CodEmpleado", aus.[cod_conc] as "CodConcepto", 
                       inc.[COD_DIAR] as "CodigoDiagnostico", aus.[tip_ause] as "TipoAusentismo",
                       aus.[fec_desd] as "FechaInicio", aus.[fec_hast] as "FechaFin", 
                       aus.[can_ause] as "CantidadDias"
                FROM [KactusGrM].[dbo].[nm_ausen] aus
                LEFT JOIN [KactusGrM].[dbo].[nm_incap] inc 
                 ON aus.[cod_empr] = inc.[cod_empr] 
                     AND aus.[cod_empl] = inc.[cod_empl] 
                     AND aus.[cod_conc] = inc.[cod_conc] 
                     AND aus.[fec_desd] = inc.[fec_desd]
                     AND aus.[fec_hast] = inc.[fec_hast] """

    # Ejecutar la consulta y cargar los resultados
    Inca = (pd.read_sql(query, con)
            .assign(CodigoDiagnostico = lambda x: x["CodigoDiagnostico"].str.strip(),
                    CodEmpleado = lambda x: x["CodEmpleado"].astype(int),
                    CantidadDias = lambda x: x["CantidadDias"].astype(int),
                    InsertDate = datetime.now())
            .drop_duplicates())

    # Envio de los datos al DW
    sql_types = {'CodEmpleado': types.INTEGER, 'CodConcepto': types.INTEGER, 
                 'FechaInicio': types.DATE, 'FechaFin': types.DATE, 'CantidadDias': types.INTEGER,
                 'InsertDate': types.TIMESTAMP}
    
    fn.cona.execute(text(f'TRUNCATE TABLE gh."{table}"'))
    Inca.to_sql(table, schema = 'gh', con = fn.cona, if_exists = 'append', index = False)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = Inca['FechaInicio'].max(), cantidad_registros = len(Inca))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
