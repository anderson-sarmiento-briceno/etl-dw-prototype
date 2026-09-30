#**********************************************************************************************
# @Nombre: Historico de novedades por operador
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                           # Manejo del sistema
import pandas as pd                                 # Manipulacion de datos
import requests                                     # Solicitud a API
import Funciones as fn                              # Funciones ETL
from requests.auth import HTTPBasicAuth             # Credenciales API
from datetime import datetime, date, timedelta      # Manejo de fechas
from sqlalchemy import text                         # Conexion base de datos
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1241
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Novedades Operadores*"
table = 'FactNovedadesOperador'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#Desarrollo -----------------------------------------------------------------------------------
try:
    # Define el DELETE como una consulta segura
    delete_query = text(''' DELETE FROM op."FactNovedadesOperador"
                            WHERE "Fecha" >= CURRENT_DATE - INTERVAL '20 days' ''')

    # Ejecutar el DELETE
    fn.cona.execute(delete_query)

    fecha_ini_descarga = '2022-04-01'
    today = date.today() - timedelta(days = 1)

    fechasactuales = (
        pd.read_sql_query(
            'select DISTINCT "Fecha" FROM "op"."FactNovedadesOperador"', con = fn.enginea)
        .astype(str)
        .Fecha.to_list())

    rangofecha = (pd.date_range(start = fecha_ini_descarga, end = today).strftime("%Y-%m-%d"))

    ctrdias = [fecha for fecha in rangofecha if fecha not in fechasactuales]

    # Obtencion del token -------------------------------------------------------------------------
    # URL del endpoint para obtener el token
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
    base_url = f"{os.getenv('API_REPORT_RIGEL')}novedades/bitacoraNovedades"
    headers = {"Authorization": f"Bearer {Token}",
               "Content-Type": "application/json"}
    resumen = []
    for select in ctrdias:
        url = f"{base_url}/{select}/{select}"

        # Captura de la tabla de novedades
        ApRigel = (clean_columns(pd.DataFrame(requests.get(url, headers = headers).json())
                   .query("tipo_novedad in ['Ausentismo', 'Daño a Flota', 'Infracciones', 'Accidentalidad']")
                   .assign(fecha = lambda x: pd.to_datetime(x['fecha'], yearfirst = True),
                           operador = lambda x: pd.to_numeric(x['operador'].str.slice(0, 6), errors = 'coerce').astype('Int64'),
                           operador_nuevo = lambda x: x['operador_nuevo'].str.slice(0, 6).astype('Int64'),
                           procede = lambda x: x['procede'].replace({'SI': True, 'NO': False}),
                           InsertDate = datetime.now())
                   .loc[:, ['idNovedad', 'fecha', 'tipo_novedad', 'pm_grupo', 'detalle_novedad',
                            'operador', 'operador_nuevo', 'vehiculo', 'vehiculo_nuevo',
                            'puntos_pm_conciliados', 'procede', 'InsertDate']], case = 'pascal'))

        # Envio de los datos al DW
        sql_types = {'IdNovedad': types.INTEGER, 'Fecha': types.DATE, 'Operador': types.INTEGER,
                     'OperadorNuevo': types.INTEGER, 'PuntosPmConciliados': types.FLOAT, 
                     'InsertDate': types.TIMESTAMP}
        
        ApRigel.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

        # Resumen para este archivo
        resumen.append({"records_inserted": len(ApRigel), "max_fecha": pd.to_datetime(select, yearfirst = True)})

    # Crear DataFrame de resumen
    res = pd.DataFrame(resumen)

    # Notificacion Proceso de descarga
    if res.empty:
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None, cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
    else:
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = res['max_fecha'].max(), cantidad_registros = res["records_inserted"].sum())
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
      