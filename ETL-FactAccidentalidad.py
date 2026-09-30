#**********************************************************************************************
# @Nombre: Historico de Accidentes
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                           # Manejo del sistema
import pandas as pd                                 # Manipulacion de datos
import numpy as np                                  # Manipulacion numerica
import requests                                     # Solicitud a API
import re                                           # Regex
import duckdb as db                                 # Bases de datos
import pyarrow.parquet as pq                        # Manipulacion de parquet
import Funciones as fn                              # Funciones ETL
from requests.auth import HTTPBasicAuth             # Credenciales API
from datetime import datetime, date                 # Manejo de fechas
from sqlalchemy import text                         # Conexion base de datos
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from glob import glob
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1240
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Accidentalidad*"
table = 'FactAccidentalidad'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Base de datos DuckDB en memoria
con = db.connect(':memory:')

try:
    #Desarrollo -----------------------------------------------------------------------------------
    src = os.path.join(os.getenv('PAT_GESTION_INFO'), '02 Actividad_Bus')
    ruta_parquet = os.path.join(os.getenv('PAT_NASPY'), r'02 Datos\11 actividad_bus')

    archivos = glob(f"{src}/*_actividad_bus_UF*.parquet")
    fechas = set(os.path.basename(f).split('_')[0] for f in archivos)

    for fecha in fechas:
        out = os.path.join(ruta_parquet, f"{fecha}_Actividad_Bus.parquet")
        if os.path.exists(out):
            continue
        files = [f for f in archivos if os.path.basename(f).startswith(fecha)]
        try:
            pd.concat([pd.read_parquet(f) for f in files], ignore_index = True).to_parquet(out, index = False)
            for f in files: os.remove(f)
            print(f"✓ {fecha} unificado y originales eliminados.")
        except Exception as e:
            print(f"⚠️ Error en {fecha}: {e}")

    # Define el DELETE como una consulta segura
    delete_query = text(''' DELETE FROM op."FactAccidentalidad"
                            WHERE "Fecha" >= CURRENT_DATE - INTERVAL '30 days' ''')

    # Ejecutar el DELETE
    fn.cona.execute(delete_query)

    # Ruta a los archivos .parquet y seleccion de fechas
    fecha_ini_descarga = '2022-04-01'
    today = date.today()

    # Seleccion de fechas del DW
    fechasactuales = (pd.read_sql_query('select DISTINCT "Fecha" FROM "op"."FactAccidentalidad"', con = fn.enginea)
                      .astype(str)
                      .Fecha
                      .to_list())

    # Rango de fechas desde el inicio de operacion
    rangofecha = (pd.date_range(start = fecha_ini_descarga, end = today).strftime("%Y-%m-%d"))

    # Seleccion de fechas pendientes
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
    url = f"{os.getenv('API_REPORT_RIGEL')}reportes/bitacoraAccidentalidad"
    headers = {"Authorization": f"Bearer {Token}",
               "Content-Type": "application/json"}

    # Captura de la tabla de novedades
    ApRigel = (pd.DataFrame(requests.get(url, headers = headers).json())
              .loc[lambda x: x["fecha"].isin(ctrdias)]
              .assign(hora = lambda x: pd.to_datetime(x['hora'], format = '%H:%M:%S'))
              .query("tipo_evento not in ['TM18 - Vandalismo', 'Seguridad y convivencia ']")
              .query("codigo_operador != 0"))

    # Leer todos los archivos .parquet disponibles
    archivos_parquet = [archivo for archivo in os.listdir(ruta_parquet) if archivo.endswith(".parquet")]

    # Extraer las fechas de los nombres de archivo
    archivos_con_fecha = [{"archivo": archivo,
                           "fecha": pd.to_datetime(archivo.split('_')[0], format = '%Y%m%d').strftime('%Y-%m-%d')}
                          for archivo in archivos_parquet]

    # Asignar la columna del archivo correspondiente a ApRigel
    ApRigel = (ApRigel.merge(pd.DataFrame(archivos_con_fecha), how = "left", left_on = "fecha", right_on = "fecha")
               .rename(columns = {"archivo": "parquet_correspondiente"})
               .dropna(subset = "parquet_correspondiente"))

    # Reges para reemplazar columna de sercones
    repl_dict = {re.compile(r'^(63).*'): 'ZMOIII',
                 re.compile(r'^(67).*'): 'ZMOV', 
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
                 re.compile(r'.*003.*'):'AA003', 
                 re.compile(r'TM01 - Accidente simple'): 1,
                 re.compile(r'TM02 - Accidente con lesionado'): 3,
                 re.compile(r'TM01 en Centro Logístico'): 1,
                 re.compile(r'TM16 - Accidente con fallecido'): 16, 
                 re.compile(r'FACTOR  HUMANO - CONDUCTOR GREEN'): 'Greenmovil',
                 re.compile(r'FACTOR HUMANO - CONDUCTOR TERCERO'): 'Tercero'} 

    # Agrupar por archivo Parquet correspondiente
    resumen = []
    for parquet_file in ApRigel['parquet_correspondiente'].unique():
        parquet_path = os.path.join(ruta_parquet, parquet_file)

        # Filtrar ApRigel solo para el archivo actual
        ApRigel_filtrado = ApRigel[ApRigel['parquet_correspondiente'] == parquet_file]

        # Leer el archivo Parquet correspondiente
        dfActBus = (pq.read_table(parquet_path, 
                                  columns = ["Fecha", "CodigoBus", "HoraReferencia", "Descripcion"],
                                  filters = [("CodigoBus", "in", ApRigel_filtrado["codigo"].unique().tolist())])
                    .to_pandas())

        # Registro de tablas en DuckDB
        con.register("Accidentes", ApRigel_filtrado)
        con.register("Act_Bus", dfActBus)

        # Query de ASOF JOIN DuckDB
        query = """ SELECT ac.fecha, ac.hora, ac.ruta, ac.direccion, ac.placa, ac.codigo, 
                           ac.codigo_operador, ac.caso_tm, ac.juridica, ac.identificacion, 
                           ac.tipo_evento, ac.clasificacion, ac.causalidad, ac.hipotesis, 
                           ac.estado_conciliacion, ac.valor_conciliado, ac.tipo_vehiculo_tercero, 
                           ac.empresa_operadora, ac.inmovilizado, ac.costos_directos, 
                           ac.costos_indirectos, ab.Descripcion AS Parada
                    FROM Accidentes ac
                    ASOF LEFT JOIN Act_Bus ab
                        ON ac.codigo = ab.CodigoBus
                        AND ac.hora >= ab.HoraReferencia; """
        AccidMerge = con.execute(query).fetchdf()

        # Merge y estandarizacion de la información
        dfAccid = (clean_columns(AccidMerge
                   .assign(fecha = lambda x: pd.to_datetime(x['fecha'], errors = 'coerce'),
                           empresa = lambda x: x["codigo_operador"].astype(str).replace(repl_dict, regex = True),
                           caso_tm = lambda x: x['caso_tm'].replace(r'^\s*$', False, regex = True).replace({'SI': True, 'NO': False}),
                           ruta = lambda x: x["ruta"].replace(repl_dict, regex = True),
                           direccion = lambda x: x['direccion'].replace(r'^\s*$', 'Sin Direccion', regex = True).fillna('Sin Direccion'),
                           empresa_operadora = lambda x: x['empresa_operadora'].replace(['', None], 'No Aplica').fillna('No Aplica').str.title(),
                           responsabilidad = lambda x: x["causalidad"].replace(repl_dict, regex = True).str.capitalize(),
                           hipotesis = lambda x: x['hipotesis'].str.slice(0, 3).replace('', pd.NA).astype(pd.Int64Dtype()),
                           puntos_ISV = lambda x: x["tipo_evento"].replace(repl_dict, regex = True),
                           tipo_evento = lambda x: np.select([x['tipo_evento'] == 'TM01 - Accidente simple', x['tipo_evento'] == 'TM02 - Accidente con lesionado', x['tipo_evento'] == 'TM01 en Centro Logístico', x['tipo_evento'] == 'TM16 - Accidente con fallecido'], ['Simple', 'Lesionados', 'Simple', 'Victima Mortal'], default = 0),
                           juridica = lambda x: np.select([x['tipo_evento'] == 'Lesionados', x['tipo_evento'] == 'Victima Mortal'], ['Asiste Juridica', 'Asiste Juridica'], default = 'No Asiste'),
                           identificacion = lambda x: x['identificacion'].replace('', pd.NA).astype(pd.Int64Dtype()),
                           clasificacion = lambda x: x['clasificacion'].str.title(),
                           causalidad = lambda x: x['causalidad'].str.title(),
                           estado_conciliacion = lambda x: x['estado_conciliacion'].str.title(),
                           tipo_vehiculo_tercero = lambda x: x['tipo_vehiculo_tercero'].str.title(),
                           inmovilizado = lambda x: x['inmovilizado'].replace(r'^\s*$', False, regex=True).replace({'SI': True, 'NO': False}),
                           InsertDate = datetime.now()), case = 'pascal')
                   .loc[:, ["Fecha", "Hora", "Ruta", "Direccion", "Placa", "Codigo", "CodigoOperador",
                            "CasoTm", "Juridica", "Identificacion", "TipoEvento", "Clasificacion", 
                            "Causalidad", "Hipotesis", "EstadoConciliacion", "ValorConciliado", 
                            "TipoVehiculoTercero", "EmpresaOperadora", "Inmovilizado", "CostosDirectos", 
                            "CostosIndirectos", "Empresa", "PuntosIsv", "Responsabilidad", "Parada", "InsertDate"]])

        # Envio de los datos al DW
        sql_types = {'Fecha': types.DATE, 'Hora': types.TIME, 'CodigoOperador': types.INTEGER,
                     'Identificacion': types.INTEGER, 'CostosDirectos': types.FLOAT,
                     'CostosIndirectos': types.FLOAT, 'PuntosIsv': types.INTEGER, 'InsertDate': types.TIMESTAMP}

        dfAccid.to_sql(table, schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

        # Resumen para este archivo
        resgis = len(dfAccid)
        max_fecha = pd.to_datetime(parquet_file[:8], format = '%Y%m%d', errors = 'coerce')
        resumen.append({"parquet_file": parquet_file, "records_inserted": resgis, "max_fecha": max_fecha})

    # Cierra DuckDB y crea DataFrame de resumen
    con.close()
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
      