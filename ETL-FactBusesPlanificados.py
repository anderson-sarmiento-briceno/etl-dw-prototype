#**********************************************************************************************
# @Nombre: Historico de Buses Planificados
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                 # Manipulacion de datos
import requests                                     # Solicitud a API
import re                                           # Regex
import os                                           # Manejo del sistema
import Funciones as fn                              # Funciones ETL
from datetime import datetime, date, timedelta      # Manejo de fechas
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from requests.auth import HTTPBasicAuth             # Credenciales API
from datetime import datetime                       # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1243
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Procesos Buses Planificados*"
table = 'FactBusesPlanificados'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#Desarrollo -----------------------------------------------------------------------------------
# Funcion para ajustar la hora
def ajustar_hora_llegada(hora):
    """Ajusta valores de la columna Hora.
    Si las horas superan las 24, resta 24 y ajusta el formato."""
    if pd.isna(hora):  # Verificar si el valor es NaN
        return pd.NaT
    try:
        partes = hora.split(":")
        horas, minutos, segundos = map(int, partes)
        if horas >= 24:
            horas -= 24
        return datetime.strptime(f"{horas:02}:{minutos:02}:{segundos:02}", "%H:%M:%S")
    except Exception:
        return pd.NaT

try:
    # Seleccion de fechas
    fecha_ini_descarga = '2022-04-02'
    today = (date.today() - timedelta(days = 1))

    fechasactuales = (
        pd.read_sql_query(
            'select DISTINCT "Fecha" FROM "op"."FactBusesPlanificados"', con = fn.enginea)
        .astype(str)
        .Fecha.to_list())

    rangofecha = (pd.date_range(start = fecha_ini_descarga, end = today).strftime("%Y-%m-%d"))

    ctrdias = [fecha for fecha in rangofecha if fecha not in fechasactuales]

    # Obtencion del token -------------------------------------------------------------------------
    # URL del endpoint para obtener el token y usuarios
    token_url = f"{os.getenv('API_REPORT_RIGEL')}oauth/token"
    authkeys = os.getenv('TOK_RIGEL').split('-')

    # Credenciales para autenticación básica
    usertoken = authkeys[0]
    passwordtoken = authkeys[1]

    # Datos requeridos en el cuerpo de la solicitud
    data = {'username': authkeys[2],
            'password': authkeys[3],
            'grant_type': 'password'}

    # Hacer la solicitud POST con autenticación básica
    response = requests.post(token_url, auth = HTTPBasicAuth(usertoken, passwordtoken), data = data)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        Token = response.json().get('access_token')
    else:
        # Si hubo un error, imprimir el código de estado y el mensaje de error
        print(f"Error al obtener el token: {response.status_code}")
        print(response.text) 

    # Procesamiento de la informacion -------------------------------------------------------------
    # Definir la URL y headers
    urlbase = f"{os.getenv('API_REPORT_RIGEL')}reportes/busesplanificados"
    headers = {"Authorization": f"Bearer {Token}",
               "Content-Type": "application/json"}

    # Reges para reemplazar columna de necesarias
    repl_dict = {re.compile(r'^(ZMO FONTIBON III SAS).*'): 'ZMOIII',
                 re.compile(r'^(ZMO FONTIBON V SAS).*'): 'ZMOV', 
                 re.compile(r'.*314.*'):'KB314',
                 re.compile(r'.*311.*'):'KG311',
                 re.compile(r'.*308.*'):'KH308',
                 re.compile(r'.*317.*'):'KH317',
                 re.compile(r'.*318.*'):'KH318',
                 re.compile(r'.*327.*'):'KH327',
                 re.compile(r'.*312.*'):'KL312',
                 re.compile(r'.*325.*'):'KL325',
                 re.compile(r'.*328.*'):'KL328',
                 re.compile(r'.*329.*'):'KL329',
                 re.compile(r'.*331.*'):'KL331',
                 re.compile(r'.*324.*'):'KA324',
                 re.compile(r'.*332.*'):'KA332',
                 re.compile(r'.*326.*'):'KB326',
                 re.compile(r'.*003.*'):'AA003'}

    # Procesamiento de la informacion y carga
    resumen = []
    for i in ctrdias:
        url = f"{urlbase}/{i}/{i}"
        buses = (clean_columns(pd.DataFrame(requests.get(url, headers = headers).json())
                           .assign(fecha = lambda x: pd.to_datetime(x['fecha'], yearfirst = True))
                           .loc[lambda d: d['fecha'].dt.date.isin(pd.to_datetime(ctrdias).date)]
                           .assign(uf = lambda x: x['uf'].replace(repl_dict, regex = True),
                                   ruta = lambda x: x['tipoTarea'].replace(repl_dict, regex = True),
                                   km = lambda x: x['km'] / 100,
                                   timeOrigin = lambda x: x['timeOrigin'].apply(ajustar_hora_llegada),
                                   timeDestiny = lambda x: x['timeDestiny'].apply(ajustar_hora_llegada),
                                   InsertDate = datetime.now())
                           .query("estadoOperacion in ('Eliminado', 'Ejecutado Parcial', 'Adicional')")
                           .loc[:, ['idPrgTc', 'fecha', 'servbus', 'tipologia', 'codigoTm', 
                                    'timeOrigin', 'timeDestiny', 'codigoBus', 'uf', 'ruta', 'km',
                                    'estadoOperacion', 'tipoNovedad', 'tipoNovedadDetalle', 
                                    'InsertDate']], case = 'pascal'))
        # Envio de los datos al DW
        sql_types = {'IdPrgTc': types.INTEGER, 'Fecha': types.DATE, 'CodigoTm': types.INTEGER,
                    'TimeOrigin': types.TIME, 'TimeDestiny': types.TIME,
                    'Km': types.FLOAT, 'InsertDate': types.TIMESTAMP}
        
        buses.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

        # Resumen para este archivo
        resgis = len(buses)
        max_fecha = pd.to_datetime(i, yearfirst = True)
        resumen.append({"records_inserted": resgis, "max_fecha": max_fecha})

    # Cierra DuckDB y crea DataFrame de resumen
    res = pd.DataFrame(resumen)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = res['max_fecha'].max(), cantidad_registros = len(res))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
