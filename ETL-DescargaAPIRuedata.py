# **********************************************************************************************
# @Nombre: Ruedata Api
# @Autor: Anderson Sarmiento
# **********************************************************************************************

# Importar librerias ---------------------------------------------------------------------------
import os                                         # Sistema
import requests                                   # Notificacion a slack
import numpy as np                                # Manipulacion numerica
import pandas as pd                               # Manipulacion de datos
import ast                                        # Manipulacion de arbol de decisión
import json                                       # Manejo de datos en Json
import Funciones as fn                            # Funciones ETL
import subprocess                                 # Controlador de scripts
import sys                                        # Interprete python
from sqlalchemy import types                      # Manejo de tipos de campos en db
from skimpy import clean_columns                  # Cambiar el tipo de nombre de columnas
from datetime import datetime                     # Manipulacion de fechas
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1090
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga API Ruedata*"
table1 = 'FactTireMovements'
table2 = 'FactTireWorks'
table3 = 'FactTireWaste'
table4 = 'FactTireAlignments'
table5 = 'FactTireGeneral'
table6 = 'FactTireRenewal'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Urls para la descarga de los datos ----------------------------------------------------------
def construir_url(endpoint, page):
    return f"{os.getenv('API_URL_RDATA')}{endpoint}?page={page}&size=3000"

# Obtener y transformar los datos -------------------------------------------------------------
try:
    # Datos de Movimientos de llantas -------------------------------------------------------------
    rename_dict = {"Nro. al calor": "codigo","Marca": "marca_llanta","Diseno": "modelo_llanta","Dimension": "dimension_llanta","Vida": "vida","Estado": "estado","Banda renovado": "banda_reencauche","Dimension renovado": "dimension_reencauche","Prof. Original diseno": "prof_original_modelo","Prof. Minima diseno": "prof_minima_modelo","Prof. Original banda": "prof_original_banda","Prof. Minima banda": "prof_minina_banda","Ult. Prof. Exterior": "ult_prof_exterior","Ult. Prof. Centro": "ult_prof_centro","Ult. Prof. Interior": "ult_prof_interior","Prof. Mas Baja": "prof_mas_baja","Situacion": "ubicacion","Tipo Inspeccion": "tipo_inspeccion","Placa": "placa_vehiculo","ID/SAP": "numero_vehiculo","Posicion inicial": "posicion_montaje","Tipo eje": "tipo_eje","Precio neumatico original": "precio_llanta_original","Precio neumatico actual": "precio_llanta_actual","Proveedor": "distribuidor","Fecha creacion": "fecha_creacion_llanta","Usuario creacion neumatico": "usuario_creacion_llanta","Fecha creacion movimiento": "fecha_creacion_movimiento","Usuario creacion movimiento": "usuario_creacion_movimiento","Fecha ultima actualizacion": "fecha_actualizacion_movimiento","Usuario actualizacion movimiento": "usuario_actualizacion_movimiento","Fecha ultima inspeccion": "fecha_ultima_inspeccion","Tipo novedad": "tipo_novedad","Motivo novedad": "motivo_novedad","Causa novedad": "causa_novedad","Fecha novedad": "fecha_novedad","DOT": "dot","Medicion recorrida inspeccion": "km_recorrido_inspeccion","Medicion recorrida vida": "km_recorrido_acumulado_vida","Medicion recorrida total": "km_recorrido_acumulado_total","Mm. gastados inspeccion": "mm_gastados_inspeccion","Mm. gastados vida": "mm_gastados_acumulados_vida","Mm. gastados total": "mm_gastados_acumulados_total","Porcentaje desgaste vida": "porcentaje_desgate","Region vida": "region_desgate","Cpk inspeccion": "cpk_inspeccion","Cpk vida": "cpk_acumulado_vida","Cpk total": "cpk_acumulado_total","Km/mm inspeccion": "km/mm_inspeccion","Km/mm Vida": "km/mm_acumulado_vida","Km/mm total": "km/mm_acumulado_total","Proyeccion Kilometros por Recorrer": "proyeccion_km_por_recorrer","Proyeccion Total Kilometros": "proyeccion_total_km","Proyeccion Total Simulada": "proyeccion_total_simulada","Proyeccion Cpk Total": "proyeccion_cpk_total","Proyeccion Cpk Total Simulada": "proyeccion_cpk_total_simulada","Costo Mm. inspeccion": "costo_mm_inspeccion","Costo Mm. Vida": "costo_mm_acumulado_vida","Precio Mm. total": "costo_mm_acumulado_total","Ciudad": "ciudad","Centro de costo": "centro_costo","Grupo vehiculo": "grupo_vehiculo","Inspeccion inyeccion": "inspeccion_inyeccion","Nro. Soporte": "numero_orden", "Ubicacion":"status"}
    column_order = ["codigo", "marca_llanta", "modelo_llanta", "dimension_llanta", "vida", "estado", "banda_reencauche", "dimension_reencauche", "prof_original_modelo", "prof_minima_modelo", "prof_original_banda", "prof_minina_banda", "ult_prof_exterior", "ult_prof_centro", "ult_prof_interior", "prof_mas_baja", "ubicacion", "tipo_inspeccion", "placa_vehiculo", "posicion_montaje", "tipo_eje", "precio_llanta_original", "precio_llanta_actual", "distribuidor", "fecha_creacion_movimiento", "usuario_creacion_movimiento", "fecha_actualizacion_movimiento", "usuario_actualizacion_movimiento", "fecha_ultima_inspeccion", "tipo_novedad", "motivo_novedad", "causa_novedad", "fecha_novedad", "km_recorrido_inspeccion", "km_recorrido_acumulado_vida", "km_recorrido_acumulado_total", "mm_gastados_inspeccion", "mm_gastados_acumulados_vida", "mm_gastados_acumulados_total", "porcentaje_desgate", "region_desgate", "cpk_inspeccion", "cpk_acumulado_vida", "cpk_acumulado_total", "km/mm_inspeccion", "km/mm_acumulado_vida", "km/mm_acumulado_total", "proyeccion_km_por_recorrer", "proyeccion_total_km", "proyeccion_total_simulada", "proyeccion_cpk_total", "proyeccion_cpk_total_simulada", "costo_mm_inspeccion", "costo_mm_acumulado_total", "status", "numero_orden", "Posicion final"]

    df_movimientos = []
    print('Tabla de Movimientos')

    # Extraccion de datos para movimientos
    headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))

    page = 1
    while True:
        print(f'Downloading page: {page}')

        response = requests.get(construir_url('movements', page), headers = headers)
        response.raise_for_status()

        json_data = response.json()
        items = json_data.get('items', [])
        total_pages = json_data.get('pages', None)

        if not items:
            break

        df_movimientos.append(pd.DataFrame(items))

        # Corte correcto
        if total_pages and page >= total_pages:
            break

        page += 1


    # Estandarizacion de la informacion
    datatiremovem = (clean_columns(pd.concat(df_movimientos)
                                   .rename(columns = rename_dict)
                                   .reindex(columns = column_order), case = 'pascal')
                     .assign(InsertDate = datetime.now(),
                              FechaUltimaInspeccion = lambda df: pd.to_datetime(df['FechaUltimaInspeccion'], format = '%Y-%m-%d %H:%M:%S', yearfirst = True).dt.tz_localize(None),
                              FechaCreacionMovimiento = lambda df: pd.to_datetime(df['FechaCreacionMovimiento'], format = '%Y-%m-%dT%H:%M:%S', yearfirst = True).dt.tz_localize(None),
                              FechaActualizacionMovimiento = lambda df: pd.to_datetime(df['FechaActualizacionMovimiento'], format = '%Y-%m-%d %H:%M:%S', yearfirst = True).dt.tz_localize(None),
                              FechaNovedad = lambda df: pd.to_datetime(df['FechaNovedad'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              IdDateInspeccion = lambda df: df['FechaUltimaInspeccion'].dt.strftime('%Y%m%d'),
                              KmRecorridoInspeccion=lambda df: df['KmRecorridoInspeccion'].fillna(0),
                              MmGastadosInspeccion=lambda df: df['MmGastadosInspeccion'].fillna(0),
                              PosicionMontaje = lambda df: df['PosicionMontaje'].where(~((df['TipoInspeccion'].isin(['Montaje', 'Inspección']) & df['PosicionMontaje'].isna()) | (df['TipoInspeccion'] == 'Rotación Vehículo')), other = df['PosicionFinal']))
                     .drop(columns = 'PosicionFinal')
                     .pipe(lambda df: df.reindex(columns = ['IdDateInspeccion'] + [col for col in df.columns if col != 'IdDateInspeccion'])))

    # Envio de los datos al DW
    sql_types = {
        'IdDateInspeccion': types.INTEGER,
        'Vida': types.INTEGER,
        'ProfMinimaModelo': types.INTEGER,
        'PrecioLlantaOriginal': types.INTEGER,
        'PosicionMontaje': types.INTEGER,
        'FechaUltimaInspeccion': types.TIMESTAMP,
        'FechaCreacionMovimiento': types.TIMESTAMP,
        'FechaActualizacionMovimiento': types.TIMESTAMP,
        'FechaNovedad': types.DATE,
        'KmRecorridoInspeccion': types.INTEGER,
        'KmRecorridoAcumuladoVida': types.INTEGER,
        'KmRecorridoAcumuladoTotal': types.INTEGER,
        'InsertDate': types.TIMESTAMP
    }

    datatiremovem.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = datatiremovem["IdDateInspeccion"].max(), cantidad_registros = len(datatiremovem))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))
try:
    # Datos de TireWorks -------------------------------------------------------------------------
    rename_dict = {"Numero al calor": "codigo","Marca": "marca_llantas","Diseno": "modelo_llantas","Dimension": "dimension_llantas","Vida": "vida","Banda renovado": "banda_reencauche","Dimension renovado": "dimension_reencauche","Placa": "placa_vehiculo","ID/ECO/SAP": "no_vehiculo","Posicion": "posicion","Tipo Trabajo": "tipo","Precio": "costo","Fecha Trabajo": "fecha","Medicion": "medicion","Prof. Int": "ult_prof_interior","Prof. Centro": "ult_prof_centro","Prof. Ext": "ult_prof_centro_exterior","Tecnico": "usuario","Ciudad": "ciudad","Centro de Costo": "centro_costo","Fornecedor": "grupo_vehiculo"}
    column_order = ["codigo", "marca_llantas", "modelo_llantas", "dimension_llantas", "vida", "banda_reencauche", "dimension_reencauche", "placa_vehiculo", "posicion", "tipo", "costo", "fecha", "medicion", "ult_prof_interior", "ult_prof_centro", "ult_prof_centro_exterior"]

    df_works = []
    print('Tabla de Trabajos')

    # Extraccion de datos para trabajos
    for i in range(1, 50):
        print(f'Downloading page: {str(i)}, Rows: {"{:,.0f}".format(3000 * i)}')
        data = pd.DataFrame(json.loads(requests.get(construir_url('tire_works', i), headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))).text).get('items'))
        if len(data) < 3001 and len(data) > 0:
            df_works.append(data)
        else: 
            break
        
    # Estandarizacion de la informacion
    datatireworks = (clean_columns(pd.concat(df_works)
                                   .rename(columns = rename_dict)
                                   .reindex(columns = column_order), case = 'pascal')
                     .assign(InsertDate = datetime.now(),
                              Fecha = lambda df: pd.to_datetime(df['Fecha'], format = '%Y-%m-%d').dt.tz_localize(None),
                              IdFecha = lambda df: df['Fecha'].dt.strftime('%Y%m%d'),
                              Costo = lambda df: df['Costo'].replace(0, np.nan))
                      .pipe(lambda df: df.reindex(columns = ['IdFecha'] + [col for col in df.columns if col != 'IdFecha'])))

    # Envio de los datos al DW
    sql_types = {'Fecha': types.TIMESTAMP, 'InsertDate': types.TIMESTAMP, 'Posicion': types.INTEGER, 'Vida': types.INTEGER}

    datatireworks.to_sql(table2, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = datatireworks["IdFecha"].max(), cantidad_registros = len(datatireworks))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

try:
    # Datos de desechos de llantas ---------------------------------------------------------------
    rename_dict = {"Nro. al calor": "congelados_llantas_codigo","Vida": "vida","Marca": "marca","Diseno": "modelo","Dimension": "dimension","Banda renovado": "banda","Marca renovado": "marca_reen","Dimension renovado": "dimension_reencauche","causa": "causas","motivo": "motivo","seccion": "seccion","ligado a": "ligado_a","Planta Siniestro": "planta_siniestro","cost_remanente": "mm_costo","mm_gastados": "mm_gastados","Prof. Minima diseno": "prof_mas_baja","Medicion Recorrida": "medicion_recorrida","Medicion Total Recorrida": "km_total_recorrido","Medicion total vehiculo": "medicion_total_vehiculo","profundity_int": "url_prof_interior","profundity_center": "url_prof_centro","profundity_ext": "url_prof_centro_exterior","ID/ECO/SAP": "numero_vehiculo","Placa": "placa_vehiculo","Centro de Costo": "centro_costo","Fecha de Desecho": "fecha_descarte","Fecha Desmonte": "fecha_desmonte","Tecnico": "tecnico","Nro. Soporte": "numero_orden","Ultima Posicion": "posicion_llanta"}
    column_order = ["congelados_llantas_codigo", "vida", "marca", "modelo", "dimension", "banda", "marca_reen", "dimension_reencauche", "causas", "motivo", "seccion", "ligado_a", "planta_siniestro", "mm_costo", "mm_gastados", "prof_mas_baja", "medicion_recorrida", "km_total_recorrido", "medicion_total_vehiculo", "url_prof_interior", "url_prof_centro", "url_prof_centro_exterior",  "placa_vehiculo", "fecha_descarte", "fecha_desmonte", "numero_orden", "posicion_llanta", "cost_remanente_util", "mm_cost_useful"]

    df_waste = []
    print('Tabla de Desechos')

    # Extraccion de datos para desechos
    for i in range(1, 50):
        print(f'Downloading page: {str(i)}, Rows: {"{:,.0f}".format(3000 * i)}')
        data = pd.DataFrame(json.loads(requests.get(construir_url('waste', i), headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))).text).get('items'))
        if len(data) < 3001 and len(data) > 0:
            df_waste.append(data)
        else: 
            break
        
    # Estandarizacion de la informacion
    datawaste = (clean_columns(pd.concat(df_waste)
                                   .rename(columns = rename_dict)
                                   .reindex(columns = column_order), case = 'pascal')
                     .assign(InsertDate = datetime.now(),
                              FechaDescarte = lambda df: pd.to_datetime(df['FechaDescarte'], format = '%Y-%m-%d').dt.tz_localize(None),
                              FechaDesmonte = lambda df: pd.to_datetime(df['FechaDesmonte'], format = '%Y-%m-%d').dt.tz_localize(None),
                              IdFechaDescarte = lambda df: df['FechaDescarte'].dt.strftime('%Y%m%d'),
                              Motivo = lambda df: df['Motivo'].str.title(),
                              Causas = lambda df: df['Causas'].str.title())
                      .pipe(lambda df: df.reindex(columns = ['IdFechaDescarte'] + [col for col in df.columns if col != 'IdFechaDescarte'])))

    # Envio de los datos al DW
    sql_types = {'FechaDescarte': types.TIMESTAMP, 'FechaDesmonte': types.TIMESTAMP,
                 'InsertDate': types.TIMESTAMP, 'IdFechaDescarte': types.INTEGER,
                 'Vida': types.INTEGER, 'ProfMinimaModelo': types.INTEGER,
                 'MedicionRecorrida': types.INTEGER, 'KmTotalRecorrido': types.INTEGER,
                 'KmTotalVehiculo': types.INTEGER, 'MedicionTotalVehiculo': types.INTEGER}

    datawaste.to_sql(table3, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = datawaste["IdFechaDescarte"].max(), cantidad_registros = len(datawaste))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))
try:
    # Datos Alineacion de llantas -----------------------------------------------------------------
    rename_dict = {'Placa': 'placa','ID/ECO/SAP': 'nro_vehiculo','Tipo Trabajo': 'tipo_trabajo','Cantidad': 'cantidad','Medicion': 'kilometraje','Precio': 'costo','Precio Total': 'costo_total','Fecha de Trabajo': 'fecha','Medicion para Proximo Trabajo': 'kms_prox_alineacion','Odometro Para Proximo Trabajo': 'odometro_prox_alineacion','Fecha Proximo Trabajo': 'fecha_prox_alineacion','Dias Proximo Trabajo': 'dias_prox_alineacion','Usuario': 'usuario','Ciudad': 'ciudad','Centro de Costo': 'centro_costo','Nro. Soporte': 'nro_orden'}
    column_order = ["placa", "tipo_trabajo", "cantidad", "kilometraje", "fecha", "kms_prox_alineacion", "odometro_prox_alineacion","fecha_prox_alineacion", "dias_prox_alineacion", "nro_orden"]

    df_aling = []
    print('Tabla de Alineaciones')

    # Extraccion de datos para desechos
    for i in range(1, 50):
        print(f'Downloading page: {str(i)}, Rows: {"{:,.0f}".format(3000 * i)}')
        data = pd.DataFrame(json.loads(requests.get(construir_url('alignments', i), headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))).text).get('items'))
        if len(data) < 3001 and len(data) > 0:
            df_aling.append(data)
        else: 
            break

    # Estandarizacion de la informacion
    dataalign = (clean_columns(pd.concat(df_aling)
                                   .rename(columns = rename_dict)
                                   .reindex(columns = column_order), case = 'pascal')
                 .assign(InsertDate = datetime.now(),
                              Fecha = lambda df: pd.to_datetime(df['Fecha'], format = '%Y-%m-%d').dt.strftime('%Y-%m-%d'),
                              FechaProxAlineacion = lambda df: pd.to_datetime(df['FechaProxAlineacion'], format = '%Y-%m-%d'))
                      .pipe(lambda df: df.reindex(columns = ['Fecha'] + [col for col in df.columns if col != 'Fecha'])))

    # Envio de los datos al DW
    sql_types = {'Fecha': types.DATE,
                 'InsertDate': types.TIMESTAMP, 'Kilometraje': types.INTEGER,
                 'KmsProxAlineacion': types.INTEGER, 'OdometroProxAlineacion': types.INTEGER,
                 'FechaProxAlineacion': types.DATE, 'DiasProxAlineacion': types.INTEGER,
                 'NroOrden': types.INTEGER}

    dataalign.to_sql('FactTireAlignments', schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), max_fecha_tabla = dataalign["Fecha"].max(), cantidad_registros = len(dataalign))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), observacion = str(e))
    
try:
    # Datos General de llantas --------------------------------------------------------------------
    rename_dict = {"Nro. al calor": "codigo","Marca": "marca_llanta","Diseno": "modelo_llanta","Dimension": "dimension_llanta","Vida": "vida","Estado": "estado","Banda renovado": "banda_reencauche","Dimension renovado": "dimension_reencauche","Prof. Original diseno": "prof_original_modelo","Prof. Minima diseno": "prof_minima_modelo","Prof. Original banda": "prof_original_banda","Prof. Minima banda": "prof_minina_banda","Ult. Prof. Exterior": "ult_prof_exterior","Ult. Prof. Centro": "ult_prof_centro","Ult. Prof. Interior": "ult_prof_interior","Prof. Mas Baja": "prof_mas_baja","Situacion": "situacion","Ubicacion": "ubicacion","Placa": "placa_vehiculo","ID/SAP": "numero_vehiculo","Tipologia": "tipologia","Posicion montaje": "posicion_montaje","Tipo eje": "tipo_eje","Precio neumatico original": "precio_llanta_original","Precio neumatico actual": "precio_llanta_actual","Proveedor": "distribuidor","Fecha creacion": "fecha_creacion","Usuario creacion neumatico": "usuario_creacion_llanta","Fecha ultima inspeccion": "fecha_ultima_inspeccion","DOT": "dot","Fecha desecho": "fecha_desecho","Fecha ultima montaje": "fecha_ultimo_montaje","Medicion montaje": "km_montaje","Historico Vidas": "historico_vidas","Medicion recorrida vida": "km_recorrido_vida","Mm. gastados vida": "mm_gastados_vida","Porcentaje desgaste vida": "porcentaje_desgaste_vida","Precio Mm. Vida": "costo_mm_vida","Cpk vida": "cpk_vida","Medicion/mm Vida": "km_mm_vida","Precio Mm. Historico": "costo_mm_historico","Cpk Historico": "cpk_historico","Region vida": "region_vida","Medicion recorrida total": "km_recorrido_total","Precio Mm. total": "costo_mm_total","Cpk total": "cpk_total","Medicion/mm total": "km_mm_total","Ciudad": "ciudad","Centro de costo": "centro_costo","Estado vehiculo": "estado_vehiculo","Fecha ultima actualizacion": "fecha_ultima_actualizacion","Usuario actualizacion": "usuario_actualizacion","Nro. Soporte": "nro_orden"}
    column_order = ["codigo", "marca_llanta", "modelo_llanta", "dimension_llanta", "vida", "estado", "banda_reencauche", "dimension_reencauche", "prof_original_modelo", "prof_minima_modelo", "prof_original_banda", "prof_minina_banda", "ult_prof_exterior", "ult_prof_centro", "ult_prof_interior", "prof_mas_baja", "situacion", "ubicacion", "placa_vehiculo", "posicion_montaje", "tipo_eje", "precio_llanta_original", "precio_llanta_actual", "distribuidor", "fecha_creacion",  "fecha_ultima_inspeccion", "fecha_desecho", "fecha_ultimo_montaje", "km_montaje", "historico_vidas", "km_recorrido_vida", "mm_gastados_vida", "porcentaje_desgaste_vida", "costo_mm_vida", "cpk_vida", "km_mm_vida", "costo_mm_historico", "cpk_historico", "region_vida", "km_recorrido_total", "costo_mm_total", "cpk_total", "km_mm_total", "fecha_ultima_actualizacion", "usuario_actualizacion", "nro_orden"]

    df_gral = []
    print('Tabla de General')

    # Extraccion de datos para desechos
    for i in range(1, 50):
        print(f'Downloading page: {str(i)}, Rows: {"{:,.0f}".format(3000 * i)}')
        data = pd.DataFrame(json.loads(requests.get(construir_url('general_query', i), headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))).text).get('items'))
        if len(data) < 3001 and len(data) > 0:
            df_gral.append(data)
        else: 
            break

    # Estandarizacion de la informacion
    datagral = (clean_columns(pd.concat(df_gral)
                                   .rename(columns = rename_dict)
                                   .reindex(columns = column_order), case = 'pascal')
                .assign(InsertDate = datetime.now(),
                              FechaCreacion = lambda df: pd.to_datetime(df['FechaCreacion'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              FechaUltimaInspeccion = lambda df: pd.to_datetime(df['FechaUltimaInspeccion'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              FechaDesecho = lambda df: pd.to_datetime(df['FechaDesecho'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              FechaUltimoMontaje = lambda df: pd.to_datetime(df['FechaUltimoMontaje'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              FechaUltimaActualizacion = lambda df: pd.to_datetime(df['FechaUltimaActualizacion'], format = '%Y-%m-%d', yearfirst = True).dt.tz_localize(None),
                              ProfMinimaModelo = lambda df: df['ProfMinimaModelo'].astype(float),
                              CostoMmHistorico = lambda df: pd.to_numeric(df['CostoMmHistorico'], errors='coerce'),
                              HistoricoVidas = lambda df: df['HistoricoVidas'].apply(lambda x: max(map(int, x.split(',')))))
                      .pipe(lambda df: df.reindex(columns = ['FechaUltimaActualizacion'] + [col for col in df.columns if col != 'FechaUltimaActualizacion'])))


    # Envio de los datos al DW
    sql_types = {'Vida': types.INTEGER, 'PosicionMontaje': types.INTEGER, 'PrecioLlantaOriginal': types.INTEGER,
                 'PrecioLlantaActual': types.INTEGER, 'FechaCreacion': types.DATE, 'FechaUltimaInspeccion': types.DATE,
                 'FechaDesecho': types.DATE, 'FechaUltimoMontaje': types.DATE, 'KmMontaje': types.INTEGER,
                 'HistoricoVidas': types.INTEGER, 'KmRecorridoVida': types.INTEGER, 'CostoMmVida': types.INTEGER,
                 'CostoMmHistorico': types.INTEGER, 'KmMmHistorico': types.INTEGER, 'KmRecorridoTotal': types.INTEGER,
                 'CostoMmTotal': types.INTEGER, 'KmMmTotal': types.INTEGER, 'FechaUltimaActualizacion': types.DATE,
                 'NroOrden': types.TEXT, 'InsertDate': types.TIMESTAMP}

    datagral.to_sql(table5, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), max_fecha_tabla = datagral["FechaUltimaInspeccion"].max(), cantidad_registros = len(datagral))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), observacion = str(e))

try:
    # Datos Historico Renovado de llantas ---------------------------------------------------------
    column_order = ["Mes", "Renovado", "Total", "Porcentaje renovado", "Aumento porcentaje"]

    df_hist = []
    print('Tabla de Historico Renovado')

    # Extraccion de datos para Historico de llantas
    for i in range(1, 50):
        print(f'Downloading page: {str(i)}, Rows: {"{:,.0f}".format(3000 * i)}')
        data = pd.DataFrame(json.loads(requests.get(construir_url('tire_historical_renewal', i), headers = ast.literal_eval(os.getenv('API_PASS_RDATA'))).text).get('items'))
        if len(data) < 3001 and len(data) > 0:
            df_hist.append(data)
        else: 
            break

    # Estandarizacion de la informacion
    datahist = (clean_columns(pd.concat(df_hist)
                                   .reindex(columns = column_order), case = 'pascal')
                .assign(InsertDate = datetime.now(),
                              FirstDayOfMonth = lambda df: pd.to_datetime(df['Mes'], format = '%Y-%m-%d', yearfirst = True))
                      .pipe(lambda df: df.reindex(columns = ['FirstDayOfMonth'] + [col for col in df.columns if col != 'FirstDayOfMonth'])))

    sql_types = {'FirstDayOfMonth': types.DATE, 'Mes': types.TEXT, 'Renovado': types.INTEGER,
                 'Total': types.INTEGER, 'PorcentajeRenovado': types.FLOAT, 
                 'AumentoPorcentaje': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    datahist.to_sql(table6, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), max_fecha_tabla = datahist["FirstDayOfMonth"].max(), cantidad_registros = len(datahist))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), observacion = str(e))

# Desencadenar el proceso de para el calculo de la durabilidad de las llantas
subprocess.run([sys.executable, r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\ETL-FactTireDurability.py"])

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_LLANTAS')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
