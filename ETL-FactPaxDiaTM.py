#**********************************************************************************************
# @Nombre: Proceso de transformacion analisis de demanda de pasajeros TM
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import Funciones as fn                 # Funciones personalizadas
from skimpy import clean_columns       # Limpieza de nombres de columnas
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1131
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Calculo Pax dia TM*"
table1 = "FactDemandaZonalTM"
table2 = "FactDemandaTroncalTM"
table3 = "FactDemandaDualTM"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Captura de fechas ejecutadas ----------------------------------------------------------------
def fechas_procesadas(tabla):
    df = pd.read_sql_query(f'SELECT DISTINCT "FechaClearing" FROM public."{tabla}"', con = fn.enginea)
    return (df.assign(FechaClearing = lambda d: pd.to_datetime(d["FechaClearing"], errors = "coerce"))
            .dropna(subset = ["FechaClearing"])
            .assign(FechaClearing = lambda d: d["FechaClearing"].dt.strftime("%Y%m%d"))["FechaClearing"]
            .unique()
            .tolist())

# Zonal
try:
    path_zonal = os.path.join(os.getenv("PAT_NAS"), "02 Datos/03 validaciones_zonal/")
    archivos = [f for f in os.listdir(path_zonal) if f.endswith(".csv")]

    fechas = fechas_procesadas(table1)

    archivos_proc = (pd.DataFrame({"Nombre": archivos})
                     .assign(Fecha = lambda d: d["Nombre"].str.extract(r"(\d+)"))
                     .query("Fecha not in @fechas and Fecha >= '20190101'")["Nombre"]
                     .tolist())

    columnas = ["Fecha_Clearing", "Fecha_Transaccion", "ID_Vehiculo", "Operador", "Estacion_Parada", "Valor"]

    patron_cenefa = r"([A-V0-9]{6})(?=_|\s|$)"

    for i in archivos_proc:
        if i in ("zonal_2023.csv", "2025020_ValidacionZonal.csv"):
            continue

        data = (pd.read_csv(os.path.join(path_zonal, i))
                .drop_duplicates()
                .loc[:, columnas]
                .assign(Fecha_Transaccion = lambda d: pd.to_datetime(d["Fecha_Transaccion"]).dt.date,
                        Estacion_Parada = lambda d: d["Estacion_Parada"].str.extract(patron_cenefa)))

        demanda = (data.groupby(["Fecha_Clearing", "Fecha_Transaccion", "Operador"], as_index = False)
                   .agg(Total = ("Operador", "size"),
                        Valor = ("Valor", "sum"),
                        VehDistinct = ("ID_Vehiculo", "nunique"))
                    .pipe(clean_columns, case = "pascal")
                    .dropna(subset = ["FechaClearing"]))

        demanda.to_sql(table1, fn.cona,  schema = "public", if_exists = "append", index = False)

        print(i)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = demanda["FechaTransaccion"].max(), cantidad_registros = len(demanda))

except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table1), observacion = str(e))

# Troncal
try:
    path_tr = os.path.join(os.getenv("PAT_NAS"), "02 Datos/05 validaciones_troncal/")
    archivos = [f for f in os.listdir(path_tr) if f.endswith(".csv")]

    fechas = fechas_procesadas(table2)

    archivos_proc = (pd.DataFrame({"Nombre": archivos})
                     .assign(Fecha = lambda d: d["Nombre"].str.extract(r"(\d+)"))
                     .query("Fecha not in @fechas and Fecha >= '20190101'")["Nombre"]
                     .tolist())

    columnas = ["Fecha_Clearing", "Fecha_Transaccion", "Linea", "Valor"]

    for i in archivos_proc:
        if i in ("2025020_ValidacionTroncal.csv"):
            continue
        data_tr = (pd.read_csv(os.path.join(path_tr, i))
                   .drop_duplicates()
                   .loc[:, columnas]
                   .assign(Fecha_Transaccion = lambda d: pd.to_datetime(d["Fecha_Transaccion"]).dt.date)
                   .groupby(["Fecha_Clearing", "Fecha_Transaccion", "Linea"], as_index = False)
                   .agg(Total = ("Linea", "size"),
                        Valor = ("Valor", "sum"))
                    .pipe(clean_columns, case = "pascal"))

        data_tr.to_sql(table2, fn.cona,  schema = "public", if_exists = "append", index = False)

        print(i)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = data_tr["FechaTransaccion"].max(), cantidad_registros = len(data_tr))
except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table2), observacion = str(e))

# Dual
try:
    path_dl = os.path.join(os.getenv("PAT_NAS"), "02 Datos/04 validaciones_dual/")
    archivos = [f for f in os.listdir(path_dl) if f.endswith(".csv")]

    fechas = fechas_procesadas(table3)

    archivos_proc = (pd.DataFrame({"Nombre": archivos})
                     .assign(Fecha = lambda d: d["Nombre"].str.extract(r"(\d+)"))
                     .query("Fecha not in @fechas and Fecha >= '20200101'")["Nombre"]
                     .tolist())

    columnas = ["Fecha_Clearing", "Fecha_Transaccion", "ID_Vehiculo", "Operador", "Valor"]

    for i in archivos_proc:
        valida = pd.read_csv(os.path.join(path_dl, i), nrows = 10)

        if len(valida) <= 1:
            print("Archivo sin registros")
            continue

        data_dl = (pd.read_csv(os.path.join(path_dl, i))
                   .drop_duplicates()
                   .loc[:, columnas]
                   .assign(Fecha_Transaccion = lambda d: pd.to_datetime(d["Fecha_Transaccion"]).dt.date)
                   .groupby(["Fecha_Clearing", "Fecha_Transaccion", "Operador"], as_index = False)
                   .agg(Total = ("Operador", "size"),
                        Valor = ("Valor", "sum"),
                        VehDistinct = ("ID_Vehiculo", "nunique"))
                    .pipe(clean_columns, case = "pascal"))

        data_dl.to_sql(table3, fn.cona,  schema = "public", if_exists = "append", index = False)

        print(i)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = data_dl["FechaTransaccion"].max(), cantidad_registros = len(data_dl))

except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table3), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)
