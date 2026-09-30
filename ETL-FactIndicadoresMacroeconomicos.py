#**********************************************************************************************
# @Nombre: Extraccion de Indicadores Macroeconomicos
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                         # Manipulacion de datos
import os                                                   # Manejo del sistema
import time                                                 # Sleep pc
import sys                                                  # Interpretre de python
import glob                                                 # Lectura de archivos
import Funciones as fn                                      # Funciones ETL
from selenium import webdriver                              # Manejador del browser
from selenium.webdriver.common.by import By                 # Selector
from selenium.webdriver.common.keys import Keys             # Constante de teclado
from datetime import date, datetime, timedelta              # Manejo de fechas
from sqlalchemy import types                                # Manejo de tipos de campos en db
from sodapy import Socrata                                  # Manejo de datos abiertos
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1300
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Indicadores Macroeconomicos*"
table = 'FactIndicadoresMacroeconomicos'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definimos el path de downloads --------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'

# Definicion de la fecha final de descarga ----------------------------------------------------
fecha_to = (date.today() - timedelta(days = 15)).strftime("%d/%m/%Y")

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


# Funciones de captura de datos ---------------------------------------------------------------
# Scrapy de captura para UVR
def uvr():
    global driver
    try:
        driver.get("https://suameca.banrep.gov.co/descarga-multiple-de-datos/")
        time.sleep(10)
        driver.find_element(By.XPATH, '//*[@id="#accordion-tab-1000_header_action"]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="pn_id_21_header_action"]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="pn_id_4-table"]/tbody/tr[1]/td[2]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="opciones-series"]/div[2]/img[1]').click()
        time.sleep(3)
        elem1 = driver.find_element(By.XPATH, '/html/body/app-root/app-panel-configuracion-series/div/div[2]/div[1]/div/div[2]/p-calendar/span/input')
        elem1.send_keys(Keys.CONTROL + "a")
        elem1.send_keys(Keys.DELETE)
        elem1.send_keys(fecha_to)
        elem1.send_keys(Keys.ENTER)
        time.sleep(3)
        driver.find_element(By.XPATH, '/html/body/app-root/app-panel-configuracion-series/div/div[2]/div[1]/div/div[3]/img').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '/html/body/app-root/app-consolidado-series/div/div[2]/div[1]/img').click()
        time.sleep(5)
        return (pd.read_excel(rut)
                .assign(Fecha = lambda x: pd.to_datetime(x['Fecha'], format = '%d/%m/%Y', errors = 'coerce'))
                .dropna(subset = ['Fecha'])
                .reset_index(drop = True)
                .iloc[:, :2]
                .assign(Categoria = "UVR")
                .rename(columns = {"Unidad de Valor Real (UVR)(Dato diario)":"Valor"})
                .assign(Valor = lambda x: pd.to_numeric(x["Valor"].astype(str).str.replace(",", "."), errors = "coerce")))
    except Exception as e: 
        print(str(e))
        return False
    
# Scrapy de captura para IBR
def ibr():
    global driver
    try:
        driver.get("https://suameca.banrep.gov.co/descarga-multiple-de-datos/")
        time.sleep(10)
        driver.find_element(By.XPATH, '//*[@id="#accordion-tab-2000_header_action"]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="pn_id_23_header_action"]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="pn_id_6-table"]/tbody/tr[36]/td[2]').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '//*[@id="opciones-series"]/div[2]/img[1]').click()
        time.sleep(3)
        elem1 = driver.find_element(By.XPATH, '/html/body/app-root/app-panel-configuracion-series/div/div[2]/div[1]/div/div[1]/p-calendar/span/input')
        elem1.send_keys(Keys.CONTROL + "a")
        elem1.send_keys(Keys.DELETE)
        elem1.send_keys(fecha_to)
        elem1.send_keys(Keys.ENTER)
        time.sleep(3)
        driver.find_element(By.XPATH, '/html/body/app-root/app-panel-configuracion-series/div/div[2]/div[1]/div/div[3]/img').click()
        time.sleep(3)
        driver.find_element(By.XPATH, '/html/body/app-root/app-consolidado-series/div/div[2]/div[1]/img').click()
        time.sleep(5)
        return (pd.read_excel(rut)
                .assign(Fecha = lambda x: pd.to_datetime(x['Fecha'], format = '%d/%m/%Y', errors = 'coerce'))
                .dropna(subset = ['Fecha'])
                .reset_index(drop = True)
                .iloc[:, :2]
                .assign(Categoria = "IBR")
                .rename(columns = {"Indicador Bancario de Referencia (IBR) a 1 mes, nominal(Dato diario)":"Valor"})
                .assign(Valor = lambda x: pd.to_numeric(x["Valor"].astype(str).str.replace(",", "."), errors = "coerce")))
    except Exception as e: 
        print(str(e))
        return False

# Scrapy de captura para IPC
def ipc():
    global driver
    try:
        driver.get("https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc/ipc-informacion-tecnica#:~:text=Informaci%C3%B3n%20agosto%202025&text=En%20agosto%20de%202025%20la,fue%20de%206%2C12%25")
        time.sleep(10)
        elem = driver.find_element(By.XPATH, '//*[@id="rlta-panel-variaciones"]/div/table/tbody/tr[3]/td/p/a')
        driver.execute_script("arguments[0].scrollIntoView(true);", elem)
        time.sleep(3)
        elem.click()
        time.sleep(5)
        mes_map = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, 
                   "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, 
                   "Diciembre": 12}
        return (pd.read_excel(glob.glob(os.path.join(pathDownload, "anex-IPC-divisionesAnuales-*.xlsx"))[0])
                .pipe(lambda d: d[d.iloc[:, 0].isin(["Mes", "Total IPC"])])
                .transpose()
                .reset_index(drop = True)
                .pipe(lambda d: d.rename(columns = d.iloc[0]).iloc[1:].reset_index(drop = True))
                .assign(Mes = lambda d: pd.to_datetime(d["Mes"].map(mes_map).astype("Int64").astype(str) + "-2025", format = "%m-%Y").dt.to_period("M").dt.to_timestamp(),
                        Categoria = "IPC")
                .rename(columns = {"Mes":"Fecha", "Total IPC":"Valor"})
                .assign(Valor = lambda x: x["Valor"].apply(pd.to_numeric, errors = "coerce"))
                .dropna(subset = ['Valor']))
    except Exception as e: 
        print(str(e))
        return False

try:
    # API de captura para TRM
    # Cliente sin autenticacion
    client = Socrata("www.datos.gov.co", None)

    # Diccionarios de sodapy
    results = client.get("32sa-8pi3", limit = 15)

    # Seleccion de datos
    results_trm = (pd.DataFrame.from_records(results)
                  .assign(Fecha = lambda x: pd.to_datetime(x['vigenciadesde'], errors = 'coerce'),
                          Categoria = "TRM")
                  .iloc[:, [4, 0, 5]]
                  .rename(columns = {"valor":"Valor"})
                  .assign(Valor = lambda x: x["Valor"].apply(pd.to_numeric, errors = "coerce")))

    # Inicializar el WebDriver con las opciones configuradas
    driver = webdriver.Chrome(options = chrome_options)
    rut = os.path.join(pathDownload, "graficador_series.xlsx")

    # Resultados
    results_uvr = uvr()
    os.remove(rut)
    driver.close()
    driver = webdriver.Chrome(options = chrome_options)
    results_ibr = ibr()
    os.remove(rut)
    results_ipc = ipc()
    os.remove(glob.glob(os.path.join(pathDownload, "anex-IPC-divisionesAnuales-*.xlsx"))[0])
    driver.close()

    # Lectura de fechas y seleccion para insertar
    if results_uvr.empty or results_ibr.empty or results_ipc.empty:
        sys.exit("Ejecución detenida por falta de documentos")
    dw_trm = pd.read_sql_query(''' SELECT "Fecha" FROM cn."FactIndicadoresMacroeconomicos" WHERE "Categoria" = 'TRM' ''', con = fn.enginea)
    dw_ipc = pd.read_sql_query(''' SELECT "Fecha" FROM cn."FactIndicadoresMacroeconomicos" WHERE "Categoria" = 'IPC' ''', con = fn.enginea)
    dw_ibr = pd.read_sql_query(''' SELECT "Fecha" FROM cn."FactIndicadoresMacroeconomicos" WHERE "Categoria" = 'IBR' ''', con = fn.enginea)
    dw_uvr = pd.read_sql_query(''' SELECT "Fecha" FROM cn."FactIndicadoresMacroeconomicos" WHERE "Categoria" = 'UVR' ''', con = fn.enginea)

    # Seleccion de datos
    df = (pd.concat([results_uvr[~results_uvr['Fecha'].isin(dw_uvr['Fecha'])],
                    results_ibr[~results_ibr['Fecha'].isin(dw_ibr['Fecha'])],
                    results_ipc[~results_ipc['Fecha'].isin(dw_ipc['Fecha'])],
                    results_trm[~results_trm['Fecha'].isin(dw_trm['Fecha'])]], axis = 0)
                    .assign(InsertDate = datetime.now()))

    sql_types = {'Fecha': types.DATE, 'Valor': types.TEXT, 'InsertDate': types.TIMESTAMP}

    df.to_sql(table, schema = 'cn', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = df['Fecha'].max(), cantidad_registros = len(df))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
