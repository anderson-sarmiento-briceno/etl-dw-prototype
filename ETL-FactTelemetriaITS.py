#**********************************************************************************************
# @Nombre: ETL-Datos Telemetria
# @Autor: Anderson Sarmiento
#**********************************************************************************************

# Importar librerias --------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import numpy as np                          # Manipulacion numerica
import duckdb as db                         # Bases de datos
import os                                   # Archivos del sistema
import subprocess                           # Invocacion de subprocesos
import Funciones as fn                      # Funciones ETL
from skimpy import clean_columns            # Cambiar el tipo de nombre de columnas
from datetime import datetime, timedelta    # Manipulacion de fechas
from sqlalchemy import types                # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1050
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Telemetria ITS*"
table1 = 'FactLatenciaStats'
table2 = 'FactTelemetriaEventos'
table3 = 'FactLatenciaP20'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Conexión y creación del archivo de la base de datos
con = db.connect(os.getenv('DBB_PATH_DUCK'))
pathdatos = os.getenv('DBB_PATH_TELEMETRIA')
pathbuses = "./01 Inputs/DimBusesAntenas.csv"
pathbus = os.path.join(os.getenv('PAT_NASPY'), r'02 Datos\11 actividad_bus')

# Conectar Data Warehouse ---------------------------------------------------------------------
hook = os.getenv('TOK_SLACK')

# Diccionario de Tablas 
tablas = [
    'ALA1', 'ALA2', 'ALA3', 'ALA7', 'ALA8', 'ALA10', 
    'EV1', 'EV2', 'EV6', 'EV7', 'EV9', 'EV10', 'EV19', 'EV20', 'EV21', 
    'P60', 'P20']

# Función para generar una lista de fechas en el formato YYYYMMDD
def generar_fechas(desde, dias):
    fechas = [(desde - timedelta(days = x)).strftime('%Y%m%d') for x in range(dias)]
    return set(fechas)

# Función para obtener archivos que coinciden con las fechas dadas
def obtener_archivos_por_fechas(carpeta, fechas):
    archivos = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith('.parquet')]
    archivos_filtrados = [archivo for archivo in archivos if os.path.basename(archivo)[:8] in fechas]
    return archivos_filtrados

def obtener_archivos_bus(carpeta, fechas):
    archivos = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith('.parquet')]
    archivos_filtrados = [archivo for archivo in archivos if os.path.basename(archivo)[:8] in fechas]
    return archivos_filtrados

# Función para crear tablas a partir de archivos parquet filtrados por fechas
def crear_tablas_parquet(con, tablas, dias):
    fecha_hoy = datetime.now()  - timedelta(days = 1)
    fechas = generar_fechas(fecha_hoy, dias)
    
    for tabla in tablas:
        carpeta = os.path.join(pathdatos, tabla)
        archivos_filtrados = obtener_archivos_por_fechas(carpeta, fechas)

        if archivos_filtrados:
            # Verificar si los archivos no están vacíos
            archivos_validos = []
            for path in archivos_filtrados:
                try:
                    df = pd.read_parquet(path)
                    if not df.empty:  # Si el archivo no está vacío
                        archivos_validos.append(path)
                except Exception as e:
                    print(f"Error al leer {path}: {e}")

            if archivos_validos:
                query = f'''
                CREATE OR REPLACE TABLE {tabla} AS
                SELECT * 
                    ,CAST(NULLIF(localizacionVehiculo.latitud, '') AS FLOAT) AS Latitud
                    ,CAST(NULLIF(localizacionVehiculo.longitud, '') AS FLOAT) AS Longitud
                    ,CAST(STRPTIME(fechaHoraLecturaDato, '%d/%m/%Y %H:%M:%S.%f') AS DATE) AS fecha
                    ,STRPTIME(fechaHoraEnvioDato, '%d/%m/%Y %H:%M:%S.%f') as fechaHoraEnvioDato_1
                    ,STRPTIME(fechaHoraLecturaDato, '%d/%m/%Y %H:%M:%S.%f') as fechaHoraLecturaDato_1
                FROM read_parquet([{", ".join(f"'{path}'" for path in archivos_filtrados)}], union_by_name = true);
    
                ALTER TABLE {tabla} DROP COLUMN localizacionVehiculo;
                ALTER TABLE {tabla} DROP COLUMN fechaHoraEnvioDato;
                ALTER TABLE {tabla} RENAME COLUMN fechaHoraEnvioDato_1 TO fechaHoraEnvioDato;
                
                ALTER TABLE {tabla} DROP COLUMN fechaHoraLecturaDato;
                ALTER TABLE {tabla} RENAME COLUMN fechaHoraLecturaDato_1 TO fechaHoraLecturaDato;
    
                '''
                con.execute(query)

# Funcion para crear las tablas de la actividad vehiculo 
def crear_tablas_bus(con, dias):
    fecha_hoy = datetime.now() - timedelta(days = 1)
    fechas = generar_fechas(fecha_hoy, dias)
    archivos_filtrados = obtener_archivos_bus(pathbus, fechas)
    
    if archivos_filtrados:
        # Primero, creamos la tabla FactTablaVehiculo si no existe
        con.execute('''
        CREATE TABLE IF NOT EXISTS FactTablaVehiculo (
            Fecha DATE,
            FechaHora TIMESTAMP,
            CodigoBus VARCHAR,
            Linea VARCHAR,
            Conductor VARCHAR,
            NombreConductor VARCHAR);
        ''')
        
        # Si la tabla ya existe, la truncamos
        con.execute('''
        TRUNCATE TABLE FactTablaVehiculo;
        ''')
        
        # Luego, iteramos sobre cada archivo y añadimos sus datos a la tabla
        for archivo in archivos_filtrados:
            query = f'''
            INSERT INTO FactTablaVehiculo
            SELECT 
                Fecha,
                make_timestamp(EXTRACT(YEAR FROM Fecha),
                               EXTRACT(MONTH FROM Fecha),
                               EXTRACT(DAY FROM Fecha),
                               EXTRACT(HOUR FROM HoraLlegada),
                               EXTRACT(MINUTE FROM HoraLlegada),
                               EXTRACT(SECOND FROM HoraLlegada)) AS FechaHora,
                REPLACE(CodigoBus, '-', '') AS CodigoBus,
                Linea,
                Conductor,
                NombreConductor
            FROM read_parquet('{archivo}')
            WHERE NumeroBus IS NOT NULL;
            '''
            con.execute(query)

# Funcion para obtener las estadisticas de las latencias de las señales
def stat_fecha(con, tablas):
    dfs = []  # Lista para almacenar los DataFrames de cada tabla
    for tabla in tablas:
            
        query = f'''
        SELECT 
            fecha,
            COUNT(*) AS Total,
            COUNT(CASE WHEN ABS(DATEDIFF('second', fechaHoraEnvioDato, fechaHoraLecturaDato)) BETWEEN -5 AND 5 THEN 1 END) AS TotalValida,
            MAX(DATEDIFF('second', fechaHoraEnvioDato, fechaHoraLecturaDato)) AS Maximo,
            MIN(DATEDIFF('second', fechaHoraEnvioDato, fechaHoraLecturaDato)) AS Min,
            (COUNT(CASE WHEN ABS(DATEDIFF('second', fechaHoraEnvioDato, fechaHoraLecturaDato)) BETWEEN -5 AND 5 THEN 1 END) * 1.0 / COUNT(*)) AS Pct
        FROM 
            {tabla}
        GROUP BY 
            fecha
        '''
        df = con.execute(query).df()  # Ejecuta la consulta y convierte el resultado a un DataFrame
        df['Tabla'] = tabla  # Añade una columna para identificar la tabla de origen
        dfs.append(df)  # Añade el DataFrame a la lista

    combined_df = pd.concat(dfs, ignore_index = True)  # Combina todos los DataFrames en uno solo
    return combined_df

# Cargue de la tabla de buses -----------------------------------------------------------------
con.execute(query = 
            f''' 
            CREATE OR REPLACE TABLE DimBusesAntenas AS
            SELECT * FROM read_csv('{pathbuses}')
            ''')
#**********************************************************************************************
# Ejecutar la funcion para crear las tablas ---------------------------------------------------
#**********************************************************************************************
crear_tablas_parquet(con, tablas, dias = 30)
crear_tablas_bus(con, dias = 30)

#**********************************************************************************************
# Ejecutar proceso para el cargue de las estadisticas al DW -----------------------------------
#**********************************************************************************************
try:
    data_fecha = clean_columns(stat_fecha(con, tablas), case = 'pascal')

    sql_types_stats = {
        'Fecha': types.DATE
    }
    
    data_fecha.to_sql(table1, schema = 'it', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types_stats)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = data_fecha['Fecha'].max(), cantidad_registros = len(data_fecha))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

#**********************************************************************************************
# Obtener los datos de los eventos (Colision, Aceleracion, Velocidad y Pastillas) -------------
#**********************************************************************************************
def execute_sql_eventos(file_path, con):
    with open(file_path, 'r') as file:
        sql_script = file.read()
    
    result_df = clean_columns(con.execute(sql_script).df(), case = 'pascal')
    
    print("SQL script executed successfully.")
    return result_df

try:
    eventos = execute_sql_eventos("./00 Querys/FactTelemetriaEventos.sql", con = con)
    eventos['Conductor'] = pd.to_numeric(eventos['Conductor'], errors = 'coerce').fillna(0).astype(int)
    eventos['IdVehiculo'] = eventos['IdVehiculo'].apply(lambda x: x if x.startswith('Z') else np.nan)
    eventos['IdVehiculo'] = eventos['IdVehiculo'].str.replace('Z', '').apply(pd.to_numeric, errors = 'coerce').astype('Int64')

    sql_types_evnt = {
        'Fecha': types.DATE,
        'Hora': types.INTEGER,
        'Conductor': types.INTEGER,
        'IdVehiculo': types.INTEGER
    }
    
    eventos.to_sql(table2, schema = 'it', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types_evnt)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = eventos['Fecha'].max(), cantidad_registros = len(eventos))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

#**********************************************************************************************
# Obtener los datos para el reporte de sombras de transmision ---------------------------------
#**********************************************************************************************
def execute_sql_sombras(file_path, con):
    with open(file_path, 'r') as file:
        sql_script = file.read()
    
    result_df_sombras = clean_columns(con.execute(sql_script).df(), case = 'pascal')
    
    print("SQL script executed successfully.")
    return result_df_sombras

try:
    sombras_p20 = execute_sql_sombras("./00 Querys/FactLatenciaP20.sql", con = con)
    sombras_p20['IdVehiculo'] = sombras_p20['IdVehiculo'].apply(lambda x: x if x.startswith('Z') else np.nan)
    sombras_p20['IdVehiculo'] = sombras_p20['IdVehiculo'].str.replace('Z', '').apply(pd.to_numeric, errors = 'coerce').astype('Int64')

    sql_types_p20 = {
        'Fecha': types.DATE,
        'Bin': types.INTEGER,
        'IdVehiculo': types.INTEGER
    }
    
    sombras_p20.to_sql(table3, schema = 'it', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types_p20)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = sombras_p20['Fecha'].max(), cantidad_registros = len(sombras_p20))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))

# Actualiza Sobras de latencia
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_LATENCIAP20')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

#**********************************************************************************************
# Cierre de la conexion -----------------------------------------------------------------------
#**********************************************************************************************
con.close()

# *********************************************************************************************
# ***************************** Invocan Otros Procesos ****************************************
# *********************************************************************************************
# Invocar reporte de tramas en Slack ----------------------------------------------------------
os.chdir("C:/Users/dev/Documents/01 Modelos/20220714-analisis-provision")
subprocess.call(["python", "Render-ITS.py"])
