#**********************************************************************************************
# @Nombre: Cargue de informacion sobre la califacion EMIC de los operadores
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                 # Manipulacion de datos
import os                                           # Manejo del sistema
import glob                                         # Busquedad de patrones de archivos
import Funciones as fn                              # Funciones ETL
from datetime import datetime                       # Manejo de fechas
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from datetime import datetime                       # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1244
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Procesos EMIC Operador*"
table = 'FactEmicOperador'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#Desarrollo -----------------------------------------------------------------------------------
try:
    # Identificacion de documentos .parquet
    rut = os.path.join(os.getenv('PAT_GESTION_INFO'), '08 Calificacion_Operador')
    docs = glob.glob(os.path.join(rut, "*.parquet"))

    # Estandarizacion de la informacion
    calemic = (clean_columns(pd.concat([pd.read_parquet(file) for file in docs], ignore_index = True)
                             .assign(Mes_Año = lambda x: x["Mes_Año"].astype('int64'),
                                     Cedula = lambda x: x["Cedula"].astype('int64'),
                                     InsertDate = datetime.now()), case = 'pascal'))

    # Envio de los datos al DW
    sql_types = {'MesAno': types.INTEGER, 'Codigo': types.INTEGER, 'Cedula': types.INTEGER,
                'PuntuacionAusencias': types.FLOAT, 'PuntuacionInfracciones': types.FLOAT,
                'PuntuacionHallazgos': types.FLOAT, 'PuntuacionDanoFlota': types.FLOAT,
                'PuntuacionAccidentes': types.FLOAT, 'Distance': types.FLOAT, 
                'DistanciaComputable': types.FLOAT, 'CumplimientoKms': types.FLOAT, 
                'PaxProgramado': types.FLOAT, 'PaxEjecutado': types.FLOAT, 
                'CumplimientoPax': types.FLOAT, 'CumplimientoDiasLaborados': types.FLOAT,
                'Excelencia': types.INTEGER, 'TotalPonderado': types.FLOAT, 
                'InsertDate': types.TIMESTAMP}

    calemic.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = pd.to_datetime(str(calemic['MesAno'].max()), format='%Y%m'), cantidad_registros = len(calemic))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
