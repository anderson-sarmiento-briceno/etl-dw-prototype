#**********************************************************************************************
# @Nombre: ETL para extraer las notificaciones del infinity
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                                # Manejo del sistema
import requests                                          # Solicitud a API
import numpy as np                                       # Manipulacion numerica
import pandas as pd                                      # Manipulacion de datos
import infinity as inf                                   # Creación del Token Api Infinity
import Funciones as fn                                   # Funciones ETL
from sqlalchemy import types                             # Manejo de tipos de campos en db
from skimpy import clean_columns                         # Cambiar el tipo de nombre de columnas
from datetime import date, timedelta, datetime           # Manipulacion de fechas
from deltalake import DeltaTable, write_deltalake        # Manejo de Deltalake
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1110
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Log Siemens *"
table = 'FactLogSiemens'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Conectar Data Warehouse ---------------------------------------------------------------------
ruta_delta = os.getenv('PAT_DLK_INFINITY_LOGS')
url_logs = "https://w26670ug8k.execute-api.us-east-1.amazonaws.com/prod/logs-errores?"

# Funciones de transformacion Infinity  -------------------------------------------------------
# funcion para asignar un id al registro de transacciones.
def assign_error_id(group):
    # Convertir el primer ErrorTimestamp a entero (timestamp Unix) y concatenar con ChargeboxAlias
    first_timestamp = group['ErrorTimestamp'].iloc[0].strftime('%Y%m%d%H%M%S')
    chargebox_alias = group['IdConector'].iloc[0]
    error_id = f"{int(first_timestamp)}{chargebox_alias}"
    group['ErrorId'] = pd.NaT  # Inicializar todos los valores como NaT
    group['ErrorId'].iloc[0] = error_id  # Asignar solo al primer registro
    return group

try:
    # Diccionario códigos de erros con su respectiva corrección -----------------------------------
    codeerr = clean_columns(
        pd.concat([pd.read_csv("01 Inputs/CodigosError.csv")]), case = 'pascal')

    codeerr = codeerr.drop(columns=['SuggestedAction'])

    # Diccionario de Cargadores -------------------------------------------------------------------
    DimCargadores = clean_columns(
        pd.concat([pd.read_csv("01 Inputs/DimCargadores.csv")]), case = 'pascal')

    # Se invoka el token del infinity -------------------------------------------------------------
    headers = inf.iniinfinity()

    # Se define el umbral en segundos -------------------------------------------------------------
    umbral_segundos = 600  

    # *********************************************************************************************
    # ************************** Proceso Descarga de datos de logs ********************************
    # *********************************************************************************************

    # Parametros para definir las fechas de inicio de descarga ------------------------------------
    fecha_ini_descarga = '2024-01-15'
    #fecha_ini_descarga = '2026-06-25'
    fecha_fin_descarga = (date.today() - timedelta(days = 1)).strftime("%Y-%m-%d")

    # Rango de fechas de descarga
    ctrrangofecha = (pd.date_range(start = fecha_ini_descarga, end = fecha_fin_descarga).strftime("%Y-%m-%d"))

    # Fechas descargardas en el deltalake
    actual = DeltaTable(ruta_delta).to_pandas(columns = ['DateStart'])
    actual = actual['DateStart'].unique()

    # Lista con las fechas a descargar
    ctrdias = [fecha for fecha in ctrrangofecha if fecha not in actual]

    # Ciclo for para iterar sobre el api, descargar los archivos e insertarlos al deltalake -------
    for d in ctrdias:

        url_errores = f"{url_logs}startDate={d}&endDate={d}"

        # API para obtener los datos de las transacciones
        response_get = requests.get(url_errores, headers = headers)

        # Validación del dataset
        val = clean_columns(pd.DataFrame(response_get.json()["data"]), case = 'pascal')
        if val.empty:
            continue
        else:
            # Transformacion de datos
            datatransa = (val
                .assign(ErrorTimestamp = lambda x: pd.to_datetime(x['ErrorTimestamp']))
                .assign(DateStart = lambda x: x['ErrorTimestamp'].dt.strftime("%Y-%m-%d"), 
                        IdConector =  lambda x: x['ChargeBoxAlias'] + "-" + x['ConnectorId'].astype(str), 
                        VendorErrorCode = lambda x: x['VendorErrorCode'].astype(int),
                        DescripcionSolucion = "",
                        VendorId = "Siemens",
                        Aplicacion = "Infinity")
                .rename(columns = {"ChargeBoxAlias":"ChargeboxAlias", "ChargeBoxId": "ChargeboxId",
                                   "ChargeBoxStatus": "ChargeboxStatus"})
                .merge(DimCargadores, left_on = 'ChargeboxAlias', right_on = 'ChargerName', how = 'left')
                .assign(TransactionId = lambda x: x["TransactionId"].fillna("").astype(str),
                        ChargeboxStatus = "",
                        VendorErrorCode = lambda x: x["VendorErrorCode"].fillna(0).astype("int32"),
                        Rownum = 1)
            )

            # Insertar filas al deltalake

        # ---> INSPECCIÓN PROFUNDA DE ÚLTIMOS DÍAS (SIN VARIABLES) <---
            #print("\n" + "!"*30 + " REVISIÓN DE TIMESTAMP " + "!"*30)
            #print("Muestra de ErrorTimestamp (Primeros 5 registros):")
            #print(datatransa['ErrorTimestamp'].head(5))
            #print("\nMuestra de ErrorTimestamp (Últimos 5 registros):")
            #print(datatransa['ErrorTimestamp'].tail(5))
            #print("\n¿Hay nulos en ErrorTimestamp?:", datatransa['ErrorTimestamp'].isnull().sum())
            #print("!"*83 + "\n")
            
            # Mantenemos el freno para que NO guarde nada en el DW todavía
            #raise Exception("Freno de control: Inspeccionando formatos de los últimos días.")

    # 1. Abre el cerrojo: Quita el UTC para que no se dañen los tipos de datos en el DW
            if pd.api.types.is_datetime64_any_dtype(datatransa['ErrorTimestamp']):
                datatransa['ErrorTimestamp'] = datatransa['ErrorTimestamp'].dt.tz_localize(None)
            else:
                datatransa['ErrorTimestamp'] = pd.to_datetime(datatransa['ErrorTimestamp']).dt.tz_localize(None)

            # 2. Te da la llave: Agrega la columna número 23 que el NAS exige
            datatransa['__index_level_0__'] = 0 

            # Guarda limpio
            #write_deltalake(ruta_delta, datatransa, mode = "append")
            
            write_deltalake(ruta_delta, datatransa, mode = "append")

            print(d)

    # *********************************************************************************************
    # ******************** Proceso Transformacion de datos de logs ********************************
    # *********************************************************************************************
    datatransa = (DeltaTable(ruta_delta).to_pandas()
                  .assign(InsertDate = datetime.now())
                  .drop(columns = ['ChargeboxAlias', 'ConnectorId', 'Rownum', 'Id', 'ChargeboxId'])
                  .sort_values(by = ['IdConector', 'ErrorDescription', 'ErrorTimestamp'])
                  .groupby(['IdConector', 'ErrorDescription'])
                  .apply(lambda x: x.assign(TiempoFueraServicio = x['ErrorTimestamp'].diff().dt.total_seconds()))
                  .reset_index(drop = True)
                  )

    # Implementación asignacion de id del evento
    result = (datatransa
              .sort_values(by = ['IdConector', 'ErrorDescription', 'ErrorTimestamp'])
              .groupby(['IdConector', 'ErrorDescription'], group_keys = False)
              .apply(assign_error_id)
             )

    # Condición para actualizar ErrorId basado en DiffTime > 3600
    result['ErrorId'] = np.where(result['TiempoFueraServicio'] > 3600, result['ErrorTimestamp'].apply(lambda x: str(x.strftime('%Y%m%d%H%M%S'))) + result['IdConector'], result['ErrorId'])

    # Hacer un relleno hacia abajo para ErrorId dentro de cada grupo
    result['ErrorId'] = result.groupby(['IdConector', 'ErrorDescription'])['ErrorId'].ffill()

    # Se selecciona la fecha mayor del grupo y se asigna a una nueva columna 
    result['FechaSolucion'] = result.groupby(['ErrorId'])['ErrorTimestamp'].transform('max')

    # Se filtra la primera fila de cada grupo 
    grupos = result.groupby(['ErrorId']).first().reset_index()

    grupos['TiempoFueraServicio'] = grupos.apply(lambda x: (x['FechaSolucion'] - x['ErrorTimestamp']).total_seconds(), axis = 1)

    datafinal = (
        grupos 
        .merge(codeerr, left_on='VendorErrorCode', right_on='Code', how='left')
        .rename(columns = {
            'DateStart': 'Fecha', 
            'ErrorTimestamp': 'FechaError', 
            'VendorErrorCode': 'CodigoError', 
            'ErrorSource': 'Fuente', 
            'ErrorAlarm': 'Alarma', 
            'ErrorDescription': 'DescripcionError'})
        .assign(TransactionId = lambda x: pd.to_numeric(x["TransactionId"], errors = "coerce"))
        .loc[:, ["ErrorId", "TransactionId", "Fecha", "Empresa", "Canopi", "IdConector", 
                 "TipoNotificacion", "FechaError", "FechaSolucion", "OcppErrorCode", "CodigoError", 
                 "Fuente", "Alarma", "DescripcionError", "DescripcionSolucion", "TiempoFueraServicio", 
                 "Aplicacion", "InsertDate"]]
    )

    # Se aplica un filtro de dos dias atras para garantizar la finalizacion del evento
    hoy = pd.Timestamp('now').normalize() + pd.Timedelta(days = 1) - pd.Timedelta(seconds = 1)
    hace_dos_dias = hoy - pd.Timedelta(days = 2)

    df_filtrado = datafinal[(datafinal['FechaError'] <= hace_dos_dias)]

    # *********************************************************************************************
    # ****************** Proceso para hacer el append en la base de datos *************************
    # *********************************************************************************************
    # Se lee la tabla Energy del DW y se extraen los Id de las Tx de Infinity ---------------------
    with fn.enginea.connect() as conn:
        idInfinity = pd.read_sql_query('''
                                          SELECT "ErrorId"
                                          FROM ma."FactLogSiemens" 
                                          ''', con = conn)

    # Datos nuevos para insertar al DW
    nuevosregistros = df_filtrado[~df_filtrado['ErrorId'].isin(idInfinity['ErrorId'])]

    # Envio de los datos al DW
    sql_types = {
        'Fecha': types.DATE,
        'Canopi': types.INTEGER,
        'TiempoFueraServicio': types.INTEGER,
        'CodigoError': types.INTEGER,
        'TransactionId': types.INTEGER,
        'InsertDate': types.TIMESTAMP
    }

    if not nuevosregistros.empty:
        with fn.enginea.begin() as conn:
            nuevosregistros.to_sql(table, 
                                schema = 'ma', 
                                con = conn, 
                                if_exists = 'append', 
                                index = False, 
                                dtype=sql_types)
            print("Datos insertados con éxito.")
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = nuevosregistros['Fecha'].max(), cantidad_registros = len(nuevosregistros))
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
    else:
        print("El DataFrame está vacío. No se insertaron datos.")
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datetime.now(), cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)

#except Exception as e:
    # registro de la ejecucion del proceso con error
    #fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))



except Exception as e:
    import traceback
    print("\n" + "!"*40 + " ¡ERROR DETECTADO! " + "!"*40)
    traceback.print_exc()
    print("!"*99 + "\n")  


