#**********************************************************************************************
# @Nombre: Proceso para obtener los datos de SIESA
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import numpy as np                     # Manipulacion numerica
import os                              # Manejo del sistema
import Funciones as fn                 # Funciones ETL
from skimpy import clean_columns       # Limpieza de nombres de columnas
from sqlalchemy import types           # Manejo de tipos de campos en db
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1114
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso SIESA*"
table1 = 'DimEmpresas'
table2 = 'DimTerceros'
table3 = 'DimCentroCosto'
table4 = 'DimAuxiliares'
table5 = 'DimBalanceEstado'
table6 = 'DimPptoReporte'
table7 = 'DimFlujoEfectivo'
table8 = 'DimActivos'
table9 = 'FactPptoFlujoEfectivo'
table10 = 'FactMovimiento'
table11 = 'FactPresupuesto'
table12 = 'FactMovimientosActivos'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# path del proyecto para leer los querys
path_project = os.getenv("PAT_PROJECT")

# Funcion para leer querys SQL desde archivos
def read_sql_file(relative_path: str) -> str:
    # Lee un archivo .sql y retorna el query como string
    full_path = os.path.join(path_project, relative_path)

    with open(full_path, "r", encoding = "utf-8") as f:
        return f.read()

# Dimensiones
try:
    # Dim empresas
    dim_empresas = (pd.read_sql(read_sql_file("00 Querys/DimEmpresas.sql"), fn.enginesi)
                    .assign(Nit = lambda df: (df["Nit"].astype(str)
                                              .str.replace(r"\D", "", regex = True)
                                              .replace("", np.nan)
                                              .astype("Int64")),
                            InsertDate = datetime.now()))
    
    sql_types = {'IdCompania': types.INTEGER, 'Nit': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    dim_empresas.to_sql(table1, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = dim_empresas["InsertDate"].max(), cantidad_registros = len(dim_empresas))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

try:
    # Dim terceros
    dim_terceros = (pd.read_sql(read_sql_file("00 Querys/DimTerceros.sql"), fn.enginesi)
                    .assign(IdTercero = lambda df: df["IdTercero"].astype(str).str.strip(),
                            RazonSocial = lambda df: df["RazonSocial"].astype(str).str.strip(),
                            PkTerceros = lambda df: (df["IdCompania"].astype(str) + df["RowId"].astype(str)).astype("Int64"),
                            InsertDate = datetime.now()))

    sql_types = {'IdCompania': types.INTEGER, 'RowId': types.INTEGER, 'PkTerceros': types.INTEGER, 
                 'InsertDate': types.TIMESTAMP}

    dim_terceros.to_sql(table2, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = dim_terceros["InsertDate"].max(), cantidad_registros = len(dim_terceros))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

try:
    # Dim centro de costos
    dim_cc = (pd.read_sql(read_sql_file("00 Querys/DimCentroCostos.sql"), fn.enginesi)
              .assign(Descripcion = lambda df: df["Descripcion"].astype(str).str.strip(),
                      IdCentroCosto = lambda df: df["IdCentroCosto"].astype(str).str.strip(),
                      PkCentroCosto = lambda df: (df["IdCompania"].astype(str) + df["RowId"].astype(str)).astype("Int64"),
                      InsertDate = datetime.now()))

    sql_types = {'IdCompania': types.INTEGER, 'RowId': types.INTEGER, 'IndEstado': types.INTEGER,
                 'IdCentroCostoMayor': types.INTEGER, 'PkCentroCosto': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    dim_cc.to_sql(table3, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = dim_cc["InsertDate"].max(), cantidad_registros = len(dim_cc))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))

try:
    # Dim Cuentas contables y auxiliares
    query_mayores = """SELECT f252_id as Id, f252_descripcion as Descripcion, f252_nivel as Nivel, 
                              f252_id_padre as IdPadre
                              FROM BI_GRMUNOEREALUF06.dbo.t252_co_mayores """

    dim_mayores = (pd.read_sql(query_mayores, fn.enginesi)
                   .applymap(lambda x: x.strip() if isinstance(x, str) else x))

    # parse_number equivalente
    for col in ["Id", "Nivel", "IdPadre"]:
        dim_mayores[col] = pd.to_numeric(dim_mayores[col], errors = "coerce")

    # DIM AUXILIARES

    dim_auxiliares = (pd.read_sql(read_sql_file("00 Querys/DimAuxiliares.sql"), fn.enginesi)
                      .assign(Descripcion = lambda df: df["Descripcion"].astype(str).str.strip(),
                              IdAuxiliar = lambda df: pd.to_numeric(df["IdAuxiliar"], errors = "coerce"))
                      .assign(Nivel1 = lambda df: df["IdAuxiliar"].astype(str).str[:1].astype(float),
                              Nivel2 = lambda df: df["IdAuxiliar"].astype(str).str[:2].astype(float),
                              Nivel3 = lambda df: df["IdAuxiliar"].astype(str).str[:4].astype(float),
                              Nivel4 = lambda df: df["IdAuxiliar"].astype(str).str[:6].astype(float),)
                      .merge(dim_mayores[["Id", "Descripcion"]], left_on = "Nivel1", right_on = "Id", how = "left", suffixes = ("", "N1"))
                      .merge(dim_mayores[["Id", "Descripcion"]], left_on = "Nivel2", right_on = "Id", how = "left", suffixes = ("", "N2"))
                      .merge(dim_mayores[["Id", "Descripcion"]], left_on = "Nivel3", right_on = "Id", how = "left", suffixes = ("", "N3"))
                      .merge(dim_mayores[["Id", "Descripcion"]], left_on = "Nivel4", right_on = "Id", how = "left", suffixes = ("", "N4"))
                      .assign(PkAuxiliar = lambda df: (df["IdCompania"].astype(str) + df["IdAuxiliar"].astype(str)).astype("Int64"),
                              InsertDate = datetime.now()))

    sql_types = {'IdCompania': types.INTEGER, 'RowId': types.INTEGER, 'IdAuxiliar': types.FLOAT, 
                 'Nivel1': types.FLOAT, 'Nivel2': types.FLOAT, 'Nivel3': types.FLOAT, 'Nivel4': types.FLOAT,
                 'PkAuxiliar': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    dim_auxiliares.to_sql(table4, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), max_fecha_tabla = dim_auxiliares["InsertDate"].max(), cantidad_registros = len(dim_auxiliares))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), observacion = str(e))

try:
    # Dim Balance
    archivo = os.path.join(path_project, "01 Inputs", "cuentas_finanzas.xlsx")
    #ppto_operacion
    #ppto_provision
    #blc_operacion
    #blc_provision

    # Balance operacion
    dim_balance_ope = (clean_columns(pd.read_excel(archivo, sheet_name = "blc_operacion"), case = 'pascal')
                            .drop_duplicates()
                            .loc[:, lambda df: df.loc[:, "Codigo":"Nivel2Er"].columns]
                            .assign(key = 1)
                            .merge(pd.DataFrame({"IdCompania": [1, 3], "key": [1, 1]}), on = "key", how = "inner")
                            .drop(columns = "key")
                            .pipe(lambda df: df[["IdCompania"] + [c for c in df.columns if c != "IdCompania"]])
                            .assign(PkAuxiliar = lambda df: (df["IdCompania"].astype(str) + df["Codigo"].astype(str)).astype("Int64"),
                                    InsertDate = datetime.now()))

    # Balance provision
    dim_balance_pro = (clean_columns(pd.read_excel(archivo, sheet_name = "blc_provision"), case = 'pascal')
                       .drop_duplicates()
                       .loc[:, lambda df: df.loc[:, "Codigo":"Nivel2Er"].columns]
                       .assign(key = 1)
                       .merge(pd.DataFrame({"IdCompania": [2, 4], "key": [1, 1]}), on = "key", how = "inner")
                       .drop(columns = "key")
                       .pipe(lambda df: df[["IdCompania"] + [c for c in df.columns if c != "IdCompania"]])
                       .assign(PkAuxiliar = lambda df: (df["IdCompania"].astype(str) + df["Codigo"].astype(str)).astype("Int64"),
                               InsertDate = datetime.now()))

    # Union de ambos balances
    dim_balance = pd.concat([dim_balance_ope, dim_balance_pro], ignore_index = True)

    sql_types = {'IdCompania': types.INTEGER, 'Codigo': types.INTEGER, 'PkAuxiliar': types.INTEGER,
                 'InsertDate': types.TIMESTAMP}

    dim_balance.to_sql(table5, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), max_fecha_tabla = dim_balance["InsertDate"].max(), cantidad_registros = len(dim_balance))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table5), observacion = str(e))

try:
    # Dim Presupuesto
    archivo = os.path.join(path_project, "01 Inputs", "cuentas_finanzas.xlsx")

    # Ptto operacion
    dim_ppto_ope = (clean_columns(pd.read_excel(archivo, sheet_name = "ppto_operacion"), case = 'pascal')
                    .drop_duplicates()
                    .loc[:, lambda df: df.loc[:, "Codigo":"Area"].columns]
                    .assign(key = 1)
                    .merge(pd.DataFrame({"IdCompania": [1, 3], "key": [1, 1]}), on = "key", how = "inner")
                    .drop(columns = "key")
                    .pipe(lambda df: df[["IdCompania"] + [c for c in df.columns if c != "IdCompania"]])
                    .assign(PkRepoPpto = lambda df: np.where(df["CentroDeCosto"].isna(), df["IdCompania"].astype(str) + df["Codigo"].astype(str), df["IdCompania"].astype(str) + df["Codigo"].astype(str) + df["CentroDeCosto"].astype(str)),
                            InsertDate = datetime.now()))

    # Ppto provision
    dim_ppto_pro = (clean_columns(pd.read_excel(archivo, sheet_name = "ppto_provision"), case = 'pascal')
                    .drop_duplicates()
                    .loc[:, lambda df: df.loc[:, "Codigo":"Area"].columns]
                    .assign(key = 1)
                    .merge(pd.DataFrame({"IdCompania": [2, 4], "key": [1, 1]}), on = "key", how = "inner")
                    .drop(columns = "key")
                    .pipe(lambda df: df[["IdCompania"] + [c for c in df.columns if c != "IdCompania"]])
                    .pipe(lambda df: df.assign(CentroDeCosto = np.nan) if "CentroDeCosto" not in df.columns else df)
                    .pipe(lambda df: (df if "Nivel1" not in df.columns 
                                      else df[(lambda cols: (cols.insert(cols.index("Nivel1"), cols.pop(cols.index("CentroDeCosto"))) or cols))(list(df.columns))]))
                    .assign(PkRepoPpto = lambda df: np.where(df["CentroDeCosto"].isna(), df["IdCompania"].astype(str) + df["Codigo"].astype(str), df["IdCompania"].astype(str) + df["Codigo"].astype(str) + df["CentroDeCosto"].astype(str)),
                            InsertDate = datetime.now()))
    
    # Union de ambos presupuestos
    dim_ppto = (pd.concat([dim_ppto_ope, dim_ppto_pro], ignore_index = True)
                .assign(IsCentro = lambda df: df["CentroDeCosto"].notna(),
                        PkRepoPpto = lambda df: pd.to_numeric(df["PkRepoPpto"])))

    # Proceso para validacion si un auxiliar tiene un centro de costos
    centros = (dim_ppto[["IdCompania", "Codigo", "IsCentro"]]
               .assign(PkAuxiliar = lambda d: (d["IdCompania"].astype(str) + d["Codigo"].astype(str)).astype("Int64"))
               .sort_values(["PkAuxiliar", "IsCentro"], ascending = [True, False])
               .drop_duplicates(subset = "PkAuxiliar", keep = "first")[["PkAuxiliar", "IsCentro"]]
               .reset_index(drop = True))

    sql_types = {'IdCompania': types.INTEGER, 'Codigo': types.INTEGER, 'CentroDeCosto': types.INTEGER,
                 'PkRepoPpto': types.BIGINT, 'IsCentro': types.BOOLEAN, 'InsertDate': types.TIMESTAMP}

    dim_ppto.to_sql(table6, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), max_fecha_tabla = dim_ppto["InsertDate"].max(), cantidad_registros = len(dim_ppto))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table6), observacion = str(e))

try:
    # Dim Conceptos flujo efectivo
    archivo = os.path.join(path_project, "01 Inputs", "cuentas_finanzas.xlsx")

    fe_operacion = (clean_columns(pd.read_excel(archivo, sheet_name = "fe_operacion"), case = 'pascal')
                    .drop_duplicates()
                    .assign(key = 1)
                    .merge(pd.DataFrame({"IdCompania": [1, 3], "key": [1, 1]}), on = "key", how = "inner")
                    .drop(columns = "key")
                    .pipe(lambda df: df[(lambda cols: (cols.insert(cols.index("IdFlujoEfectivo"), cols.pop(cols.index("IdCompania"))) or cols))(list(df.columns))])
                    .assign(IdCompania = lambda df: df["IdCompania"].astype(int),
                            IdFlujoEfectivo = lambda df: df["IdFlujoEfectivo"].astype(int)))

    fe_provision = (clean_columns(pd.read_excel(archivo, sheet_name = "fe_provision"), case = 'pascal')
                    .drop_duplicates()
                    .assign(key = 1)
                    .merge(pd.DataFrame({"IdCompania": [2, 4], "key": [1, 1]}), on = "key", how = "inner")
                    .drop(columns = "key")
                    .pipe(lambda df: df[(lambda cols: (cols.insert(cols.index("IdFlujoEfectivo"), cols.pop(cols.index("IdCompania"))) or cols))(list(df.columns))])
                    .assign(IdCompania = lambda df: df["IdCompania"].astype(int),
                            IdFlujoEfectivo = lambda df: df["IdFlujoEfectivo"].astype(int)))
    
    # Union de ambos conceptos de flujo efectivo
    cuentas_flujo = pd.concat([fe_operacion, fe_provision], ignore_index = True)

    dim_flujoefectivo = (pd.read_sql(read_sql_file("00 Querys/DimConceptosFlujoEfectivo.sql"), fn.enginesi)
                         .assign(Descripcion = lambda df: df["Descripcion"].astype(str).str.strip(),
                                 IdFlujoEfectivo = lambda df: (df["IdFlujoEfectivo"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64")),
                                 PkFlujoEfectivo = lambda df: (df["IdCompania"].astype(str) + df["RowIdFlujoEfectivo"].astype(str)).astype("Int64"))
                         .merge(cuentas_flujo, how = "left", on = ["IdCompania", "IdFlujoEfectivo"])
                         .assign(InsertDate = datetime.now()))

    sql_types = {'IdCompania': types.INTEGER, 'RowIdFlujoEfectivo': types.INTEGER, 'IdFlujoEfectivo': types.INTEGER,
                 'PkFlujoEfectivo': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    dim_flujoefectivo.to_sql(table7, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table7), max_fecha_tabla = dim_flujoefectivo["InsertDate"].max(), cantidad_registros = len(dim_flujoefectivo))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table7), observacion = str(e))

try:
    # Dim Activos Fijos
    dim_activos = (pd.read_sql(read_sql_file("00 Querys/DimActivosFijos.sql"), fn.enginesi)
                   .assign(Nit = lambda d: (d["Nit"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64")),
                           CentroCostoCodigo = lambda d: (d["CentroCostoCodigo"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64")),
                           Identificacion = lambda d: (d["Identificacion"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64")),
                           InsertDate = datetime.now()))
    
    sql_types = {'Nit': types.INTEGER, 'CentroCostoCodigo': types.INTEGER, 'Identificacion': types.BIGINT,
                 'FechaAdq': types.DATE, 'InsertDate': types.TIMESTAMP}

    dim_activos.to_sql(table8, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table8), max_fecha_tabla = dim_activos["InsertDate"].max(), cantidad_registros = len(dim_activos))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table8), observacion = str(e))

try:
    # Fact Presupuesto Flujo Efectivo
    fact_ppto_flujoefectivo = (pd.read_sql(read_sql_file("00 Querys/FactPptoFlujoEfectivo.sql"), fn.enginesi)
                         .assign(FlujoEfectivo = lambda d: d["FlujoEfectivo"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64"),
                                 InsertDate = datetime.now()))

    sql_types = {'FlujoEfectivo': types.INTEGER, 'Periodo': types.INTEGER, 'Valor': types.FLOAT,
                 'InsertDate': types.TIMESTAMP}

    fact_ppto_flujoefectivo.to_sql(table9, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table9), max_fecha_tabla = fact_ppto_flujoefectivo["InsertDate"].max(), cantidad_registros = len(fact_ppto_flujoefectivo))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table9), observacion = str(e))
    
# Hechos
try:
    # Movimientos
    centrovalida = (dim_ppto["CentroDeCosto"].dropna().astype(str).unique())

    fact_movimiento = (pd.read_sql(read_sql_file("00 Querys/FactMovimientoDocumentos.sql"), fn.enginesi)
        .assign(IdAuxiliar = lambda d: (d["IdAuxiliar"].astype(str).str.strip().str.extract(r"(\d+)", expand = False).astype("Int64")),
                CentroDeCosto = lambda d: (d["CentroDeCosto"].astype(str).str.strip()),
                PkTerceros = lambda d: pd.to_numeric(d["IdCompania"].astype(str) + d["RowIdTercero"].astype(str), errors = "coerce"),
                PkFlujoEfectivo = lambda d: pd.to_numeric(d["IdCompania"].astype(str) + d["RowIdFlujoEfectivo"].astype(str), errors = "coerce"),
                PkCentroCosto = lambda d: pd.to_numeric(d["IdCompania"].astype(str) + d["RowIdCentroCosto"].astype(str), errors = "coerce"),
                PkAuxiliar = lambda d: pd.to_numeric(d["IdCompania"].astype(str) + d["IdAuxiliar"].astype(str), errors = "coerce"),
                InsertDate = datetime.now())
        .merge(centros, on = "PkAuxiliar", how = "left")
        .assign(PkRepoPpto = lambda d: np.where(d["IsCentro"] == True, (d["IdCompania"].astype(str) + d["IdAuxiliar"].astype(str) + d["CentroDeCosto"].astype(str)),
                                                (d["IdCompania"].astype(str) + d["IdAuxiliar"].astype(str))))
        .assign(PkRepoPpto = lambda d: d["PkRepoPpto"].astype("Int64"))
        .drop(columns = ["IsCentro"]))
    
    sql_types = {'IdCompania': types.INTEGER, 'ConsecutivoDocumento': types.INTEGER, 'IdAuxiliar': types.INTEGER,
                 'RowIdTercero': types.INTEGER, 'RowIdCentroCosto': types.INTEGER, 'RowIdFlujoEfectivo': types.INTEGER,
                 'Fecha': types.DATE, 'ValorDebito2': types.FLOAT, 'ValorCredito2': types.FLOAT, 
                 'PkTerceros': types.INTEGER, 'PkFlujoEfectivo': types.INTEGER, 'PkCentroCosto': types.INTEGER, 
                 'PkAuxiliar': types.INTEGER, 'PkRepoPpto': types.BIGINT, 'InsertDate': types.TIMESTAMP}

    fact_movimiento.to_sql(table10, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table10), max_fecha_tabla = fact_movimiento["InsertDate"].max(), cantidad_registros = len(fact_movimiento))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table10), observacion = str(e))

try:
    # Presupuesto
    fact_presupuesto = (pd.read_sql(read_sql_file("00 Querys/FactPresupuestoSiesa.sql"), fn.enginesi)
                        .assign(IdAuxiliar = lambda df: (df["IdAuxiliar"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True).str.extract(r"(\d+)", expand = False).astype("Int64")),
                                CentroDeCosto = lambda df: (df["CentroDeCosto"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True)),
                                Periodo = lambda df: pd.to_datetime(df["Periodo"].astype(str) + "01", format = "%Y%m%d", errors = "coerce"),
                                PkAuxiliar = lambda df: (df["IdCompania"].astype(str) + df["IdAuxiliar"].astype(str)).astype("Int64"),
                                InsertDate = datetime.now())
                        .merge(centros, on = "PkAuxiliar", how = "left")
                        .assign(PkRepoPpto = lambda df: pd.to_numeric(np.where(df["IsCentro"] == True, df["IdCompania"].astype(str) + df["IdAuxiliar"].astype(str) + df["CentroDeCosto"].astype(str), df["IdCompania"].astype(str) + df["IdAuxiliar"].astype(str)), errors = "coerce"))
                        .drop(columns = ["IsCentro"]))

    sql_types = {'IdCompania': types.INTEGER, 'RowIdAuxiliar': types.INTEGER, 'IdAuxiliar': types.INTEGER,
                 'RowIdCentroCosto': types.INTEGER, 'Periodo': types.DATE, 'Valor': types.FLOAT,
                 'PkAuxiliar': types.INTEGER, 'PkRepoPpto': types.BIGINT, 'InsertDate': types.TIMESTAMP}

    fact_presupuesto.to_sql(table11, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table11), max_fecha_tabla = fact_presupuesto["InsertDate"].max(), cantidad_registros = len(fact_presupuesto))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table11), observacion = str(e))

try:
    # Movimientos Activos Fijos
    fact_movact = (pd.read_sql(read_sql_file("00 Querys/FactMovimientosActivos.sql"), fn.enginesi)
                   .assign(Fecha = lambda df: pd.to_datetime(df["Fecha"].astype(str), errors = "coerce").dt.date,        
                           CentroCostoCodigo = lambda df: (df["CentroCostoCodigo"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True).str.extract(r"(\d+)", expand = False).astype("Int64")),
                           Identificacion = lambda df: (df["Identificacion"].astype(str).str.strip().str.replace(r"\s+", " ", regex = True).str.extract(r"(\d+)", expand = False).astype("Int64")),
                           InsertDate = datetime.now()))
    
    sql_types = {'Fecha': types.DATE, 'PeriodoDepreciar': types.INTEGER, 'PeriodosDepreciados': types.FLOAT,
                 'PeriodosPendientesDepreciar': types.FLOAT, 'Depreciacion': types.FLOAT, 'CostoMovimiento': types.FLOAT,
                 'PeriodosDepreciadosMovimiento': types.FLOAT, 'CentroCostoCodigo': types.INTEGER, 
                 'Identificacion': types.BIGINT, 'InsertDate': types.TIMESTAMP}

    fact_movact.to_sql(table12, schema = "cn", con = fn.cona, if_exists = "replace", index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table12), max_fecha_tabla = fact_movact["Fecha"].max(), cantidad_registros = len(fact_movact))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table12), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_CONTROLPRES')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
