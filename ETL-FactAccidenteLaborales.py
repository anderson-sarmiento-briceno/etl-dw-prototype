#**********************************************************************************************
# @Nombre: Proceso de Accidentes Laborales de la ARL Seguros Bolivar
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                 # Manipulacion de datos
import os                                           # Manejo del sistema
import time                                         # Manejo de pausas y tiempos de espera en la ejecucion
import Funciones as fn                              # Funciones ETL
from skimpy import clean_columns                    # Cambiar el tipo de nombre de columnas
from unidecode import unidecode                     # Elimina acentos y caracteres especiales de textos
from selenium import webdriver                      # Controla navegadores web de forma automatizada
from selenium.webdriver.common.by import By         # Permite ubicar elementos dentro del DOM por diferentes metodos
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime                       # Manejo de fechas
from sqlalchemy import types                        # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1150
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Accidentes Laborales ARL*"
table = 'FactAccidenteLaborales'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definimos el path de downloads --------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'

# Características en el Web Driver ------------------------------------------------------------
chrome_options = webdriver.ChromeOptions()

# Deshabilitar la advertencia de seguridad
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument("--safebrowsing-disable-download-protection")
chrome_options.add_argument('--allow-running-insecure-content')
# Permitir descargas inseguras
chrome_options.add_experimental_option('prefs', {
    "download.prompt_for_download": False, # Para evitar el diálogo de descarga
    "download.directory_upgrade": True,
    "safebrowsing_for_trusted_sources_enabled": False, # Deshabilita la protección de navegación segura para fuentes confiables
    "safebrowsing.enabled": False, # Deshabilita la protección de navegación segura
    "profile.default_content_settings.popups": 0,  # Desactiva las ventanas emergentes de descarga bloqueadas
    "download_restrictions": 0  # Permite todas las descargas, incluso las bloqueadas
})

# Funcion auxiliar de descarga
def download():
    global empre
    empresas = {'ZMOV':'//*[@id="p-highlighted-option"]/div',
                'ZMOIII':'//*[@id="pr_id_3_list"]/p-dropdownitem[2]/li/div',
                'ZMPIII':'//*[@id="pr_id_3_list"]/p-dropdownitem[3]/li/div',
                'ZMPV':'//*[@id="pr_id_3_list"]/p-dropdownitem[4]/li/div'}
    for emp, rut in empresas.items():
        driver.find_element(By.XPATH, '//*[@id="empresa"]').click()
        time.sleep(2)
        driver.find_element(By.XPATH, rut).click()
        driver.find_element(By.XPATH, '//button[@type="submit" or contains(.,"Buscar")]').click()
        time.sleep(10)
        try:
            driver.find_element(By.XPATH, '/html/body/poc-refarl-root/poc-refarl-plantilla-con-menu/div/div[2]/poc-refarl-gestion-accidentes/div/div/div/poc-refarl-consulta-accidentes/poc-refarl-resultado-consulta/div/div[1]/div[2]/poc-refarl-exportacion-datos-accidente/button').click()
            driver.find_element(By.XPATH, '/html/body/poc-refarl-root/poc-refarl-plantilla-con-menu/div/div[2]/poc-refarl-gestion-accidentes/div/div/div/poc-refarl-consulta-accidentes/poc-refarl-resultado-consulta/div/div[1]/div[2]/poc-refarl-exportacion-datos-accidente/p-dialog/div/div/div[3]/div[1]/div/div[2]/p-radiobutton').click()
            driver.find_element(By.XPATH, '/html/body/poc-refarl-root/poc-refarl-plantilla-con-menu/div/div[2]/poc-refarl-gestion-accidentes/div/div/div/poc-refarl-consulta-accidentes/poc-refarl-resultado-consulta/div/div[1]/div[2]/poc-refarl-exportacion-datos-accidente/p-dialog/div/div/div[3]/div[2]/button[2]').click()
            time.sleep(30)
            driver.find_element(By.XPATH, '//span[text()="Aceptar"]/parent::button').click()
            # Rename
            found_file = None
            for f in os.listdir(pathDownload):
                if f.startswith("Listado de Accidentes_") and f.endswith(".xlsx"):
                    found_file = os.path.join(pathDownload, f)
                    break
            if found_file:
                new_name = os.path.join(pathDownload, f"{emp}.xlsx")
                os.rename(found_file, new_name)
                empre.append(new_name)
        except (TimeoutException, NoSuchElementException):
            print(f"El botón no se encontró o no fue clickeable para {emp}. Continuando...")
        


# Logueo  y ubicacion de archivos
def login():
    global driver
    try:
        driver.get("https://arlonline.segurosbolivar.com/portal/arl/#/home")
        time.sleep(30)
        try:
            driver.find_element(By.ID, 'Num_Documento').send_keys(os.getenv('APP_USER_ARL'))
            driver.find_element(By.XPATH, '//*[@id="form"]/div[2]/input').send_keys(os.getenv('APP_PASS_ARL'))
            driver.find_element(By.XPATH, '//*[@id="form1"]').click()
            time.sleep(20)
        except (TimeoutException, NoSuchElementException):
            print("Error al intentar ingresar usuario o contraseña. Verifica los selectores o tiempos de espera.")
            return False
        try:
            driver.find_element(By.XPATH, '/html/body/poc-refarl-root/poc-refarl-plantilla-con-menu/div/div[1]/poc-refarl-menu/div/div[2]/p-panelmenu/div/div[4]/div/a/span[2]').click()
            time.sleep(10)
            download()
        except (TimeoutException, NoSuchElementException):
            print("Error al intentar navegar al módulo de descarga.")
            return False
        return driver.close()
    except Exception as e:
        print(f"Error general en login: {e}")
        return False
    
try:
    # Inicializar el WebDriver con las opciones configuradas
    driver = webdriver.Chrome(options = chrome_options)
    empre = []
    login()

    # Seleccion de registros ya insertados
    dw_al = pd.read_sql_query(''' SELECT "NoFurat" FROM st."FactAccidenteLaborales" ''', con = fn.enginea)

    # Renombrar columnas
    cols = {"1NoFurat":"NoFurat", "14NombreEmpresa":"Empresa", "38NumdocTrab":"CodEmpleado", 
            "55DiasOcupacionTrab":"DiasOcupacionTrab", "58JornadaHabitualTrab":"JornadaHabitualTrab", 
            "62JornadaLaboralAcc":"JornadaLaboral", "64HorasTrabajoAntAcc":"HorasPreAccidente", 
            "65MinutosTrabajoAntAcc":"MinsPreAccidente", "73LugarAcc":"LugarAccidente",
            "74SitioAcc":"SitioAccidente", "75LesionesAcc":"LesionesAccidente", 
            "76ParteCuerpoAcc":"ParteAfectada", "77AgenteAcc":"AgenteAccidente", 
            "78MecanismoAcc":"MecanismoAccidente", "89NumdocDiligencioAcc":"CodEmpeladoReporta", 
            "92FechaDiligencioAcc":"FechaRegistroAccidente", "93DescipcionAccidente":"DescripcionAccidente", 
            "59FechaAccidente":"FechaAccidente", "61HoraAccidente":"HoraAccidente", "66TipoAccidente":"TipoAccidente"}

    # Columnas a procesar texto
    cols_texto = ["JornadaHabitualTrab", "JornadaLaboral", "LugarAccidente", "SitioAccidente", 
                  "LesionesAccidente", "ParteAfectada", "AgenteAccidente", "MecanismoAccidente",
                  "DescripcionAccidente", "TipoAccidente"]

    # Limpieza y estandarizacion de datos
    accide = (clean_columns(pd.concat([pd.read_excel(f, header = 2) for f in empre], ignore_index = True), case = 'pascal')
              .loc[:, list(cols.keys())]
              .rename(columns = cols)
              .drop_duplicates()
              .assign(Empresa = lambda x: x["Empresa"].replace({"ZMO FONTIBON V SAS": "ZMOV",
                                                                "ZMO FONTIBON III S.A.S.": "ZMOIII",
                                                                "ZMP FONTIBON V SAS": "ZMPV",
                                                                "ZMP FONTIBON III SAS": "ZMPIII"}),
                      FechaRegistroAccidente = lambda x: pd.to_datetime(x["FechaRegistroAccidente"], format = "%d/%m/%Y %H:%M:%S", errors = "coerce"),
                      FechaAccidente = lambda x: pd.to_datetime(x["FechaAccidente"], format = "%d/%m/%Y", errors = "coerce"),
                      HoraAccidente = lambda x: pd.to_datetime(x["HoraAccidente"], format = "%H:%M:%S", errors = "coerce").dt.time,
                      **{c: lambda x, col = c: x[col].astype(str).apply(lambda t: unidecode(t.strip().title())) for c in cols_texto},
                      InsertDate = datetime.now())
              .loc[lambda df: ~df["NoFurat"].isin(dw_al["NoFurat"])])

    # Elimina los documentos ya procesados
    [os.remove(f) for f in empre if os.path.exists(f)]

    sql_types = {'NoFurat': types.INTEGER, 'CodEmpleado': types.INTEGER, 'DiasOcupacionTrab': types.INTEGER,
                 'HorasPreAccidente': types.INTEGER, 'MinsPreAccidente': types.INTEGER, 'CodEmpeladoReporta': types.INTEGER, 
                 'FechaRegistroAccidente': types.TIMESTAMP, 'FechaAccidente': types.DATE, 'HoraAccidente':types.TIME, 
                 'InsertDate': types.TIMESTAMP}

    accide.to_sql(table, schema = 'st', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = None if pd.isna(accide["FechaAccidente"].max()) else accide["FechaAccidente"].max(), cantidad_registros = len(accide))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)