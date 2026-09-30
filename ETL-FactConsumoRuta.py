#**********************************************************************************************
# @Nombre: 
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import re                              # Manejo de expresiones regulares
import Funciones as fn                 # Funciones personalizadas
from sqlalchemy import types, text     # Manejo de tipos de campos en db
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1161
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Consumo Energia Ruta*"
table = "FactConsumoRuta"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#----------------------------------------------------------------------------------------------
def zscore_mad(series):
    med = series.median()
    mad = (series - med).abs().median()
    return (series - med).abs() <= 2 * mad

try:
    #------------------------------------------------------------------------------------------
    userpc = os.getenv("PAT_NAS")
    rut = "02 Datos/12 viajes_desglosados"

    pathfiles = [os.path.join(userpc, rut, f)
                 for f in os.listdir(os.path.join(userpc, rut))
                 if f.endswith(".parquet")
                 and int(re.search(r"^\d{8}", f).group()) >= 20250601]

    columnas = ["Fecha", "Linea", "Sentido", "Vehiculo", "Cumplimiento","LongitudRuta", 
                "DistanciaComputable", "DurReal"]

    dimrutas = pd.DataFrame({"Ruta": ["KA324","KB326","KH308","KH317","KL312","KL328","KL329",
                                      "KA332","KB314","KG311","KH318","KH327","KL325","KL331"],
                             "UF": ["UF06"]*7 + ["UF17"]*7,
                             "Tipo": ["BUSETON","PADRON","BUSETON","PADRON","BUSETON","PADRON","BUSETON",
                                      "PADRON","BUSETON","BUSETON","PADRON","BUSETON","BUSETON","BUSETON"]})

    #------------------------------------------------------------------------------------------
    # Dimensiones
    dim_vehiculo = (pd.read_sql_query(''' SELECT "IdVehiculo" AS "Vehiculo",
                                                 LOWER("AssetNum") AS "AssetNum",
                                                 "TIPO" AS "Tipo"
                                          FROM public."DimFlota" ''', con = fn.enginea))

    kms_flota = (pd.read_sql_query(''' SELECT "DateKeyReading" AS "Fecha",
                                              flt."IdVehiculo" AS "Vehiculo", "Delta"
                                       FROM ma."FactMeterReading" mtr
                                       LEFT JOIN "DimFlota" flt 
                                        ON mtr."AssetNum" = flt."AssetNum"
                                       WHERE "MeasureUnitId" = 'KMS'
                                        AND "DateKeyReading" >= '20220901' ''', con = fn.enginea)
                 .assign(Fecha = lambda d: pd.to_datetime(d["Fecha"], format = '%Y%m%d')))

    puerto_carga = (pd.read_sql_query(text(''' SELECT "NumeroTM"::integer AS "Id", md."AssetNum",
                                                      "ModuleSn" AS "P", fl."TIPO" AS "Tipo"
                                               FROM "DimModulesVehicles" md
                                               LEFT JOIN "DimFlota" fl 
                                                ON md."AssetNum" = fl."AssetNum"
                                               WHERE "NumeroTM" NOT IN ('Dummy','PARTICULAR')
                                                AND "NumeroTM" NOT LIKE 'LM%' '''), con = fn.cona)
                    .assign(P = lambda d: d["P"].str[:12]))

    #------------------------------------------------------------------------------------------
    rate_buseton = 2.82
    rate_padron = 3.7

    data_siemens = (pd.read_sql_query(''' SELECT "ModuleId" AS "VehicleId", "StartAt", 
                                                 "EnergyDeliveredKWh", "PercentCharged"
                                          FROM ma."FactConsumoEnergy"
                                          WHERE "PercentCharged" > 0
                                            AND "DateStart" >= '2022-09-01' ''', con = fn.enginea)
                    .assign(VehicleId = lambda x: (x["VehicleId"].astype(str).str.strip()))
                    .query("VehicleId not in ['-', '', 'nan', 'None']")
                    .assign(VehicleId = lambda d: d["VehicleId"].str.lower().str[:12],
                            DateStart = lambda d: (pd.to_datetime(d["StartAt"]) - pd.to_timedelta(21660, unit = "s")).dt.date)
                    .merge(puerto_carga[["Id","P"]], left_on = "VehicleId", right_on = "P", how = "left")
                    .merge(dim_vehiculo[["Vehiculo","AssetNum"]], left_on = "VehicleId", right_on = "AssetNum", how = "left")
                    .assign(IdVehiculoDef = lambda d: d["Id"].fillna(d["Vehiculo"]))
                    .dropna(subset = ["IdVehiculoDef"])
                    .drop(columns = "Vehiculo")
                    .rename(columns = {"IdVehiculoDef":"Vehiculo"})
                    .loc[:, ["DateStart","Vehiculo","EnergyDeliveredKWh","PercentCharged"]]
                    .merge(dim_vehiculo[["Vehiculo","Tipo"]], on = "Vehiculo", how = "left")
                    .assign(EnergyDeliveredKWh = lambda d: d.apply(lambda r: int(r["PercentCharged"] * rate_buseton)
                                                                   if r["EnergyDeliveredKWh"] == 0 and r["Tipo"] == "BUSETON"
                                                                   else int(r["PercentCharged"] * rate_padron)
                                                                   if r["EnergyDeliveredKWh"] == 0 and r["Tipo"] == "PADRON"
                                                                   else r["EnergyDeliveredKWh"], axis = 1))
                    .groupby(["DateStart","Vehiculo"], as_index = False)
                    .agg(EnergyDeliveredKWh = ("EnergyDeliveredKWh","sum"))
                    .merge(kms_flota.assign(Fecha = lambda x: x["Fecha"].dt.date,
                                            Vehiculo = lambda x: x["Vehiculo"].astype(float)), left_on = ["DateStart", "Vehiculo"], right_on = ["Fecha","Vehiculo"], how = "left")
                    .assign(KwhrKm = lambda d: d["EnergyDeliveredKWh"] / d["Delta"])
                    .merge(dim_vehiculo, on = "Vehiculo", how = "left"))

    data_siemens["MadKwhrKm"] = (data_siemens.groupby("Tipo")["KwhrKm"]
                                 .transform(zscore_mad))

    data_siemens = (data_siemens[data_siemens["MadKwhrKm"]]
                    .loc[:, ["DateStart", "Vehiculo", "EnergyDeliveredKWh", "Delta"]])

    #------------------------------------------------------------------------------------------
    # Viajes
    viajes = (pd.concat([pd.read_parquet(p, columns = columnas) for p in pathfiles], ignore_index = True)
              .query("DurReal not in ['', 'nan', 'NaT', 'None']")
              .assign(Fecha = lambda d: pd.to_datetime(d["Fecha"], dayfirst = True),
                      DistanciaComputable = lambda d: pd.to_numeric(d["DistanciaComputable"].astype(str).str.replace(r"[^\d.]", "", regex = True), errors = "coerce"),
                      LongitudRuta = lambda d: d["LongitudRuta"].astype(str).str.replace(r"[^\d.]", "", regex = True).astype(float),
                      Vehiculo = lambda d: pd.to_numeric(d["Vehiculo"].astype(str)
                                                       .str.replace("-", "", regex = False)
                                                       .str.replace("Z", "", regex = False), errors = "coerce")
                                                       .astype("Int64"))
              .assign(Var = lambda d: (d["DistanciaComputable"] / d["LongitudRuta"]).round(2))
              .query("Var > 0.9")
              .assign(Ruta = lambda d: d["Linea"].str.split().str[1],
                      Linea = lambda d: d["Linea"].str.split().str[0])
              .rename(columns = {"Linea":"LineaSae"})
              .merge(dimrutas, on = "Ruta", how = "left"))

    viajes["RutasxDia"] = (viajes.groupby(["Fecha","Vehiculo"])["Ruta"].transform("nunique"))

    viajes = viajes[viajes["RutasxDia"] == 1]

    viajes = (viajes.assign(Fecha = lambda x: pd.to_datetime(x["Fecha"]).dt.date)
              .drop(columns = ["RutasxDia","Cumplimiento","Var","Sentido"])
              .assign(FilterTipo = lambda x: (x["Vehiculo"].astype(str)
                                              .str.replace(r".*634.*", "BUSETON", regex = True)
                                              .str.replace(r".*674.*", "BUSETON", regex = True)
                                              .str.replace(r".*637.*", "PADRON", regex = True)
                                              .str.replace(r".*677.*", "PADRON", regex = True)))
              .query("Tipo == FilterTipo")
              .drop_duplicates(subset = ["Fecha","Vehiculo","Ruta"])
              .merge(data_siemens.assign(Vehiculo = lambda d: d["Vehiculo"].astype("int64")), left_on = ["Fecha","Vehiculo"], right_on = ["DateStart","Vehiculo"], how = "left")
              .assign(ConsumoRuta = lambda d: (d["EnergyDeliveredKWh"] / d["Delta"]).round(3),
                      InsertDate = datetime.now())
              .dropna()
              .rename(columns = {"Vehiculo":"IdVehiculo","Ruta":"Linea"})
              .loc[:, ["Fecha", "IdVehiculo", "Linea", "EnergyDeliveredKWh", "Delta", "ConsumoRuta", "InsertDate"]])

    #------------------------------------------------------------------------------------------
    sql_types = {"Fecha": types.DATE, "IdVehiculo": types.INTEGER, "Linea": types.TEXT,
                 "EnergyDeliveredKWh": types.INTEGER, "Delta": types.INTEGER, "ConsumoRuta": types.FLOAT,
                 "InsertDate": types.TIMESTAMP}

    viajes.to_sql(table, schema = "ma", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = viajes["Fecha"].max(), cantidad_registros = len(viajes))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))
