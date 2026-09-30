#**********************************************************************************************
# @Nombre: ETL para obtener el token del API de Infinity y Telemetría
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                   # Manejo del sistema
import numpy as np                          # Operaciones matematicas
import re                                   # Regex
import infinity as inf                      # Creación del Token Api Infinity
import pandas as pd                         # Manipulacion de datos
import Funciones as fn                      # Funciones ETL
from sqlalchemy import text                 # Conexion base de datos
from skimpy import clean_columns            # Cambiar el tipo de nombre de columnas
from datetime import datetime               # Manejo de fechas
from sqlalchemy import types                # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1118
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso de Suministro Vehicular*"
table = "FactSuministroVehicular"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definir el rango de ejecucion
inicio = datetime.strptime("18:00", "%H:%M").time()
fin = datetime.strptime("06:00", "%H:%M").time()
ahora = datetime.now().time()
horaree = (ahora.hour, ahora.minute)

# Configuración de tablas y columnas
table_config = {"energy":{"table": "energy_table",
                          "columns": ["FechaActual", "idVehiculo", "Dispensador", "estado", "Bahia", "SOCActual", "kilometrosOdometro", "latitud", "longitud"]},
                "vehicle_soc":{"table": "dim_vehicles",
                               "columns": ["alias", "batery_max_cap"]},
                "infinity":{"table":"infinity",
                            "columns":["idVehiculo", "FechaInf", "SocInf"]}}

try:
    if horaree == (18, 00):
        print("Reinicio de tabla")
        inf.leer_base(table = table_config["energy"]["table"], columns = table_config["energy"]["columns"])
        inf.leer_base(table = table_config["infinity"]["table"], columns = table_config["infinity"]["columns"])

    elif ahora >= inicio or ahora <= fin:
        # Consulta de Odometros
        DimOdo = pd.read_sql_query(
               f''' SELECT (df."IdVehiculo") as "idVehiculo", ftm."Reading"
                    FROM ma."FactMeterReading" ftm
                    LEFT JOIN "DimFlota" df
                        ON ftm."AssetNum" = df."AssetNum"
                    WHERE ftm."ReadingDate" = (
                        SELECT MAX("ReadingDate")
                        FROM ma."FactMeterReading") ''', con = fn.cona)

        # Extraccion de informacion
        facttelemetry = inf.telemetry()
        factinfinity = inf.infinity()

        # Reges para reemplazar columna de sercones
        repl_dict = {re.compile(r'Charging'): 'Cargando',
                     re.compile(r'Finishing'): 'Parada',
                     re.compile(r'Offline'): 'Fuera de Servicio',
                     re.compile(r'Available'): 'Disponible'}

        # Base de la informacion
        select = (facttelemetry.merge(factinfinity, how = "left", on = "idVehiculo")
                  .assign(estado = lambda x: x["estado"].fillna("Desconectado").replace(repl_dict, regex = True),
                          Dispensador = lambda x: x["Dispensador"].fillna(np.nan),
                          Bahia = lambda x: x["Bahia"].fillna(np.nan),
                          SOCActual = lambda x: np.where(x["FechaHora"] > x["fechaHoraLecturaDato"], x["SOC"], x["nivelRestanteEnergia"]),
                          FechaActual = lambda x: np.where(x["FechaHora"] > x["fechaHoraLecturaDato"], x["FechaHora"], x["fechaHoraLecturaDato"]),
                          idVehiculo = lambda x: x["idVehiculo"].astype(int))
                  .merge(inf.leer_base(table = table_config["vehicle_soc"]["table"], columns = table_config["vehicle_soc"]["columns"]), how = "left", left_on = "idVehiculo", right_on = "alias")
                  .merge(DimOdo, how = "left", on = "idVehiculo")
                  .assign(kilometrosOdometro = lambda x: np.where(x["kilometrosOdometro"] < x["Reading"], x["Reading"], x["kilometrosOdometro"]))
                  .drop(columns = ["alias", "Reading"])
                  .rename(columns = {"batery_max_cap": "SOCObjetivo"}))

        # Seleccion de informacion a almacenar en sqlite
        baselite = select.loc[:, table_config["energy"]["columns"] + ["SOCObjetivo"]]

        # Se extrae información reciente
        basenergy = (inf.leer_base(table = table_config["energy"]["table"], columns = table_config["energy"]["columns"])
                     .sort_values("FechaActual", ascending = False)
                     .drop_duplicates(subset = "idVehiculo", keep = "first"))

        # Datos adicionales de infinity
        add = select.loc[:, ["idVehiculo", "FechaHora", "SOC"]].rename(columns = {"FechaHora":"FechaInf", "SOC":"SocInf"})

        # Valida que la base de datos no este vacia
        if not basenergy.isna().all().all():
            # Calcula los movimientos con respecto al pasado
            pushdw = (baselite.merge(basenergy, how = "left", on = "idVehiculo", suffixes = ("", "_base"))
                      .assign(Conexion = lambda x: np.where(pd.notna(x["Dispensador"]), "Conectado", "Pendiente"),
                              Dispensador = lambda x: np.where(pd.isna(x["Dispensador"]) & pd.notna(x["Dispensador_base"]), x["Dispensador_base"], x["Dispensador"]),
                              Bahia = lambda x: np.where(pd.isna(x["Bahia"]) & pd.notna(x["Bahia_base"]), x["Bahia_base"], x["Bahia"]))
                      .assign(estado = lambda x: np.where((x["estado"] == "Finalizado") | (x["estado_base"] == "Finalizado"), "Finalizado",
                                                          np.where(x["estado"] == "Cargando", "Cargando",
                                                                   np.where(x["estado"] == "Parada",
                                                                            np.where(x["SOCActual"] >= x["SOCObjetivo"], "Finalizado", "Fallo Carga"),
                                                                            np.where((x["estado"] == "Desconectado") & (x["estado_base"] != "Desconectado"),
                                                                                     np.where(x["SOCActual"] >= x["SOCObjetivo"], "Finalizado", "Fallo Carga"),
                                                                                     x["estado"])))),
                              InsertDate = datetime.now())
                      .loc[:, table_config["energy"]["columns"] + ["SOCObjetivo", "Conexion","InsertDate"]])

            # Almacena el ultimo resultado
            inf.guardar_base(df = pushdw.drop(columns = "InsertDate"), table = table_config["energy"]["table"])

            # Actualizacion de base de datos
            add = add = (pd.concat([add, (inf.leer_base(table = table_config["infinity"]["table"], columns = table_config["infinity"]["columns"])
                                    .assign(SocInf = lambda x: x["SocInf"].astype("Int64")))])
                   .assign(FechaInf = lambda x: pd.to_datetime(x["FechaInf"], errors = "coerce"))
                   .sort_values("FechaInf", ascending = False)
                   .drop_duplicates(subset = "idVehiculo", keep = "first")
                   .dropna(subset = "idVehiculo"))
            inf.guardar_base(df = add, table = table_config["infinity"]["table"])

            # Envio de los datos al DW
            sql_types = {'FechaActual': types.TIMESTAMP, 'IdVehiculo': types.INTEGER, 
                         'SocActual': types.INTEGER, 'KilometrosOdometro': types.INTEGER, 
                         'Latitud': types.FLOAT, 'Longitud': types.FLOAT, 'SOCObjetivo': types.INTEGER,
                         'FechaInf': types.TIMESTAMP, 'SocInf': types.INTEGER, 'InsertDate': types.TIMESTAMP}

            pushdw = clean_columns(pushdw.merge(add, how = "left", on = "idVehiculo"), case = 'pascal')
            fn.cona.execute(text(f'TRUNCATE TABLE ma."{table}"'))
            pushdw.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)
            if datetime.now().strftime("%H:%M") == "05:55":
                # Registro de la ejecucion del proceso
                fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = pushdw['FechaActual'].max(), cantidad_registros = len(pushdw))
                fn.update_process(id_process = IdProceso, engine = fn.enginea)
        else:
            # Almacena el ultimo resultado
            inf.guardar_base(df = baselite, table = table_config["energy"]["table"])
            inf.guardar_base(df = add, table = table_config["infinity"]["table"])

            pushdw = clean_columns(baselite.assign(Conexion = "Pendiente",
                                                   InsertDate = datetime.now())
                                            .merge(add, how = "left", on = "idVehiculo"), case = 'pascal')

            # Envio de los datos al DW
            sql_types = {'FechaActual': types.TIMESTAMP, 'IdVehiculo': types.INTEGER, 
                         'SocActual': types.INTEGER, 'KilometrosOdometro': types.INTEGER, 
                         'Latitud': types.FLOAT, 'Longitud': types.FLOAT, 'FechaInf': types.TIMESTAMP, 
                         'SocInf': types.INTEGER, 'InsertDate': types.TIMESTAMP}

            fn.cona.execute(text(f'TRUNCATE TABLE ma."{table}"'))
            pushdw.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)
    
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)