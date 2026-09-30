#**********************************************************************************************
# @Nombre: Proceso de descarga Validacion de Pasajeros 
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                      # Manipulacion de datos 
from datetime import date, timedelta, datetime           # Manejo de fechas
import os                                                # Sistema
import time                                              # Sleep pc
import Funciones as fn                                   # Funciones ETL
from selenium import webdriver                           # Manejador del browser
from selenium.webdriver.support.ui import WebDriverWait  # Manejar el tiempo carga de la web
from selenium.webdriver import ActionChains              # Acciones del mouse
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.service import Service    # Para siempre tener actualizado el driver
from webdriver_manager.chrome import ChromeDriverManager # Controlar navegador
from selenium.webdriver.chrome.options import Options    # Poner opciones al navegador
from selenium.webdriver.common.by import By              # Selector
from selenium.webdriver.common.keys import Keys          # Manejo de teclas
from sqlalchemy import types                             # Manejo de tipos de campos en db
from skimpy import clean_columns                         # Cambiar el tipo de nombre de columnas
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1190
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Pax SAE*"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext + 
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definicion del hook y contraseña ------------------------------------------------------------
usuario_EIC = os.getenv('APP_USER_TMTOOLS') 
contrasena = os.getenv('APP_PASS_TMTOOLS') 

# Definimos el path de downloads --------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'
pathdestiny = os.path.join(os.getenv('PAT_NASPY'), r'02 Datos\08 pasajeros_sae')

# Definicion de variables ---------------------------------------------------------------------
fecha_ini_descarga = '2022-04-02'
listfiles = []
session_id = False
loginState = False
driver = False
options = Options()
options.add_argument("start-maximized")
options.add_argument('--ignore-certificate-errors')
options.add_argument("--safebrowsing-disable-download-protection")
options.add_argument('--allow-running-insecure-content')
options.add_experimental_option("excludeSwitches", ["enable-logging"])

# Data types insert DW ------------------------------------------------------------------------
# Envio de los datos al DW
sql_types =  {
    'FechaClearing' : types.DATE,
    'DiaTrx': types.DATE,
    'Operador' : types.TEXT,
    'TotalPax' : types.INTEGER,
    'InsertDate': types.TIMESTAMP
    }

# Definicion de funciones ---------------------------------------------------------------------
# Inicio del Navegador ------------------------------------------------------------------------
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

# Click Capcha --------------------------------------------------------------------------------
def clickCapcha():
    captcha_iframe = WebDriverWait(driver, 10).until(
        ec.presence_of_element_located(
            (
                By.TAG_NAME, 'iframe'
            )
        )
    )
    ActionChains(driver).move_to_element(captcha_iframe).click().perform()
    # click im not robot
    captcha_box = WebDriverWait(driver, 10).until(
        ec.presence_of_element_located(
            (
                By.ID, 'g-recaptcha-response'
            )
        )
    )
    driver.execute_script("arguments[0].click()", captcha_box)    

# Logeo ---------------------------------------------------------------------------------------
def login():
    global driver
    try:
        driver.get("http://transmitools.transmilenio.gov.co/")
        time.sleep(2)
        # Coordenadas (x, y) dentro de la ventana y click aleatorio
        x, y = 100, 200
        ActionChains(driver).move_by_offset(x, y).click().perform()
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="login_user"]').send_keys(usuario_EIC)
        time.sleep(1)
        driver.find_element(By.XPATH,'//*[@id="password_user"]').send_keys(contrasena)
        time.sleep(2)
        driver.switch_to.frame(0)
        return True
    except Exception as e: 
        print(str(e))
        return False

# Descarga de pasajeros -----------------------------------------------------------------------
def descargapax(empresa, fecha_from):
    driver.get("http://transmitools.transmilenio.gov.co/transmireports/")
    time.sleep(3)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/div/p-select/span').click()
    time.sleep(3)
    driver.find_element(By.XPATH, '//*[@id="pn_id_9_11"]').click()
    time.sleep(3)
    elem = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[1]/p-iconfield/p-datepicker/input')
    elem.send_keys(datetime.strptime(fecha_from, '%d/%m/%Y').strftime('%Y-%m-%d'))
    elem.send_keys(Keys.ENTER)
    elem1 = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[2]/p-iconfield/p-inputnumber/input')
    elem1.click()
    elem1.send_keys(empresa)
    elem.send_keys(Keys.ENTER)
    time.sleep(10)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[3]/button').click()
    time.sleep(5)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[2]/section/div/div[1]/section[2]/p-table/div[1]/section/div[2]/button[2]').click()
    time.sleep(45)
    return True

# Funcion para renombrar los archivos según uf y almacenarlo en formato parquet ---------------
def namefile(fecha_descarga, nombre_archivo):
    # Se ajusta fecha del archivo
    fecha = datetime.strptime(fecha_descarga, '%d/%m/%Y')
    dia_ajus = fecha.strftime("%Y%m%d")
    filename = (dia_ajus + nombre_archivo)

    # Se abre el archivo csv 
    df = pd.read_csv(pathDownload + 'Consulta de Validaciones por Operador.csv', sep = ";")

    df = clean_columns(df, case = 'pascal').rename(columns = {"IdOperador":"Operador", "IdLinea":"Linea"})
    datadw = df[['FechaClearing', 'DiaTrx', 'Operador']]
    datadw = datadw.groupby(['FechaClearing', 'DiaTrx', 'Operador']).size().reset_index(name = 'TotalPax')
    # Reemplazar los valores en la columna Operador
    datadw['Operador'] = datadw['Operador'].replace({231: 'ZMOIII', 233: 'ZMOV'})

    # Agregar la columna InsertDate con la fecha actual
    datadw['InsertDate'] = datetime.now()

    # Insertar los datos en el DW
    datadw.to_sql('FactPasajerosSae', schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types)

    # Se reescribe en formato parquet
    df.to_parquet(os.path.join(pathdestiny, filename))
    
    # Agrupamiento de tallado
    df = (df.loc[:, ["FechaClearing", "Vehiculo", "Linea"]]
          .groupby(["FechaClearing", "Vehiculo", "Linea"])
          .size()
          .reset_index(name = "Pasajeros")
          .assign(InsertDate = datetime.now()))
    
    # Envio de los datos al DW
    sql_types2 =  {'FechaClearing' : types.DATE, 'Pasajeros' : types.INTEGER, 'InsertDate': types.TIMESTAMP}

    # Insertar los datos en el DW
    df.to_sql('FactPasajerosDetalleSae', schema = 'op', con = fn.cona, if_exists = 'append', index = False, dtype = sql_types2)

    # Se elimina el archivo de las descargas
    os.remove(pathDownload + 'Consulta de Validaciones por Operador.csv')

    # Se agrega a la lista de las descargas 
    listfiles.append(filename)

# Abrir Navegador -----------------------------------------------------------------------------
openBrowser()
login()

try:
    # Tabla control - Secuencia de dias para descargar la informacion -------------------------
    ctrfechasactuales = (
        pd.read_sql_query(
            """
            select DISTINCT "DiaTrx" 
            FROM "op"."FactPasajerosSae" order by 1
            """, con = fn.enginea)
        .assign(FechaClearing = lambda x: pd.to_datetime(x['DiaTrx']).dt.strftime('%d/%m/%Y'))
        .astype(str)
        .FechaClearing.to_list())

    ctrrangofecha = (
        pd.date_range(start = fecha_ini_descarga, end = (date.today() - timedelta(days = 2)))
        .strftime("%d/%m/%Y"))

    # Lista con las fechas a descargar
    ctrdias = [fecha for fecha in ctrrangofecha if fecha not in ctrfechasactuales]

    # Bucle de descarga archivos validacion de pasajeros 
    for i in ctrdias:
        # descarga validacion de pasajeros para la UF17
        descargapax('233', i)
        print("Descarga Completa dia " + i + " para la UF17")

        # renombramiento del archivo UF17
        namefile(i, '_ValidacionZonal_UF17.parquet')
        print("Renombramiento completado día " + i + " para la UF17")

        # descarga validacion de pasajeros para la UF06
        descargapax('231', i)
        print("Descarga Completa dia " + i + " para la UF06")

        # renombramiento del archivo UF06
        namefile(i, '_ValidacionZonal_UF06.parquet')
        print("Renombramiento completado día " + i + " para la UF06")

    # Se cierra el navegador
    driver.close()
    
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "FactPasajerosSae"), max_fecha_tabla = pd.to_datetime(ctrdias, format="%d/%m/%Y").max(), cantidad_registros = len(listfiles))
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "FactPasajerosDetalleSae"), max_fecha_tabla = pd.to_datetime(ctrdias, format="%d/%m/%Y").max(), cantidad_registros = len(listfiles))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "FactPasajerosSae"), observacion = str(e))
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "FactPasajerosDetalleSae"), observacion = str(e))

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
     "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
