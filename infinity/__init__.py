#**********************************************************************************************
# @Nombre: ETL para obtener el token del API de Infinity y Telemetría
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import sqlite3                                          # Base de datos SQLite
import os                                               # Manejo del sistema
import requests                                         # Solicitudes de API
import boto3                                            # Intereccion con AWS
import pandas as pd                                     # Manipulacion de datos
from datetime import datetime                           # Manejo de fechas
from botocore.exceptions import NoCredentialsError      # Manejo de credenciales AWS
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Datos para la autenticación
def iniinfinity():
    # URL del punto final de autorización de Cognito
    client_id = "51e720ii0mmdntddqkr7vmor01"

    # Credenciales del cliente
    client_secret = '12rugr0tbpd6bpkocks91vee5d66jb4rhtg15301ko8lh1mo3s4h'
    url = 'https://us-east-1aiczbcqzp.auth.us-east-1.amazoncognito.com/oauth2/token'
    data = {'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        response = requests.post(url, data = data, headers = headers)
        if response.status_code == 200:
            token = response.json().get('access_token')
            return {'Authorization': f'Bearer {token}'}
        else:
            return print(f"Error obteniendo token: {response.text}")
    except Exception as e:
        print(f"Error al obtener el token: {str(e)}")
    
# Extraccion de datos actuales de infinity
def infinity():
    # Captura de datos ----------------------------------------------------------------------------
    url_dashboard = os.getenv("API_INFI_URL")

    # API para obtener los datos de las transacciones 
    response_get = requests.get(url_dashboard, headers = iniinfinity())

    # Extraccion de datos
    datat = pd.json_normalize(pd.json_normalize(response_get.json()["fuunit"], record_path = "chgr_details", errors = "ignore")
                              .explode('connectors', ignore_index = True)['connectors'])

    # Seleccion de datos a tratar
    report = (datat.loc[:, ["connector_alias", "status", "max_timestamp", "soc", "placa", "conn_location"]]
              .rename(columns = {"connector_alias":"Dispensador", "status":"estado", "max_timestamp":"FechaHora",
                                 "soc":"SOC", "placa":"idVehiculo", "conn_location":"Bahia"})
              .assign(FechaHora = lambda x: pd.to_datetime(x.FechaHora, dayfirst = True, errors = 'coerce'),
                      SOC = lambda x: pd.to_numeric(x['SOC'].replace('', pd.NA), errors = 'coerce').astype('Int64')))
    
    return report

# Define la URL de la API----------------------------------------------------------------------
def telemetry():
    url = os.getenv('API_P60')

    # Define los encabezados con el token
    headers = {'token': os.getenv('TOK_TELEMETRIA')}

    # Realiza la solicitud GET
    response = requests.get(url, headers = headers)

    # Verifica el estado de la respuesta
    if response.status_code == 200:
        if response.json()['status'] == 1:
            data = (pd.json_normalize(response.json()['periodic_60'], sep = '_')
                      .loc[:, ["fechaHoraLecturaDato", "idVehiculo", "nivelRestanteEnergia", "kilometrosOdometro", "localizacionVehiculo"]]
                      .assign(fechaHoraLecturaDato = lambda x: pd.to_datetime(x.fechaHoraLecturaDato, dayfirst = True, errors = 'coerce'),
                              latitud = lambda x: x['localizacionVehiculo'].apply(lambda loc: float(loc[0]['latitud'])),
                              longitud = lambda x: x['localizacionVehiculo'].apply(lambda loc: float(loc[0]['longitud'])),
                              idVehiculo = lambda x: x['idVehiculo'].str.replace('^Z', '', regex = True))
                      .drop(columns = 'localizacionVehiculo'))
    return data

# Funcion para el almacenamiento---------------------------------------------------------------
rutbase = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charge.db")

# Lectura o reinicio de tabla
def leer_base(table, columns):
    conn = sqlite3.connect(rutbase)
    hora_actual = datetime.now().strftime("%H:%M")
    
    # Verificar si la tabla existe
    cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type = 'table' AND name = '{table}'")
    tabla_existe = cursor.fetchone() is not None

    if hora_actual == "18:00":
        print("Reiniciando la tabla...")
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        tabla_existe = False
        
        # Creacion de seteo del SOC
        url_vehicles = "https://iui6n4fe13.execute-api.us-east-1.amazonaws.com/vehicles" 
        datavehicles = (pd.DataFrame(requests.get(url_vehicles, headers = iniinfinity()).json())
                                    .loc[:, ["alias", "batery_max_cap"]]
                                    .assign(alias = lambda df: pd.to_numeric(df["alias"], errors = "coerce"))
                                    .dropna(subset = ["alias"])
                                    .assign(alias = lambda df: df["alias"].astype(int)))
        datavehicles.to_sql('dim_vehicles', conn, if_exists = 'replace', index = False)

    if tabla_existe:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
    else:
        df = pd.DataFrame(columns = columns)

    conn.close()
    return df

# Sobrescribir la tabla
def guardar_base(df, table):
    conn = sqlite3.connect(rutbase)
    df.to_sql(table, conn, if_exists = "replace", index = False)
    conn.close()
    print(f"Datos guardados a las {datetime.now().strftime('%H:%M')}")
