#**********************************************************************************************
# @Nombre: Proceso de Calculo Asistencia Operadores - Rigel
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import os                                   # Manejo del sistema
import subprocess                           # Ejecución de procesos externos
import Funciones as fn                      # Funciones ETL
import json                                 # Manejo de datos en formato JSON
from sqlalchemy import types                # Manejo de tipos de campos en db
from skimpy import clean_columns            # Limpieza de nombres de columnas
from urllib.request import urlopen          # Realizar solicitudes a URLs
from datetime import datetime               # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1070
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Ausentismo Rigel*"
table = 'FactAusentismoOperador'

# Proceso de obtencion de datos
user = os.getenv("API_USER_AUSENT")
password = os.getenv("API_PASS_AUSENT")

desde = pd.to_datetime("2022-04-01")
hasta = pd.Timestamp.today().normalize() - pd.Timedelta(days = 1)

# Crear secuencia de años y luego fechas de corte
fechas = [desde] + pd.date_range(start = desde, end = hasta, freq = "YS").tolist()

if fechas[-1] != hasta:
    fechas.append(hasta + pd.Timedelta(days = 1))

rango_fechas = pd.DataFrame({"desde": fechas[:-1],
                             "hasta": [d - pd.Timedelta(days = 1) for d in fechas[1:]]})

# Función consulta API
def consultar_ausentismo(fecha_ini, fecha_fin):
    url = ("http://myservice.grupomovil.com.co:9999/WS-MOVIL/service/queryNewness/findDataFilter"
           f"?desde={fecha_ini}&hasta={fecha_fin}&user={user}&pass={password}")

    try:
        response = urlopen(url)
        data = json.loads(response.read().decode())
        df = pd.json_normalize(data)
        if df.empty:
            return df
        # Limpieza columnas
        df = (df.pipe(clean_columns, case = "pascal")
              .assign(Nombres = lambda x: (x["Nombres"] + " " + x["Apellidos"]).str.title(),
                      Empresa = lambda x: (x["Empresa"].str.replace(".*III.*", "ZMOIII", regex = True)
                                                       .str.replace(".*GREEN MOVIL.*", "ZMOV", regex = True)
                                                       .str.replace(".*V.*", "ZMOV", regex = True)),
                      InsertDate = datetime.now(),
                      CodigoTm = lambda x: pd.to_numeric(x["CodigoTm"], errors = "coerce"),
                      Identificacion = lambda x: pd.to_numeric(x["Identificacion"].str.replace("OLD", "", regex = False), errors = "coerce"))
              .pipe(lambda x: x[["Nombres", "CodigoTm", "Empresa"] + [c for c in x.columns if c not in ["Nombres", "CodigoTm", "Empresa"]]])
              .drop(columns = ["Apellidos", "IdGopUnidadFuncional"], errors = "ignore"))
        return df

    except Exception as e:
        print(f"Error en el rango {fecha_ini} - {fecha_fin}: {str(e)}")
        return None

# Ejecutar consultas por rango
try:
    dfs = []
    for _, row in rango_fechas.iterrows():
        df = consultar_ausentismo(row["desde"].strftime("%Y-%m-%d"),
                                  row["hasta"].strftime("%Y-%m-%d"))
        if df is not None:
            dfs.append(df)

    ausentismo = pd.concat(dfs, ignore_index = True)

    # Envio de los datos al DW
    sql_types = {'CodigoTm': types.INTEGER, 'Fecha': types.DATE, 'IdNovedadTipoDetalle': types.INTEGER,
                'Identificacion': types.INTEGER, 'Procede': types.INTEGER, 'PuntosPm': types.INTEGER, 
                'PuntosPmConciliados': types.INTEGER, 'Desde': types.DATE, 'Dias': types.INTEGER, 
                'Hasta': types.DATE, 'InsertDate': types.TIMESTAMP}

    ausentismo.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = ausentismo['Fecha'].max(), cantidad_registros = len(ausentismo))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Refresh PowerBI
path = os.getenv("PAT_PBI_REFRESH")
subprocess.run(["python", path, os.getenv("PBI_ASISTENCIAOPER")])
