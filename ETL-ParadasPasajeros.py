#**********************************************************************************************
# @Nombre: Evaluación de comportamiento de pasajeros por EV1
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                 # Manipulacion de datos
import os                                           # Manejo del sistema
import duckdb as db                                 # Manejo de base de datos
import Funciones as fn                              # Funciones ETL
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from datetime import datetime, timedelta            # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1053
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Pasajeros por Parada*"
table = 'FactParadasPasajeros'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Base de datos DuckDB en memoria
con = db.connect(':memory:')

# Rutas de los documentos parquet
ev1 = os.path.join(os.getenv('DBB_PATH_TELEMETRIA'), r'EV1')
act_bus = os.path.join(os.getenv('PAT_NASPY'), r'02 Datos\11 actividad_bus')


#Desarrollo -----------------------------------------------------------------------------------
# Función para generar una lista de fechas en el formato YYYYMMDD
def generar_fechas(desde, dias):
    fechas = [(desde - timedelta(days = x)).strftime('%Y%m%d') for x in range(dias)]
    return set(fechas)

# Función para obtener archivos que coinciden con las fechas dadas
def obtener_archivos_por_fechas(carpeta, fechas):
    archivos = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith('.parquet')]
    archivos_filtrados = [archivo for archivo in archivos if os.path.basename(archivo)[:8] in fechas]
    return archivos_filtrados


# Funcion para crear las tablas de la actividad vehiculo 
def crear_tablas_parquet(con, dias):
    fecha_hoy = datetime.now()  - timedelta(days = 1)
    fechas = generar_fechas(fecha_hoy, dias)
    
    archivos_filtrados = obtener_archivos_por_fechas(ev1, fechas)
    
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
            CREATE OR REPLACE TABLE EV1 AS
            SELECT * 
                ,CAST(NULLIF(localizacionVehiculo.latitud, '') AS FLOAT) AS Latitud
                ,CAST(NULLIF(localizacionVehiculo.longitud, '') AS FLOAT) AS Longitud
                ,CAST(STRPTIME(fechaHoraLecturaDato, '%d/%m/%Y %H:%M:%S.%f') AS DATE) AS fecha
                ,STRPTIME(fechaHoraEnvioDato, '%d/%m/%Y %H:%M:%S.%f') as fechaHoraEnvioDato_1
                ,STRPTIME(fechaHoraLecturaDato, '%d/%m/%Y %H:%M:%S.%f') as fechaHoraLecturaDato_1
            FROM read_parquet([{", ".join(f"'{path}'" for path in archivos_filtrados)}], union_by_name = true);

            ALTER TABLE EV1 DROP COLUMN localizacionVehiculo;
            ALTER TABLE EV1 DROP COLUMN fechaHoraEnvioDato;
            ALTER TABLE EV1 RENAME COLUMN fechaHoraEnvioDato_1 TO fechaHoraEnvioDato;
            
            ALTER TABLE EV1 DROP COLUMN fechaHoraLecturaDato;
            ALTER TABLE EV1 RENAME COLUMN fechaHoraLecturaDato_1 TO fechaHoraLecturaDato;

            '''
            con.execute(query)

def crear_tablas_bus(con, dias):
    fecha_hoy = datetime.now() - timedelta(days = 1)
    fechas = generar_fechas(fecha_hoy, dias)
    archivos_filtrados = obtener_archivos_por_fechas(act_bus, fechas)
    
    if archivos_filtrados:
        # Primero, creamos la tabla FactTablaVehiculo si no existe
        con.execute('''
        CREATE TABLE IF NOT EXISTS FactTablaVehiculo (
            Fecha DATE,
            FechaHora TIMESTAMP,
            CodigoBus VARCHAR,
            Linea VARCHAR,
            SentidoRuta VARCHAR,
            Descripcion VARCHAR);
        ''')
        
        # Si la tabla ya existe, la truncamos
        con.execute('''
        TRUNCATE TABLE FactTablaVehiculo;
        ''')
        
        # Luego, iteramos sobre cada archivo y añadimos sus datos a la tabla <------------------------------------------
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
                SentidoRuta,
                Descripcion
            FROM read_parquet('{archivo}')
            WHERE NumeroBus IS NOT NULL;
            '''
            con.execute(query)

# Funcion de procesamiento de la tabla
def execute_sql_eventos(file_path, con, dias):
    with open(file_path, 'r') as file:
        sql_script = file.read()
    
    crear_tablas_parquet(con, dias)
    crear_tablas_bus(con, dias)

    result_df = clean_columns(con.execute(sql_script).df(), case = 'pascal')
    
    print("SQL script executed successfully.")
    return result_df

try:
    # Dataframe resultante
    eventos = (execute_sql_eventos("./00 Querys/FactParadasPasajeros.sql", con = con, dias = 10)
               .dropna(subset = ['Abordo', 'Bajan', 'Suben'])
               .dropna(subset = ['Linea', 'SentidoRuta', 'Descripcion'])
               .groupby(["Fecha", "Hora", "Linea", "SentidoRuta", "Descripcion"])
               .mean()
               .reset_index()
               .rename(columns = {"Abordo":"MeanAbordo", "Bajan":"MeanBajan", "Suben":"MeanSuben"})
               .assign(Parada = lambda x: x["Descripcion"].str[:6],
                       Descripcion = lambda x: x["Descripcion"].str[7:],
                       NombreLinea = lambda x: x["Linea"].str[9:],
                       Linea = lambda x: x["Linea"].str[1:6]))

    con.close()

    # Seleccion de fechas a insertar
    feceven = set(eventos["Fecha"].unique().tolist())
    fechasactuales = set(pd.read_sql_query('select DISTINCT "Fecha" FROM "op"."FactParadasPasajeros"', con = fn.enginea)
                      .astype(str)
                      .Fecha
                      .to_list())

    # Filtrado de fechas
    fecinsert = list(feceven.difference(fechasactuales))
    df = eventos[eventos["Fecha"].isin(fecinsert)].assign(InsertDate = datetime.now())

    # Envio de los datos al DW
    sql_types = {'FechaHoraLecturaDato': types.TIMESTAMP, 'Latitud': types.FLOAT, 'Longitud': types.FLOAT,
                 'Hora': types.INTEGER, 'Abordo': types.FLOAT, 'Bajan': types.FLOAT, 'Suben': types.INTEGER,
                 'FechaHora': types.TIMESTAMP, 'InsertDate': types.TIMESTAMP}
    
    df.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    if df.empty:
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None, cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
    else:
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = df['Fecha'].max(), cantidad_registros = len(df))
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
      