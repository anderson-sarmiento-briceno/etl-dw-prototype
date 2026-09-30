#**********************************************************************************************
# @Nombre: Scrapy ICO Detalle
# @Autor: Anderson Sarmiento
#**********************************************************************************************

#Importar librerias ---------------------------------------------------------------------------
import pandas as pd                                         # Manipulacion de datos
import os                                                   # Manejo del sistema
import re                                                   # Expresiones regulares
import time                                                 # Sleep pc
import Funciones as fn                                      # Funciones ETL
from selenium import webdriver                              # Manejador del browser
from selenium.webdriver import ActionChains                 # Secuencias complejas
from selenium.webdriver.common.by import By                 # Selector
from selenium.webdriver.common.keys import Keys             # Constante de teclado
from datetime import date, datetime                         # Manejo de fechas
from selenium.webdriver.common.action_chains import ActionChains
from skimpy import clean_columns                            # Cambiar el tipo de nombre de columnas
from sqlalchemy import types                                # Manejo de tipos de campos en db
from dotenv import load_dotenv
load_dotenv()

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
IdProceso = 1143
# Titulo que se desplega en el mensaje de slack
pretext = f"{IdProceso} - Proceso Descarga ICO e ISV Consolidado*"
table1 = 'FactDetalleIco'
table2 = 'FactDetalleIsv'

# Mensaje Inicio del Proceso ------------------------------------------------------------------
start_time = datetime.now()

print("*" * 95 + "\nProceso:" + pretext +
      "\nHora Inicio: " + start_time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "*" * 95)

# Definicion del url y contraseña -------------------------------------------------------------
url = os.getenv('URL_TRASMITOOL_TM')
usuario_EIC = os.getenv('APP_USER_TMTOOLS') 
contrasena = os.getenv('APP_PASS_TMTOOLS') 


#Desarrollo -----------------------------------------------------------------------------------
# Funcion para asignar valores
def clasificar_descripcion(texto, diccionario):
    for categoria, patrones in diccionario.items():
            if re.search(patrones, texto):
                return categoria
    return None

# Diccionario de valores.
categoria = {"I5003-2":"Rayones", "I5027-1":"Elementos ITS", "I5006":"Aseo", "I8007":"Autorregulacion",
             "I5007":"Mantenimiento", "I5014":"Mantenimiento", "I8006":"Rehusar el transporte a pasajeros",
             "I5017":"Mantenimiento", "I5013-1":"Manchas o grafitis", "I5016":"Mantenimiento"}

repl_dict = {
    'Puerta abierta': r'(puerta número 1 abierta|puerta de servicio N° 3 abierta|puertas #1 y #2 abiertas|puerta #1 abierta|puertas número 3 abierta|puerta número 2 abierta|puerta #2 abierta|puerta 2 abierta|puerta#1 abierta|puerta número uno abierta|puertas número 1 y 2 abiertas|puerta del conductor abierta|puerta número 3 abierta)',
    'Ingreso de forma irregular': r'(ingreso de forma irregular|sin validar pasaje|sin validar pasaje|sin validar su respectivo pasaje|sin validar el respectivo pasaje|permite el ingreso de dos usuarios|sube acompañante por la puerta # 2|ingreso a una persona|permite el ingreso de usuario|permite el ingreso de un usuario|permite el ingreso de 1 usuario|permite ingreso de operador|permitiendo el ingreso de personas|I8001|recoge usuarios por puerta #3|ingreso a usuario por puerta número dos|ingreso de 3 personas por puerta # 2|deja ingresar 1 persona por puerta 2|ingreso de usuario por puerta Tres|ingresar 1 persona por puerta 3|ingresar 1 persona por puerta 2|1 persona por puerta de servicio # 3|ingreso de usuario por puerta dos|ingreso de una persona por puerta N° 2|ingreso de una persona por puerta 2|usuario ingresando por puerta dos)',
    'No cumplir con las paradas': r'(Operador hace caso omiso a la solicitud realizada por parte de usuario|I6003-1|omite parada|omisión de paradero|omisión de parada|deja 3 usuarios en un punto donde no hay un paradero establecido|omite el paradero|omite paradero|Dejar usuarios en lugar diferente)',
    'Prendas adicionales': r'(prendas que no hacen parte del uniforme|prendas adicionales|Buso|Cuellero|Chaleco|Chaqueta|chaqueta con capota|Capota|CUELLERO|CHAQUETA|BUFANDA|porta de manera inadecuada su uniforme|manguillas|chaqueta|Camibuso|buso|Gorra|prendas diferentes al uniforme|bufanda|gorra|buzo|cuellero|pantalón impermeable|portando prenda)',
    'Compra ambulante': r'(realizando compra ambulante|compras ambulantes|comprando producto)',
    'Conversacion': r'(entablando conversación mientras conduce|entabla conversación|entablando conversación con usuaria mientras conduce|entablando conversación con operador mientras conduce|hablar con otro operador|entablando conversación)',
    'Acompanante': r'(acompañante en su ejercicio de conducción|en recorrido lleva acompañante|con acompañante|lleva en la cabina a otra compaÃ±era operadora|lleva en la cabina a otra compañera|acompañante)',
    'Omision de mensaje': r'(El Operador omite el enví­o de mensaje|Cupo Disponible|luego de enviar mensaje|Bus Lleno)',
    'Abandono de movil': r'(operador se baja del móvil dejando mal parqueado el zonal|descendiendo del móvil|abandona el vehículo desde las 21:15 a las 21:36|zonal abandonado|descenso del móvil sin autorización|desciende del Bus|Móvil abandonado)',
    'Uso inadecuado de espejos': r'(uso inadecuados de espejos internos|uso inadecuado de espejos internos)',
    'Desvio': r'(no atendió desvio que estaba parametrizado)',
    'Cubrir camara': r'(tapando cámara del móvil|cubre con elemento la cámara frontal|cubriendo la cámara|tapando la cámara|tapa la cámara|desenfocando la cámara|cámara obstaculizada)',
    'Detencion en la via': r'(se detiene, abre su puerta y habla con una persona mientras genera tráfico)',
    'Consumir alimentos': r'(en recorrido comiendo|consumiendo alimentos|comiendo en servicio|consume alimentos|Se evidenció comiendo al interior)',
    'Capota': r'(capota del costado derecho parte central sucia|capota)',
    'Objeto en la cabina': r'(bicicleta dentro de la cabina|bicicleta dentro del habitáculo|maleta en la ventana izquierda|lleva una bicicleta en la cabina|maleta de color negro en ventana derecha)',
    'Ventanas': r'(vidrios|vetana|vidrios del lado izquierdo sucios|ventanas del costado derecho|vidrios de la ventana del lado izquierdo|vidrios de la puerta de servicio 1 hoja 1 y 2 sucios|vidrios del costado izquierdo|ventanas posición 2 y 3|vidrios de las ventanas 3 y 4|ventanas de usuario delanteras|ventanas 2 y 3|vidrios del costado derecho|marco de la ventana 2|vidrios corredizos de las ventanas 5 y 6|ventana de usuarios|ventanas del costado izquierdo|ventana 2 del costado derecho|vidrios de la ventana de la puerta del operador|vidrio posición 3|vidrio de la ventana|ventana del operador|ultima ventana|ventanas del lado izquierdo|ventana 5 izquierda sucia|ventana 1 costado derecho sucios|sin  aseo en ventanas|aseo deficiente en ventanas  externas|ventana 1 del costado derecho sin aseo|ventana número 1 derecha sucia|vidrio ventana cabina de operador costado derecho sucios|ventana 5 del costado izquierdo|ventana manchada con pintura verde|ventana posición 2 del costado izquierdo manchada|ventana lateral del costado derecho número 4)',
    'Cabina del operador': r'(cabina del operador|cabina obz|habitáculo del operador|silla obz|puerta del operador|cabina operador|silla del operador|habitáculo|piso del operador sucio|desaseo en pedaleras|aseo en pedaleras deficiente|aseo en pedales deficiente|cabina del  operador manchada costado izquierdo|cojá­n silla operador en mal estado|cojin de silla operador en mal estado|cojin de la silla operador en mal estado|cojín silla operador en mal estado|cojín de la silla operador en mal estado|piso del operador lado izquierdo sucio|pedalera del operador|pedalera del habitaculo del operador)',
    'Acrilico': r'(acrílico|acrí­licos|acrilico)',
    'Panoramico': r'(panorámico|vidrio panoramico trasero)',
    'Piso del bus': r'(piso de usuarios|piso del área de accesibilidad manchado|piso de la zona preferencial|taraflex)',
    'Rejillas': r'(rejillas de ventiladores y extractores|rejilla de ventilador número uno|rejilla número 1|rejillas de ventilación|rejillas  de ventilado|rrejilla|rejilla)',
    'Panel de instrumentos': r'(millaré sucio|panel de instrumentos|panel de instrumento|tablero interno costa derecho sucio)',
    'Casco': r'(casco trasero)',
    'Pasamanos': r'(pasamanos)',
    'Equipos electronicos': r'(I6012|manipula el celular|Celular|audífonos|audÃ­fonos)',
    'Pare': r'(PARE)',
    'No sujetar el volante': r'(sin sujetar el volante con las dos manos|con una sola mano|soltando el timón|sin las manos en el volante|sin tener las dos manos en el volante)',
    'Reversa en la via': r'(reversa)',
    'Transbordo de pasajeros': r'(trasbordo de usuarios|transbordo de usuarios)',
    'Semaforo en rojo': r'(semáforo en rojo|I6024)',
    'Conduccion peligrosa': r'(conduciendo de manera peligrosa y con una conducta altamente imprudente|transitando por el andÃ©n|transitando por el anden|transita en contravÃ­a|invadiendo carril de sentido contrario|maniobras peligrosas|maniobra de adelantamiento|maniobra peligrosa|manejo peligroso|contra vía|sobre pasar la congestión vehicular|sobrepasos sin aplicar manejo preventivo|conduce sin calzado|manejando peligrosamente el   vehículo|Conducir peligrosamente|Terrible el conductor para manejar|adelantamiento en contravía|evidencia en contravía)',
    'Cinturon de seguridad': r'(cinturón de seguridad|evidenciado con el cinturón bloqueado|cinturón|cinturon de seguridad|cinturo|cinturón de seguridad descolgado)',
    'Plataforma de accesibilidad': r'(personas con discapacidad en mal funcionamiento|plataforma de accesibilidad|plataforma de acceso|plataforma discapacitados|plataforma de discapacitados|plataforma|elevador de discapacitados|elevador de  discapacitados sucio|elevador para discapacitados sucio|rampa de acceso sucia|elevador de acceso de discapacitados|rampa de acceso de discapacitados)',
    'Luces': r'(luces|luz delantera|farola)',
    'Aseo interno': r'(sillas de usuario|sillas usuarios|silla fila 7|aseo interno|aseo  interno|sillas de la fila 4|basura en la parte trasera|claraboya|escalones|sillas de la fila 1 y 2|separación de cabina del  operador manchados|lateral derecho manchado en silla posición 2|lateral derecho junto a la silla de la fila 3 sucio|silla 1 costado derecho sucia|fila 4 costado derecho sucio|panel lateral derecho manchado entre silla 3 y 4|panel lateral interno costado derecho manchado|cerca a la silla de la fila 1 sucio|casco interno trasero sucio|silla 1 derecha sucia|marco de la ventana 1 derecha|casco interno trasero sucio|bocel interno costado derecho sucio|manchado en silla posición 2|palomera casco interno trasero sucia|palomera del casco interno trasero costado derecho sucia|bocel interno costa derecho sucio|casco internado trasero costado izquierdo sucia|palomera del casco interno trasero sucia|panel interno del costado derecho parte trasera sucio|tablero interno costado derecho parte trasera manchado|parte interna del casco trasero sucia|fila 5 derecha sucio|paneles internos en ambos costados parte delantera sucios|panel interno del lado derecho parte delantera sucio|panel interno lado derecho parte delantera sucio|sillas preferenciales del lado derecho parte delantera sucias|palomera trasera casco interno costado izquierdo sucio|espaldares de las sillas preferenciales costado derecho parte central sucios|silla preferencial 4 costado derecho mojada|sillas preferenciales de ambos costados sucias|panel interno del lado derecho parte frontal sucio|sillas de la parte trasera sucias|silla preferencial del lado derecho parte central sucio|boceles internos sucios|casco delantero sucios|silla preferencial lado derecho sucia|cabina de usuarios sucios|parte interna del casco|silla de usuarios  número 5 fila izquierda|silla de usuarios posición 5 izquierda lado pasillo manchada|silla de usuario fila 5 interior manchada|silla de la fila 5 del costado derecho manchada|fila 3 del costado izquierdo manchadapanel interno junto a la silla posición 2 izquierda|paredes interiores manchadas|tableros interno laterales manchados|fila 3 del costado izquierdo manchada|silla posición 2 izquierda|silla de usuarios posición 1 izquierda manchado|pintura debajo silla fila 1 derecha|fila 4 del costado izquierdo manchada|posición 1 lado derecho manchada|mancha en la silla de la fila 4 izquierda|fila 1 costado derecho lado pasillo en mal estado|silla 3 del lado derecho manchado|base de la silla de usuario fila 6 derecha|pegamento en silla 2 fila 2 costado izquierdo|silla de usuarios fila 1 costado derecho manchado|base de la silla de la fila 1 izquierda| sucios|base de las sillas de la fila 3 derecha sucia)', 
    'Puertas bus': r'(puerta 1|puerta de servicio 1|puerta de servicio 1 hoja 1 y 2|puerta 1|puerta de usuarios 2|hojas de puertaspuerta 2 sucia|puerta 2 sucia|puerta de usuarios 1 sucio|hojas de las puertas sucias|puertas parte interna sucia|puerta de servicio 2 sucia|puertas 2 y 3 sucias|hojas de puertas de servicio posición 1|hoja 2 de la puerta 3|tapa superior de la puerta 3 manchados|panel interno del lado derecho parte delantera manchado|puerta número 1 manchado|puerta de servicio 2 manchado)',
    'Espejos': r'(espejo auxiliar)',
    'Equipo SIRCI': r'(compuerta del control SIRCI manchada|manchas en la consola SIRCI|falla SIRCI)',
    'Carril exclusivo': r'(I6008|carril exclusivo|carril rápido|carril central de particulares|transitar por carril central)',
    'Carril incorrecto': r'(tercer carril|carril izquierdo|carril  izquierdo|respectivo carril|iba por la izquierda|carril dos|Carril Izquierdo|carril Izquierdo|Carril izquierdo|Segundo Carril|segundo carril)',
    'No respetar la prelacion': r'(giró de forma inadecuada según la demarcación|No respeta la prelación|no respeta la prelación)',
    'Objetos sobre el millare': r'(millare)',
    'Invasion de espacio peatonal': r'(paso peatonal|cebra peatonal|invade cebra|invadiendo cebra|estacionado sobre el anden)',
    'Uso incorrecto de las direccionales': r'(luz direccional)',
    'Conducir sin mirar adelante': r'(no mirar hacia adelante)',
    'Operador distraido': r'(evidenciado Distraído)',
    'Dificulta la visibilidad': r'(elemento de color plateado en ventana izquierda|elemento de color negro en ventana izquierda)',
    'Giro prohibido': r'(giro prohibido a la izquierda|giro prohibido hacia la izquierda)',
    'Giro inadecuado': r'(giro de forma inadecuada)',
    'Invadir interseccion': r'(invade la interseccion|invadiendo intersección)',
    'Elemento roto': r'(roto|lateral izquierdo rota|faldón lateral derecho rota)',
    'Elemento rayado': r'(rin posición 2 rayado|parachoques trasero lado izquierdo rayados|rayones|parachoques trasero rayado|tablero rayado|rayón en  faldón derecho|rayón en el costado izquierdo|parachoques trasero lado derecho rayado|parachoques delantero rayado|tablero costado izquierdo sección central rayado|rayón en Lamina derecha|faldones rayados)',
    'Atencion en via': r'(atención en vía|I5025)',
    'Agresion verbal': r'(responde de una manera grosera|agresión verbal|contesta de forma agresiva|actitud inadecuado|actitud inadecuada|maltrato verbal|agrediendo verbalmente|I8003|presenta agresión física|conducta inadecuada|agrede fí­sicamente|agrede fí­sica y verbalmente|genera improperios a voz abierta|palabras despectivas y amenazantes)',
    'Salida retrasada': r'(sale tarde)',
    'Alterar el recorrido': r'(I6011|desvía|desviá|desvió|omitiendo 2 paraderos|desvío|omite los paraderos|retorno|retorna|fuera de ruta|no conocer la ruta|recorrido de la ruta|desvío|Alterar el recorrido|no continúa trazado|desvio|I6011|Alterar el recorrido)',
    'Incorrecta aproximacion': r'(aproximación al paradero|correcta aproximación|incorrecta aproximación|ascenso de usuarios a distancia no segura|aproximación adecuada|I6025)',
    'Exceso de velocidad': r'(I6026|exceso de velocidad|exceso dé  velocidad)',
    'Tecla F3': r'(tecla F3|liberando torniquete)',
    'No cumple instrucciones': r'(en los tiempos establecidos para la salidas en servicio|instrucciones|operador hace caso  omiso|omitió la indicación|caso omiso a la instrucción|Por medio de Mensajes a la Unidad Lógica y Fonías|desacato al operador|caso omiso a instrucción|desciende del móvil sin previa autorización|no cumple con las  indicaciones|Operador no acata instrucción|operador en recorrido toma la decisión|operador no aplica la capacitación|desciende del vehículo sin autorización|no cumple con la instrucción)',
    'Conectar dispositivos': r'(I5019|cable USB|dispositivo celular conectado|elemento ajeno a la unidad lógica|componente no SIRCI)',
    'Omision de informacion': r'(información errónea|no brinda información|omite información|no informa novedad|I6020-1|no reporto la novedad|no realiza fonia para reportar la novedad|omisión de inforación|no reporta la novedad|sin realizar ningún reporte|operador no quiso contestar más foní­as|omite el reporte|omite la información|no da ninguna otra información|cambiando la versión|no reporta en el tiempo real|no reporta novedad|reporte oportuno|reporta la novedad de manera errónea|no reportó la novedad|omitió informar|no reporto dicha novedad|Omite Reportar|no reporta  novedad|omisión de información|Omisión de información|no informa al Técnico de Control|no notifico el incidente|omite informar al centro de control|informa que presentaba falla con el rutero y estaba hablando con operaciones para darle solución|omitiendo la información|no realizar fonia y continuar recorrido|omite realizar el reporte al centro de control)',
    'Rutero': r'(I8007-1|rutero|informador|Informador)',
    'Mala conducta': r'(necesidades fisiológicas|realizar compras en turno|compra productos|cámaras obstaculizadas|cámara del operador desenfocada)',
    'Aseo externo': r'(aseo externo|parte externa|aseo exterior|frontal externa|carrocerí­a externa costado derecho sucia|faldón costado derecho sección central delantera sucios|desaseo en la carrocería costado izquierdo|rin posición 2 sucio|carrocería externa sucia|rin posición 2 sucios|rin posición 2 manchado|rin posición 3 sucio|rin posición 6 sucios|rines posición 1, 2 y 3 sucios|casco externo lado izquierdo sucio|rin posición 1 sin aseo|sin aseo en los rines delanteros|rin posición 1 sucio|rin posición 2 y posición 3-4 sin aseo|rines traseros sucios|sin aseo en rin posición 3-4|sin aseo en rin posición 2|desaseo en rin posición 3-4|rines delanteros sin aseo|sin aseo en rines delanteros|rines delanteros sucios|rines delanteros sin aseo|casco externo derecho sucio|techo externo al costado derecho|techo costado derecho parte central sucio|techo al costado derecho|techo costado derecho|aseo deficiente en los rines del costado derecho|carrocerí­a del lado derecho sucia|rin posición uno sin aseo|presencia de moho en el techo|rines en general sin aseo|rin sucio posiciÃ³n 1|carrocería externa costado derecho sucia|faldón izquierdo sucio|sin aseo  en rines delanteros|tapa de inspección trasera izquierda sucia|faldón costado izquierdo sucio sucio|faldón costado derecho sucio|rines posición 1 y 2 sucios|rines posición 1, 3-4 y 5-6|con el aseo deficiente|rin sucio posición 1|carrocería del lado derecho sucia|mampara posición 1 costado derecho manchada|parachoques trasero costado izquierdo manchado con pegante|faldón trasero izquierdo manchado con grasa|faldón del costado derecho parte central|lámina inferior izquierda trasera manchada|parte lateral bodega módulos ITS|mampara de la zona de ayuda viva|rin posición 6 manchado|laterales manchados|Rin posición 3-4 manchado|faldón costado derecho parte central manchado|pegamento en compartimento its|parachoques trasero lado izquierdo golpeado|Tapas de inspección puerta número 2 manchada|rin manchado posición 5-6|rin posición 3 manchado|carrocería externa costado frontal derecho|rin posición 3-4 manchado|parachoques trasero costado derecho manchado|mancha de pegamento en el costado derecho|lamina izquierda inferior trasera manchada|lateral costado izquierdo parte trasera|faldón lateral izquierdo parte central manchado|manchas en el rin posición 2|rin posicion 2 rayado)',
    'Fumar en recorrido': r'(fumando)',
    'Codigo diferente al asignado': r'(del operador del viaje anterior|I6034)',
    'Transitar por lugares no autorizados': r'(transita por la estación de servicio|)',
    'No portar botiquin': r'(de primeros auxilios)',
    'No portar el carnet': r'(carnet de operaciones)',
    'No realiza el recorrido': r'(Operador se niega a realizar el recorrido|negarse a realizar el último servicio|desiste del servicio)',
    'Mantenimiento': r'(testigo ABS con alarma|base de la silla de usuarios|ruido anormal|golpeados|fuga de aire|golpeado|boca rueda posición|abolladura|tapa de inspección|pasa rueda posición|carrocerí­a externa en mal estado|golpe|daño|cinta reflectiva costado derecha seccion central deteriorada|vinilo de hojas del lado izquierdo en mal estado|mal estado|sin la boquilla de uno de los |sin el agua en sistema de limpiabrisas|faldón doblado|boca rueda|bocarueda|tablero izquierdo parte central rayado|rayones en el para choques|faldón izquierdo costado izquierdo rayado|kit de contingencias|fuga de aceite hidráulico|sin un extintor|sin el extintor trasero|puerta 2 desajustado|extintor|Extintor|lavaparabrisas fuera de servicio|propaganda deteriorada|parte central rayada|costado derecho rayado|kit de contingencia|fisura en el parachoques  delantero|Golpes en Boca Rueda|pintura rayada|propaganda no autorizada|luz antiniebla frontal derecha fuera de servicio|calcomanía no autorizada en la mampara|kit contingencia|Golpes en parachoques delantero|señalitica costado izquierdo parte central deteriorada|sin la tapa de protección de la fusilera|Golpe en parachoques delantero|módulo carrocería desprotegido|Rin posición 2 pelado|señalética de timbre despegada|sin el vidrio corredizo de la ventana 1|parachoques delantero Golpeado|filtración de agua en la luz led|carrocería externa costado inferior lateral derecho rota|sin extintor ubicado al lado puerta 2|sin uno de los |sin botiquí­n|sin extintor|sin la boquilla de un extintor|testigo falla gestión térmica|vinilo de hojas verdes del costado derecho deteriorado|testigo forros de freno con alarma de advertencia|testigo forros frenos con alarma de advertencia|testigo forros freno activo|luz delimitadora|fuga de aceite|tablero de instrumento desajustado|tornillos de semi eje|sistema de ABS encendido|columna de dirección|sistema de ABS encendido|testigo de USB sin funcionar|limpiaparabrisas|consola del radio|tablero de instrumentos|luz frontal|vehículo se evidencia sin botiquín|llanta|limpiabrisas|limpia parabrisas|luz antiniebla|sistema contra incendios|fuga|amortiguador|gestión térmica|luz antiniebla|lavaparabrisas|luz exploradora|vehículo se evidencia sin el botiquín|testigo de falla ABS encendido|base de la silla usuario)',
    'Manejo preventivo': r'(No aplica manejo preventivo|manejo preventivo|no aplica manejo preventivo|transitando por el central|invasión de sendero peatonal|transita por Segundo carril)',
    'Boton de panico': r'(obturación de botón de pánico)',
    'Filtraciones': r'(filtración de agua)',
    'Transitar por la demarcacion': r'(achurado)',
    'Elemento en freno': r'(elemento colgado al soporte del freno)',
    'Publicidad no autorizada': r'(publicidad no autorizada|evidencia propaganda)',
    'Falla camara ': r'(proyección de imagen y video borrosa|cámaras)',
    'Trasbordo sin Autorización': r'(realiza trasbordo sin previa autorización|I6033)',
    'Uso incorrecto F2': r'(F2)'}

# Definimos el path de downloads --------------------------------------------------------------
usuario = os.getlogin()
pathDownload = f'C://Users//{usuario}//Downloads//'
namefile = date.today().strftime("%Y%m%d")

# Definicion de la fecha final de descarga ----------------------------------------------------
fecha_from = "2022-04-01"
fecha_to = date.today().strftime("%Y-%m-%d")

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

# Scrapy reporte ICO
def scrapico():
    driver.get("http://transmitools.transmilenio.gov.co/transmireports/mainpage")
    time.sleep(3)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/div/p-select/span').click()
    time.sleep(2)
    driver.find_element(By.XPATH, '//*[@id="pn_id_8_3"]/span').click()
    time.sleep(3)
    elem = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[1]/p-iconfield/p-datepicker/input')
    elem.send_keys(datetime.strptime(fecha_from, '%Y-%m-%d').strftime('%Y-%m-%d'))
    elem.send_keys(Keys.ENTER)
    time.sleep(3)
    elem = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[2]/p-iconfield/p-datepicker/input')
    elem.send_keys(datetime.strptime(fecha_to, '%Y-%m-%d').strftime('%Y-%m-%d'))
    elem.send_keys(Keys.ENTER)
    time.sleep(8)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[2]/section/div/div[1]/section[2]/p-table/div[1]/section/div[3]/button').click()
    time.sleep(10)
    driver.find_element(By.XPATH, '/html/body/div/div/section/button[2]').click()
    time.sleep(45)
    return True

# Scrapy reporte ISV
def scrapisv():
    driver.get("http://transmitools.transmilenio.gov.co/transmireports/mainpage")
    time.sleep(3)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/div/p-select/span').click()
    time.sleep(2)
    driver.find_element(By.XPATH, '//*[@id="pn_id_8_4"]/span').click()
    time.sleep(3)
    elem = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[1]/p-iconfield/p-datepicker/input')
    elem.send_keys(datetime.strptime(fecha_from, '%Y-%m-%d').strftime('%Y-%m-%d'))
    elem.send_keys(Keys.ENTER)
    time.sleep(3)
    elem = driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[1]/section/p-fluid/div/section[2]/div[2]/p-iconfield/p-datepicker/input')
    elem.send_keys(datetime.strptime(fecha_to, '%Y-%m-%d').strftime('%Y-%m-%d'))
    elem.send_keys(Keys.ENTER)
    time.sleep(8)
    driver.find_element(By.XPATH, '/html/body/app-root/app-report/div[1]/section[2]/div[2]/section/div/div[1]/section[2]/p-table/div[1]/section/div[3]/button').click()
    time.sleep(10)
    driver.find_element(By.XPATH, '/html/body/div/div/section/button[2]').click()
    time.sleep(45)
    return True

# Inicializar el WebDriver con las opciones configuradas
driver = webdriver.Chrome(options = chrome_options)
# Descarga de la informacion
login()
scrapico()
scrapisv()
driver.close()

try:
    # Ruta de documentos y lectura de los mismos
    rut = os.path.join(pathDownload, "Consolidado Registros ICO.csv")
    ruth = os.path.join(os.getenv('PAT_PROJECT'), "01 Inputs//Hallazgos Operacionales Servidor.xlsx")
    ruti = os.path.join(pathDownload, "Consolidado Registros ISV.csv")

    Ico = clean_columns(pd.read_csv(os.path.join(pathDownload, "Consolidado Registros ICO.csv"), sep = ';'), case = 'pascal')
    Hallazgo = clean_columns(pd.read_excel(ruth, usecols = ["Tipo Novedad", "Palabra Clave"]), case = 'pascal')

    # Procesamiento de la tabla
    dfico = (Ico.assign(Detalle = lambda df: df["TipoNovedad"].map(categoria))
             .assign(Detalle = lambda df: df["Detalle"].combine_first(df.apply(lambda row: clasificar_descripcion(str(row["Descripcion"]), repl_dict), axis = 1)),
                     FechaNovedad = lambda x: pd.to_datetime(x["FechaNovedad"], yearfirst = True),
                     FechaInicioDp = lambda x: pd.to_datetime(x["FechaInicioDp"], yearfirst = True),
                     NroSaeConductor = lambda x: pd.to_numeric(x["NroSaeConductor"], errors = 'coerce'),
                     CedulaConductor = lambda x: pd.to_numeric(x["NroSaeConductor"], errors = 'coerce'))
                     .merge(Hallazgo, how = "left", on = "TipoNovedad")
                     .assign(InsertDate = datetime.now())
                     .loc[:, ['IdIco', 'Etapa', 'EstadoDp', 'Estado', 'FechaFinDp', 'IdOperador', 
                              'TipoNovedad', 'FechaNovedad', 'Area', 'Direccion', 'Placa', 
                              'NroSaeConductor', 'CedulaConductor', 'NombreConductor', 'Puntos', 
                              'Descripcion', 'Detalle', 'PalabraClave', 'InsertDate']])

    # Eliminacion del archivo
    os.remove(rut)

    # Envio de los datos al DW
    sql_types = {'IdIco': types.INTEGER, 'FechaFinDp': types.DATE, 'IdOperador': types.INTEGER,
                 'FechaNovedad': types.TIMESTAMP, 'NroSaeConductor': types.INTEGER, 'CedulaConductor': types.INTEGER,
                 'Puntos': types.INTEGER, 'InsertDate': types.TIMESTAMP}
    
    dfico.to_sql(table1, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), max_fecha_tabla = dfico['FechaNovedad'].max(), cantidad_registros = len(dfico))
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table1), observacion = str(e))

try:
    Isv = clean_columns(pd.read_csv(os.path.join(pathDownload, "Consolidado Registros ISV.csv"), sep = ';')
                        .assign(InsertDate = datetime.now()), case = 'pascal')

    # Eliminacion del archivo
    os.remove(ruti)

    # Envio de los datos al DW
    sql_types = {'IdIsv': types.INTEGER, 'FechaInicioDp': types.DATE, 'FechaFinDp': types.DATE,
                 'IdSae': types.INTEGER, 'IdOperador': types.INTEGER, 'Instante': types.TIMESTAMP,
                 'NoLesionadosNoVal': types.INTEGER, 'NoLesionadosVal': types.INTEGER, 
                 'NoLesionadosTras': types.INTEGER, 'NoVictimasFat': types.INTEGER, 'InsertDate': types.TIMESTAMP}
    
    Isv.to_sql(table2, schema = 'op', con = fn.cona, if_exists = 'replace', index = False, dtype = sql_types)

    # Registro de la ejecucion del proceso
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), max_fecha_tabla = Isv['FechaFinDp'].max(), cantidad_registros = len(Isv))
    fn.update_process(id_process = IdProceso, engine = fn.enginea)
except Exception as e:
    # registro de la ejecucion del proceso con error
    fn.registrar_actualizacion(engine = fn.enginea, id_proceso = IdProceso, id_tabla = fn.ind_tabla(fn.enginea, table2), observacion = str(e))

print("*" * 95 + "\nProceso:" + pretext + "\nHora Fin: " + start_time.strftime("%Y-%m-%d %H:%M:%S") +
      "\nDuracion: " + str((datetime.now() - start_time).total_seconds()) + "\n" + "*" * 95)
