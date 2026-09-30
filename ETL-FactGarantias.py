#**********************************************************************************************
# @Nombre: Proceso Transformacion Archivos de Garantias
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import datetime as dt                  # Manipulacion de fechas
import pandas as pd                    # Manipulacion de datos
import numpy as np                     # Manipulacion numerica
import os                              # Manejo del sistema
import re                              # Regex
import Funciones as fn                 # Funciones ETL
from sqlalchemy import types           # Manejo de tipos de campos en db
from datetime import datetime          # Manejo de fechas
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1220
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Garantias*"
table = "FactGarantiasFlota"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Path de documentos excel
url = r"E:\Drive\greenmovil.com.co\Gestion Mantenimiento - General\Documentos\12 PM\20 Garantias\01 Vehiculos"

try:
    files = [str(Path(url) / f) for f in os.listdir(url) if f.endswith((".xlsx", ".xls"))]

    registros = []
    for file in files:
        print(file)
        data = pd.read_excel(file, sheet_name = "Warranty Request", header = None, names = ["A", "B", "C", "D", "E"])

        # Fecha Excel (serial)
        fecha = data.loc[9, "E"]
        
        # Id Vehiculo
        idvehiculo = None
        if pd.notna(data.loc[6, "E"]):
            txt = str(data.loc[6, "E"]).replace("-", "")
            match = re.search(r"\d+", txt)
            if match:
                idvehiculo = match.group()

        # OT number desde nombre archivo
        ot_match = re.search(r"_([^.]+)_", file)
        ot_number = None
        if ot_match:
            digits = re.search(r"\d+", ot_match.group())
            if digits:
                ot_number = digits.group()

        # Fecha desde nombre archivo (8 dígitos)
        filename_match = re.search(r"\d{8}", file)
        filename_date = filename_match.group() if filename_match else None

        registros.append({"Fecha": fecha, "Idvehiculo": idvehiculo, "Sistema": data.loc[11, "C"],
                          "Odometro": data.loc[9, "C"], "DescripcionFalla": data.loc[15, "A"],
                          "SolicitudCliente": data.loc[17, "A"], "OtNumber": ot_number, "Filename": filename_date})

    # Drataframe final
    garantias = (pd.DataFrame(registros)
                 .assign(Fecha = lambda df: pd.to_datetime(df["Fecha"], errors = "coerce"),
                         FilenameTmp = lambda df: pd.to_datetime(df["Filename"], format = "%Y%m%d", errors = "coerce"))
                 .assign(Fecha = lambda df: df["Fecha"].fillna(df["FilenameTmp"]))
                 .assign(Days = lambda df: (df["FilenameTmp"] - df["Fecha"]).dt.days)
                 .assign(Fecha = lambda df: np.where((df["Days"] < 0) | (df["Days"] > 5), df["FilenameTmp"], df["Fecha"]),
                         Odometro = lambda df: pd.to_numeric(df["Odometro"], errors = "coerce"),
                         InsertDate = datetime.now())
                 .drop(columns = ["Days", "FilenameTmp"]))
    
    sql_types = {'Fecha': types.DATE, 'Odometro': types.INTEGER, 'OtNumber': types.INTEGER,
                 'Filename': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    garantias.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = garantias['Fecha'].max(), cantidad_registros = len(garantias))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
