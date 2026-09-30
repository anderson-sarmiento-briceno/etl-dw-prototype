# **********************************************************************************************
# @Nombre: Obtener la tabla control por medio del servicio SOAP
# @Autor: Anderson Sarmiento
# **********************************************************************************************

# Importar librerias ---------------------------------------------------------------------------
import pandas as pd                              # Manejo de datos
import numpy as np                               # Manejo numerico
import Funciones as fn                           # Funciones ETL
import re                                        # Regex
import os                                        # Sistema
from zeep import Client                          # Manejo del servicio SOAP
from zeep.helpers import serialize_object        # Serializar objetos SOAP
from datetime import datetime, date, timedelta   # Manejo de Fecha
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1200
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Freeway*"
table1 = 'FactTablaControl'
table2 = 'FactTablaVehiculo'
table3 = 'FactTablaResumenConductor'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Parametros ----------------------------------------------------------------------------------
a_dict = {"ZMOIII": 231, "ZMOV": 233}
puertos = {"ZMOIII": [8794, os.getenv("API_FREEWAY_UF6")], "ZMOV": [8791, os.getenv("API_FREEWAY_UF17")]}
fecha_ini_descarga = '2022-07-31'
fecha_ini_descarga_crew = '2022-11-21'

# Funcion para parsear las fechas -------------------------------------------------------------
def hhmmss(tiempo, fecha):
    hora24 = int(tiempo.days)
    segundos = str(timedelta(seconds = int(tiempo.seconds)))
    final = (pd.to_datetime(fecha) + pd.DateOffset(hora24)).strftime("%Y-%m-%d") + ' ' + segundos
    return final

# Tabla control - Secuencia de dias para descargar la informacion -----------------------------
# Se crea la variable de fecha semana
today = date.today()
start = today - timedelta(days = today.weekday())
fechasemana = start + timedelta(days = 6)

ctrfechasactuales = (
    pd.read_sql_query(
        'select DISTINCT "Date" FROM "op"."FactTablaControl"', con = fn.enginea)
    .astype(str)
    .Date.to_list())

ctrrangofecha = (pd.date_range(start = fecha_ini_descarga, end = fechasemana).strftime("%Y-%m-%d"))

# Lista con las fechas a descargar
ctrdias = [fecha for fecha in ctrrangofecha if fecha not in ctrfechasactuales]

# Tabla Vehiculo - Secuencia de dias para descargar la informacion ----------------------------
vehfechasactuales = (
    pd.read_sql_query(
        'select DISTINCT "Date" FROM "op"."FactTablaVehiculo"', con = fn.enginea)
    .astype(str)
    .Date.to_list())

vehrangofecha = (pd.date_range(start = fecha_ini_descarga, end = fechasemana).strftime("%Y-%m-%d"))

# Lista con las fechas a descargar
vehdias = [fecha for fecha in vehrangofecha if fecha not in vehfechasactuales]

# Tabla Resumen Conductor - Secuencia de dias para descargar la informacion -------------------
crefechasactuales = (
    pd.read_sql_query(
        'select DISTINCT "Date" FROM "op"."FactTablaResumenConductor"', con = fn.enginea)
    .astype(str)
    .Date.to_list())

crerangofecha = (pd.date_range(start = fecha_ini_descarga_crew, end = fechasemana).strftime("%Y-%m-%d"))

# Lista con las fechas a descargar
credias = [fecha for fecha in crerangofecha if fecha not in crefechasactuales]

# *********************************************************************************************
# Tabla Control Proceso de obtencion y carga de datos -----------------------------------------
# *********************************************************************************************
# Ordenamiento de columnas
ctrcolumnas = ['DateId', 'Date', 'Organization', 'CrewService', 'CodeDriver', 'Driver',
               'Amplitude', 'WorkTime', 'ProductionDistance', 'PieceOfWork', 'TaskType', 
               'FromStopPoint', 'ToStopPoint', 'StartTime', 'EndTime', 'IsJob', 'TaskDuration', 
               'Distance', 'VehicleService', 'CodeVehicleServiceBase', 'VehicleType', 'Line', 
               'Route', 'VehicleInRoute', 'Trip', 'Pattern', 'InsertDate']

# Reges para reemplazar columna de sercones
repl_dict = {re.compile('.*MANTENI.*'): 'MANTENIMIENTO',
             re.compile('.*MTTO.*'): 'MANTENIMIENTO',
             re.compile('.*ALISTAMI.*'): 'ALISTAMIENTO',
             re.compile('.*CARRO.*'): 'CARRO TALLER',
             re.compile('.*ELECTROMOV.*'): 'ELECTROMOVILIDAD',
             re.compile('.*DESPROGRAMA.*'): 'DESPROGRAMADO',
             re.compile('.*APOYO.*'): 'APOYO TECNICO',
             re.compile('^(FC|FE).*'): 'SERCON',
             re.compile('^(DISPONIBLE OPE).*'): 'DISPONIBLE',
             re.compile('.*SANCI.*'): 'SANCION',
             re.compile('.*ASCENS.*'): 'CAPACITACION',
             re.compile('.*CAPACI.*'): 'CAPACITACION'}

# Ejecucion de la consulta --------------------------------------------------------------------
try:
    for d in ctrdias:

        tc_registros = 0
        df_tabla_control = []

        fecha_ini = d + 'T00:00:00'
        fecha_fin = d + 'T00:00:00'

        print(d, '--------------------')

        for puerto in puertos:
            print("Estoy en la organizacion: " + str(puerto))
            print("Con el puerto: " + str(puertos[puerto]))

            cmp = a_dict[puerto]

            url = puertos[puerto][1]

            # Cliente de conexion
            client = Client(url)
            # Verificacion de estado del servicio
            request = client.service.CanUseService()
            # Obtiene los datos y se almacena en un data frame
            df = pd.DataFrame(serialize_object(client.service.GetControlData(startDate = fecha_ini,
                                                                             endDate = fecha_fin,
                                                                             codeOrganizationList = cmp)))
            print('1/3 Ok Descarga datos Tabla Control')
            # Transformacion de datos
            df['DateId'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y%m%d')
            df['Date'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y-%m-%d')
            df['Organization'] = str(puerto)
            df['Driver'] = df['Driver'].str.capitalize()
            df['Amplitude'] = df['Amplitude'].dt.seconds
            df['WorkTime'] = df['WorkTime'].dt.seconds
            df['TaskDuration'] = df['TaskDuration'].dt.seconds
            df['StartTime'] = df.apply(lambda x: hhmmss(x['StartTime'], x['Date']), axis = 1)
            df['EndTime'] = df.apply(lambda x: hhmmss(x['EndTime'], x['Date']), axis = 1)
            df['StartTime'] = np.where(df["WorkTime"] == 0, np.nan, df['StartTime'])
            df['EndTime'] = np.where(df["WorkTime"] == 0, np.nan, df['EndTime'])
            df['TaskDuration'] = np.where(df["WorkTime"] == 0, 0, df['TaskDuration'])
            df['CrewService'] = df['CrewService'].str.upper()
            df['CrewService'] = df['CrewService'].replace(repl_dict, regex = True)
            df['TaskType'] = df['TaskType'].str.upper()
            df['Driver'] = df['Driver'].str.title()
            df['InsertDate'] = datetime.now()
            df = df[df['Date'].notna()]
            # Append de los datos
            print('2/3 Ok Transformacion Tabla Control')
            # Ordenamiento de columnas
            df = df[ctrcolumnas]
            df_tabla_control.append(df)
            print("3/3 Ok Append datos Tabla Control")

            # Dataframe consolidado
            tabla_control = pd.concat(df_tabla_control)
        
        # Envio de los datos al DW
        tabla_control.to_sql(table1, schema = 'op', con = fn.cona, if_exists = 'append', index = False)
        tc_registros += len(tabla_control)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = d, cantidad_registros = tc_registros)
except Exception as e:
    print("Error:", e)
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))
# *********************************************************************************************
# Tabla Vehiculo Proceso de obtencion y carga de datos ----------------------------------------
# *********************************************************************************************
# Ordenamiento de columnas
vehcolumnas = ["DateId", "Date", "Organization", "Activity", "VehicleService", "VehicleType",
               "Lines", "Expedition", "StartTime", "FromStopPoint", "EndTime", "ToStopPoint", 
               "ProductionDistance", "BusinessDistance", "EmptyDistance", "ProductionTime", 
               "BusinessTime", "EmptyTime", "DeadTime", "InsertDate"]

# Ejecucion de la consulta --------------------------------------------------------------------
try:
    for d in vehdias:

        tv_registros = 0
        df_tabla_vehiculo = []

        fecha_ini = d + 'T00:00:00'
        fecha_fin = d + 'T00:00:00'

        print(d, '--------------------')

        for puerto in puertos:
            print("Estoy en la organizacion: " + str(puerto))
            print("Con el puerto: " + str(puertos[puerto]))

            cmp = a_dict[puerto]

            url = puertos[puerto][1]

            # Cliente de conexion
            client = Client(url)
            # Verificacion de estado del servicio
            request = client.service.CanUseService()
            # Obtiene los datos y se almacena en un data frame
            df = pd.DataFrame(serialize_object(client.service.GetVehicleStatusDataByLine(startDate = fecha_ini,
                                                                                   endDate = fecha_fin,
                                                                                   codeOrganizationList = cmp)))
            print('1/3 Ok Descarga datos Tabla Vehiculo')
            # Transformacion de datos
            df['DateId'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y%m%d')
            df['Date'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y-%m-%d')
            df['Organization'] = str(puerto)
            df['BusinessTime'] = df['BusinessTime'].dt.seconds
            df['DeadTime'] = df['DeadTime'].dt.seconds
            df['EmptyTime'] = df['EmptyTime'].dt.seconds
            df['EndTime'] = df.apply(lambda x: hhmmss(x['EndTime'], x['Date']), axis = 1)
            df['ProductionTime'] = df['ProductionTime'].dt.seconds
            df['StartTime'] = df.apply(lambda x: hhmmss(x['StartTime'], x['Date']), axis = 1)
            df['InsertDate'] = datetime.now()
            df = df[df['Date'].notna()]
            # Append de los datos
            print('2/3 Ok Transformacion Tabla Vehiculo')
            # Ordenamiento de columnas
            df = df[vehcolumnas]
            df_tabla_vehiculo.append(df)
            print("3/3 Ok Append datos Tabla Vehiculo")

            # Dataframe consolidado
            tabla_vehiculo = pd.concat(df_tabla_vehiculo)
        
        # Envio de los datos al DW
        tabla_vehiculo.to_sql(table2, schema = 'op', con = fn.cona, if_exists = 'append', index = False)
        tv_registros += len(tabla_vehiculo)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = d, cantidad_registros = tv_registros)
except Exception as e:
    print("Error:", e)
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))
# Refresh dataset power bi service ------------------------------------------------------------
if len(vehdias) != 0:
    file_phyton = os.getenv('PAT_PBI_REFRESH')
    datasetid = os.getenv('PBI_TABLAVEHICULO')
    command = f'python "{file_phyton}" "{datasetid}"'
    os.system(command)

# *********************************************************************************************
# Tabla Resumen Conductor Proceso de obtencion y carga de datos -------------------------------
# *********************************************************************************************
# Vector para eliminar las columnas innecesarias
dropcolumns = ['Duration4', 'Duration5', 'EndTime4', 'EndTime5', 'FromStopPoint4', 
               'FromStopPoint5', 'Line4', 'Line5', 'StartTime4', 'StartTime5', 'ToStopPoint4',
               'ToStopPoint5', 'VehicleInRoute4', 'VehicleInRoute5', 'VehicleService4',
               'VehicleService5']

# Vector de Ordenamiento de columnas
ordercolumns = ['Date', 'Organization', 'DriverCode', 'IdentificationDocument', 'DriverName',
                'IssueName', 'BusinessDistance', 'BusinessTrip',  'ProductionTime', 'StartTime1', 
                'EndTime1', 'Duration1', 'FromStopPoint1', 'ToStopPoint1', 'Line1', 
                'VehicleInRoute1', 'VehicleService1', 'StartTime2', 'EndTime2', 'Duration2', 
                'FromStopPoint2', 'ToStopPoint2', 'Line2', 'VehicleInRoute2', 'VehicleService2', 
                'StartTime3', 'EndTime3', 'Duration3', 'FromStopPoint3', 'ToStopPoint3', 'Line3', 
                'VehicleInRoute3', 'VehicleService3']

# Ejecucion de la consulta --------------------------------------------------------------------
try: 
    for d in credias:

        tr_registros = 0
        df_tabla_crew = []

        fecha_ini = d + 'T00:00:00'
        fecha_fin = d + 'T00:00:00'

        print(d, '--------------------')

        for puerto in puertos:
            print("Estoy en la organizacion: " + str(puerto))
            print("Con el puerto: " + str(puertos[puerto]))

            cmp = a_dict[puerto]

            url = puertos[puerto][1]

            # Cliente de conexion
            client = Client(url)
            # Verificacion de estado del servicio
            request = client.service.CanUseService()
            # Obtiene los datos y se almacena en un data frame
            df = pd.DataFrame(serialize_object(client.service.GetCrewServiceSummary(startDate = fecha_ini,
                                                                                    endDate = fecha_fin,
                                                                                    nameOrganizationList = cmp)))
            print('1/3 Ok Descarga datos Tabla Resumen Conductor')
            # Transformacion de datos
            df.drop(dropcolumns, inplace = True, axis = 1)
            df = df[ordercolumns]
            df['DateId'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y%m%d')
            df['Date'] = pd.to_datetime(df['Date'], format = '%d/%m/%Y').dt.strftime('%Y-%m-%d')
            df['Organization'] = str(puerto)
            df['DriverName'] = df['DriverName'].str.title()
            # Transformaciones de duracion
            df['ProductionTime'] = df['ProductionTime'].dt.seconds
            # Parte 1 de trabajo
            df['StartTime1'] = df.apply(lambda x: hhmmss(x['StartTime1'], x['Date']), axis = 1)
            df['EndTime1'] = df.apply(lambda x: hhmmss(x['EndTime1'], x['Date']), axis = 1)
            df['Duration1'] = df['Duration1'].dt.seconds
            # Se optimiza valores en celda
            df['StartTime1'] = np.where(df["Duration1"] == 0, np.nan, df['StartTime1'])
            df['EndTime1'] = np.where(df["Duration1"] == 0, np.nan, df['EndTime1'])
            # Parte 2 de trabajo
            df['StartTime2'] = df.apply(lambda x: hhmmss(x['StartTime2'], x['Date']), axis = 1)
            df['EndTime2'] = df.apply(lambda x: hhmmss(x['EndTime2'], x['Date']), axis = 1)
            df['Duration2'] = df['Duration2'].dt.seconds
            # Se optimiza valores en celda
            df['StartTime2'] = np.where(df["Duration2"] == 0, np.nan, df['StartTime2'])
            df['EndTime2'] = np.where(df["Duration2"] == 0, np.nan, df['EndTime2'])
            # Parte 3 de trabajo
            df['StartTime3'] = df.apply(lambda x: hhmmss(x['StartTime3'], x['Date']), axis = 1)
            df['EndTime3'] = df.apply(lambda x: hhmmss(x['EndTime3'], x['Date']), axis = 1)
            df['Duration3'] = df['Duration3'].dt.seconds
            # Se optimiza valores en celda
            df['StartTime3'] = np.where(df["Duration3"] == 0, np.nan, df['StartTime3'])
            df['EndTime3'] = np.where(df["Duration3"] == 0, np.nan, df['EndTime3'])
            df['InsertDate'] = datetime.now()
            # replace all zeros with NaN values
            df.replace(0, np.nan, inplace = True)
            df = df[df['Date'].notna()]
            # Append de los datos
            print('2/3 Ok Transformacion Tabla Resumen Conductor')
            df_tabla_crew.append(df)
            print("3/3 Ok Append datos Tabla Resumen Conductor")

            # Dataframe consolidado
            tabla_crew = pd.concat(df_tabla_crew)
        
        # Envio de los datos al DW
        tabla_crew.to_sql(table3, schema = 'op', con = fn.cona, if_exists = 'append', index = False)
        tr_registros += len(tabla_crew)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = d, cantidad_registros = tr_registros)
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    print("Error:", e)
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
     "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
