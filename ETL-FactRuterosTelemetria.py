#**********************************************************************************************
# @Nombre: ETL-Seguimiento de Rutas
# @Autor: Anderson Sarmiento
#**********************************************************************************************

# Importar librerias --------------------------------------------------------------------------
import os                                         # Manejo del sistema
import duckdb as db                               # Bases de datos
import Funciones as fn                            # Funciones ETL
from sqlalchemy import types                      # Manejo de tipos de campos en db
from skimpy import clean_columns                  # Cambiar el tipo de nombre de columnas
from datetime import datetime                     # Manipulacion de fechas
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1052
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Seguimiento Ruteros Telemetria*"
table = "FactRuterosTelemetria"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

try:
    # Conectar Data Warehouse ---------------------------------------------------------------------
    con = db.connect(os.getenv('DBB_PATH_DUCK'))
    # Directorio donde están los archivos parquet
    carpeta = os.path.join(os.getenv('PAT_NASPY'), r'02 Datos\11 actividad_bus')

    # Urls para la descarga de los datos ----------------------------------------------------------
    fechas  = con.execute(""" SELECT MAX(fechaHoraLecturaDato::DATE) AS Maximo,
                    MIN(fechaHoraLecturaDato::DATE) AS Minimo FROM P60 """).fetchdf()

    # Convertir fechas al formato de los nombres de archivo (YYYYMMDD)
    fecha_min = fechas['Minimo'][0].strftime('%Y%m%d')
    fecha_max = fechas['Maximo'][0].strftime('%Y%m%d')

    # Filtrar archivos dentro del rango de fechas
    archivos_en_rango = [os.path.join(carpeta, f)
                         for f in os.listdir(carpeta)
                         if f.endswith('_Actividad_Bus.parquet') and fecha_min <= f[:8] <= fecha_max]

    # Validar si hay archivos
    if archivos_en_rango:
        # Convertir lista de archivos a string en formato SQL
        archivos_sql = ', '.join(f"'{archivo}'" for archivo in archivos_en_rango)

        # Leer solamente las columnas deseadas
        columnas_deseadas = ''' "Fecha", "CodigoBus", "SentidoRuta", "Linea", "HoraLlegada", 
                                "Descripcion", "Conductor", "Lista de acciones regulatorias",
                                "ViajeLinea", "Coche", "Id Ruta" '''

        # Consulta
        consulta_union = f"""
            CREATE OR REPLACE TEMP TABLE ActividadBus AS
            SELECT {columnas_deseadas}
            FROM read_parquet([{archivos_sql}]) """

        # Ejecutar y obtener DataFrame
        con.execute(consulta_union).fetchdf()
    else:
        print("⚠️ No se encontraron archivos dentro del rango de fechas.")

    con.query(""" CREATE OR REPLACE TEMP TABLE ActividadResumen AS
                  SELECT Fecha, CodigoBus, Coche, ViajeLinea, MIN(HoraLlegada) AS HoraMinima,
                  MAX(HoraLlegada) AS HoraMaxima
                  FROM ActividadBus
                  GROUP BY Fecha, CodigoBus, Coche, ViajeLinea """)

    con.execute(""" CREATE OR REPLACE TEMP TABLE UnionAll AS 
                    SELECT p.idRuta, p.idVehiculo, p.Latitud, p.Longitud, p.fechaHoraLecturaDato,
                           ab.SentidoRuta, ab.Descripcion, ab.Conductor, p.fecha, ab."Id Ruta" as "Linea",
                           CASE 
                                WHEN p.idRuta = ab.SentidoRuta THEN TRUE
                                WHEN ab."Lista de acciones regulatorias" IS NULL 
                                  OR trim(ab."Lista de acciones regulatorias") = '' THEN FALSE
                                ELSE TRUE
                           END AS Validacion,
                           CAST(p.fechaHoraLecturaDato AS TIME) as Hora
                    FROM P60 p
                    ASOF JOIN ActividadBus ab
                        ON p.idVehiculo = REPLACE(ab.CodigoBus, '-', '')
                        AND p.fechaHoraLecturaDato >= ab.Fecha + 
                            (ab.HoraLlegada - TIMESTAMP '1900-01-01 00:00:00') """)

    # Creación de tabla
    Rut = (clean_columns(con.execute(""" SELECT ua.idRuta, ua.idVehiculo, ua.Latitud, ua.Longitud, 
                           ua.fechaHoraLecturaDato, ua.SentidoRuta, ua.Descripcion, ua.Conductor, 
                           ua.Validacion, ua.Linea
                    FROM UnionAll ua
                    JOIN ActividadResumen ar
                        ON ua.fecha = ar.Fecha
                        AND ua.idVehiculo = REPLACE(ar.CodigoBus, '-', '')
                        AND ua.Hora BETWEEN CAST(ar.HoraMinima AS TIME) AND CAST(ar.HoraMaxima AS TIME)
                    WHERE ua.Validacion = False """).fetchdf(), case = 'pascal')
                          .assign(InsertDate = datetime.now()))

    sql_types = {'Latitud': types.FLOAT, 'Longitud': types.FLOAT, 'fechaHoraLecturaDato': types.TIMESTAMP,
                 'Conductor': types.INTEGER}
    
    Rut.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    con.close()

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = Rut['FechaHoraLecturaDato'].max(), cantidad_registros = len(Rut))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
