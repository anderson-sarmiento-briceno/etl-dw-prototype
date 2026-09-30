#**********************************************************************************************
# @Nombre: Proceos para el cargue de los datos de ocupacion de tecnicos
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import os                                   # Manejo del sistema
import Funciones as fn                      # Funciones personalizadas
from sqlalchemy import types                # Manejo de tipos de campos en db
from datetime import datetime, timedelta    # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1100
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Turnos Tecnicos Mtto*"
table = "FactTurnosTecnicos"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Paths
userpc = r"E:\Drive"
turnos = r"greenmovil.com.co\Gestion Mantenimiento - General\Documentos\10 Datos\09 Turnos"
files_accidente = os.path.join(userpc, turnos, "FactOcupacionTecnicos.xlsx")

try:
    # Lectura dimension de turnos
    dim_turnos = (pd.read_csv("01 Inputs/Turnos.csv")
                  .assign(CicloInicio = lambda d: pd.to_datetime(d["CicloInicio"], dayfirst = True),
                          CicloFin = lambda d: pd.to_datetime(d["CicloFin"], dayfirst = True)))

    # Lectura turnos SharePoint
    dataturnos = (pd.read_excel(files_accidente, sheet_name = "Turnos")
                  .pipe(lambda d: d.rename(columns = lambda c: c.strip()))
                  .melt(id_vars = "Cedula", var_name = "Fecha", value_name = "Turno")
                  .assign(Fecha = lambda d: pd.to_datetime(d["Fecha"], dayfirst = True),
                          Turno = lambda d: d["Turno"].astype(str).str.strip())
                          .query("Turno != 'nan'"))

    # Merge equivalente a data.table
    dataturnos = (dataturnos.merge(dim_turnos, on = "Turno", how = "left")
                  .query("Fecha >= CicloInicio and Fecha <= CicloFin")
                  .assign(HoraInicioReal = lambda d: pd.to_datetime(d["Fecha"].astype(str) + " " + d["HoraIni"]),
                          HoraFinReal = lambda d: pd.to_datetime(d["Fecha"].astype(str) + " " + d["HoraFin"])))

    # Ajuste de turnos que pasan de día
    mask = dataturnos["PassDay"] == 1
    dataturnos.loc[mask, "HoraFinReal"] = (dataturnos.loc[mask, "HoraFinReal"] + timedelta(days = 1))

    dataturnos = (dataturnos.assign(InsertDate = datetime.now())
                  .drop(columns = ["CicloInicio", "CicloFin"]))

    # Tipos SQL (equivalente field.types)
    sql_types = {"Cedula": types.INTEGER, "Fecha": types.DATE, "Turno": types.TEXT, "HoraIni": types.TEXT,
                 "HoraFin": types.TEXT, "PassDay": types.INTEGER, "Tiempo1P": types.FLOAT, "Tiempo2P": types.FLOAT,
                 "HoraInicioReal": types.TIMESTAMP, "HoraFinReal": types.TIMESTAMP, "InsertDate": types.TIMESTAMP}

    # Cargue al DW
    dataturnos.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    #------------------------------------------------------------------------------------------
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None if pd.isna(dataturnos["Fecha"].max()) else dataturnos["Fecha"].max(), cantidad_registros = len(dataturnos))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

#----------------------------------------------------------------------------------------------
# Actualizacion Power BI
path = os.getenv("PAT_PBI_REFRESH")
os.system(f'python "{path}" {os.getenv("PBI_MANOBRA")}')
