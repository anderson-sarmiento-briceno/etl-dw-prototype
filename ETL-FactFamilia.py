#**********************************************************************************************
# @Nombre: Extraccion de informacion de la familia de los empleados y educacion
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import Funciones as fn                 # Funciones personalizadas
from skimpy import clean_columns       # Formato de columnas
from sqlalchemy import text            # Conexion base de datos
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1031
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Familia*"
table1 = "FactFamilia"
table2 = "FactSociodemografico"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

path_project = os.getenv("PAT_PROJECT")

query_fam = os.path.join(path_project, "00 Querys/FactFamilia.sql")
query_soc = os.path.join(path_project, "00 Querys/FactSociodemografico.sql")

try:
    dim_fam = (pd.read_sql(open(query_fam).read(), fn.enginekt)
               .assign(RelacionFamiliar = lambda x: x["RelacionFamiliar"].replace({"H": "Hijo", 
                                                                                   "C": "Conyuge", 
                                                                                   "P": "Padre", 
                                                                                   "M": "Madre", 
                                                                                   "J": "Hijastro",
                                                                                   "T": "Tio",
                                                                                   "R": "Referencia",
                                                                                   "B": "Beneficiario"}),
                       CodEmpleado = lambda x: x["CodEmpleado"].astype("Int64"),
                       CodFamiliar = lambda x: x["CodFamiliar"].astype("Int64"),
                       EdadFamiliar = lambda x: x["EdadFamiliar"].astype("Int64"),
                       InsertDate = datetime.now()))
    
    # Carga DW
    fn.cona.execute(text(f'TRUNCATE TABLE tmp."{table1}"'))
    dim_fam.to_sql(table1, fn.enginea, schema = 'tmp', if_exists = "append", index = False)
    
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = datetime.today().date(), cantidad_registros = len(dim_fam))
except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table1), observacion = str(e))

try:
    factsocio = (clean_columns(pd.read_sql(open(query_soc).read(), fn.enginekt), case = "pascal")
               .assign(Empresa = lambda x: x["Empresa"].str.strip(),
                       Telefono = lambda x: pd.to_numeric(x["Telefono"], errors = "coerce"),
                       CorreoCorporativo = lambda x: x["CorreoCorporativo"].str.lower(),
                       CorreoPersonal = lambda x: x["CorreoPersonal"].str.lower(),
                       RangoEdades = lambda x: x["RangoEdades"] + ' años',
                       CodigoOperador = lambda x: pd.to_numeric(x["CodigoOperador"], errors = "coerce"),
                       NoContrato = lambda x: pd.to_numeric(x["NoContrato"], errors = "coerce"),
                       InsertDate = datetime.now()))

    # Carga DW
    fn.cona.execute(text(f'TRUNCATE TABLE tmp."{table2}"'))
    factsocio.to_sql(table2, fn.enginea, schema = 'tmp', if_exists = "append", index = False)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = datetime.today().date(), cantidad_registros = len(factsocio))
except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table2), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)
