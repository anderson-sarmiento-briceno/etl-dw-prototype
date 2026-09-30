#**********************************************************************************************
# @Nombre: Descarga tabla precios bolsa
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
from datetime import date, datetime                                # Manipulacion de fechas
import os                                                          # Sistema
import pandas as pd                                                # Manipulacion de datos
import Funciones as fn                                             # Funciones ETL
import time                                                        # Para pausar el código
import glob                                                        # Manejo de archivos
import re                                                          # Regex 
from selenium import webdriver                                     # Para llenar formularios
from selenium.webdriver.chrome.service import Service              # Para siempre tener actualizado el driver
from webdriver_manager.chrome import ChromeDriverManager           # Controlar navegador
from selenium.webdriver.chrome.options import Options              # Poner opciones al navegador
from selenium.webdriver.common.by import By                        # Selector
from skimpy import clean_columns                                   # Limpieza de columnas
from sqlalchemy import types                                       # Tipos de datos SQL
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1120
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Precio Bolsa*"
table = "FactPrecioBolsa"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Conectar Data Warehouse ---------------------------------------------------------------------
hook = os.getenv('TOK_SLACK')

# Diccionario para convertir las fechas
repl_dict = {re.compile('.*ene.*'): '01',
            re.compile('.*feb.*'): '02',
            re.compile('.*mar.*'): '03',
            re.compile('.*abr.*'): '04',
            re.compile('.*may.*'): '05',
            re.compile('.*jun.*'): '06',
            re.compile('.*jul.*'): '07',
            re.compile('.*ago.*'): '08',
            re.compile('.*sep.*'): '09',
            re.compile('.*oct.*'): '10',
            re.compile('.*nov.*'): '11',
            re.compile('.*dic.*'): '12'}

# Se ajustan las opciones de navegación -------------------------------------------------------------------
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

# Path de la navegación -----------------------------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'
pathdestiny = f'E://Drive//greenmovil.com.co//Gestion Informacion - General//03 SubEstaciones//'
namefile = date.today().strftime("%Y%m%d") 

# Características en el Web Driver ------------------------------------------------------------
session_id = False
loginState = False
driver = False
options = Options()
options.add_argument("start-maximized")
options.add_argument("--disable-web-security")
options.add_experimental_option("excludeSwitches", ["enable-logging"])

#Inicio del Navegador -------------------------------------------------------------------------
def openBrowser():
    global session_id
    global loginState
    global driver    
    try:
        if session_id == False:        
            driver = webdriver.Chrome(service = Service(ChromeDriverManager(driver_version = "147.0.7727.56").install()), options = options)
            driver.implicitly_wait(40)  # seconds
            session_id = driver.session_id
        return True
    except Exception as e: 
        print(str(e))
        return False

try:
    openBrowser()
    time.sleep(10)
    url = 'https://www.xm.com.co/transacciones/cargo-por-confiabilidad/precio-de-bolsa-y-escasez'

    # Se inicializa el navegador en la página deseada ----------------------------------------------------------
    driver.get(url)
    time.sleep(3)

    # Proceso de acceso al Shadow Root 
    host = driver.find_element(By.XPATH, '//*[@id="block-xm-content"]/article/div/div[1]/div/div/div[2]/div/div[2]/div/precio-escasez-precio-bolsa-component')
    time.sleep(3)

    # Botón para cambiar de vista 
    driver.execute_script("return arguments[0].shadowRoot.getElementById('boton-cambiar-vista').click()", host)
    time.sleep(3)

    # Boton de descarga de la información 
    driver.execute_script("return arguments[0].shadowRoot.querySelector('div > div.web.mt-5 > div > div > button.btn-base.button-secondary.btn-medium').click()", host)

    # Se setea un tiempo para que termine de descargarse los archivos
    time.sleep(8)

    # Se sale del navegador
    driver.quit()

    # Obtener el listado de archivos descargados
    os.chdir('C://Users//dev//Downloads//')
    result = glob.glob('*escasez*.xlsx')

    # Proceso de transformacion y envio al DW -----------------------------------------------------

    # Lectura del archivo que se descarga de la pagina
    data = clean_columns(pd.read_excel('C://Users//dev//Downloads//' + result[0]),
                        case = 'pascal')
    data['Fecha'] = data['Fecha'].str[8:] + "-" + data['Fecha'].replace(repl_dict, regex = True) + "-" + data['Fecha'].str[:2]
    data['InsertDate'] = datetime.now()
    
    # Envio de los datos al DW
    sql_types =  {'Fecha' : types.DATE, 'InsertDate': types.TIMESTAMP}
    data.to_sql(table, schema = 'ma',  con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)
    data.to_csv(pathdestiny + "FactPrecioBolsa.csv", index = False)

    # Borrar el archivo descargado
    os.remove('C://Users//dev//Downloads//' + result[0])
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = data['Fecha'].max(), cantidad_registros = len(data))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), observacion = str(e))

# Refresh dataset power bi service ------------------------------------------------------------
file_phyton = os.getenv('PAT_PBI_REFRESH')
datasetid = os.getenv('PBI_BOLSAXM')
os.system("python " + file_phyton + " " + datasetid)

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
     "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
