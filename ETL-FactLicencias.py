#**********************************************************************************************
# @Nombre: Extraccion de licencias de conduccion de kactus
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import Funciones as fn                 # Funciones personalizadas
from sqlalchemy import text            # Conexion base de datos
from datetime import datetime          # Manipulacion de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1173
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Licencias Conductores*"
table = 'FactLicencias'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Obtener y transformar los datos -------------------------------------------------------------
try:
    licencia = (pd.read_sql(""" SELECT cod_empl, num_docu, fec_venc
                                FROM bi_empdo """, fn.enginekt)
                                .rename(columns = {"cod_empl": "Cedula", "num_docu": "Licencia", 
                                                   "fec_venc": "FecVencLicencia"})
                                .sort_values(["Cedula", "FecVencLicencia"])
                                .drop_duplicates(subset = "Cedula", keep = "last"))
    
    # Carga DW
    fn.cona.execute(text(f'TRUNCATE TABLE gh."{table}"'))
    licencia.to_sql(table, schema = 'gh', con = fn.cona, if_exists = 'append', index = False)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = licencia["FecVencLicencia"].max(), cantidad_registros = len(licencia))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))