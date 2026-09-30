#**********************************************************************************************
# @Nombre: Proceso para Almacenar los datos de los lubricantes
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                    # Manipulacion de datos
import os                              # Manejo del sistema
import Funciones as fn                 # Funciones ETL
from sqlalchemy import types           # Manejo de tipos de campos en db
from skimpy import clean_columns       # Cambiar el tipo de nombre de columnas
from datetime import datetime          # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1250
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Actualizacion Lubricantes*"
table = 'FactLubricantes'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

#Desarrollo -----------------------------------------------------------------------------------
# Ruta del documento
rut = f'E://Drive//greenmovil.com.co//Gestion Mantenimiento - General//Documentos//10 Datos//08 SmartAssistance//Plantilla Smart Assistance.xlsx'

# Seleccion de columnas
Cols = ["NOMBRE_OPERACION", "FECHA_MUESTREO", "FECHA_INGRESO", "FECHA_RECEPCION", "FECHA_INFORME",
        "EDAD_COMPONENTE", "UNIDAD_EDAD_COMPONENTE", "EDAD_PRODUCTO", "UNIDAD_EDAD_PRODUCTO", 
        "PRODUCTO", "COMPONENTE", "DESCRIPTOR_COMPONENTE", "ESTADO", "id_muestra", 
        "AGUA CUALITATIVA (PLANCHA) - 360", "ALUMINIO (AL) - 20", "BARIO (BA) - 21", "BORO (B) - 18", 
        "CADMIO (CD) - 23", "CALCIO (CA) - 22", "COBRE (CU) - 25", "CROMO (CR) - 24", 
        "ESTAÑO (SN) - 37", "FÓSFORO (P) - 34", "HIERRO (FE) - 26", "MAGNESIO (MG) - 28", 
        "MOLIBDENO (MO) - 30", "NÍQUEL (NI) - 32", "**OXIDACIÓN - 80", "PLATA (AG) - 19", 
        "PLOMO (PB) - 35", "POTASIO (K) - 27", "SILICIO (SI) - 36", "SODIO (NA) - 31", 
        "TITANIO (TI) - 38", "VISCOSIDAD A 100 °C - 13", "VISCOSIDAD A 40 °C - 14", "ZINC (ZN) - 40"]

# Asignación de nombres y tipo de categoria
Valores = {'Viscosidad40C':['Lubricante', 'Viscosidad'], 'Oxidacion':['Lubricante', 'Oxidacion'],
           'Viscosidad100C':['Lubricante', 'Viscosidad'], 'H2O':['Lubricante', 'Agua'], 
           'Ag':['Desgaste', 'Plata'], 'Al':['Desgaste', 'Aluminio'], 'Cr':['Desgaste', 'Cromo'], 
           'Cu':['Desgaste', 'Cobre'], 'Fe':['Desgaste', 'Hierro'], 'Mo':['Desgaste', 'Molibdeno'], 
           'Ni':['Desgaste', 'Niquel'], 'Pb':['Desgaste', 'Plomo'], 'Sn':['Desgaste', 'Estano'], 
           'K':['Contaminante', 'Potasio'], 'Na':['Contaminante', 'Sodio'], 
           'Si':['Contaminante', 'Silicio'], 'B':['Aditivo', 'Boro'], 'Ba':['Aditivo', 'Bario'], 
           'Ca':['Aditivo', 'Calcio'], 'Mg':['Aditivo', 'Magnesio'], 'P':['Aditivo', 'Fosforo'], 
           'Zn':['Aditivo', 'Zinc'], 'Cd':['Desgaste', 'Cadmio'], 'Ti':['Desgaste', 'Titanio']}

try:
    # Transformación del dataframe
    dfoil = (clean_columns(pd.read_excel(rut, usecols = Cols), case = 'pascal')
         .rename(columns = {"AguaCualitativaPlancha360":"H2O", "AluminioAl20":"Al", "BarioBa21":"Ba", 
                            "BoroB18":"B", "CadmioCd23":"Cd", "CalcioCa22":"Ca", "CobreCu25":"Cu",
                            "CromoCr24":"Cr", "EstanoSn37":"Sn", "FosforoP34":"P", "HierroFe26":"Fe",
                            "MagnesioMg28":"Mg", "MolibdenoMo30":"Mo", "NiquelNi32":"Ni", 
                            "Oxidacion80":"Oxidacion", "PlataAg19":"Ag", "PlomoPb35":"Pb", "PotasioK27":"K",
                            "SilicioSi36":"Si", "SodioNa31":"Na", "TitanioTi38":"Ti", 
                            "ViscosidadA100C13":"Viscosidad100C", "ViscosidadA40C14":"Viscosidad40C",
                            "ZincZn40":"Zn"})
         .melt(id_vars = ['NombreOperacion', 'FechaMuestreo', 'FechaIngreso', 'FechaRecepcion', 
                          'FechaInforme', 'EdadComponente', 'UnidadEdadComponente', 'EdadProducto', 
                          'UnidadEdadProducto', 'Producto', 'Componente', 'DescriptorComponente', 
                          'Estado', 'IdMuestra'], var_name = 'Variable', value_name = 'Valor')
         .assign(Categoria = lambda x: x['Variable'].map(lambda key: Valores.get(key, [None, None])[0]),
                 Nombre = lambda x: x['Variable'].map(lambda key: Valores.get(key, [None, None])[1]),
                 InsertDate = datetime.now())
         .replace({'Valor': {"NotDetected": 0, "Detected": 1, "Detectado": 1, "WET": pd.NA}}))

    # Envio de los datos al DW
    sql_types = {'FechaMuestreo': types.DATE, 'FechaIngreso': types.DATE, 'FechaRecepcion': types.DATE,
                 'FechaInforme': types.DATE, 'EdadComponente': types.INTEGER, 'EdadProducto': types.INTEGER,
                 'Valor': types.FLOAT, 'InsertDate': types.TIMESTAMP}

    dfoil.to_sql(table, schema = 'ma', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = dfoil['FechaMuestreo'].max(), cantidad_registros = len(dfoil))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_LUBRICANTES')
command = f'python "{file_phyton}" "{datasetid}"'
os.system(command)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
