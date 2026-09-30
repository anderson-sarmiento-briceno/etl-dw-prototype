#**********************************************************************************************
# @Nombre: Transformacion Datos energia Terpel
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                     # Manipulacion de datos
import numpy as np                                      # Manipulacion numerica
import os                                               # Manejo del sistema
import Funciones as fn                                  # Funciones ETL
import subprocess                                       # Ejecucion de procesos externos
import gspread                                          # Manipulacion de Google Sheets
from skimpy import clean_columns                        # Limpieza de nombres de columnas
from sqlalchemy import types                            # Definir tipos de datos para sql
from skimpy import clean_columns                        # Limpieza de nombres de columnas
from google.oauth2.service_account import Credentials   # Autenticacion con Google Sheets
from datetime import datetime                           # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1061
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Consumo Terpel*"
table1 = "FactCostoEnergia"
table2 = "FactProvisionEnergia"
table3 = "FactPrecioBolsaxHora"

# Funcion de indexacion segun el periodo
def indexacion(fecha, ipp):
    anio = fecha.year
    if anio == 2022:
        # Se calcula el valor con el que se comparara el valor maximo 
        # @ipp de dic 2021 = 147.65
        # @ipp de feb 2021 = 128.63
        valor_validacion = ipp / 147.65
        # Formula para el 2022 desde septiembre hasta diciembre
        return round((147.65 / 128.63) *
                     min(1.155, valor_validacion), 9)
    elif anio == 2023:
        # Se calcula el valor con el que se comparara el valor maximo
        valor_validacion = 176.17 / 147.65
        # Formula para el 2023
        # @ipp de dic 2021 = 147.65
        # @ipp de feb 2021 = 128.63
        # # @ipp de dic 2022 = 176.17
        return round((147.65 / 128.63) *
                     min(1.155, valor_validacion) *
                     (ipp / 176.17), 9)
    else:
        # Formula para el 2024 en adelante
        # @ipp de feb 2021 = 128.63
        return round((ipp / 128.63), 9)

# Funcion para distribucion de energia
def kwhrcurva(kwhr, pld1, pld2):
    total = pld1 + pld2
    kwhr_pld1 = np.where(kwhr <= pld1, kwhr, pld1)
    kwhr_pld2 = np.where((kwhr > pld1) & (kwhr <= total), kwhr - pld1,
                         np.where(kwhr > total, pld2, 0))
    kwhr_bolsa = np.where(kwhr > total, kwhr - total, 0)
    return kwhr_pld1, kwhr_pld2, kwhr_bolsa

def relleno(series):
    return series.ffill()

try:
    rut = r"E:\Drive\greenmovil.com.co\Gestion Mantenimiento - General\Documentos\10 Datos\13 PreciosBolsa\FactPreciosBolsaHora.xlsx"

    prec = (clean_columns(pd.read_excel(rut), case = "pascal")
            .drop(columns = ["Version"])
            .melt(id_vars = ['Fecha'], var_name = 'Hora', value_name = 'CostoBolsa')
            .assign(Hora = lambda x: pd.to_numeric(x["Hora"], errors = "coerce"),
                    InsertDate = datetime.now()))
    
    # Envio de los datos al DW
    sql_types = {'Fecha': types.DATE, 'Hora': types.INTEGER, 'CostoBolsa': types.FLOAT, 
                 'InsertDate': types.TIMESTAMP}

    # Carga a tabla
    prec.to_sql(table3, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = prec["Fecha"].max(), cantidad_registros = len(prec))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))


# Calculo del costo de la energia
try:
    ## Leer los datos del IPP
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_file("01 Inputs/credenciales.json", scopes = scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1IZnU1oj4vXXohk028YdbMl08TXb1kKS5BB0LfFbPoWc")

    # IPP
    FactIPP = (clean_columns(pd.DataFrame(sheet.worksheet("Indices").get_all_records()), case = "pascal")
               .assign(Fecha = lambda df: pd.to_datetime(df["Fecha"], format = "%Y%m%d"),
                       Ipp = lambda x: relleno(x["Ipp"]))
                .loc[:, ["Fecha", "Ipp"]])

    # Precios regulados
    FactPreciosRegulados = (clean_columns(pd.DataFrame(sheet.worksheet("PreciosRegulados").get_all_records()), case = "pascal")
                            .assign(Fecha = lambda df: pd.to_datetime(df["Fecha"], format = "%Y%m%d"))
                            .drop(columns = ["G", "C", "Cu"]))

    ## Curva del costo de la energía según contrato
    curva_terpel = pd.read_sql(""" SELECT "Hora", "Pld1", "Pld2", "Pld1"+"Pld2" AS "Total", 
                                          "CostoKwHpld1"-10 AS "CostoPld1", "CostoKwHpld2"-10 AS "CostoPld2"
                                   FROM ma."FactConsumoCurvaTerpel" """, fn.enginea)

    ## Se obtiene los datos de precio de bolsa
    bolsa_ponderado = pd.read_sql(""" SELECT "Fecha", "PppDeEscasez", "PrecioEscasezActivacion"
                                      FROM ma."FactPrecioBolsaPonderado" """, fn.enginea)

    bolsa_energ = (pd.read_sql(""" SELECT "Fecha", "Hora", "CostoBolsa" AS "PrecioBolsa"
                                  FROM ma."FactPrecioBolsaxHora" """, fn.enginea)
                        .merge(bolsa_ponderado, on = "Fecha", how = "left")
                        .assign(PrecioEscasezActivacion = lambda df: np.where(df["PrecioEscasezActivacion"].isna(), df["PrecioBolsa"], df["PrecioEscasezActivacion"]),
                                PrecioBolsa = lambda df: np.where(df["PrecioBolsa"] > df["PrecioEscasezActivacion"], df["PppDeEscasez"], df["PrecioBolsa"]))
                        .drop(columns = ["PppDeEscasez", "PrecioEscasezActivacion"]))

     # Se trae la tabla del DW
    dataterpel = pd.read_sql(""" SELECT "Fecha", "Empresa", "Variable", "Hora", "Kwhr"
                                 FROM ma."FactConsumoTerpel" """, fn.enginea)

    ## Calculo de Fact de precios de bolsa
    data_total = (dataterpel.query("Variable == 'kWhD'")
                  .assign(Hora = lambda df: df["Hora"].astype(int))
                  # Se suma la energía consumida por fecha empresa y hora
                  .groupby(["Fecha", "Empresa", "Hora"], as_index = False)["Kwhr"]
                  .sum()
                  # Se añade la curva de terpel
                  .merge(curva_terpel, on = "Hora")
                  # Se añaden los precios de bolsa
                  .merge(bolsa_energ, on = ["Fecha", "Hora"])
                  .assign(KwhrPld1 = lambda df: kwhrcurva(df["Kwhr"].values, df["Pld1"].values, df["Pld2"].values)[0],
                          KwhrPld2 = lambda df: kwhrcurva(df["Kwhr"].values, df["Pld1"].values, df["Pld2"].values)[1],
                          KwhrBolsa = lambda df: kwhrcurva(df["Kwhr"].values, df["Pld1"].values, df["Pld2"].values)[2])
                  .assign(Mes = lambda df: pd.to_datetime(df["Fecha"]).dt.to_period("M").dt.to_timestamp())
                  .merge(FactIPP.rename(columns = {"Fecha": "Mes"}), on = "Mes", how = "left")
                  # Se aplica fórmula de Indexación según aplique el periodo
                  .assign(Indexacion = lambda df: df.apply(lambda x: indexacion(x["Fecha"], pd.to_numeric(x["Ipp"], errors = "coerce")), axis = 1))
                  .assign(CostoIndexPld1 = lambda df: df["CostoPld1"] * df["Indexacion"] * df["KwhrPld1"],
                          CostoIndexPld2 = lambda df: df["CostoPld2"] * df["Indexacion"] * df["KwhrPld2"],
                          CostoBolsa = lambda df: df["PrecioBolsa"] * df["KwhrBolsa"],
                          InsertDate = datetime.now(),
                          Ipp = lambda df: pd.to_numeric(df["Ipp"], errors = "coerce"))
                  .drop(columns = "Mes"))

    # Envio de los datos al DW
    sql_types = {'Fecha': types.DATE, 'Hora': types.INTEGER, 'Kwhr': types.FLOAT,
                 'Pld1': types.INTEGER, 'Pld2': types.INTEGER, 'Total': types.INTEGER,
                 'CostoPld1': types.FLOAT, 'CostoPld2': types.FLOAT, 'PrecioBolsa': types.FLOAT,
                 'KwhrPld1': types.FLOAT, 'KwhrPld2': types.FLOAT, 'KwhrBolsa': types.FLOAT,
                 'Ipp': types.FLOAT, 'Indexacion': types.FLOAT, 'CostoIndexPld1' : types.FLOAT,
                 'CostoIndexPld2': types.FLOAT, 'CostoBolsa': types.FLOAT,
                 'InsertDate': types.TIMESTAMP}

    # Carga a tabla
    data_total.to_sql(table1, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = data_total["Fecha"].max(), cantidad_registros = len(data_total))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

# Proceso de Provisionamiento de Factura
try:
    # Total energía reactiva consumida
    data_reac = (dataterpel.query("Variable == 'kVarhR'")
                 .assign(Mes = lambda df: pd.to_datetime(df["Fecha"]).dt.to_period("M").dt.to_timestamp())
                 .groupby(["Mes", "Empresa"], as_index = False)["Kwhr"]
                 .sum()
                 .rename(columns = {"Kwhr": "TotalKwR"}))

    #Informacion final de la factura para provisión de eneria
    # Información factura oficinas
    data_factura_of = (data_total.assign(Mes = lambda df: pd.to_datetime(df["Fecha"]).dt.to_period("M").dt.to_timestamp())
                       .loc[lambda df: df["Empresa"] == "OFICINAS"]
                       .groupby(["Mes", "Empresa"], as_index = False)
                       .agg(KwOf = ("Kwhr", "sum"),
                            CostoIndexPld1 = ("CostoIndexPld1", "sum"),
                            Indexacion = ("Indexacion", "max"))
                        .assign(Empresa = "ZMOIII", 
                                C = lambda df: 10 * df["Indexacion"] * df["KwOf"])
                        .merge(FactPreciosRegulados, left_on = ["Mes", "Empresa"], right_on = ["Fecha", "Empresa"], how = "left")
                        .assign(CostoOficinas = lambda df: (df["CostoIndexPld1"] + df["C"] + (df["Transmision"] * df["KwOf"]) + (df["D"] * df["KwOf"]) + (df["Pr"] * df["KwOf"]) + (df["R"] * df["KwOf"])))
                        .drop(columns = "Fecha"))

    # Informacion factura final 
    data_factura = (data_total.assign(Mes = lambda df: pd.to_datetime(df["Fecha"]).dt.to_period("M").dt.to_timestamp(),
                                      CostoTmp = lambda df: df["CostoIndexPld1"] + df["CostoIndexPld2"] + df["CostoBolsa"])
                              .query("Empresa != 'OFICINAS'")
                              .groupby(["Mes", "Empresa"], as_index = False)
                              .agg(Kwhr = ("Kwhr", "sum"),
                                   Costo = ("CostoTmp", "sum"),
                                   Indexacion = ("Indexacion", "max"))
                              .merge(data_reac, on = ["Mes", "Empresa"], how = "left")
                              .merge(FactPreciosRegulados.rename(columns = {"Fecha": "Mes"}), on = ["Mes", "Empresa"], how = "left")
                              .assign(C = lambda df: 10 * df["Indexacion"] * df["Kwhr"],
                                      CostoBuses = lambda df: (df["Costo"] + df["C"] + (df["Transmision"] * df["Kwhr"]) + (df["D"] * df["Kwhr"]) + (df["Pr"] * df["Kwhr"]) + (df["R"] * df["Kwhr"])),
                                      CostoReact = lambda df: df["TotalKwR"] * df["D"] * df["M"])
                              .merge(data_factura_of[["Mes", "Empresa", "KwOf", "CostoOficinas"]], on = ["Mes", "Empresa"], how = "left")
                              .assign(Contribucion = lambda df: df["CostoOficinas"] * 0.2,
                              Total = lambda df: np.where( df["Empresa"] == "ZMOV", df["CostoBuses"] + df["CostoReact"] + 161403, df["CostoBuses"] + df["CostoReact"] + df["Contribucion"] + 139021),
                              InsertDate = datetime.now()))

    # Envio de los datos al DW
    sql_types = {'Mes': types.DATE, 'Kwhr': types.FLOAT, 'Costo': types.FLOAT,
                 'Indexacion': types.FLOAT, 'TotalKwR': types.FLOAT, 'D': types.FLOAT,
                 'Transmision': types.FLOAT, 'Pr': types.FLOAT, 'R': types.FLOAT,
                 'M': types.FLOAT, 'C': types.FLOAT, 'CostoBuses': types.FLOAT,
                 'CostoReact': types.FLOAT, 'KwOf': types.FLOAT, 'CostoOficinas' : types.FLOAT,
                 'Contribucion': types.FLOAT, 'Total': types.FLOAT,
                 'InsertDate': types.TIMESTAMP}

    # Carga a tabla
    data_factura.to_sql(table2, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = data_factura["Mes"].max(), cantidad_registros = len(data_factura))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

# Actualizar dataset PowerBI
fn.update_process(id_process = IdProceso, engine = fn.enginea)
path = os.getenv("PAT_PBI_REFRESH")
subprocess.run(["python", path, os.getenv("PBI_CONSUMOENERGY")])
