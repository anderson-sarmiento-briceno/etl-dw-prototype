#**********************************************************************************************
# @Nombre: Extraccion y Transformacion de datos de Maximo
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import numpy as np                     # Manipulacion numerica
import os                              # Manejo del sistema
import Funciones as fn                 # Funciones ETL
from sqlalchemy import text            # Conexion base de datos
from sqlalchemy import types           # Manejo de tipos de campos en db
from pathlib import Path               # Manejo de rutas de archivos
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1020
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Datos Maximo*"
table1 = 'FactInvuseline'
table2 = 'FactInvReserve'
table3 = 'FactWorkOrder'
table4 = 'FactWorkService'
table5 = 'FactAssetMeters'
table6 = 'FactMeterReading'
table7 = 'FactPm'
table8 = 'FactServiceTrans'
table9 = 'FactMaterialTrans'
table10 = 'FactMaterialReceive'
table11 = 'FactLaborTrans'
table12 = 'FactPurchaseRequest'
table13 = 'FactPurchaseOrder'
table14 = 'FactPurchaseOrderLines'
table15 = 'DimItem'
table16 = 'DimItemSpec'
table17 = 'DimCompany'
table18 = 'DimTareasMaximo'

# Función para evitar error por división entre cero
def safe_div(x, y):
    return 180 if y == 0 else x / y

def read_query(file_path):
    with open(file_path, "r", encoding = "utf-8") as f:
        return f.read()

# Parametros del query
path_project = Path(os.getenv("PAT_PROJECT"))

query_invuseline = path_project / "00 Querys" / "FactInvuseline.sql"
query_invreserve = path_project / "00 Querys" / "FactInvReserve.sql"
query_workorder = path_project / "00 Querys" / "FactWorkorder.sql"
query_meters = path_project / "00 Querys" / "FactAssetMeters.sql"
query_meterreading = path_project / "00 Querys" / "FactMeterReading.sql"
query_service = path_project / "00 Querys" / "FactWorkService.sql"
query_item = path_project / "00 Querys" / "DimItem.sql"
query_item_spec = path_project / "00 Querys" / "DimItemSpec.sql"
query_pm = path_project / "00 Querys" / "FactPm.sql"
query_service_trans = path_project / "00 Querys" / "FactServiceTrans.sql"
query_material_trans = path_project / "00 Querys" / "FactMaterialTrans.sql"
query_labor_trans = path_project / "00 Querys" / "FactLaborTrans.sql"
query_purchase_request = path_project / "00 Querys" / "FactPurchaseRequest.sql"
query_purchase_order = path_project / "00 Querys" / "FactPurchaseOrder.sql"
query_purchase_order_lines = path_project / "00 Querys" / "FactPurchaseOrderLine.sql"
query_material_receive = path_project / "00 Querys" / "FactMatRecTrans.sql"

# Obtener y transformar datos -----------------------------------------------------------------
try:
    # Fact Invuseline
    fact_invuseline = (pd.read_sql(read_query(query_invuseline), fn.enginemx)
                       .assign(DatekeyActual = lambda df: (pd.to_datetime(df["ActualDate"]).dt.strftime("%Y%m%d").astype(int)),
                               InsertDate = datetime.now(),
                               Quantity = lambda df: np.where(df["UseType"] == "DEVOLVER", df["Quantity"] * -1, df["Quantity"]),
                               UnitCost = lambda df: np.where(df["UseType"] == "DEVOLVER", df["UnitCost"] * -1, df["UnitCost"]),
                               LineCost = lambda df: np.where(df["UseType"] == "DEVOLVER", df["LineCost"] * -1, df["LineCost"]))
                       .pipe(lambda df: df[["DatekeyActual"] + [c for c in df.columns if c != "DatekeyActual"]]))
    
    # Envio de los datos al DW
    sql_types = {'DatekeyActual': types.INTEGER, 'CreateDate': types.TIMESTAMP, 'InvuseNum': types.INTEGER,
                 'ActualDate': types.TIMESTAMP, 'FinancialPeriod': types.INTEGER, 'Parent': types.INTEGER,
                 'Refwo': types.INTEGER, 'InvuselineNum': types.INTEGER, 'Quantity': types.FLOAT, 
                 'ReturnedQty': types.FLOAT, 'UnitCost': types.FLOAT, 'LineCost': types.FLOAT, 
                 'IssueTo': types.INTEGER, 'RequestNum': types.INTEGER, 'Conversion': types.INTEGER, 
                 'ReturnAgainstIssue': types.INTEGER, 'ReceiptsComplete': types.INTEGER, 'ReceivedQty': types.FLOAT, 
                 'InspectionRequired': types.FLOAT, 'InvuseLineid': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_invuseline.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = fact_invuseline['ActualDate'].max(), cantidad_registros = len(fact_invuseline))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

try:
    # Fact InvReserve
    fact_invreserve = (pd.read_sql(read_query(query_invreserve), fn.enginemx)
                       .assign(InsertDate = datetime.now(),
                               DatekeyActual = lambda df: (pd.to_datetime(df["RequireDate"]).dt.strftime("%Y%m%d").astype(int)))
                       .pipe(lambda df: df[["DatekeyActual"] + [c for c in df.columns if c != "DatekeyActual"]]))

    # Envio de los datos al DW
    sql_types = {'DatekeyActual': types.INTEGER, 'ItemNum': types.INTEGER, 'Parent': types.INTEGER,
                 'WoNum': types.INTEGER, 'ItemQty': types.FLOAT, 'RequireDate': types.TIMESTAMP,
                 'InsertDate': types.TIMESTAMP}

    fact_invreserve.to_sql(table2, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = fact_invreserve['RequireDate'].max(), cantidad_registros = len(fact_invreserve))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

try:
    # Fact Work Order
    fact_workorder = (pd.read_sql(read_query(query_workorder), fn.enginemx)
                        .assign(InsertDate = datetime.now(),
                                DatekeyActual = lambda df: (pd.to_datetime(df["ReportDate"]).dt.strftime("%Y%m%d").astype("Int64")),
                                WorkTypeAdj = None)
                                .pipe(lambda df: df[["DatekeyActual"] + [c for c in df.columns if c != "DatekeyActual"]]))

    fact_em = (fact_workorder.loc[lambda df: ~df["WoClass"].isin(["ORDENTRABAJO", "ACTIVIDAD"])])

    fact_ot = (fact_workorder.loc[lambda df: df["WoClass"] == "ORDENTRABAJO"])

    fact_tmp = (fact_workorder.loc[lambda df: df["WoClass"] == "ORDENTRABAJO", ["WoNum","WorkType","LectOdom","FechaLectodom","DescriptionClass"]]
                              .rename(columns = {"WorkType": "WorkTypeAdjEra", "LectOdom": "LectOdomAdj", 
                                                 "FechaLectodom": "FechaLectodomAdj", "DescriptionClass": "DescriptionClassAdj"})
                              .assign(LectOdomAdj = lambda df: df["LectOdomAdj"].replace(0, np.nan)))

    fact_at = (fact_workorder.loc[lambda df: df["WoClass"] == "ACTIVIDAD"]
                             .merge(fact_tmp, left_on = "Parent", right_on = "WoNum", how = "left", suffixes = ("", "_tmp"))
                             .assign(LectOdom = lambda df: np.where(df["LectOdomAdj"].isna(), df["LectOdom"], df["LectOdomAdj"]),
                                     FechaLectodom = lambda df: pd.to_datetime(np.where(df["FechaLectodomAdj"].isna(), df["FechaLectodom"].astype(str), df["FechaLectodomAdj"].astype(str))),
                                     DescriptionClass = lambda df: np.where(df["DescriptionClassAdj"].isna(), df["DescriptionClass"], df["DescriptionClassAdj"]),
                                     WorkTypeAdj = lambda df: np.where(df["WorkTypeAdjEra"].isna(), df["WorkType"], df["WorkTypeAdjEra"]))
                             .drop(columns = ["DescriptionClassAdj", "LectOdomAdj", "FechaLectodomAdj", "WorkTypeAdjEra"]))
    
    fact_ot_final = (pd.concat([fact_ot, fact_at, fact_em], ignore_index = True)
                        .assign(WorkTypeAdj = lambda df: np.where(df["WorkTypeAdj"].isna(), df["WorkType"], df["WorkTypeAdj"]),
                                DescriptionOt = lambda df: (df["DescriptionOt"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True)),
                                PluscJpRevnum = lambda df: df["PluscJpRevnum"].astype("Int64"),
                                WoPriority = lambda df: df["WoPriority"].astype("Int64"))
                        .drop(columns = "WoNum_tmp"))

    # Envio de los datos al DW
    sql_types = {'DatekeyActual': types.INTEGER, 'WoNum': types.INTEGER, 'DescriptionOt': types.VARCHAR(255),
                 'SiteId': types.VARCHAR(15), 'WoClass': types.VARCHAR(15), 'Status': types.VARCHAR(15),
                 'AssetNum': types.VARCHAR(15), 'WorkType': types.VARCHAR(5), 'StatusDate': types.TIMESTAMP,
                 'DescriptionClass': types.VARCHAR(25), 'Parent': types.INTEGER, 'LectOdom': types.FLOAT,
                 'FechaLectodom': types.TIMESTAMP, 'JpNum': types.VARCHAR(25), 'PluscJpRevnum': types.VARCHAR(2),
                 'PmNum': types.VARCHAR(25), 'WoPriority': types.VARCHAR(2), 'SchedStart': types.TIMESTAMP,
                 'SchedFinish': types.TIMESTAMP, 'ActStart': types.TIMESTAMP, 'ActFinish': types.TIMESTAMP,
                 'EstDur': types.FLOAT, 'ReportDate': types.TIMESTAMP, 'TaskId': types.INTEGER,
                 'IsTask': types.VARCHAR(2), 'Route': types.VARCHAR(25), 'EstMatCost': types.FLOAT,
                 'ActMatCost': types.FLOAT, 'ActServCost': types.FLOAT, 'EstServCost': types.FLOAT,
                 'WorkOrderId': types.INTEGER, 'WorkTypeAdj': types.VARCHAR(5), 'InsertDate': types.TIMESTAMP}

    # Carga DW
    fn.cona.execute(text(f'TRUNCATE TABLE ma."{table3}"'))
    fact_ot_final.to_sql(table3, schema = 'ma', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = fact_ot_final['StatusDate'].max(), cantidad_registros = len(fact_ot_final))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))

try:
    # Fact Work Service
    fact_service = (pd.read_sql(read_query(query_service), fn.enginemx)
                    .merge(fact_ot_final[['WoNum', 'DescriptionClass', 'DatekeyActual']], on = 'WoNum', how = 'left')
                    .assign(InsertDate = datetime.now())
                    .pipe(lambda df: df[['DatekeyActual'] + [col for col in df.columns if col != 'DatekeyActual']]))

     # Envio de los datos al DW
    sql_types = {'DatekeyActual': types.INTEGER, 'WoNum': types.INTEGER, 'Parent': types.INTEGER,
                 'AssetNum': types.VARCHAR(15), 'Status': types.VARCHAR(15), 'DescriptionClass': types.VARCHAR(25),
                 'WoClass': types.VARCHAR(15), 'ItemNum': types.VARCHAR(15), 'Description': types.VARCHAR(55),
                 'ItemQty': types.FLOAT, 'UnitCost': types.FLOAT, 'LineCost': types.FLOAT,
                 'OrderUnit': types.VARCHAR(15), 'Pr': types.INTEGER, 'PrlineNum': types.INTEGER,
                 'RequestBy': types.VARCHAR(15), 'RequestNum': types.INTEGER, 'RequireDate': types.TIMESTAMP,
                 'SiteId': types.VARCHAR(15), 'Vendor': types.VARCHAR(25), 'VendorPackCode': types.VARCHAR(25),
                 'VendorPackQuantity': types.INTEGER, 'VendorUnitCost': types.INTEGER, 'WpItemId': types.INTEGER,
                 'WpItemId': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_service.to_sql(table4, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), max_fecha_tabla = fact_service['RequireDate'].max(), cantidad_registros = len(fact_service))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), observacion = str(e))

try:
    # Fact Asset Meters
    fact_meters = (pd.read_sql(read_query(query_meters), fn.enginemx)
                   .assign(DateKeyReading = lambda x: pd.to_datetime(x['LastReadingDate']).dt.strftime('%Y%m%d').astype("Int64"),
                           InsertDate = datetime.now(),
                           LastReading = lambda x: x["LastReading"].str.replace(".", "", regex = False)
                                                                   .str.replace(",", ".", regex = False)
                                                                   .astype(float).astype("Int64"))
                   .pipe(lambda df: df[['DateKeyReading'] + [col for col in df.columns if col != 'DateKeyReading']]))

    # Envio de los datos al DW
    sql_types = {'DateKeyReading': types.INTEGER, 'AssetNum': types.VARCHAR(15), 'MeterName': types.VARCHAR(15),
                 'Active': types.VARCHAR(2), 'AvgCalcMethod': types.VARCHAR(15), 'SlidingWindowSize': types.INTEGER,
                 'LifeToDate': types.FLOAT, 'ChangeBy': types.VARCHAR(25), 'ChangeDate': types.TIMESTAMP,
                 'Remarks': types.VARCHAR(55), 'LastReadingDate': types.TIMESTAMP, 'LastReading': types.FLOAT,
                 'Average': types.FLOAT, 'ReadingType': types.VARCHAR(15), 'AssetMeterid': types.INTEGER,
                 'InsertDate': types.TIMESTAMP}

    fact_meters.to_sql(table5, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), max_fecha_tabla = fact_meters['LastReadingDate'].max(), cantidad_registros = len(fact_meters))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), observacion = str(e))

try:
    # Fact MeterReading
    fact_meter_reading = (pd.read_sql(read_query(query_meterreading), fn.enginemx)
                          .assign(DateKeyReading = lambda x: pd.to_datetime(x["ReadingDate"]).dt.strftime("%Y%m%d").astype(int),
                                  InsertDate = datetime.now())
                          .sort_values(["AssetNum", "ReadingDate"], ascending = [True, False])
                          .loc[:, lambda x: ["DateKeyReading"] + [c for c in x.columns if c != "DateKeyReading"]])

    # Envio de los datos al DW
    sql_types = {'DateKeyReading': types.INTEGER, 'Delta': types.FLOAT, 'Reading': types.FLOAT,
                 'RollOver': types.FLOAT, 'ReadingDate': types.TIMESTAMP, 'EnterDate': types.TIMESTAMP,
                 'Modified': types.INTEGER, 'MeterReadingId': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_meter_reading.to_sql(table6, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), max_fecha_tabla = fact_meter_reading['ReadingDate'].max(), cantidad_registros = len(fact_meter_reading))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), observacion = str(e))

try:
    # Fact PM
    fact_pm = (pd.read_sql(read_query(query_pm), fn.enginemx)
               .assign(LastReading = lambda x: (x["LastReading"].str.replace(".", "", regex = False)
                                                                .str.replace(",", ".", regex = False)
                                                                .astype(float)))
               .assign(LastPmWoGenRead = lambda x: x["LastPmWoGenRead"].fillna(0),
                       LastReading = lambda x: x["LastReading"].fillna(0),
                       Average = lambda x: x["Average"].fillna(0))
               .assign(DateKeyReading = lambda x: pd.to_datetime(x["LastReadingDate"]).dt.strftime("%Y%m%d").astype("Int64"),
                       UnistToGo = lambda x: x["ReadingAtNextWo"] - x["LastReading"])
               .assign(DateOfNextWo = lambda x: pd.Timestamp.today().normalize() + pd.to_timedelta(np.round(x["UnistToGo"] / x["Average"], 0), unit = "D"),
                       InsertDate = datetime.now(),
                       Description = lambda x: x["Description"].str.replace(r"\s+", " ", regex = True).str.strip())
               .loc[:, lambda x: ["DateKeyReading"] + [c for c in x.columns if c != "DateKeyReading"]])

    # Envio de los datos al DW
    sql_types = {'DateKeyReading': types.INTEGER, 'LastCompDate': types.TIMESTAMP, 'LastStartDate': types.TIMESTAMP,
                 'FirstDate': types.TIMESTAMP, 'FrequencyPm': types.INTEGER, 'PmCounter': types.INTEGER,
                 'JpEeqinUse': types.INTEGER, 'NextDate': types.TIMESTAMP, 'GrnStartPmFreq': types.TIMESTAMP,
                 'Frequency': types.INTEGER, 'Tolerance': types.INTEGER, 'LastPmWoGenRead': types.FLOAT,
                 'LastPmWoDenReadDt': types.TIMESTAMP, 'ReadingAtNextWo': types.FLOAT, 'LtdReadAtNextWo': types.FLOAT,
                 'LtdLastPmWoRead': types.FLOAT, 'LifetoDate': types.FLOAT, 'LastReadingDate': types.TIMESTAMP, 
                 'LastReading': types.FLOAT, 'Average': types.FLOAT, 'ChangeDate': types.TIMESTAMP, 
                 'UnistToGo': types.FLOAT, 'DateOfNextWo': types.DATE, 'InsertDate': types.TIMESTAMP}

    fact_pm.to_sql(table7, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table7), max_fecha_tabla = fact_pm['LastStartDate'].max(), cantidad_registros = len(fact_pm))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table7), observacion = str(e))

try:
    # Fact Servicios Transacciones
    fact_service_trans = (pd.read_sql(read_query(query_service_trans), fn.enginemx)
                          .merge(fact_ot_final[["WoNum", "WoClass", "DescriptionClass", "WorkType", "WoPriority", "Parent"]], left_on = "RefWo", right_on = "WoNum", how = "left")
                          .drop(columns = "WoNum")
                          .assign(DateKeyEnter = lambda x: pd.to_datetime(x["EnterDate"]).dt.strftime("%Y%m%d").astype("Int64"),
                                  InsertDate = datetime.now(),
                                  Parent = lambda x: np.where(x["WoClass"] == "ORDENTRABAJO", x["RefWo"], x["Parent"]))
                          .pipe(lambda x: x[["DateKeyEnter"] + [c for c in x.columns if c != "DateKeyEnter"]])
                          .pipe(lambda x: x[x.columns[: x.columns.get_loc("RefWo") + 1].tolist()
                                            + ["WoClass", "DescriptionClass", "WorkType", "WoPriority", "Parent"]
                                            + [c for c in x.columns if c not in ["WoClass","DescriptionClass","WorkType","WoPriority","Parent"] 
                                               and c not in x.columns[: x.columns.get_loc("RefWo") + 1]]]))
    # Wo Status
    fact_wo_status = (pd.read_sql(""" SELECT wonum as WoNum, changedate as WoStartDate
                                      FROM GRMAXPR.dbo.wostatus
                                      WHERE status = 'APROB' """, fn.enginemx)
                                  .loc[lambda x: x["WoNum"].isin(fact_service_trans["Parent"])]
                                  .sort_values(["WoNum", "WoStartDate"])
                                  .drop_duplicates("WoNum", keep = "first")
                                  .assign(WoStartDate = lambda x: pd.to_datetime(x["WoStartDate"]).dt.date))
    # Join final
    fact_service_trans = (fact_service_trans.merge(fact_wo_status, left_on = "Parent", right_on = "WoNum", how = "left")
                          .drop(columns = "WoNum")
                          .sort_values("WoStartDate")
                          .assign(RejectCost = lambda x: x["RejectCost"].fillna(0)))

    fact_service_trans.to_sql(table8, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table8), max_fecha_tabla = fact_service_trans['EnterDate'].max(), cantidad_registros = len(fact_service_trans))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table8), observacion = str(e))

try:
    # Fact Materiales Transaccion
    fact_materiales_trans = (pd.read_sql(read_query(query_material_trans), fn.enginemx)
                             .merge(fact_ot_final[["WoNum", "WoClass", "DescriptionClass", "WorkType", "WoPriority", "Parent"]], left_on = "RefWo", right_on = "WoNum", how = "left")
                             .drop(columns = "WoNum")
                             .assign(DateKeyActual = lambda x: pd.to_datetime(x["ActualDate"]).dt.strftime("%Y%m%d").astype(int),
                             InsertDate = datetime.now())
                             .pipe(lambda df: df[["DateKeyActual"] + [c for c in df.columns if c != "DateKeyActual"]])
                             .pipe(lambda df: df[df.columns[: df.columns.get_loc("RefWo") + 1].tolist()
                                                 + ["WoClass", "DescriptionClass", "WorkType", "WoPriority", "Parent"]
                                                 + [c for c in df.columns if c not in (
                                                     df.columns[: df.columns.get_loc("RefWo") + 1].tolist()
                                                     + ["WoClass", "DescriptionClass", "WorkType", "WoPriority", "Parent"])]]))

    # Envio de los datos al DW
    sql_types = {'DateKeyActual': types.INTEGER, 'ActualDate': types.TIMESTAMP, 'RefWo': types.INTEGER,
                 'WoPriority': types.INTEGER, 'Parent': types.INTEGER, 'EnteredAsTask': types.INTEGER,
                 'CurBal': types.FLOAT, 'PhysCnt': types.FLOAT, 'ActualCost': types.FLOAT,
                 'QtyRequested': types.FLOAT, 'Quantity': types.FLOAT, 'UnitCost': types.FLOAT,
                 'QtyReturned': types.FLOAT, 'LineCost': types.FLOAT, 'TransDate': types.TIMESTAMP,
                 'InsertDate': types.TIMESTAMP}

    fact_materiales_trans.to_sql(table9, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table9), max_fecha_tabla = fact_materiales_trans['TransDate'].max(), cantidad_registros = len(fact_materiales_trans))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table9), observacion = str(e))

try:
    # Fact Materiales recepcion
    fact_materiales_recei = (pd.read_sql(read_query(query_material_receive), fn.enginemx)
                             .assign(ActualDate = lambda x: pd.to_datetime(x["ActualDate"]).dt.date,
                                     RequiredDate = lambda x: pd.to_datetime(x["RequiredDate"]).dt.date,
                                     OrderDate = lambda x: pd.to_datetime(x["OrderDate"]).dt.date)
                             .assign(LeadTimeDays = lambda x: (pd.to_datetime(x["ActualDate"]) - pd.to_datetime(x["OrderDate"])).dt.days,
                                     OnTimeDays = lambda x: (pd.to_datetime(x["ActualDate"]) - pd.to_datetime(x["RequiredDate"])).dt.days,
                                     InsertDate = datetime.now()))

    # Envio de los datos al DW
    sql_types = {'Ponum': types.INTEGER, 'PoRevisionNum': types.INTEGER, 'ActualDate': types.DATE,
                 'RequiredDate': types.DATE, 'OrderDate': types.DATE, 'Quantity': types.FLOAT,
                 'RejectQty': types.FLOAT, 'LineCost': types.FLOAT, 'FinancialPeriod': types.INTEGER,
                 'LeadTimeDays': types.INTEGER, 'OnTimeDays': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_materiales_recei.to_sql(table10, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table10), max_fecha_tabla = fact_materiales_recei['ActualDate'].max(), cantidad_registros = len(fact_materiales_recei))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table10), observacion = str(e))

try:
    # Fact Labor Trans
    fact_labor_trans = (pd.read_sql(read_query(query_labor_trans), fn.enginemx)
        .assign(DateKeyStart = lambda x: pd.to_datetime(x["StartDateTime"]).dt.strftime("%Y%m%d").astype("Int64"),
                InsertDate = datetime.now())
        .pipe(lambda df: df[["DateKeyStart"] + [c for c in df.columns if c != "DateKeyStart"]]))

    # Envio de los datos al DW
    sql_types = {'DateKeyStart': types.INTEGER, 'PaymentTransDate': types.TIMESTAMP, 'TransDate': types.TIMESTAMP,
                 'RefWo': types.INTEGER, 'Parent': types.INTEGER, 'StartDateTime': types.TIMESTAMP,
                 'FinishDateTime': types.TIMESTAMP, 'PayRate': types.FLOAT, 'LineCost': types.FLOAT,
                 'RegularHrs': types.FLOAT, 'StartDate': types.TIMESTAMP, 'StartTime': types.TIMESTAMP,
                 'FinishDate': types.TIMESTAMP, 'FinishTime': types.TIMESTAMP, 'GenApprServReceipt': types.INTEGER,
                 'EnteredAsTask': types.INTEGER, 'EnterDate': types.TIMESTAMP, 'LabTransId': types.INTEGER,
                 'InsertDate': types.TIMESTAMP}

    fact_labor_trans.to_sql(table11, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table11), max_fecha_tabla = fact_labor_trans['TransDate'].max(), cantidad_registros = len(fact_labor_trans))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table11), observacion = str(e))

try:
    # Fact Purchase Request
    fact_purchase_request = (pd.read_sql(read_query(query_purchase_request), fn.enginemx)
                             .assign(DateKeyIssue = lambda x: pd.to_datetime(x["IssueDate"]).dt.strftime("%Y%m%d").astype("Int64"),
                                     RequiredDate = lambda x: pd.to_datetime(x["RequiredDate"]).dt.date,
                                     InsertDate = datetime.now())
                             .pipe(lambda df: df[["DateKeyIssue"] + [c for c in df.columns if c != "DateKeyIssue"]]))

    # Envio de los datos al DW
    sql_types = {'DateKeyIssue': types.INTEGER, 'PrNum': types.INTEGER, 'RequiredDate': types.DATE,
                 'Ponum': types.INTEGER, 'Polinenum': types.INTEGER, 'PoRevisionNum': types.INTEGER,
                 'ReceiptsComplete': types.INTEGER, 'PrLineNum': types.INTEGER, 'OrderQty': types.FLOAT,
                 'OrderQtyPurchase': types.FLOAT, 'ReceivedQty': types.FLOAT, 'UnitCost': types.FLOAT,
                 'LineCost': types.FLOAT, 'Tax1': types.FLOAT, 'LoadedCost': types.FLOAT,
                 'RefWo': types.INTEGER, 'EnteredasTask': types.INTEGER, 'ReqDeliveryDate': types.DATE,
                 'VenDeliveryDate': types.DATE, 'EnterDate': types.TIMESTAMP, 'ReceiptReqd': types.INTEGER,
                 'InspectionRequired': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_purchase_request.to_sql(table12, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table12), max_fecha_tabla = fact_purchase_request['RequiredDate'].max(), cantidad_registros = len(fact_purchase_request))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table12), observacion = str(e))

try:
    # Fact Purchase Order
    fact_purchase_order = (pd.read_sql(read_query(query_purchase_order), fn.enginemx)
                           .assign(DateOrder = lambda x: pd.to_datetime(x["OrderDate"]).dt.strftime("%Y%m%d").astype(int),
                                   RequiredDate = lambda x: pd.to_datetime(x["RequiredDate"]).dt.date,
                                   Ponum = lambda x: pd.to_numeric(x["Ponum"].astype(str).str.replace("C", "", regex = False), errors = "coerce"),
                                   InsertDate = datetime.now())
                           .pipe(lambda df: df[["DateOrder"] + [c for c in df.columns if c != "DateOrder"]]))

    # Envio de los datos al DW
    sql_types = {'DateOrder': types.INTEGER, 'Ponum': types.INTEGER, 'OrderDate': types.TIMESTAMP,
                 'RequiredDate': types.DATE, 'OriginalPonum': types.INTEGER, 'StatusDate': types.TIMESTAMP,
                 'TotalCost': types.FLOAT, 'Priority': types.INTEGER, 'HistoryFlag': types.BOOLEAN,
                 'VendeliveryDate': types.TIMESTAMP, 'ExchangeRate': types.FLOAT, 'ExchangeDate': types.TIMESTAMP,
                 'TotalTax1': types.FLOAT, 'RevisionNum': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    fact_purchase_order.to_sql(table13, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table13), max_fecha_tabla = fact_purchase_order['OrderDate'].max(), cantidad_registros = len(fact_purchase_order))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table13), observacion = str(e))

try:
    # Fact Purchase Order Lines
    fact_purchase_order_lines = (pd.read_sql(read_query(query_purchase_order_lines), fn.enginemx)
                                 .assign(EnterDate = lambda x: pd.to_datetime(x["EnterDate"]).dt.date,
                                         PoNum = lambda x: pd.to_numeric(x["PoNum"].astype(str).str.replace("C", "", regex = False), errors = "coerce"),
                                         VenDeliveryDate = lambda x: pd.to_datetime(x["VenDeliveryDate"]).dt.date,
                                         InsertDate = datetime.now()))

    # Envio de los datos al DW
    sql_types = {'PoNum': types.INTEGER, 'OrderQty': types.FLOAT, 'UnitCost': types.FLOAT,
                 'ReceivedQty': types.FLOAT, 'ReceivedUnitCost': types.FLOAT, 'ReceivedTotalCost': types.FLOAT,
                 'RejectedQty': types.FLOAT, 'VenDeliveryDate': types.DATE, 'EnterDate': types.DATE,
                 'ReqDeliveryDate': types.DATE, 'Issue': types.INTEGER, 'PolineNum': types.INTEGER,
                 'Taxed': types.INTEGER, 'LineCost': types.FLOAT, 'Tax1': types.FLOAT, 'ReceiptReqd': types.INTEGER,
                 'LoadedCost': types.FLOAT, 'ReceiptsComplete': types.INTEGER, 'InspectionRequired': types.INTEGER,
                 'ProrateCost': types.FLOAT, 'PolineId':types.INTEGER, 'LineCost2': types.FLOAT,
                 'RefWo': types.INTEGER, 'EnteredAsTask': types.INTEGER, 'Conversion': types.FLOAT,
                 'MktplcItem': types.INTEGER, 'RevisionNum': types.INTEGER, 'TaxExempt': types.INTEGER,
                 'LineCost1': types.FLOAT, 'LoadedCost1': types.FLOAT, 'Obsequio': types.INTEGER,
                 'Descuento': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    fact_purchase_order_lines.to_sql(table14, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table14), max_fecha_tabla = fact_purchase_order_lines['EnterDate'].max(), cantidad_registros = len(fact_purchase_order_lines))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table14), observacion = str(e))

try:
    # Dim Item
    dim_item = (pd.read_sql(read_query(query_item), fn.enginemx)
                .assign(InsertDate = datetime.now()))

    dim_item.to_sql(table15, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table15), max_fecha_tabla = dim_item['StatusDate'].max(), cantidad_registros = len(dim_item))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table15), observacion = str(e))

try:
    # Dim Item Specification
    dim_item_spec = (pd.read_sql(read_query(query_item_spec), fn.enginemx)
                     .assign(InsertDate = datetime.now()))

    dim_item_spec.to_sql(table16, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table16), max_fecha_tabla = dim_item_spec['ChangeDate'].max(), cantidad_registros = len(dim_item_spec))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table16), observacion = str(e))

try:
    # Dim Empresas
    dim_empresa = (pd.read_sql(''' SELECT company as Company, name as Name 
                                   FROM GRMAXPR.dbo.companies ''', con = fn.enginemx)
                        .assign(InsertDate = datetime.now()))

    dim_empresa.to_sql(table17, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table17), max_fecha_tabla = datetime.now(), cantidad_registros = len(dim_empresa))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table17), observacion = str(e))

try:
    # Dim Tareas
    dim_tareas = (pd.read_sql(''' SELECT sistem as "Sistema", description as "Description", 
                                         taskduration as "Duration", tipo as "Tipo", activa as "Estado"
                                  FROM GRMAXPR.dbo.tareas
                                  WHERE description IS NOT NULL ''', con = fn.enginemx)
                    .assign(Description = lambda x: x["Description"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True),
                            Duration = lambda x: x["Duration"].round(3),
                            Estado = lambda x: x["Estado"].apply(lambda v: True if v == 1 else False),
                            InsertDate = datetime.now()))

    # Envio de los datos al DW
    sql_types = {'Duration': types.FLOAT, 'Estado': types.BOOLEAN, 'InsertDate': types.TIMESTAMP}

    dim_tareas.to_sql(table18, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table18), max_fecha_tabla = datetime.now(), cantidad_registros = len(dim_tareas))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table18), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)
