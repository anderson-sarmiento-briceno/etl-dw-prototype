#**********************************************************************************************
# @Nombre: Seguimiento de peso de tablas en Data Warehouse
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import Funciones as fn                              # Funciones ETL
from sqlalchemy import text                         # Conexion base de datos
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1400
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Auditor de Peso DW*"
table = 'AuditorDW'

day = fn.check_habil_day(fn.enginea)

try:
    if day == 1:
        # Llama la funcion de insercion
        with fn.enginea.begin() as conn:
            conn.execute(text("CALL bi.sp_weight_tables();"))
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None, cantidad_registros = 1)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))