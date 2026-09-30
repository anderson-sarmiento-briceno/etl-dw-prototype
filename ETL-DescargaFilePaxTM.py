#**********************************************************************************************
# @Nombre: Proceso para la descarga de validaciones zonal de Transmilenio
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import os                               # Manejo del sistema
import re                               # Manejo de expresiones regulares
import zipfile                          # Manejo de archivos zip
import requests                         # Manejo de solicitudes HTTP
import Funciones as fn                  # Funciones ETL
import subprocess                       # Controlador de scripts
import sys                              # Interprete python
from bs4 import BeautifulSoup           # Manejo de HTML
from datetime import datetime           # Manejo de fechas
from dotenv import load_dotenv
load_dotenv()

#Desarrollo -----------------------------------------------------------------------------------
# Funciones auxiliares
def obtener_links_zip(url):
    resp = requests.get(url, timeout = 360)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return ([a["href"] for a in soup.find_all("a", href = True)
            if a["href"].endswith(".zip")])

def fechas_en_archivos(archivos):
    fechas = []
    for f in archivos:
        m = re.search(r"\d+", f)
        if m:
            fechas.append(m.group())
    return fechas

def descargar_y_extraer(url, destino, sufijo):
    fecha = re.search(r"\d+", url).group()
    nombre_zip = f"{fecha}_{sufijo}.zip"
    ruta_zip = os.path.join(destino, nombre_zip)

    # Descargar
    with requests.get(url, stream = True, timeout = 360) as r:
        r.raise_for_status()
        with open(ruta_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size = 8192):
                f.write(chunk)

    # Extraer
    with zipfile.ZipFile(ruta_zip, "r") as z:
        z.extractall(destino)

    # Renombrar CSV
    csv_original = os.path.join(destino, f"{fecha}.csv")
    csv_final = os.path.join(destino, f"{fecha}_{sufijo}.csv")
    if os.path.exists(csv_original):
        os.rename(csv_original, csv_final)

    # Eliminar ZIP
    os.remove(ruta_zip)

    return nombre_zip

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1130
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga Pasajeros TM*"
table = "ValidacionesTM"

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

procesados = []
errores = []

try:
    procesos = [{"url": os.getenv("URL_ZONAL_TM"),
                 "path": os.path.join(os.getenv("PAT_NAS"), "02 Datos/03 validaciones_zonal"),
                 "sufijo": "ValidacionZonal"},
                {"url": os.getenv("URL_DUAL_TM"),
                 "path": os.path.join(os.getenv("PAT_NAS"), "02 Datos/04 validaciones_dual"),
                 "sufijo": "ValidacionDual"},
                {"url": os.getenv("URL_TRONCAL_TM"),
                 "path": os.path.join(os.getenv("PAT_NAS"), "02 Datos/05 validaciones_troncal"),
                 "sufijo": "ValidacionTroncal"}]

    for p in procesos:
        os.makedirs(p["path"], exist_ok = True)

        disponibles = obtener_links_zip(p["url"])
        actuales = os.listdir(p["path"])

        fechas_actuales = fechas_en_archivos(actuales)

        pendientes = [f for f in disponibles
                      if re.search(r"\d+", f).group() not in fechas_actuales]

        for url_zip in pendientes:
            try:
                nombre = descargar_y_extraer(url_zip, p["path"], p["sufijo"])
                procesados.append(nombre)
                print(nombre)
            except Exception as e:
                errores.append(url_zip)

    # Métricas finales
    cantidad_registros = len(procesados)

    if cantidad_registros == 0:
        max_fecha_tabla = None
    else:
        fechas = [datetime.strptime(f[:8], "%Y%m%d")
                  for f in procesados]
        max_fecha_tabla = max(fechas)

    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table), max_fecha_tabla = max_fecha_tabla, cantidad_registros = cantidad_registros)
    fn.update_process(id_process = IdProceso, engine = fn.enginea)

except Exception as e:
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginegr, table), observacion = str(e))
    raise

# Invocar proceso diario
if not procesados:
    print("Sin archivos")
else:
    # Desencadenar el proceso de para el calculo de la durabilidad de las llantas
    subprocess.run([sys.executable, r"C:\Users\dev\Documents\01 Modelos\20211230-etl-dwgm\ETL-FactPaxDiaTM.py"])

# Mensaje Fin del Proceso ---------------------------------------------------------------------
print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
