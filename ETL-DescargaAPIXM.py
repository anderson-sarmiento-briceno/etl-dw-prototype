#**********************************************************************************************
# @Nombre: Proceso para obtener los datos del API de XM
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
from datetime import date, timedelta, datetime    # Manipulacion de fechas
import pandas as pd                               # Manipulacion de datos
import os                                         # Sistema
import Funciones as fn                            # Funciones ETL
from sqlalchemy import types                      # Manejo de tipos de campos en db
from skimpy import clean_columns                  # Limpieza de columnas
from pydataxm import *                            # Paquete de XM
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1120
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Precio Bolsa API XM*"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Path de la navegación -----------------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'
pathdestiny = f'E://Drive//greenmovil.com.co//Gestion Mantenimiento - General//Documentos//10 Datos//14 PreciosBolsaXM//'

# Creacion del proceso ------------------------------------------------------------------------
# Se indica el nombre de la métrica tal como se llama en el campo metricId, para este caso se
# usara las siguientes metricas:
# @PrecBolsNaci = Precio Bolsa Nacional por Sistema, Sistema, HourlyEntities
# @PrecPromContNoRegu =	Precio Promedio Contratos No Regulados por Sistema,	Sistema, HourlyEntities
# @PrecPromContRegu = Precio Promedio Contratos Regulados por Sistema, Sistema, HourlyEntities
# @PrecBolsNaciTX1 = Precio Bolsa Promedio AritmÃ©tico TX1 por Sistema, Sistema, HourlyEntities
# @PrecPromCont = Precio Promedio Contrato por Sistema, Sistema, DailyEntities
# @PrecEscaAct = Precio Escasez ActivaciÃ³n por Sistema,	Sistema, DailyEntities
# @PrecEsca = Precio Escasez por Sistema,	Sistema, DailyEntities
# @PrecEscaMarg = Precio Marginal Escasez por Sistema, Sistema, DailyEntities
# @PrecEscaPon = Precio Escasez Ponderado por Sistema, Sistema, DailyEntities

# Procesamiento de Fechas para la descarga ----------------------------------------------------

# Diccionario de metricas
metricid = {"PrecBolsNaci": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecBolsNaci")],
            "PrecPromContNoRegu": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecPromContNoRegu")],
            "PrecPromContRegu": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecPromContRegu")],
            "PrecBolsNaciTX1": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecBolsNaciTX1")],
            "PrecPromCont": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecPromCont")],
            "PrecEscaAct": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecEscaAct")],
            "PrecEsca": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecEsca")],
            "PrecEscaMarg": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecEscaMarg")],
            "PrecEscaPon": ["Sistema", fn.ind_tabla(fn.enginea, "FactPrecEscaPon")]}

sql_types =  {'Date' : types.DATE, 'InsertDate': types.TIMESTAMP}

# Se inicia el objeto del api
objetoAPI = pydataxm.ReadDB()

# Funcion para obtener la ultima fecha --------------------------------------------------------
def obtener_fecha_inicio(metrica):
    # Consulta la última fecha descargada desde la base de datos
    fecha_inicio = (
    pd.read_sql_query(
        f'''
        select MAX("Date") as "Date" FROM ma."Fact{metrica}"
        '''
        , con = fn.enginea)
    ).iloc[0, 0]

    if fecha_inicio is None:
        # Si no hay fecha en la base de datos, comienza desde una fecha predeterminada o la fecha actual
        fecha_inicio = date(2021, 1, 1)

    return fecha_inicio

# Funcion para descargar y transformar los datos de XM ----------------------------------------
def descargar_informacion(metricid_dict, directorio_destino):

    for metrica, valor in metricid_dict.items():
        try:
            print(f"*{metrica}.csv*")

            fecha_ini = obtener_fecha_inicio(metrica) + timedelta(days = 1)
            fecha_fin = date.today()

            # objetoAPI.request_data devuelve los datos en forma de lista
            datos = objetoAPI.request_data(metrica, valor[0], fecha_ini, fecha_fin)

            if len(datos) == 0:
            
                print(f"El DataFrame: {metrica} no tiene fecha para descargar")
                fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = valor[1], max_fecha_tabla = None, cantidad_registros = 0)

            else:

                # Crear un DataFrame a partir de los datos
                df = clean_columns(pd.DataFrame(datos), case = 'pascal')
                df.drop(columns = ['Id'], inplace = True)

                if 'ValuesCode' in df.columns:
                    df.drop(columns = ['ValuesCode'], inplace = True)

                nuevosnombres = {nombrecol: nombrecol.replace('ValuesHour', '') for nombrecol in df.columns}

                df.rename(columns = nuevosnombres, inplace = True)

                if df.shape[1] > 10:

                    df = pd.melt(df, id_vars = ['Date'], var_name = 'Hora', value_name = 'Valor')

                    columnasorder = ['Date', 'Hora', 'Valor']
                    df = df[columnasorder]

                else:

                    df = df.rename(columns = {'Value': 'Valor'})
                    columnasorder = ['Date', 'Valor']
                    df = df[columnasorder]

                df['InsertDate'] = datetime.now()

                # Insercion al Data Warehouse
                df.to_sql(f"Fact{metrica}", schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)
                
                # Registro de la ejecucion del proceso
                fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = valor[1], max_fecha_tabla = df['Date'].max(), cantidad_registros = len(df))

                # Guardar el DataFrame en el diccionario usando la métrica como clave
                nombrearchivo = f"Fact{metrica}.csv"
                rutaarchivo = f"{directorio_destino}/{nombrearchivo}"

                # Guardar los nuevos registros en el archivo CSV en modo "append"
                with open(rutaarchivo, 'a', newline = '') as archivo_csv:
                    df.to_csv(archivo_csv, header = False, index = False)
            
        except Exception as e:
            # registro de la ejecucion del proceso con error
            fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = valor[1], observacion = str(e))

# Se invocan las funciones para la descargar y guardado de los archivos -----------------------
# Llamar a la funcion para la descarga
descargar_informacion(metricid, pathdestiny)

# Se ejecuta Script Descarga precio Bolsa Diario ----------------------------------------------
file_path_Api_XM = os.getenv('PAT_SCRIPT_XM')
command = f'python "{file_path_Api_XM}"' 
os.system(command)

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_BOLSAXM')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
