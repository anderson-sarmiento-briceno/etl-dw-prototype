#**********************************************************************************************
# @Nombre: Proceso de Carga de la información al DW para Terpel
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------              
import os                                 # Sistema
import subprocess                         # Ejecutar procesos de R
import pandas as pd                       # Manipulacion de datos
import xmlrpc.client                      # Conexión al API de Terpel
import Funciones as fn                    # Funciones ETL
import sys                                # Interprete python
from sqlalchemy import types              # Especificar el tipo de dato
from dotenv import load_dotenv            # Manejo archivo .env
from datetime import datetime, timedelta  # Manipulacion de fechas
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1060
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Terpel*"
table = 'FactConsumoTerpel'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Se trae la última fecha disponible en el DW para cada empresa -------------------------------
fechasdw = pd.read_sql_query('''
                            SELECT MAX("Fecha") as "UltimaFecha", "Empresa"
                            FROM ma."FactConsumoTerpel"
                            GROUP BY "Empresa"
                            ''', con = fn.enginea)

# Se realiza el diccionario de empresas para reemplazo en el df
codigosic_dict = {
    "ZMOIII": "Frt46502",
    "ZMOV": "Frt46528", 
    "OFICINAS": "None"
}

# Desarrollo ----------------------------------------------------------------------------------
# Función para realizar la consulta al API y unir las respuestas en un DataFrame --------------
def consultar_y_unir(url, start_date, codigosic, empresa):
    # Creando un objeto ServerProxy
    server = xmlrpc.client.ServerProxy(url)
    
    # Inicializar una lista para almacenar todas las respuestas
    all_records = []
    
    # Fecha actual
    end_date = datetime.now() - timedelta(days = 1)
    
    # Vector de fechas a descargar
    ctrrangofecha = (pd.date_range(start = start_date, end = end_date).strftime("%Y-%m-%d"))
    # Filtro de fechas finales
    ctrdias = [fecha for fecha in ctrrangofecha if fecha not in start_date]
    
    for i in ctrdias:
        # Calcular la fecha para la consulta actual
        consulta_fecha = pd.to_datetime(i)
        
        # Parámetros de la consulta
        params = [
            'medicion',
            284,
            'TP98',
            'telmetergy.webservices',
            'webserviceConsumosActual2',
            [
                {},
                {
                    'ano': consulta_fecha.year,
                    'mes': consulta_fecha.month,
                    'dia': consulta_fecha.day,
                    'codigosic': codigosic
                }
            ]
        ]
        
        # Llamada al método XML-RPC
        response = server.execute_kw(*params)
        
        # Imprimir la respuesta para entender su estructura
        print(f"Respuesta para {consulta_fecha.date()}: {response}")
        
        # Verificar si 'registros' está en la respuesta y manejar diferentes estructuras
        if 'registros' in response:
            for record in response['registros']:
                # Añadir las columnas 'Fecha' y 'Empresa' a cada registro
                record['Fecha'] = consulta_fecha
                record['Empresa'] = empresa
                all_records.append(record)
        else:
            print(f"No se encontró 'registros' en la respuesta para {consulta_fecha.date()}")
    
    # Convertir la lista de todos los registros en un DataFrame
    df_final = pd.DataFrame(all_records)
    
    return df_final

# URL del servidor XML-RPC - Asegúrate de que esta URL sea correcta y accesible
url = os.getenv('API_TERPEL')

df_final = pd.DataFrame()
try:
    # Iterar sobre las empresas y realizar las consultas necesarias
    for empresa, codigosic in codigosic_dict.items():
        # Obtener la última fecha de la base de datos para la empresa actual
        start_date = fechasdw.loc[fechasdw['Empresa'] == empresa, 'UltimaFecha'].values[0].strftime("%Y-%m-%d")

        print(f"Consultando para {empresa} desde {start_date} hasta hoy con codigosic {codigosic}")

        # Se ejecuta la funcion
        df_resultado = consultar_y_unir(url, start_date, codigosic, empresa)

        # Mostrar el DataFrame resultado
        print(df_resultado)

        # Se crea un dataframe con toda la informacion
        df_final = pd.concat([df_final, df_resultado], ignore_index = True)

    # Se filtran los datos de las horas para validar existencia
    if df_final.filter(like = 'hora').isnull().values.any():
        fn.registrar_actualizacion(engine = fn.enginegr, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datetime.now(), cantidad_registros = 0)
        raise Exception("Se encontró una columna con solo valores 0 o NaN. Deteniendo la ejecución.")

    if not df_final.empty:
        # Proceso de Transformacion df ----------------------------------------------------------------
        data = (
            df_final.query('funcion == "principal"')
            .melt(id_vars = ['Fecha', 'Empresa', 'canal'], value_vars = [f'hora{i}' for i in range(24)], var_name = 'Hora', value_name = 'Kwhr')
            .assign(Hora = lambda x: x['Hora'].str.extract('(\d+)').astype(int))  # Extrae el número de la hora y convierte a entero
            .rename(columns = {'canal': 'Variable'})  # Renombra la columna 'canal' a 'Variable'
            .assign(InsertDate = datetime.now())  # Añade la columna 'InsertDate' con la fecha y hora actual
        )

        # Se especifica el tipo de dato
        sql_types = {
            'Fecha': types.DATE,
            'Hora': types.INTEGER,
            'Kwhr': types.FLOAT,
            'InsertDate': types.TIMESTAMP
        }

        # Envío de datos al DW
        data.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

        # Se almacena los datos crudos en disco
        dataP = (data.drop(columns = ['InsertDate']))

        for fecha in dataP['Fecha'].dt.date.unique():
            # Filtrar el DataFrame para la fecha actual
            df_fecha = dataP[dataP['Fecha'].dt.date == fecha]

            # Formatear la fecha como cadena para usarla en el nombre del archivo
            fecha_str = fecha.strftime('%Y%m%d')

            # Si prefieres guardar como archivo Parquet, usa la siguiente línea:
            df_fecha.to_parquet(os.path.join(os.getenv('PAT_TERPEL_API'), f'{fecha_str}_ConsumoTerpel.parquet'), engine = 'pyarrow')

        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = data["Fecha"].max(), cantidad_registros = len(data))
        fn.update_process(id_process = IdProceso, engine = fn.enginea)

        # Mensaje Fin del Proceso ---------------------------------------------------------------------
        print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
             "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)

        # Desencadenar el proceso de para el calculo de la durabilidad de las llantas
        subprocess.run([sys.executable, r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\ETL-FactConsumoTerpel.py"])

    else:
        print("El DataFrame está vacío. No se insertaron datos.")  
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datetime.now(), cantidad_registros = 0)
        fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
