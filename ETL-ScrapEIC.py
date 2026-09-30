# *********************************************************************************************

# Algoritmo para descargar los datos de la plataforma EMIC
# @autor: Anderson Sarmiento
# *********************************************************************************************

# Detalle de las Url's ------------------------------------------------------------------------
# Componentes fase V
# Todas las URL´s comparten esta primera estructura 
# http://transmitools.transmilenio.gov.co/EIC/Downloadkm?operador=231
# DPV -----------------------------------------------------------------------------------------
# &Step=1&IdKpi=1&nom=DPV_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=2&IdKpi=1&nom=DPV_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=6&IdKpi=1&nom=DPV_cerrrado&ini=undefined&fin=undefined&actor=2&IdEtapa=1&persona=&estado=&etapa=
# 
# ISV -----------------------------------------------------------------------------------------
# &Step=1&IdKpi=3&nom=ISV_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=2&IdKpi=3&nom=ISV_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=6&IdKpi=3&nom=ISV_cerrrado&ini=undefined&fin=undefined&actor=2&IdEtapa=1&persona=&estado=&etapa=
# 
# ICO -----------------------------------------------------------------------------------------
# &Step=1&IdKpi=4&nom=ICO_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=2&IdKpi=4&nom=ICO_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=6&IdKpi=4&nom=ICO_cerrrado&ini=undefined&fin=undefined&actor=2&IdEtapa=1&persona=&estado=&etapa=
# 
# ITS -----------------------------------------------------------------------------------------
# &Step=1&IdKpi=11&nom=ITS_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=2&IdKpi=11&nom=ITS_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=6&IdKpi=11&nom=ITS_cerrrado&ini=undefined&fin=undefined&actor=2&IdEtapa=1&persona=&estado=&etapa=
#
# ICS -----------------------------------------------------------------------------------------
# &Step=1&IdKpi=10&nom=UNIDADES%20FUNCIONALES_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=2&IdKpi=10&nom=UNIDADES%20FUNCIONALES_Etapa1&ini=undefined&fin=undefined&actor=2&IdEtapa=1
# &Step=6&IdKpi=10&nom=UNIDADES%20FUNCIONALES_cerrado&ini=2022-06-01&fin=2022-06-19&actor=2&IdEtapa=1

# Instalacion de Librerias --------------------------------------------------------------------
import os                                                # Sistema
import glob                                              # Obtener listado de archivos
import time                                              # Sleep pc
import subprocess                                        # Desencadenar otros procesos
import shutil                                            # Mover archivos
import Funciones as fn                                   # Funciones ETL
from selenium import webdriver                           # Manejador del browser
from selenium.webdriver import ActionChains              # Acciones del navegador
from selenium.webdriver.common.by import By              # Selector
from datetime import date, timedelta, datetime           # Manejo de fechas
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1140
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Archivos EMIC*"

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
pathdestiny = f'E://Drive//greenmovil.com.co//Gestion Mantenimiento - General//Documentos//10 Datos//02 Emic//'
namefile = date.today().strftime("%Y%m%d")

# Definicion de la fecha final de descarga ----------------------------------------------------
fecha_from = (date.today() - timedelta(days = 30)).strftime("%Y-%m-%d")
fecha_to = date.today().strftime("%Y-%m-%d")
url = os.getenv('URL_TRASMITOOL_TM')

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

# Inicio en la Página --------------------------------------------------------------------------------
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
        return True
    except Exception as e: 
        print(str(e))
        return False

# Diccionarios de parametros ------------------------------------------------------------------
indicador = {"DPV", "ISV", "ICO", "ICS", "ITS"}

archivos = {"DPV": {"IdKpi": "1", "etapa0": "DPV_Etapa0", "etapa1": "DPV_Etapa1", "etapa2": "DPV_Etapa4"}, 
            "ISV": {"IdKpi": "3", "etapa0": "ISV_Etapa0", "etapa1": "ISV_Etapa1", "etapa2": "ISV_Etapa4"},
            "ICO": {"IdKpi": "4", "etapa0": "ICO_Etapa0", "etapa1": "ICO_Etapa1", "etapa2": "ICO_Etapa4"},
            "ICS": {"IdKpi": "10", "etapa0": "ICS_Etapa0", "etapa1": "ICS_Etapa1", "etapa2": "ICS_Etapa4"},
            "ITS": {"IdKpi": "11", "etapa0": "ITS_Etapa0", "etapa1": "ITS_Etapa1", "etapa2": "ITS_Etapa4"}}

# Proceso de logeo en la pagina web de transmilenio -------------------------------------------
def validateFileExist(name, url):
    fileExist = os.path.exists(pathDownload + name + '.csv')
    if fileExist:
        print("El archivo Existe")
    else:
        print("El archivo NO Existe")
        driver.get(url)
        fileExist = os.path.exists(pathDownload + name + '.csv')
        time.sleep(1)
            
def validateIsDowloading(name):
    fileExist = os.path.exists(pathDownload + name + '.csv')
    while os.path.exists(pathDownload + name + '.csv.crdownload'):
        starDownload = True
        print("El archivo esta descargando")
        print(starDownload)
        time.sleep(1)
        
def validateIfAllFilesExist():
    os.chdir(pathDownload)
    result = glob.glob('*Etapa*.csv')

    while len(result) < 15:
      downloadFiles()

# Loop para el proceso de descarga de los archivos --------------------------------------------
def downloadFiles():
    for indice in indicador:
        IdKpi = "IdKpi=" + archivos[indice]['IdKpi'] + "&"
        for etapa, valor in list(archivos[indice].items())[1:]:
            if etapa == "etapa0":
                nombre = "nom=" + valor
                urldescarga = url + "Step=1&" + IdKpi + nombre + "&ini=undefined&fin=undefined&actor=2&IdEtapa=1"
            elif etapa == "etapa1":
                nombre = "nom=" + valor
                urldescarga = url + "Step=2&"+IdKpi + nombre + "&ini=undefined&fin=undefined&actor=2&IdEtapa=1"
            elif etapa == "etapa2":
                nombre = "nom=" + valor
                urldescarga = url + "Step=6&" + IdKpi + nombre + "&ini=" + fecha_from + "&fin=" + fecha_to + "&actor=2&IdEtapa=1"
            validateFileExist(valor, urldescarga)
            time.sleep(2)

# Loop para el movimiento y renombramiento de los archivos ------------------------------------
def movefiles():
    os.chdir(pathDownload)
    global listfiles
    listfiles = glob.glob('*Etapa*.csv')

    # Esperar hasta que se descarguen los 15 archivos
    while len(listfiles) < 15:
        print("Pendiente descarga de algún archivo...")
        time.sleep(5)
        listfiles = glob.glob('*Etapa*.csv')

    # Mover archivos
    for file in listfiles:
        src = os.path.join(pathDownload, file)
        dst = os.path.join(pathdestiny, f"{namefile}_{file}")
        os.makedirs(os.path.dirname(dst), exist_ok = True)
        try:
            shutil.move(src, dst)
            print(f"Movido: {file} -> {dst}")
        except Exception as e:
            print(f"Error moviendo {file}: {e}")

# Ejecucion de funciones ----------------------------------------------------------------------
# Inicializar el WebDriver con las opciones configuradas
driver = webdriver.Chrome(options=chrome_options)
time.sleep(5)
login()
time.sleep(10)
try:
    downloadFiles()
    time.sleep(30)
    movefiles()
    driver.quit()
    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "DocumentosEMIC"), max_fecha_tabla = datetime.today(), cantidad_registros = len(listfiles))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
    # Ejecución proceso de Transformación EMIC ----------------------------------------------------
    subprocess.call([r'C:\Users\dev\Documents\00 Executables\20230801_EMIC.bat'])
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, "DocumentosEMIC"), observacion = str(e))
