#**********************************************************************************************
# @Nombre: Historial de Procesos Disciplinarios
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                           # Manejo del sistema
import pandas as pd                                 # Manipulacion de datos
import requests                                     # Solicitud a API
import re                                           # Regex
import numpy as np                                  # Manipulacion numerica
import Funciones as fn                              # Funciones ETL
from requests.auth import HTTPBasicAuth             # Credenciales API
from datetime import datetime                       # Manejo de fechas
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1242
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Procesos Disciplinarios*"
table = "FactProcesosDisciplinarios"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#Desarrollo -----------------------------------------------------------------------------------
# Obtencion del token -------------------------------------------------------------------------
try:
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
    url = "http://10.0.3.138:8080/ws/reportes/maestroProDisciplinarios"
    headers = {"Authorization": f"Bearer {Token}",
               "Content-Type": "application/json"}

    # Reges para reemplazar columna de sercones
    repl_dict = {re.compile(r'En gestión'): 'En gestion',
                 re.compile(r'Cerrado- Apelación'): 'Cerrado- Apelacion',
                 re.compile(r'Sanción'): 'Sancion',
                 re.compile(r'Llamado de atención'): 'Llamado de atencion'}
    # Estandarizacion de la información
    disci = (clean_columns(pd.DataFrame(requests.get(url, headers = headers).json())
                           .assign(fechaApertura = lambda x: pd.to_datetime(x['fechaApertura'], yearfirst = True))
                           .assign(fechaCierre = lambda x: pd.to_datetime(x['fechaCierre'], yearfirst = True),
                                   identificacion = lambda x: x["identificacion"].astype('Int64'),
                                   fechaCitacion = lambda x: pd.to_datetime(x['fechaCitacion'], format='%Y-%m-%d %H:%M:%S'),
                                   fechaIniSancion = lambda x: pd.to_datetime(x['fechaIniSancion'], yearfirst = True),
                                   fechaFinSancion = lambda x: pd.to_datetime(x['fechaFinSancion'], yearfirst = True),
                                   asistencia = lambda x: x['asistencia'].replace({'SI': True, 'NO': False, '': np.nan}),
                                   estado = lambda x: x['estado'].replace(repl_dict, regex = True),
                                   gestion = lambda x: x['gestion'].replace(repl_dict, regex = True),
                                   InsertDate = datetime.now())
                           .loc[:, ['idPdMaestro', 'fechaApertura', 'fechaCierre', 'identificacion',
                                    'codigoTm', 'estado', 'gestion', 'fechaCitacion', 
                                    'fechaIniSancion', 'fechaFinSancion', 'usuarioApertura',
                                    'usuarioResponsable', 'asistencia', 'InsertDate']], case = 'pascal'))

    # Lectura de Historico de procesos y unificacion
    hist = pd.read_parquet(os.path.join(r"E:\Drive", r"greenmovil.com.co\Gestion Informacion - General\07 Gestion_Humana\Historico Procesos Disciplinarios\ProcesosDisciplinarios2023.parquet"))
    procdis = (pd.concat([disci, hist])
               .sort_values("FechaApertura", ascending = True))

    # Envio de los datos al DW
    sql_types = {'FechaApertura': types.DATE, 'FechaCierre': types.DATE,
                    'FechaCitacion': types.DATE, 'FechaIniSancion': types.DATE,
                    'FechaFinSancion': types.DATE, 'Asistencia': types.BOOLEAN,
                    'InsertDate': types.TIMESTAMP}
    
    procdis.to_sql(table, schema = 'gh', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = disci['FechaApertura'].max(), cantidad_registros = len(disci))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
