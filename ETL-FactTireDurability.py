#**********************************************************************************************
# @Nombre: 
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                                           # Manejo del sistema
import pandas as pd                                 # Manipulacion de datos
import numpy as np                                  # Manipulacion numerica
import Funciones as fn                              # Funciones ETL
from datetime import datetime                       # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1090
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga API Ruedata*"
table = 'FactTireDurability'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

region = ["Nueva", "3/4 Vida", "1/2 Vida", "1/4 Vida", "Programación", "Cambio"]
tipoeje = ["Direccional", "Mixta", "Traccion"]

try:
  # Codigos de llantas desechadas
  descarte = pd.read_sql_query(' SELECT "CongeladosLlantasCodigo" AS "Codigo" FROM ma."FactTireWaste" ', con = fn.enginea)

  # Registros de llantas
  query = ''' SELECT "Codigo", "DimensionLlanta", "Estado", CASE WHEN "TipoEje" = 'Tracción' 
                                                              THEN 'Traccion' 
                                                              ELSE "TipoEje" 
                                                            END AS "TipoEje",
                     "FechaUltimaInspeccion" AS "Fecha", "TipoInspeccion",
                     "RegionDesgate", "Ubicacion", "KmRecorridoAcumuladoVida" AS "KmLife",
                     "MmGastadosAcumuladosVida" AS "MmLife", "KmRecorridoAcumuladoTotal" AS "KmAcum", 
                     "MmGastadosAcumuladosTotal" AS "MmAcum"
              FROM ma."FactTireMovements"
              WHERE "Vida" = 0
                AND "TipoEje" IS NOT NULL
                AND LEFT("Codigo", 1) <> 'B' '''

  movimientos = (pd.read_sql_query(query, con = fn.enginea)
                 .merge(descarte, on = "Codigo", how = "left", indicator = True)
                 .query("_merge == 'left_only'")
                 .drop(columns = "_merge")
                 .sort_values(['Codigo', 'Fecha'], ascending = False)
                 .assign(TipoEjeAdj = lambda x: (x.groupby('Codigo')['TipoEje']
                                                 .transform(lambda s: 'Mixta' if s.nunique() == 2 else s.iloc[0])),
                         RegionDesgate = lambda x: pd.Categorical(x['RegionDesgate'], categories = region, ordered = True),
                         TipoEjeAdj_cat = lambda x: pd.Categorical(x['TipoEjeAdj'], categories = tipoeje, ordered = True),
                         Val = lambda x: (x.groupby('Codigo')['TipoEje'].apply(lambda s: (s != s.shift()).astype(int))
                                          .reset_index(level = 0, drop = True)))
                 .assign(Val = lambda x: x['Val'].fillna(0))
                 .sort_values(['Codigo', 'Fecha'])
                 .assign(Cambios = lambda x: x.groupby('Codigo')['Val'].transform('sum'),
                         Acum = lambda x: x.groupby('Codigo')['Val'].cumsum())
                 .reset_index(drop = True))

  # Se analiza la cantidad de kms que recorrido la llanta en cada eje
  cambios = (movimientos.query("Val == 1")
              .loc[:, ['Codigo', 'TipoEje', 'Fecha', 'KmAcum']]
              .sort_values(['Codigo', 'Fecha'], ascending = False)
              .assign(KmReco = lambda x: (x['KmAcum'] - x.groupby('Codigo')['KmAcum'].shift(-1)))
              .assign(KmReco = lambda x: x['KmReco'].fillna(x['KmAcum']))
              .loc[:, ['Codigo', 'TipoEje', 'KmReco']]
              .loc[lambda x: x['KmReco'].notna() & (x['KmReco'] != 0)]
              .groupby(['Codigo', 'TipoEje'], as_index = False)['KmReco']
              .sum()
              .pivot(index = 'Codigo', columns = 'TipoEje', values = 'KmReco')
              .reset_index())

  # Se crea el dataset con el km acumulado de la llanta
  durabilidad = (movimientos.drop(columns = ['Val', 'Cambios', 'Acum', 'TipoEjeAdj_cat'], errors = 'ignore')
                 .sort_values(['Codigo', 'Fecha'], ascending = [True, False])
                 .assign(rn = lambda x: x.groupby('Codigo').cumcount())
                 .loc[lambda x: x['rn'] == 0]
                 .drop(columns = 'rn')
                 .merge(cambios, on = 'Codigo', how = 'left')
                 .assign(PctDireccion = lambda x: np.where(x['Direccional'].isna(), 0, (x['Direccional'] / x['KmAcum']).round(4)),
                         InsertDate = pd.Timestamp.now()))

  # Envio de los datos al DW
  sql_types = {'Fecha': types.DATE, 'KmLife': types.INTEGER, 'MmLife': types.FLOAT, 'KmAcum': types.INTEGER, 
               'MmAcum': types.FLOAT, 'Direccional': types.INTEGER, 'Traccion': types.INTEGER, 
               'PctDireccion': types.FLOAT, 'InsertDate': types.TIMESTAMP}

  durabilidad.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
  # Registro de la ejecucion del proceso
  fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = durabilidad['Fecha'].max(), cantidad_registros = durabilidad.shape[0])
  fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
  # registro de la ejecucion del proceso con error
  fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
