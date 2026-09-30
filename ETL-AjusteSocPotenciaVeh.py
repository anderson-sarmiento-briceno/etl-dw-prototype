#**********************************************************************************************
# @Nombre: Proceso para imputar información SOC y Kwh
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os
import requests                                          # Hacer consultas en API's
import pandas as pd                                      # Manipulacion de datos
import infinity as inf                                   # Token infinity 
import Funciones as fn                                   # Funciones ETL
from sqlalchemy import text                              # Funciones de texto SQL
from datetime import datetime                            # Manipulacion de fechas
from slack_sdk import WebClient                          # Cliente de Slack
from slack_sdk.errors import SlackApiError               # Manejo de errores de Slack
from dotenv import load_dotenv
load_dotenv()

try:
    # Inicializar el cliente de Slack con tu token
    client = WebClient(token = os.getenv('TOK_SLACK_MESG'))

    # *********************************************************************************************
    # ******************************* Informacion SOC *********************************************
    # *********************************************************************************************
    query = """
    SELECT 
        "VehicleInfo", 
        MAX("DateStart") AS "LastDateStart", 
        CURRENT_DATE - MAX("DateStart") as "Valid",
        CASE 
                WHEN CURRENT_DATE - MAX("DateStart") < 4 THEN 92
                ELSE 100
            END AS "PercentCharge"
    FROM ma."FactConsumoEnergy"
    WHERE LENGTH("VehicleInfo") = 6
    AND "EndSoCPercent" = 100
    GROUP BY "VehicleInfo";
    """

    # Ejecutar el query y cargar los resultados en un DataFrame
    checksoc = pd.read_sql_query(query, con = fn.enginea)
    hook = os.getenv('TOK_SLACK')
    # Nombre del proceso para correr en el script -------------------------------------------------
    # Colocar el Id del proceso que esta en el DW
    IdProceso = 1116
    # Titulo que se desplega en el mensaje de slack
    pretext = f"{IdProceso} - Proceso Actualización SOC Flota*"
    # *********************************************************************************************
    # ********************************* SOC Final *************************************************
    # *********************************************************************************************
    # Se parametrizan las variables de soc y potencia de carga
    # Datos para la solicitud GET
    url_vehicles = "https://w26670ug8k.execute-api.us-east-1.amazonaws.com/prod/vehicles" 
    headers = inf.iniinfinity()

    # Se lee la información del API de vehículo ---------------------------------------------------
    vehicles_get = requests.get(url_vehicles, headers = headers)

    # Se crea el dataframe con la información de la tabla
    datavehicles = (
        pd.DataFrame(vehicles_get.json())
        .query("SiteId == 'ZMOIII' | SiteId == 'ZMOV'")
        .drop(columns=['Modules', 'Placa', 'BateryMaxCap', 'ChargeMaxCap', 'Status'])
        .merge(checksoc, left_on = "Alias", right_on = "VehicleInfo", how = "left")
        .assign(BateryMaxCap = lambda x: x["PercentCharge"])
        .drop(["LastDateStart", "VehicleInfo", "Valid", "PercentCharge", "Alias"], axis = 1))

    # Crear una lista de diccionarios con los datos de cada fila
    payloads = datavehicles.to_dict(orient = 'records')

    # Configurar el SOC Final en cada uno de los vehiculos
    for idx, payload in enumerate(payloads, start = 1):
        # Hacer la solicitud PUT
        response = requests.put(url_vehicles, json = payload, headers = headers)

        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            print(f"Solicitud PUT exitosa para el vehículo {payload['Id']}")
        else:
            print(f"Error en la solicitud PUT para el vehículo {payload['Id']}: {response.status_code}")
        print(f"Payload {idx}:", payload)

    alerta = checksoc.query("Valid > 4")

    if len(alerta) == 0:
           print("No hay alarmas") #slack(None, soc)
    else:
        # Notificacion Proceso
        # Crear el mensaje
         now = datetime.now().strftime("%Y-%m-%d") 
         mensaje = f"""
         A continuación se adjunta la Información importante respecto al proceso de carga:
         \n
         :warning: Para el día de hoy *{now}* se tienen *{len(alerta)}* vehículos que llevan más de 4 días sin cargar al 100%
         \n
         *Por favor es importante que se de continuidad a ese proceso de carga*
         """
         # Enviar el mensaje
         try:
             response = client.chat_postMessage(
                 channel = os.getenv("SLK_CARGA"),  # ID del canal de
                 text = mensaje
             )
             print("Mensaje enviado con éxito")
         except SlackApiError as e:
             print(f"Error al enviar el mensaje: {e}")

    query = text("""
        SELECT 
        "VehicleInfo", 
        MAX("DateStart") AS "LastDateStart", 
        CURRENT_DATE - MAX("DateStart") as "Valid",
        CASE 
                WHEN CURRENT_DATE - MAX("DateStart") < 5 THEN 90
                ELSE 100
            END AS "PercentCharge"
    FROM ma."FactConsumoEnergy"
    WHERE "VehicleInfo" LIKE 'LM%'
    AND "EndSoCPercent" = 100
    GROUP BY "VehicleInfo";
        """)
    check = pd.read_sql_query(query, con = fn.enginea)

    datalets = (pd.DataFrame(vehicles_get.json())
                .query("SiteId == 'LETSMOVIL'")
                .drop(columns = ['Modules', 'Placa', 'BateryMaxCap', 'ChargeMaxCap', 'Status'])
                .merge(check, left_on = "Alias", right_on = "VehicleInfo", how = "left")
                .assign(BateryMaxCap = lambda x: x["PercentCharge"])
                .drop(["LastDateStart", "VehicleInfo", "Valid", "PercentCharge", "Alias"], axis = 1))

    payload = datalets.to_dict(orient = 'records')

    # Configurar el SOC Final en cada uno de los vehiculos
    for idx, payload in enumerate(payload, start = 1):
        # Hacer la solicitud PUT
        response = requests.put(url_vehicles, json = payload, headers = headers)
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            print(f"Solicitud PUT exitosa para el vehículo {payload['Id']}")
        else:
            print(f"Error en la solicitud PUT para el vehículo {payload['Id']}: {response.status_code}")
        print(f"Payload {idx}:", payload)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "InfinityUpdateSOC"), max_fecha_tabla = datetime.now(), cantidad_registros = len(datavehicles))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "InfinityUpdateSOC"), observacion = str(e))

