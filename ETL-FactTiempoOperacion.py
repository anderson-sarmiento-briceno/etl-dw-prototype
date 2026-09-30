#**********************************************************************************************
# @Nombre: Estimacion de tiempo de operacion de los vehiculos
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                 # Manipulacion de datos
import os                                           # Manejo del sistema
import duckdb as db                                 # Bases de datos
import re                                           # Regex
import Funciones as fn                              # Funciones ETL
from datetime import datetime                       # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1162
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Extraccion de Tiempos de Operacion*"
table = 'FactTiempoOperacion'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definimos el path de downloads --------------------------------------------------------------
rut = os.path.join(os.getenv('PAT_NASPY'), r"02 Datos\12 viajes_desglosados")
fechainicio = datetime(2025, 1, 1).date()

# Extraccion de datos cargados
ctrfechasactuales = (pd.read_sql_query(""" SELECT DISTINCT "Fecha" 
                                           FROM op."FactTiempoOperacion" """, con = fn.enginea).Fecha.to_list())

# Seleccion de archivos parquet
archivos = [os.path.join(rut, f)
            for f in os.listdir(rut)
            if f.endswith(".parquet")
            and datetime.strptime(f[:8], "%Y%m%d").date() >= fechainicio
            and datetime.strptime(f[:8], "%Y%m%d").date() not in ctrfechasactuales]

try:
    # Procesamiento
    if archivos:
        # Lectura y extraccion de parquets
        df = db.execute(""" SELECT Fecha, Operador, DurReal 
                            FROM read_parquet($files)""", {"files": archivos}).df()

        # Reges para reemplazar columna de sercones
        repl_dict = {re.compile(r'.*233.*'):'ZMOIII',
                     re.compile(r'.*231.*'):'ZMOV'}

        # Limpieza de datos
        times = (df.assign(Fecha = lambda d: pd.to_datetime(d["Fecha"], dayfirst = True),
                           DurReal = lambda d: pd.to_timedelta(d["DurReal"].dt.time.astype(str)))
                   .groupby(["Fecha", "Operador"], as_index = False)
                   .agg(DurReal = ("DurReal", "sum"))
                   .assign(DuracionHrs = lambda d: (d["DurReal"].dt.total_seconds() / 3600).round(2),
                           SiteId = lambda x: x["Operador"].replace(repl_dict, regex = True),
                           InsertDate = datetime.now())
                   .loc[:, ["Fecha", "SiteId", "DuracionHrs", "InsertDate"]])

        # Envio de los datos al DW
        sql_types = {'Fecha': types.DATE, 'DuracionHrs': types.FLOAT, 'InsertDate': types.TIMESTAMP}
        
        times.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = times['Fecha'].max(), cantidad_registros = times.shape[0])
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
    else:
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None, cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
