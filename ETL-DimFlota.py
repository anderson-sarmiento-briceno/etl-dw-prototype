# *********************************************************************************************
#  @Nombre: ETL Dimension de Vehiculos y Activos Infraestructura
#  @Autor: Anderson Sarmiento
# *********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os
import pandas as pd
import Funciones as fn                 # Funciones personalizadas
from datetime import datetime
from sqlalchemy import text
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1180
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Actualizacion Activos (Flota)*"
table1 = "DimFlota"
table2 = "DimActivosInfra"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Paths de queries
path_project = "C:/Users/dev/Documents/01 Modelos/20211230-etl-dwgm/"
query_vehiculos = os.path.join(path_project, "00 Querys/DimFlota.sql")
query_especificaciones = os.path.join(path_project, "00 Querys/DimFlotaEspe.sql")
query_infra = os.path.join(path_project, "00 Querys/DimActivosInfra.sql")

# Dim Vehiculos -------------------------------------------------------------------------------
try:
    with open(query_especificaciones, "r", encoding = "utf-8") as f:
        sql_especificaciones = f.read()

    dim_especificaciones = pd.read_sql(text(sql_especificaciones), con = fn.enginemx)

    dim_especificaciones["Valor"] = dim_especificaciones["AlnValue"].fillna(dim_especificaciones["NumValue"])

    dim_especificaciones = (dim_especificaciones[["AssetNum", "AssetAttrId", "Valor"]]
                            .pivot(index = "AssetNum", columns = "AssetAttrId", values = "Valor")
                            .reset_index())

    with open(query_vehiculos, "r", encoding="utf-8") as f:
        sql_vehiculos = f.read()

    dim_vehiculo = pd.read_sql(text(sql_vehiculos), con = fn.enginemx)

    dim_vehiculo = (dim_vehiculo.merge(dim_especificaciones, on = "AssetNum", how = "left")
                                .assign(IdVehiculo = lambda x: x["Description"].str.replace(r"\D+", "", regex = True)
                                        .pipe(pd.to_numeric, errors = "coerce")
                                        .astype("Int64"))
                                .dropna(subset = ["IdVehiculo"]))
    dim_vehiculo = dim_vehiculo[["IdVehiculo"] + [c for c in dim_vehiculo.columns if c != "IdVehiculo"]]

    # Escritura en DW
    dim_vehiculo.to_sql(table1, fn.cona, schema = "public", if_exists = "replace", index = False)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = datetime.today().date(), cantidad_registros = len(dim_vehiculo))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table1), observacion = str(e))

# Dim Activos Infraestructura -----------------------------------------------------------------
try:
    with open(query_infra, "r", encoding = "utf-8") as f:
        sql_infra = f.read()

    dim_infra = (pd.read_sql(text(sql_infra), con = fn.enginemx)
                 .dropna(subset = ["SerialNum"]))
    
    dim_infra.to_sql(table2, fn.cona, schema = "public", if_exists = "replace", index = False)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = datetime.today().date(), cantidad_registros = len(dim_infra))
except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table2), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)