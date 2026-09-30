#**********************************************************************************************
# @Nombre: Funciones de los procesos ETLs
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import os                                   # Manejo del sistema
import requests                             # Hacer consultas en API's
import urllib.parse                         # Manejo de URLs
from datetime import date, datetime         # Manejo de fechas
from sqlalchemy import create_engine, text  # Conexion base de datos
from sqlalchemy.engine import URL           # Para construir URLs de conexion
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Credenciales de la base de datos
usuarioa = os.getenv('DBB_USER_DWGRMA')
contraa = os.getenv('DBB_PASS_DWGRMA')

# Conexion a la base de datos Green Movil Amatista
enginea = create_engine(f'postgresql://{usuarioa}:{contraa}@10.0.22.78:5432/GRMDW')
cona = enginea.connect()

# Conexion a la base de datos Kactus
paramskt = urllib.parse.quote_plus('DRIVER={ODBC Driver 17 for SQL Server};'
                                 'SERVER=10.0.3.63\\RRHHMSSQL;'
                                 'DATABASE=KactusGrM;'
                                 f'UID={os.getenv("DBB_USER_KACTUS")};'
                                 f'PWD={os.getenv("DBB_PASS_KACTUS")};'
                                 'TrustServerCertificate=yes;')
enginekt = create_engine(f"mssql+pyodbc:///?odbc_connect={paramskt}")

# Conexion a la base de datos Maximo
paramsmx = urllib.parse.quote_plus("DRIVER={ODBC Driver 17 for SQL Server};"
                                 "SERVER=10.0.3.58\\MANTENIMIENTOSQL;"
                                 "DATABASE=GRMAXPR;"
                                 f"UID={os.getenv('DBB_USER_MAXIM')};"
                                 f"PWD={os.getenv('DBB_PASS_MAXIM')};"
                                 "TrustServerCertificate=yes;")

enginemx = create_engine(f"mssql+pyodbc:///?odbc_connect={paramsmx}")

# Conexion a la base de datos SIESA
connection_url = URL.create("mssql+pyodbc",
                            username = os.getenv('DBB_USER_SIESA'),
                            password = os.getenv('DBB_PASS_SIESA'),
                            host = "10.0.3.61\\CONTABLEMMSQL",
                            database = "BI_GRMUNOEREALUF06",
                            query={"driver": "ODBC Driver 17 for SQL Server",
                                   "TrustServerCertificate": "yes"})

enginesi = create_engine(connection_url)

# Funcion para extraer indice de la tabla
def ind_tabla(engine, tabla):
    df_ind = pd.read_sql(f""" SELECT id_tabla
                              FROM bi.monitored_tables
                              WHERE tabla = '{tabla}' """, engine)
    if df_ind.empty:
        return None
    else:
        return df_ind.loc[0, "id_tabla"]

# Funcion para registrar la actualizacion de una tabla
def registrar_actualizacion(engine, id_tabla, id_proceso, max_fecha_tabla = None,
                            cantidad_registros = None, observacion = None):
    today = date.today()
    dia_hoy = today.day

    # 1. Saber si hoy es dia habil
    day_habil = pd.read_sql(f''' SELECT ("IsWeekday" = 1 AND "IsHoliday" = 0) AS habil
                                 FROM "DimDate"
                                 WHERE "Date" = '{today}' ''', engine).iloc[0, 0]

    # 2. Traer parametros del proceso
    df_proc = pd.read_sql(f''' SELECT frecuencia, frecuencia_fija
                               FROM bi.process
                               WHERE id_proceso = {id_proceso} ''', engine)

    frec = df_proc.loc[0, "frecuencia"]
    dias_mes_raw = df_proc.loc[0, "frecuencia_fija"]

    # Inicializar indicador
    indicador = None

    # 2.5 Regla especial: hay error → fuerza comportamiento
    if observacion is not None and str(observacion).strip() != "":
        indicador = 0 if day_habil else None
    else:
        # 4. Caso: dias fijos del mes
        if dias_mes_raw is not None:
            dias_mes = [int(x) for x in dias_mes_raw.split(",")]
            indicador = 1 if dia_hoy in dias_mes else 0
        else:
            # 3. Si NO es dia habil → indicador NULL
            if not day_habil:
                indicador = None
            else:
                # 5. Caso: frecuencia en dias exactos
                if frec == 1:
                    indicador = 1
                else:
                    df_last = pd.read_sql(f''' SELECT fecha_actualizacion
                                               FROM bi.table_updates
                                               WHERE id_proceso = {id_proceso}
                                                AND id_tabla = {id_tabla}
                                               ORDER BY fecha_actualizacion DESC
                                               LIMIT 1 ''', engine)
                    if df_last.empty:
                        indicador = 1
                    else:
                        diff_days = (today - df_last.iloc[0, 0].date()).days
                        indicador = 1 if diff_days <= frec else 0

    # 6. Registrar fila
    df = pd.DataFrame([{"id_tabla": id_tabla, "id_proceso": id_proceso, "max_fecha_tabla": max_fecha_tabla,
                        "cantidad_registros": cantidad_registros, "indicador": indicador, "observacion": observacion}])

    # 7. Insertar en la tabla
    df.to_sql("table_updates", engine, schema = "bi", if_exists = "append", index = False)
    
# Funcion para registrar el conteo de procesos diarios
def check_habil_day(engine):
    today = date.today()
    dia_hoy = today.day

    # Saber si hoy es dia habil
    day_habil = pd.read_sql(f''' SELECT ("IsWeekday" = 1 AND "IsHoliday" = 0) AS habil
                                 FROM "DimDate"
                                 WHERE "Date" = '{today}' ''', engine).iloc[0, 0]

    if not day_habil:
        return

    process = pd.read_sql_query(''' SELECT id_proceso, frecuencia, frecuencia_fija
                                    FROM bi.process
                                    WHERE frecuencia >= 1
                                      AND estado = 'A' ''', con = engine)

    monitor = pd.read_sql_query(''' SELECT id_proceso
                                    FROM bi.monitored_tables
                                    WHERE id_proceso IS NOT NULL
                                      AND activo = true ''', con = engine)

    # Frecuencia fija por día
    subpro = (process.loc[process["frecuencia_fija"].notna()]
              .assign(flag_dia = lambda d: d["frecuencia_fija"].astype(str).str.split(",")
                      .apply(lambda xs: str(dia_hoy) in [x.strip() for x in xs]))
              .loc[lambda d: d["flag_dia"]]
              .drop(columns = ["flag_dia"]))
    # Frecuencia normal
    subprod = process[process["frecuencia_fija"].isna() & (process["frecuencia"] == 1)]
    subprodu = pd.DataFrame()
    if today.weekday() == 0:
        subprodu = process[process["frecuencia_fija"].isna() & (process["frecuencia"] != 1)]
    process = pd.concat([subpro, subprod, subprodu])["id_proceso"].to_list()
    # Conteo final
    count = (monitor.loc[monitor["id_proceso"].isin(process)]
             .shape[0])
    df_insert = pd.DataFrame([{"fecha": today, "total_procesos": count}])

    df_insert.to_sql("daily_execution_control", con = engine, schema = "bi", if_exists = "append", index = False)
    
    return dia_hoy

# Funcion para actualizar la fecha de ultima ejecucion del proceso
def update_process(id_process, engine):
    with engine.begin() as conn:
        conn.execute(text(""" UPDATE bi.process
                              SET fecha_ultima_ejecucion = :fecha_ultima_ejecucion
                              WHERE id_proceso = :id_proceso """),
                    {"fecha_ultima_ejecucion": datetime.now(), "id_proceso": id_process})
