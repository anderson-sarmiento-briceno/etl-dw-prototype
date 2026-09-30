#**********************************************************************************************
# @Nombre: Proceso de extraccion ausentismo y tiempo suplementario
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                         # Manipulacion de datos
import numpy as np                          # Manipulacion numerica
import os                                   # Manejo del sistema
import subprocess                           # Ejecucion de procesos externos
import Funciones as fn                      # Funciones ETL
from sqlalchemy import types                # Manejo de tipos de campos en db
from datetime import datetime               # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1170
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Ausentismo - Tiempo Suple*"
table1 = 'DimConceptosAus'
table2 = 'DimConceptosInca'
table3 = 'FactAusentismoKactus'
table4 = 'FactTiempoSuplementario'

# Notas ---------------------------------------------------------------------------------------
# 736 = ZMOIII - 7362 = ZMOV
# EL código 172 son de vacaciones y deben quitarse de la disponibilidad
# No se considera el codigo 522 el cual pertenece a los dominicales
# Incluye el código 2001 el cual contiene las personas de la escuela.

# Proceso de obtencion de datos
def expand_grid_df(df1, df2):
    df1["_tmp"] = 1
    df2["_tmp"] = 1
    out = df1.merge(df2, on = "_tmp").drop("_tmp", axis=1)
    df1.drop("_tmp", axis = 1, inplace = True)
    df2.drop("_tmp", axis = 1, inplace = True)
    return out

# Paths
userpc = "E:\\Drive"
incapacidad = "\\greenmovil.com.co\\Gestion Informacion - General\\07 Gestion_Humana\\"

# Cargue de Documentos de referencia
try:
    # Dimension de conceptos de ausentismo
    query = """ SELECT cod_conc as CodConcepto, nom_conc as NombreConcepto
                FROM KactusGrM.dbo.nm_conce """

    dimconceptos = (pd.read_sql(query, fn.enginekt).drop_duplicates("CodConcepto")
                    .assign(InsertDate = datetime.now(),
                            NombreConcepto = lambda x: x["NombreConcepto"].str.strip().str.title()))

    # Envio de los datos al DW
    sql_types = {'CodConcepto': types.INTEGER, 'InsertDate': types.TIMESTAMP}

    dimconceptos.to_sql(table1, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = datetime.today(), cantidad_registros = len(dimconceptos))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))


try:
    # Dimension de conceptos de incapacidad
    query = """ SELECT COD_DIAG as CodigoDiagnostico, NOM_DIAG as NombreDiagnostico
                FROM KactusGrM.dbo.SO_CODIA """

    dimincap = (pd.read_sql(query, fn.enginekt)
                        .assign(CodigoDiagnostico = lambda x: x["CodigoDiagnostico"].str.strip(),
                                NombreDiagnostico = lambda x: x["NombreDiagnostico"].str.strip().str.title(),
                                InsertDate = datetime.now())
                        .drop_duplicates("CodigoDiagnostico"))

    # Envio de los datos al DW
    sql_types = {'InsertDate': types.TIMESTAMP}

    dimincap.to_sql(table2, schema = 'public', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = datetime.today(), cantidad_registros = len(dimincap))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

# Se obtiene la planta de empleados
try:
    # Dimension de empleados
    query = """ SELECT "CodEmpresa", "CodEmpleado", "NombreEmpleado", "FechaContratacion", "FechaRetiro",
                       "Cargo", "NoSAE", "TelefonoMovil", "FechaNacimiento"
                FROM public."DimEmpleados"
                WHERE "CodCentroCostos" = 2001 """

    dimempleados = (pd.read_sql(query, fn.enginea).sort_values(["CodEmpleado", "FechaRetiro"])
                        .assign(Sec = lambda df: df.groupby("CodEmpleado").cumcount() + 1,
                                Total = lambda df: df.groupby("CodEmpleado")["CodEmpleado"].transform("count"))
                        .assign(FechaInicio = lambda df: np.where(df["Sec"] == 1, df["FechaContratacion"],
                                                                  df.groupby("CodEmpleado")["FechaRetiro"].shift() + pd.Timedelta(days = 1)),
                                FechaRetiro = lambda df: pd.to_datetime(df["FechaRetiro"].fillna(pd.Timestamp.today())),
                                CodEmpresa = lambda df: (df["CodEmpresa"].str.replace(".*III.*", "736", regex = True)
                                                                         .str.replace(".*V.*", "7362", regex = True)
                                                                         .astype(int)),
                                FechaContratacion = lambda x: pd.to_datetime(x["FechaContratacion"])))

    # Fact de ausentismos generados
    query = """ SELECT aus.cod_empr as "CodEmpresa", aus.cod_empl as "CodEmpleado", aus.cod_conc as "CodConcepto",
                       inc.COD_DIAR as "CodigoDiagnostico", aus.tip_ause as "TipoAusentismo", 
                       aus.fec_desd as "FechaInicio", aus.fec_hast as "FechaFin", aus.can_ause as "CantidadDias",
                       aus.can_ause * 8 as "TotalHoras"
                FROM KactusGrM.dbo.nm_ausen aus
                LEFT JOIN KactusGrM.dbo.nm_incap inc 
                    ON aus.cod_empr = inc.cod_empr 
                    AND aus.cod_empl = inc.cod_empl 
                    AND aus.cod_conc = inc.cod_conc 
                    AND aus.fec_desd = inc.fec_desd
                    AND aus.fec_hast = inc.fec_hast """

    kactusAusentismo = (pd.read_sql(query, fn.enginekt)
                        # El sistema registra solo para descontar el dominical pero no es una ausencia
                        .loc[lambda x: (x["CodEmpleado"].isin(dimempleados["CodEmpleado"])) & (x["CodConcepto"] != 522)]
                        .drop_duplicates()
                        .assign(CodigoDiagnostico = lambda x: (x["CodigoDiagnostico"].str.strip().str.replace(r"\s+", " ", regex = True))))

    # Funciones para expandir las fechas
    ExpandAusentismo = pd.DataFrame({"FechaAplicacion":pd.date_range(kactusAusentismo["FechaInicio"].min(), kactusAusentismo["FechaFin"].max(), freq = "D")})
    ExpandContratacion = pd.DataFrame({"FechaAplicacion": pd.date_range(dimempleados["FechaContratacion"].min(), dimempleados["FechaRetiro"].max(), freq = "D")})

    ## Procesamiento de datos ---------------------------------------------------------------------  
    # Transformación del fact de ausentimos para que eliminar la duplicidad de los registros por 
    # temas de sustitución patronal
    kactusAusentismo = (kactusAusentismo.merge(dimempleados[["CodEmpresa", "CodEmpleado", "FechaInicio", "FechaRetiro"]]
                                               .rename(columns = {"FechaInicio": "FechaContrato"}),
                                               on = ["CodEmpresa", "CodEmpleado"], how = "left")
                                        # Flag para saber que registro es el repetido, el cual debe eliminarse
                                        .assign(Flag = lambda x: ((x["FechaInicio"] >= x["FechaContrato"]) & (x["FechaFin"] <= x["FechaRetiro"])))
                                        .loc[lambda x: x["Flag"]]
                                        # se eliman duplicados para corregir posibles errores de digitacion
                                        .drop_duplicates(subset = ["CodEmpresa", "CodEmpleado", "FechaInicio", "FechaFin"])
                                        # Se hace una expansión de las fechas del ausentismo
                                        .pipe(expand_grid_df, ExpandAusentismo)
                                        # Validacion de aplicabilidad de las fechas
                                        .assign(Flag = lambda x: ((x["FechaAplicacion"] >= x["FechaInicio"]) & (x["FechaAplicacion"] <= x["FechaFin"])),
                                                HrsAusente = 8)
                                        .loc[lambda x: x["Flag"]][["CodEmpresa", "CodEmpleado", "CodConcepto",
                                                                   "CodigoDiagnostico", "TipoAusentismo", "FechaAplicacion", 
                                                                   "HrsAusente"]])

    # dataframe que muestra la relacion de fechas que la persona ha trabajado en la compañia
    FactAusentismoKactus = (dimempleados.pipe(expand_grid_df, ExpandContratacion)
                            .assign(Flag = lambda x: ((x["FechaAplicacion"] >= x["FechaInicio"]) & (x["FechaAplicacion"] <= x["FechaRetiro"])),
                                    HrsLaborales = 8)
                            .loc[lambda x: x["Flag"]][["CodEmpresa","CodEmpleado","Cargo","FechaAplicacion","HrsLaborales"]]
                            .merge(kactusAusentismo, on = ["CodEmpresa","CodEmpleado","FechaAplicacion"], how = "left")
                            .assign(InsertDate = datetime.now(), CodEmpresa = lambda x: np.where(x["CodEmpresa"] == 736, "ZMOIII", "ZMOV")))

    # Archivo Incapacidades
    dimempleados = (dimempleados[["CodEmpresa", "CodEmpleado", "NombreEmpleado", "NoSAE", "TelefonoMovil", "FechaNacimiento"]]
                    .drop_duplicates())

    # Consulta incapacidades
    query = """ SELECT aus.cod_empr as "CodEmpresa", aus.cod_empl as "CodEmpleado", aus.cod_conc as "CodConcepto",
                       inc.COD_DIAR as "CodigoDiagnostico", aus.tip_ause as "TipoAusentismo", aus.fec_desd as "FechaInicio",
                       aus.fec_hast as "FechaFin", aus.can_ause as "CantidadDias", aus.can_ause * 8 as "TotalHoras"
                FROM KactusGrM.dbo.nm_ausen aus
                LEFT JOIN KactusGrM.dbo.nm_incap inc 
                    ON aus.cod_empr = inc.cod_empr
                    AND aus.cod_empl = inc.cod_empl
                    AND aus.cod_conc = inc.cod_conc
                    AND aus.fec_desd = inc.fec_desd
                    AND aus.fec_hast = inc.fec_hast """
    incapacidades = (pd.read_sql(query, fn.enginekt).assign(CodigoDiagnostico = lambda x: x["CodigoDiagnostico"].astype(str).str.strip())
                                                    .merge(dimincap.iloc[:, 0:2], on = "CodigoDiagnostico", how = "left")
                                                    # El sistema registra solo para descontar el dominical pero no es una ausencia
                                                    .loc[lambda x: x["CodEmpleado"].isin(dimempleados["CodEmpleado"])]
                                                    .loc[lambda x: x["CodConcepto"] != 522]
                                                    .loc[lambda x: x["CodigoDiagnostico"] != 'None']
                                                    .drop_duplicates()
                                                    .assign(CodigoDiagnostico = lambda x: x["CodigoDiagnostico"].astype(str).str.strip())
                                                    .merge(dimempleados[["CodEmpresa", "CodEmpleado", "NombreEmpleado", "NoSAE", "TelefonoMovil", "FechaNacimiento"]].drop_duplicates(), 
                                                           on = ["CodEmpresa", "CodEmpleado"], how = "left")
                                                    .assign(CodEmpresa = lambda x: np.where(x["CodEmpresa"] == 736, "ZMOIII", "ZMOV")))

    # Se guarda el archivo en excel
    incapacidades.to_excel(userpc + incapacidad + "FactIncapacidades.xlsx", index = False)

    # Envio de los datos al DW
    sql_types = {'CodEmpleado': types.INTEGER, 'FechaAplicacion': types.DATE, 'HrsLaborales': types.FLOAT,
                'CodConcepto': types.INTEGER, 'HrsAusente': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    FactAusentismoKactus.to_sql(table3, schema = 'gh', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), max_fecha_tabla = FactAusentismoKactus["FechaAplicacion"].max(), cantidad_registros = len(FactAusentismoKactus))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table3), observacion = str(e))


# Proceso de tiempo suplementario
dia = datetime.today().day

try:
    # Proceso para validar el dia del mes y que corra solo los dias 1 y 15
    if dia in [16,30]:

        query = """ SELECT CASE acu.cod_empr 
                                WHEN 736 THEN 'ZMOIII'
    		                    WHEN 7362 THEN 'ZMOV'
    		                    WHEN 7361 THEN 'ZMPIII'
    		                    WHEN 7363 THEN 'ZMPV'
    		               END as "CodEmpresa",
                           cod_empl as "CodEmpleado", cod_conc as "CodConcepto", DATEADD(month, -1, fec_acum) as "FechaCausa",
                           fec_acum as "FechaPagoNomina", can_acum as "CantidadHoras", val_acum as "ValorAcumulado",
                           nom_ccos as "CentroCosto"
                    FROM KactusGrM.dbo.nm_acumu acu
                    LEFT JOIN gn_ccost cco 
                        ON acu.cod_empr = cco.cod_empr 
                        AND acu.cod_ccos = cco.cod_ccos
                    WHERE cod_conc IN (121, 122, 123, 124, 125, 126, 127, 141, 184)
                    ORDER BY cod_empl, fec_acum desc"""

        tiemposuple = (pd.read_sql(query, fn.enginekt)
                            .assign(CentroCosto = lambda x: x["CentroCosto"].astype(str).str.strip(),
                                    InsertDate = datetime.now()))

        # Envio de los datos al DW
        sql_types = {'CodEmpleado': types.INTEGER, 'CodConcepto': types.INTEGER, 'FechaCausa': types.DATE,
                    'FechaPagoNomina': types.DATE, 'CantidadHoras': types.FLOAT, 'ValorAcumulado': types.FLOAT, 
                    'InsertDate': types.TIMESTAMP}

        tiemposuple.to_sql(table4, schema = 'gh', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

        # Actualizacion del dataset de PowerBI
        path = os.getenv("PAT_PBI_REFRESH")
        subprocess.run(["python", path, os.getenv("PBI_TIEMPOSUPLE")])

        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), max_fecha_tabla = tiemposuple["FechaCausa"].max(), cantidad_registros = len(tiemposuple))
    else:
        # Registro de la ejecucion del proceso
        fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), max_fecha_tabla = datetime.today(), cantidad_registros = 0)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table4), observacion = str(e))

fn.update_process(id_process = IdProceso, engine = fn.enginea)