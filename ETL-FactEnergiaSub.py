#**********************************************************************************************
# @Nombre: Transformacion de datos de scada de las sub estaciones de carga
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import Funciones as fn                 # Funciones ETL
from sqlalchemy import types           # Manejo de tipos de campos en db
import os                              # Manejo del sistema
import re                              # Manejo de expresiones regulares
import glob                            # Busquedad de patrones de archivos
import pyarrow.parquet as pq           # Manipulacion de parquet
import pyarrow as pa                   # Manipulacion de parquet
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1210
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Energia Subestacion*"
table1 = "FactConsumoEstaciones"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

to_val = os.path.join(os.getenv("PAT_NAS"), "02 Datos/06 telemetria/04 sub/")

current_val = os.listdir(to_val)

userpc = r"E:\Drive"
sharepoint = r"\greenmovil.com.co\Gestion Informacion - General\03 SubEstaciones\\"
pathfiles = userpc + sharepoint

nombres = ["Fecha", "Instante", "NomSubEstacion", "TipoEnergia", "Valor", "Unidad"]

# Validacion de archivos nuevos

base_path = os.getenv("DBB_PATH_SUBESTACION")

try:
    files = glob.glob(os.path.join(base_path, "*"))

    archivos = []

    for f in files:
        filename = os.path.basename(f)

        tipo = filename[:2]
        fecha_match = re.search(r"\d{6}", filename)

        if fecha_match:
            fecha = "20" + fecha_match.group()
            file_parquet = f"{fecha}_{tipo}.parquet"

            if fecha >= "20220801" and file_parquet not in current_val:
                archivos.append({"Archivo": f, "Tipo": tipo, "Fecha": fecha, "FileName": file_parquet})

    archivos = sorted(archivos, key = lambda x: x["Fecha"])

    # Procesamiento de txt a parquet

    if len(archivos) == 0:
        print("Revisar Disponibilidad de archivos")
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = None, cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)

    else:
        for fileinfo in archivos:
            datatemp = (pd.read_csv(fileinfo["Archivo"], encoding = "UTF-16LE", sep = ";", header = None, names = nombres)
                        .assign(Fecha = lambda df: pd.to_datetime(df["Fecha"], dayfirst = True))
                        .assign(tipo_ampm = lambda df: (df["Instante"].str.extract(r"(p|a)", expand = False)
                                                        .replace({"a": "AM", "p": "PM"})),
                                hora_base = lambda df: pd.to_datetime(df["Instante"].str.extract(r"(\d{1,2}:\d{2}:\d{2})", expand = False) + " " + df["tipo_ampm"]))
                        .assign(Instante = lambda df: df["hora_base"].dt.strftime("%H:%M:%S"))
                        .assign(FechaHoraDato = lambda df: pd.to_datetime(df["Fecha"].dt.strftime("%Y-%m-%d") + " " + df["Instante"], errors = "coerce"))
                        .assign(NomSubEstacion = lambda df: df["NomSubEstacion"].str.extract(r":(.+?):"),
                                TipoEnergia = lambda df: df["TipoEnergia"].str.extract(r"-\s(.+)"))
                        .assign(Fuente = fileinfo["Tipo"],
                                Fecha = lambda df: df["Fecha"].dt.date,
                                FechaHoraDato = lambda df: df["FechaHoraDato"].dt.strftime("%Y-%m-%d %H:%M"))
                        .drop(columns = ["Unidad", "tipo_ampm", "hora_base"]))

            # Guardar parquet
            output_path = os.path.join(to_val, fileinfo["FileName"])
            table = pa.Table.from_pandas(datatemp)
            pq.write_table(table, output_path)

            print(f"Procesado: {fileinfo['FileName']}")

        # Calculo de consumo

        listte = glob.glob(os.path.join(to_val, "*_TE.parquet"))

        dfs = []

        for file in listte:
            df = pq.read_table(file).to_pandas()
            dfs.append(df)

        consumo = (pd.concat(dfs, ignore_index = True)
                   .loc[lambda df: df["TipoEnergia"].isin(["Energia Activa en demanda", "Energia Activa en demanda Fase R"])]
                   .assign(Instante = lambda df: df["Instante"].str[:2])
                   .sort_values(["Fecha", "NomSubEstacion", "TipoEnergia"])
                   .assign(DeltaValor = lambda df: df.groupby(["Fecha", "NomSubEstacion", "TipoEnergia"])["Valor"].diff())
                   .assign(Validador = lambda df: ~((df["DeltaValor"] > 1.5) | (df["DeltaValor"] < -1.5)))
                   .loc[lambda df: df["Validador"]]
                   .groupby(["Fecha", "NomSubEstacion", "Instante"], as_index = False)
                   .agg({"DeltaValor": "sum"})
                   .assign(Consumo = lambda df: df["DeltaValor"] * 1000,
                           InsertDate = datetime.now())
                   .drop(columns = ["DeltaValor"]))

        # Exportacion de csv a sherepoint

        output_csv = os.path.join(pathfiles, "FactSubEstaciones.csv")
        consumo.to_csv(output_csv, index = False)

        sql_types = {'Fecha': types.DATE, 'Instante': types.INTEGER, 'Consumo': types.FLOAT,
                     'InsertDate': types.TIMESTAMP}

        consumo.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = consumo['Fecha'].max(), cantidad_registros = len(consumo))
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))
