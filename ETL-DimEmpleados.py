#**********************************************************************************************
# @Nombre: ETL Dimension de empleados
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import googlemaps                      # Cliente de Google Maps API
import Funciones as fn                 # Funciones personalizadas
from sqlalchemy import text            # Conexion base de datos
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1030
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Empleados*"
table = "DimEmpleados"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Paths y queries
path_project = os.getenv("PAT_PROJECT")

query_dim = os.path.join(path_project, "00 Querys/DimEmpleados.sql")
query_eps = os.path.join(path_project, "00 Querys/DimEmpleadosEPS.sql")
query_invuseline = os.path.join(path_project, "00 Querys/FactInvuseline.sql")

userpc = r"E:\Drive"
sharepoint = r"\greenmovil.com.co\Gestion Informacion - General\07 Gestion_Humana\Capacitacion Operadores\DimEntregasC1ma.xlsx"

# Google Maps client
gmaps = googlemaps.Client(key = os.getenv("TOK_GEOENCODER"))

# Función de geocodificación
def geocode_address(address, city = "Bogotá", country = "Colombia"):
    if not address or not str(address).strip():
        return None, None
    full_address = f"{address}, {city}, {country}"

    try:
        result = gmaps.geocode(full_address, region = "co", 
                               components = {"country": "CO", "locality": "Bogotá"})
        if not result:
            return None, None
        location = result[0]["geometry"]["location"]
        return location["lat"], location["lng"]
    except Exception:
        return None, None

try:
    # Ubicaciones ya existentes en DW
    datalatlong = (pd.read_sql(""" SELECT "CodEmpleado", "DireccionResidencia", "Longitud" AS "LongDW", 
                                         "Latitud" AS "LatDW"
                                  FROM public."DimEmpleados" """, fn.enginea)
                                  .drop_duplicates(subset = ["CodEmpleado"]))

    # Operadores ascenso
    factoper = (pd.read_excel(os.path.join(userpc, sharepoint.lstrip("\\")), sheet_name = "C1ma")
                .loc[:, ["CC", "EntregaOperaciones", "Programa"]]
                .rename(columns = {"CC": "CodEmpleado", "EntregaOperaciones": "FechaPrograma"}))

    # Patrones de direcciones
    pattern = {"CR": "CARRERA", "DG": "DIAGONAL", "CL": "CALLE", "AV": "AVENIDA", "TV": "TRANSVERSAL",
               "AK": "CARRERA"}

    # Dimensiones auxiliares
    dim_eps = pd.read_sql(open(query_eps).read(), fn.enginekt).drop_duplicates("CodEmpleado")

    dim_codigo_renuncia = pd.read_sql(""" SELECT cntr.cod_empl AS CodEmpleado, 
                                                 cntr.act_hora AS HoraActualizacion,
                                                 cntr.cod_esca AS CodMotivoReal,
                                                 esc.nom_esca  AS NomMotivoReal,
                                                 cntr.cod_mdej AS CodMotivoRetiro,
                                                 dja.nom_mdej  AS NomMotivoRetiro
                                          FROM nm_contr cntr
                                          LEFT JOIN nm_escar esc    
                                            ON cntr.cod_empr = esc.cod_empr 
                                            AND cntr.cod_esca = esc.cod_esca
                                          LEFT JOIN nm_mdeja dja
                                            ON cntr.cod_empr = dja.cod_empr 
                                            AND cntr.cod_mdej = dja.cod_mdej """, fn.enginekt)

    # Dimensión principal
    dim = pd.read_sql(open(query_dim).read(), fn.enginekt)

    cols_bigint = ["TelefonoResidencia", "TelefonoMovil", "NoSAE", "CantidadContratos"]

    dim = (dim.merge(dim_eps, on = "CodEmpleado", how = "left")
           .merge(dim_codigo_renuncia, on = ["CodEmpleado", "HoraActualizacion"], how = "left")
           .sort_values(["CodEmpleado", "EstadoEmpleado", "FechaRetiro"], ascending = [True, True, False])
           .assign(AplicaRotacion = lambda df: (df["FechaContratacion"] != df.groupby("CodEmpleado")["FechaContratacion"].shift()),
                   **{col: lambda df, c = col: (df[c].astype(str).str.strip().str.replace(r"\s+", "", regex = True)
                                                .replace({"": None, "nan": None}).pipe(pd.to_numeric, errors = "coerce").astype("Int64"))
                                                for col in cols_bigint})
           .query("CodCentroCostos not in [2011, 2012]"))

    # Limpiezas
    for col in ["AFP", "ARP", "CCF", "EPS", "CentroCostos", "CodCargo", "Empresa"]:
        dim[col] = dim[col].astype(str).str.strip()

    dim["NombreEmpleado"] = dim["NombreEmpleado"].str.title()
    dim["Cargo"] = dim["Cargo"].str.title()
    dim["BarrioResidencia"] = dim["BarrioResidencia"].str.title()

    dim["CodEmpresa"] = dim["Empresa"].replace({r".*ZMO FONTIBON III.*": "ZMOIII",
                                                r".*ZMP FONTIBON III.*": "ZMPIII",
                                                r".*ZMO FONTIBON V.*": "ZMOV",
                                                r".*ZMP FONTIBON V.*": "ZMPV"}, regex = True)

    # Dirección normalizada
    dim["DireccionResidencia"] = (dim["DireccionResidencia"].str.upper()
                                  .str.extract(r"([^,]*)")[0]
                                  .str.replace("#", "", regex = False))

    for k, v in pattern.items():
        dim["DireccionResidencia"] = dim["DireccionResidencia"].str.replace(k, v, regex = False)

    # Geocodificación
    pendientes_geo = (dim[~dim["CodEmpleado"].isin(datalatlong["CodEmpleado"])]
                      .dropna(subset = ["DireccionResidencia"])
                      .drop_duplicates("CodEmpleado"))

    geo_data = []
    for _, row in pendientes_geo.iterrows():
        lat, lon = geocode_address(row["DireccionResidencia"])
        geo_data.append({"CodEmpleado": row["CodEmpleado"],
                         "DireccionResidencia": row["DireccionResidencia"],
                         "Latitud": lat,
                         "Longitud": lon})
    latlog = pd.DataFrame(geo_data)

    # Merge final
    if pendientes_geo.empty:
        dim = (dim.assign(DireccionResidencia = lambda df: df["DireccionResidencia"].add(", Bogota"))
                  .merge(datalatlong, on = ["CodEmpleado", "DireccionResidencia"], how = "left")
                  .merge(factoper, on = "CodEmpleado", how = "left")
                  .assign(Longitud = lambda d: d["LongDW"],
                          Latitud = lambda d: d["LatDW"],
                          InsertDate = datetime.now())
                  .drop(columns = ["LongDW", "LatDW"]))
    else:
        dim = (dim.assign(DireccionResidencia = lambda df: df["DireccionResidencia"].add(", Bogota"))
                  .merge(latlog, on = ["CodEmpleado", "DireccionResidencia"], how = "left")
                  .merge(datalatlong, on = ["CodEmpleado", "DireccionResidencia"], how = "left")
                  .merge(factoper, on = "CodEmpleado", how = "left")
                  .assign(Longitud = lambda d: d["Longitud"].fillna(d["LongDW"]),
                          Latitud = lambda d: d["Latitud"].fillna(d["LatDW"]),
                          InsertDate = datetime.now())
                  .drop(columns = ["LongDW", "LatDW"]))

    dim["Programa"] = dim.apply(lambda x: "Experto"
        if x["Cargo"] in ["Operador/A De Bus", "Operador/A Padron"] and pd.isna(x["Programa"])
        else x["Programa"], axis = 1)

    # Carga DW
    fn.cona.execute(text(f'TRUNCATE TABLE "{table}"'))

    dim.to_sql(table, fn.enginea, if_exists = "append", index = False)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = datetime.today().date(), cantidad_registros = len(dim))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)

except Exception as e:
    fn.registrar_actualizacion(fn.enginea, IdProceso, fn.ind_tabla(fn.enginea, table), observacion = str(e))
    