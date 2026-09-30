#**********************************************************************************************
# @Nombre: ETL Fact Inventario
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import Funciones as fn                      # Funciones ETL
from datetime import datetime, timedelta    # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1010
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Inventario*"
table = "FactInventory"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

try:
    query_inventory_path = r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\00 Querys\FactInventory.sql"

    with open(query_inventory_path, "r", encoding = "utf-8") as f:
        query_inventory = f.read()

    # Fact Invuseline
    fact_inventory = (pd.read_sql(query_inventory, fn.enginemx)
                      .assign(InsertDate = datetime.now(),
                              Datekey = lambda df: int((datetime.now() - timedelta(days = 1)).strftime("%Y%m%d")))
                      .pipe(lambda df: df[["Datekey"] + [c for c in df.columns if c != "Datekey"]]))
    
    fact_inventory.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'append', index = False)
  
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = fact_inventory['InsertDate'].max(), cantidad_registros = len(fact_inventory))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
