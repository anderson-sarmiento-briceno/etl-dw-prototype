#**********************************************************************************************
# @Nombre: Proceso de calculo de consumo energetico Siemens
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import numpy as np                          # Manipulacion numerica
import Funciones as fn                      # Funciones ETL
from sqlalchemy import text, types          # Consulta a base de datos
from datetime import datetime, timedelta    # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1112
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Rendimiento Siemens*"
table = "FactConsumptionSiemens"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Funcion Zscore
def zscore_mad(series):
    med = series.median(skipna = True)
    mad = np.median(np.abs(series - med))
    return np.abs(series - med) <= 2 * mad

try:
  # Carga de la dimension de vehiculo para filtrar los valores correctos
  dim_vehiculo = (pd.read_sql(""" SELECT "IdVehiculo", "AssetNum", "TIPO" as "Tipo"
                                  FROM public."DimFlota" """, fn.cona)
                          .assign(AssetNum = lambda x: x["AssetNum"].str.lower()))

  # Carga de los kms de flota
  kms_flota = (pd.read_sql("""  SELECT "DateKeyReading", fl."IdVehiculo", "Reading" as "Odometro"
                                FROM ma."FactMeterReading" mt
                                LEFT JOIN "DimFlota" fl 
                                  ON mt."AssetNum" = fl."AssetNum"
                                WHERE "MeterName" = 'ODOMKMS' """, fn.cona)
                          .assign(DateKeyReading = lambda x: pd.to_datetime(x["DateKeyReading"], format = "%Y%m%d")))

  # Carga de Id de vehiculos
  puerto_carga = (pd.read_sql(text(""" SELECT "NumeroTM"::integer as "Id", md."AssetNum", "ModuleSn" as "P",
                                         fl."TIPO" as "Tipo"
                                  FROM "DimModulesVehicles" md
                                  LEFT JOIN "DimFlota" fl 
                                   ON md."AssetNum" = fl."AssetNum"
                                  WHERE "NumeroTM" NOT IN ('Dummy','PARTICULAR')
                                   AND "NumeroTM" NOT LIKE 'LM%' """), fn.cona)
                          .assign(P = lambda x: x["P"].str[:12]))

  # Carga de los datos de siemens
  limite = (pd.to_datetime((kms_flota["DateKeyReading"].max() + timedelta(days = 1)).date()) + pd.Timedelta(hours = 6))
  data_siemens = (pd.read_sql(""" SELECT "DateStart", "ModuleId" as "VehicleId", "StartAt", 
                                         "EnergyDeliveredKWh", "PercentCharged"
                                  FROM ma."FactConsumoEnergy"
                                  WHERE "PercentCharged" > 0 """, fn.cona)
                          .assign(VehicleId = lambda df: (df["VehicleId"].astype(str).str.lower().str[:12]))
                          .loc[lambda df: df["StartAt"] <= limite])

  # Proceso de calculo del rendimiento
  rate_buseton = 2.82 # 2,82 KWh / 1% SOC
  rate_padron = 3.7 # 3,7 KWh / 1% SOC

  carga_siemens = (data_siemens[(data_siemens["VehicleId"] != "") & (data_siemens["VehicleId"] != "-")]
                   .merge(puerto_carga[["Id", "P"]], left_on = "VehicleId", right_on = "P", how = "left")
                   .merge(dim_vehiculo[["IdVehiculo", "AssetNum"]], left_on = "VehicleId", right_on = "AssetNum", how = "left")
                   .assign(IdVehiculo = lambda df: np.where(df["Id"].isna(), df["IdVehiculo"], df["Id"]))
                   .loc[lambda df: df["IdVehiculo"].notna()]
                   .rename(columns = {"DateStart": "FechaCarga"})
                   .merge(dim_vehiculo.drop(columns = ["AssetNum"]), on = "IdVehiculo", how = "left")
                   .assign(EnergyDeliveredKWh = lambda df: np.where((df["EnergyDeliveredKWh"] == 0) & (df["Tipo"] == "BUSETON"), df["PercentCharged"] * rate_buseton,
                                                                    np.where((df["EnergyDeliveredKWh"] == 0) & (df["Tipo"] == "PADRON"), df["PercentCharged"] * rate_padron, df["EnergyDeliveredKWh"])))
                   .groupby(["FechaCarga", "IdVehiculo"], as_index = False)["EnergyDeliveredKWh"]
                   .sum()
                   .assign(FechaCarga = lambda x: pd.to_datetime(x["FechaCarga"]),
                           IdVehiculo = lambda x: x["IdVehiculo"].astype(int))
                   .merge(kms_flota, left_on = ["FechaCarga", "IdVehiculo"], right_on = ["DateKeyReading", "IdVehiculo"], how = "left")
                   .assign(Mes = lambda df: df["FechaCarga"].dt.to_period("M"),
                           InsertDate = datetime.now())
                   .sort_values(["IdVehiculo", "FechaCarga"])
                   .assign(Recorrido = lambda df: (df.groupby("IdVehiculo")["Odometro"].diff()))
                   .assign(KwhrKm = lambda df: (df.groupby(["Mes", "IdVehiculo"]).apply(lambda x: x["EnergyDeliveredKWh"].sum() / x["Recorrido"].sum())
                                                .reset_index(level = [0,1], drop = True)))
                   .merge(dim_vehiculo.drop(columns = ["AssetNum"]), on = "IdVehiculo", how = "left")
                   .assign(MadKwhrKm = lambda df: (df.groupby("Tipo")["KwhrKm"].transform(zscore_mad)))
                   [["FechaCarga", "IdVehiculo", "EnergyDeliveredKWh", "Odometro", "Recorrido", 
                     "MadKwhrKm", "InsertDate"]])
  
  sql_types_p20 = {'FechaCarga': types.DATE, 'IdVehiculo': types.INTEGER, 'EnergyDeliveredKWh': types.INTEGER,
                   'Odometro': types.FLOAT, 'Recorrido': types.FLOAT, 'MadKwhrKm': types.BOOLEAN,
                   'InsertDate': types.TIMESTAMP}
  
  carga_siemens.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types_p20)
  
  # Registro de la ejecucion del proceso
  fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = carga_siemens['FechaCarga'].max(), cantidad_registros = len(carga_siemens))
  fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
  # registro de la ejecucion del proceso con error
  fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
