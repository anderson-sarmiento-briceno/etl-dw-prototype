#**********************************************************************************************
#  @Nombre: Proceso Transformacion DVP
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
suppressWarnings(suppressPackageStartupMessages({
  library(ggmap)        # Geocoding
}))

# Recive argumentos del script de python ------------------------------------------------------
args <- "C:/Users/dev/Documents/01 Modelos/20211230-etl-dwgm"
if (length(args) > 0) {
  setwd(args)
}

test <- getwd()
print(test)

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")
source("Funciones/funciones.R")

# Nombre del proceso para correr en el script -------------------------------------------------
# Titulo que se desplega en el mensaje de slack
IdProceso = 1141
pretext <- paste0(IdProceso, " - Proceso Transformacion EMIC*")
# Función del proceso
ini_proceso(IdProceso = IdProceso, pretext = pretext)

# Path of documents ---------------------------------------------------------------------------
userpc <- "E:\\Drive"
sharepoint <- "\\greenmovil.com.co\\Gestion Mantenimiento - General\\Documentos\\10 Datos\\02 Emic\\"
varados_file <- "\\greenmovil.com.co\\Gestion Mantenimiento - General\\Documentos\\10 Datos\\12 Varados\\"
siapo <- "\\greenmovil.com.co\\Gestion Mantenimiento - General\\Documentos\\10 Datos\\03 Siapo\\"
pathfiles <- str_c(userpc, sharepoint)

# Clave para obtener las coordenadas de las direcciones
ggmap::register_google(key = Sys.getenv("TOK_GEOENCODER"))

#**********************************************************************************************
# Proceso para transformar los datos descargados y cargarlos al DW, el proceso consiste en:
# 1. Leer el ultimo archivo descargado de cada etapa de la plataforma
# 2. Obtener los Ids existentes en el DW de las estapas 4
# 3. Para la etapa 4Filtras los Ids y dejar los no existentes e insertar los nuevos.
# 4. En la etapa 1 remitar los ids que llegaron a la etapa 4 y reemplazar la base de la etapa 1  
#**********************************************************************************************

# Funcion para evualuar existencia del dataframe resultante
get_num_rows <- function(data) {
  if (!exists(data)) {
    return("No hay datos")
  } else {
    return(str_c(dim(get(data))[1], " Rows"))
  }
}

#**********************************************************************************************
# DPV -----------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
## Etapa 4 ------------------------------------------------------------------------------------
# se obtienen los ids existentes del DW
dpv4exist <- odbc::dbGetQuery(cona(), 'select "IdDpv" from op."FactEmicDPV4"')

lastfiledpv4 <- list.files(pathfiles, "DPV_Etapa4", full.names = T) %>% tail(1)

datadpv4 <- fread(lastfiledpv4, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdDpv %in% dpv4exist$IdDpv)

if (dim(datadpv4)[1] > 0) {
  
  datadpv4 <- datadpv4 %>% 
    janitor::remove_empty(which = c("cols")) %>% 
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    mutate_at(vars("CausaDeLaInmovilizacion", "DescripcionDeLaNovedad"), .funs = stringi::stri_trans_general, "Latin-ASCII") %>%
    select("IdDpv", "Etapa",	"Estado",	"FInicioDp", "FCierreDp",	"Empresa", "Fuente", "Placa", 
           "Movil", "FInmovilizacion",	"CausaDeLaInmovilizacion","DescripcionDeLaNovedad") %>% 
    mutate(Detalle = str_extract(DescripcionDeLaNovedad, ".+?(?=\\/)"),
           Ruta = str_extract(DescripcionDeLaNovedad, "(?i)(ruta).+?(?=\\/)"),
           Tabla = str_extract(DescripcionDeLaNovedad, "(?i)(Tabla).+?(?=\\/)"),
           Viaje = str_extract(DescripcionDeLaNovedad, "(?i)(Via).+?(?=\\/)"),
           Direccion = str_extract(DescripcionDeLaNovedad, "(?i)(av|calle|carre|trans|tv|cll|cra).+?(?=\\/)"),
           Operador = str_extract(str_extract(DescripcionDeLaNovedad, "(?i)(Op|op).+?(?=\\/)"), "[:digit:]+")) %>%
    mutate_if("is_character", .funs = str_squish) %>% 
    mutate(Empresa = str_replace_all(Empresa, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           Direccion = str_c(Direccion, ", bogota"),
           InsertDate = format(Sys.time(), tz = "")) %>%
    distinct(IdDpv, .keep_all = T)
  
  latlog <- datadpv4 %>% 
    select(IdDpv, Direccion) %>%
    filter(!is.na(Direccion)) %>%
    ggmap::mutate_geocode(Direccion) %>%
    rename("Latitud" = "lat", "Longitud" = "lon")

  datafinaldpv4 <- datadpv4 %>%
    left_join(latlog, c("IdDpv", "Direccion")) %>% 
    # Se hace una validacion de regex para casos especificos
    mutate(FiltroDetalle = case_when(
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "rute(ro|rro|ros|o)") ~ "Rutero",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "cam(e|a)r(a|as)") ~ "Camaras",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "timbr(e|es)") ~ "Timbres",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "puert(a|as)") ~ "Puertas",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "vidri(o|os)") ~ "Vidrios",
      TRUE ~ Detalle))
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicDPV4"'), datafinaldpv4, append = TRUE)
  
  print("Registros insertados DPV Etapa 4")

  registrar_actualizacion(cona(), 95, IdProceso, max_fecha_tabla = max(datafinaldpv4$FInmovilizacion, na.rm = TRUE), cantidad_registros = nrow(datafinaldpv4))

} else {
  
  print("No hay registros nuevos DPV Etapa 4")
  registrar_actualizacion(cona(), 95, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 95, IdProceso, observacion = e$message)})

tryCatch({
## Etapa 1 ------------------------------------------------------------------------------------
dpv4exist <- odbc::dbGetQuery(cona(), 'select "IdDpv" from op."FactEmicDPV4"')

dpv1exist <- odbc::dbGetQuery(cona(), 'select * from op."FactEmicDPV1"') %>% 
  filter(!IdDpv %in% dpv4exist$IdDpv) %>% 
  # Se Elimian los casos de la etapa 0
  filter(is.na(Etapa)) %>% 
  mutate(InsertDate = as.character(InsertDate))

# Cargamos los datos de la etapa 0
datadpv0 <- list.files(pathfiles, "DPV_Etapa0", full.names = T) %>% tail(1) %>% 
  fread(encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  {if (nrow(.) > 0) janitor::remove_empty(., which = c("cols")) else .} %>% 
  {if (!"Etapa" %in% names(.)) mutate(., Etapa = "Etapa0") else .}

# Proceso de validacion cuando no se tiene varados en etapa 0
if (nrow(datadpv0) > 0) {
  
  datadpv0  <-  datadpv0 %>% 
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>% 
    mutate_at(vars("CausaDeLaInmovilizacion", "DescripcionDeLaNovedad"), .funs = stringi::stri_trans_general, "Latin-ASCII") %>%
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) %>% 
    {if ("CorreccionDeLaNovedad" %in% names(.)) select(., -CorreccionDeLaNovedad) else .}
  
}

lastfiledpv1 <- list.files(pathfiles, "DPV_Etapa1", full.names = T) %>% tail(1)

datadpv1 <- fread(lastfiledpv1, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdDpv %in% dpv1exist$IdDpv)

if (dim(datadpv1)[1] > 0 || dim(datadpv0)[1] > 0) {
  
  datadpv1 <- datadpv1 %>% 
    #janitor::remove_empty(which = c("cols")) %>% 
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    mutate_at(vars("CausaDeLaInmovilizacion", "DescripcionDeLaNovedad"), .funs = stringi::stri_trans_general, "Latin-ASCII") %>%
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) %>% 
    select("IdDpv", "Etapa",	"Estado",	"FInicioDp", "FCierreDp",	"Empresa", "Fuente", "Placa", 
           "Movil", "FInmovilizacion",	"CausaDeLaInmovilizacion","DescripcionDeLaNovedad") %>%
    # Se agrega los casos que estan en informacion habilitada
    {if (nrow(datadpv0) > 0) bind_rows(., datadpv0) else .} %>% 
    mutate(Detalle = str_extract(DescripcionDeLaNovedad, ".+?(?=\\/)"),
           Ruta = str_extract(DescripcionDeLaNovedad, "(?i)(ruta).+?(?=\\/)"),
           Tabla = str_extract(DescripcionDeLaNovedad, "(?i)(Tabla).+?(?=\\/)"),
           Viaje = str_extract(DescripcionDeLaNovedad, "(?i)(Via).+?(?=\\/)"),
           Direccion = str_extract(DescripcionDeLaNovedad, "(?i)(av|calle|carre|trans|tv|cll|cra).+?(?=\\/)"),
           Operador = str_extract(str_extract(DescripcionDeLaNovedad, "(?i)(Op|op).+?(?=\\/)"), "[:digit:]+")) %>%
    mutate_if("is_character", .funs = str_squish) %>% 
    mutate(Empresa = str_replace_all(Empresa, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           Direccion = str_c(Direccion, ", bogota"),
           InsertDate = format(Sys.time(), tz = "")) %>%
    distinct(IdDpv, .keep_all = T)
  
  latlog1 <- datadpv1 %>% 
    select(IdDpv, Direccion) %>%
    filter(!is.na(Direccion)) %>%
    ggmap::mutate_geocode(Direccion) %>%
    rename("Latitud" = "lat", "Longitud" = "lon")
  
  datafinaldpv1 <- datadpv1 %>%
    left_join(latlog1, c("IdDpv", "Direccion")) %>% 
    # Se hace una validacion de regex para casos especificos
    mutate(FiltroDetalle = case_when(
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "rute(ro|rro|ros|o)") ~ "Rutero",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "cam(e|a)r(a|as)") ~ "Camaras",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "timbr(e|es)") ~ "Timbres",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "puert(a|as)") ~ "Puertas",
      stringr::str_detect(stringr::str_to_lower(DescripcionDeLaNovedad), "vidri(o|os)") ~ "Vidrios",
      TRUE ~ Detalle)) %>% 
    # Se agregan los datos existentes del DW en la etapa 1
    rbind(dpv1exist)
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicDPV1"'), datafinaldpv1, overwrite = TRUE,
                     field.types = c(IdDpv = "integer",
                                     Etapa = "text",
                                     Estado = "text",
                                     FInicioDp = "date",
                                     FCierreDp = "date",
                                     Empresa = "text",
                                     Fuente = "text",
                                     Placa = "text",
                                     Movil = "text",
                                     FInmovilizacion = "timestamp",
                                     CausaDeLaInmovilizacion = "text",
                                     DescripcionDeLaNovedad = "text",
                                     Detalle = "text",
                                     Ruta = "text",
                                     Tabla = "text",
                                     Viaje = "text",
                                     Direccion = "text",
                                     FiltroDetalle = "text",
                                     Longitud = "double precision",
                                     Latitud = "double precision",
                                     Operador = "text",
                                     InsertDate = "timestamp"))
  
  print("Registros insertados DPV Etapa 1 y 0")

  registrar_actualizacion(cona(), 94, IdProceso, max_fecha_tabla = max(datafinaldpv1$FInmovilizacion, na.rm = TRUE), cantidad_registros = nrow(datafinaldpv1))
  
} else {
  
  print("No hay registros nuevos DPV Etapa 1 y 0")
  registrar_actualizacion(cona(), 94, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}

}, error = function(e){registrar_actualizacion(cona(), 94, IdProceso, observacion = e$message)})
#**********************************************************************************************
# DPV RCA -------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
  
  varados <- readxl::read_xlsx(str_c(userpc, varados_file, "20260123_Seguimiento_Varados_V2.xlsx"), 
                               sheet = "Base Datos") %>% 
    janitor::clean_names(., case = c("upper_camel")) %>% 
    select(IdDpv, Placa:ElementoQueFallo, Operador, Ruta, DescripcionDeLaRevisionMaximo,
           FechaDeInmovilizacion, FechaDeHabilitacion) %>% 
    mutate(InsertDate = format(Sys.time(), tz = ""),
           FechaDeHabilitacion = as.Date(as.numeric(FechaDeHabilitacion), origin = "1899-12-30"))
  
  odbc::dbWriteTable(cona(), DBI::SQL('ma."FactDPVRca"'), varados, overwrite = TRUE,
                     field.types = c(IdDpv = "integer",
                                     Placa = "text",                
                                     OrdenDeTrabajo = "integer",
                                     CausaVaradoFms = "text",
                                     Categoria = "text",
                                     Sistema = "text",
                                     SubSistema = "text",               
                                     CausaFalla = "text",
                                     PartePrincipal = "text",
                                     ElementoQueFallo = "text",
                                     Operador = "integer",
                                     Ruta = "Text",
                                     DescripcionDeLaRevisionMaximo = "text",
                                     FechaDeInmovilizacion = "timestamp",
                                     FechaDeHabilitacion = "timestamp",
                                     InsertDate = "timestamp"))
  
  registrar_actualizacion(cona(), 93, IdProceso, max_fecha_tabla = max(varados$FechaDeInmovilizacion, na.rm = TRUE), cantidad_registros = nrow(varados))

}, error = function(e) {
    # Esta función se ejecutará si ocurre un error
    print(paste("Error:", e$message))
    registrar_actualizacion(cona(), 93, IdProceso, observacion = e$message)
})

#**********************************************************************************************
# ISV -----------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
## Etapa 4 ------------------------------------------------------------------------------------
# se obtienen los ids existentes del DW
isv4exist <- odbc::dbGetQuery(cona(), 'select "IdIsv" from op."FactEmicISV4"')

lastfileisv4 <- list.files(pathfiles, "ISV_Etapa4", full.names = T) %>% tail(1)

dataisv4 <- vroom::vroom(lastfileisv4, col_types = cols()) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIsv %in% isv4exist$IdIsv)

if (dim(dataisv4)[1] > 0) {

  dataisv4 <- dataisv4 %>%
    janitor::remove_empty(which = c("cols")) %>%
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Estado" %in% names(.)) mutate(., Estado = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    {if (!"NoDeIpat" %in% names(.)) mutate(., NoDeIpat = NA_character_) else .} %>%
    {if (!"ObsTmsa" %in% names(.)) mutate(., ObsTmsa = NA_character_) else .} %>%
    select("IdIsv", "Etapa", "Estado", "FInicioDp", "FCierreDp", "IdSae", "Operador", "Fuente",
           "Inst", "Clase", "Tipo", "DescSuceso", "NoLesionadosNoVal", "NoLesionadosVal",
           "NoLesionadosTras", "NoVictimasFatales", "GravedadEvento", "NoDeIpat", "InstDilig",
           "CreadoPor", "FechaReporte", "TipoServBus", "NoSae", "Placa", "Linea", "Ruta",
           "ObsTmsa", "PersonaRevisaTmsa") %>%
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>%
    mutate_at(vars("FInicioDp", "FCierreDp", "Inst", "FechaReporte"), .funs = as.character) %>%
    mutate(Operador = str_replace_all(NoSae, c("63.*" = "ZMOIII", "67.*" = "ZMOV")),
           InsertDate = format(Sys.time(), tz = "")) %>%
    distinct(IdIsv, .keep_all = T)
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicISV4"'), dataisv4, append = TRUE)
  
  print("Registros insertados ISV Etapa 4")

  registrar_actualizacion(cona(), 101, IdProceso, max_fecha_tabla = max(dataisv4$FInicioDp, na.rm = TRUE), cantidad_registros = nrow(dataisv4))
  
} else {
  
  print("No hay registros nuevos ISV Etapa 4")
  registrar_actualizacion(cona(), 101, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 101, IdProceso, observacion = e$message)})

tryCatch({
## Etapa 1 ------------------------------------------------------------------------------------
isv4exist <- odbc::dbGetQuery(cona(), 'select "IdIsv" from op."FactEmicISV4"')

isv1exist <- odbc::dbGetQuery(cona(), 'select * from op."FactEmicISV1"') %>% 
  filter(!IdIsv %in% isv4exist$IdIsv) %>% 
  mutate_at(vars("FInicioDp", "FCierreDp", "InsertDate", "Inst", "FechaReporte"), .funs = as.character)

lastfileisv1 <- list.files(pathfiles, "ISV_Etapa1", full.names = T) %>% tail(1)

dataisv1 <- vroom::vroom(lastfileisv1, col_types = cols()) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIsv %in% isv1exist$IdIsv)

if (dim(dataisv1)[1] > 0) {
  
  dataisv1 <- dataisv1 %>%
    janitor::clean_names(., case = c("upper_camel")) %>%
    janitor::remove_empty(which = c("cols")) %>%
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"Estado" %in% names(.)) mutate(., Estado = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    {if (!"NoDeIpat" %in% names(.)) mutate(., NoDeIpat = NA_character_) else .} %>%
    {if (!"ObsTmsa" %in% names(.)) mutate(., ObsTmsa = NA_character_) else .} %>%
    select("IdIsv", "Etapa", "Estado", "FInicioDp", "FCierreDp", "IdSae", "Operador", "Fuente",
           "Inst", "Clase", "Tipo", "DescSuceso", "NoLesionadosNoVal", "NoLesionadosVal",
           "NoLesionadosTras", "NoVictimasFatales", "GravedadEvento", "NoDeIpat", "InstDilig",
           "CreadoPor", "FechaReporte", "TipoServBus", "NoSae", "Placa", "Linea", "Ruta",
           "ObsTmsa", "PersonaRevisaTmsa") %>%
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) %>% 
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>%
    mutate_at(vars("FInicioDp", "FCierreDp", "Inst", "FechaReporte"), .funs = as.character) %>%
    mutate(Operador = str_replace_all(NoSae, c(".*63.*" = "ZMOIII", ".*67.*" = "ZMOV")),
           InsertDate = format(Sys.time(), tz = "")) %>%
    distinct(IdIsv, .keep_all = T) %>% 
    # Se agregan los datos existentes del DW en la etapa 1
    rbind(isv1exist)
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicISV1"'), dataisv1, overwrite = TRUE,
                     field.types = c(IdIsv = "integer",
                                     Etapa = "text",
                                     Estado = "text",
                                     FInicioDp = "date",
                                     FCierreDp = "date",
                                     IdSae = "integer",
                                     Operador = "text",
                                     Fuente = "text",
                                     Inst = "timestamp",
                                     Clase = "text",
                                     Tipo = "text",
                                     DescSuceso = "text",
                                     NoLesionadosNoVal = "integer",
                                     NoLesionadosVal = "integer",
                                     NoLesionadosTras = "integer",
                                     NoVictimasFatales = "integer",
                                     GravedadEvento = "text",
                                     NoDeIpat = "text",
                                     InstDilig = "timestamp",
                                     CreadoPor = "text",
                                     FechaReporte = "timestamp",
                                     TipoServBus = "text",
                                     NoSae = "integer",
                                     Placa = "text",
                                     Linea = "text",
                                     Ruta = "text",
                                     ObsTmsa = "text",
                                     PersonaRevisaTmsa = "text",
                                     InsertDate = "timestamp")) 
  
  print("Registros insertados ISV Etapa 1")

  registrar_actualizacion(cona(), 100, IdProceso, max_fecha_tabla = max(dataisv1$FInicioDp, na.rm = TRUE), cantidad_registros = nrow(dataisv1))
  
} else {
  
  print("No hay registros nuevos ISV Etapa 1")
  registrar_actualizacion(cona(), 100, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 100, IdProceso, observacion = e$message)})
#**********************************************************************************************
# ICO -----------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
## Etapa 4 ------------------------------------------------------------------------------------
# se obtienen los ids existentes del DW
ico4exist <- odbc::dbGetQuery(cona(), 'select "IdIco" from op."FactEmicICO4"')

lastfileico4 <- list.files(pathfiles, "ICO_Etapa4", full.names = T) %>% tail(1)

dataico4 <- fread(lastfileico4, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIco %in% ico4exist$IdIco)

if (dim(dataico4)[1] > 0) {
  
  dataico4 <- dataico4 %>% 
    janitor::remove_empty(which = c("cols")) %>% 
    {if (!"IdentificacionConductor" %in% names(.)) mutate(., IdentificacionConductor = NA_integer_) else .} %>% 
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>% 
    mutate_at(vars("FInicioDp", "FCierreDp", "FechaNovedad", "FechaIdentificacion", "FechaNotificacion"), .funs = as.character) %>% 
    mutate(Empresa = str_replace_all(Empresa, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           InsertDate = format(Sys.time(), tz = ""),
           IdentificacionConductor = as.integer(IdentificacionConductor)) %>% 
    distinct(IdIco, .keep_all = T)

    # Insertar los datos al DW
    odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicICO4"'), dataico4, append = TRUE)  
    
    print("Registros insertados ICO Etapa 4")

  registrar_actualizacion(cona(), 97, IdProceso, max_fecha_tabla = max(dataico4$FechaNovedad, na.rm = TRUE), cantidad_registros = nrow(dataico4))

} else {
  
  print("No hay registros nuevos ICO Etapa 4")
  registrar_actualizacion(cona(), 97, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 97, IdProceso, observacion = e$message)})

tryCatch({
## Etapa 1 ------------------------------------------------------------------------------------
ico4exist <- odbc::dbGetQuery(cona(), 'select "IdIco" from op."FactEmicICO4"')

lastfileico1 <- list.files(pathfiles, "ICO_Etapa1", full.names = T) %>% tail(1)

dataico1 <- fread(lastfileico1, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) 


ico1exist <- odbc::dbGetQuery(cona(), 'select * from op."FactEmicICO1"') %>% 
  filter(!IdIco %in% ico4exist$IdIco) %>% 
  mutate_at(vars("FInicioDp", "FCierreDp", "InsertDate", "FechaNovedad", "FechaIdentificacion",
                 "FechaNotificacion"), .funs = as.character) %>% 
  left_join(dataico1 %>%  select("IdIco", "Estado"), by = join_by(IdIco)) %>% 
  mutate(Estado = ifelse(is.na(Estado.y), Estado.x, Estado.y), .keep = c("unused"), .after = "IdNovedad")


dataico1 <- fread(lastfileico1, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIco %in% ico1exist$IdIco)

if (dim(dataico1)[1] > 0) {
  
  dataico1 <- dataico1 %>% 
    select(!starts_with("V")) %>% 
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>% 
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"IdEmpresa" %in% names(.)) mutate(., IdEmpresa = NA_character_) else .} %>%
    {if (!"Departamento" %in% names(.)) mutate(., Departamento = NA_character_) else .} %>%
    {if (!"TotalMaterialVihanet" %in% names(.)) mutate(., TotalMaterialVihanet = NA_character_) else .} %>%
    mutate_at(vars("FInicioDp", "FCierreDp", "FechaNovedad", "FechaIdentificacion",
                   "FechaNotificacion"), .funs = as.character) %>% 
    mutate(Empresa = str_replace_all(Empresa, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           IdEmpresa = ifelse(Empresa == "ZMOIII", 231, 233),
           InsertDate = format(Sys.time(), tz = ""),
           IdentificacionConductor = as.integer(IdentificacionConductor)) %>% 
    rename("TotalMaterialEic" = "TotalMaterial") %>% 
    distinct(IdIco, .keep_all = T) %>% 
    # Se agregan los datos existentes del DW en la etapa 1
    rbind(ico1exist)
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicICO1"'), dataico1, overwrite = TRUE,
                     field.types = c(IdIco = "integer",
                                     Etapa = "text",
                                     IdNovedad = "integer",
                                     Estado = "text",
                                     FInicioDp = "date",
                                     FCierreDp = "date",
                                     IdEmpresa = "integer",
                                     Empresa = "text",
                                     TipoNovedad = "text",
                                     FechaNovedad = "timestamp",
                                     FechaIdentificacion = "timestamp",
                                     FechaNotificacion = "timestamp",
                                     Fuente = "text",
                                     Area = "text",
                                     Departamento = "text",
                                     Linea = "text",
                                     Direccion = "text",
                                     Placa = "text",
                                     Movil = "text",
                                     IdSaeConductor = "integer",
                                     IdentificacionConductor = "integer",
                                     NombreConductor = "text",
                                     Puntos = "integer",
                                     Descripcion = "text",
                                     NoImagenes = "integer",
                                     NoVideos = "integer",
                                     NoFonias = "integer",
                                     Registros = "integer",
                                     InformacionSaeOperador = "integer",
                                     TotalMaterialVihanet = "integer",
                                     TotalMaterialEic = "integer",
                                     LinkEvidencias = "text",
                                     InsertDate = "timestamp"))

  print("Registros insertados ICO Etapa 1")

  registrar_actualizacion(cona(), 96, IdProceso, max_fecha_tabla = max(dataico1$FechaNovedad, na.rm = TRUE), cantidad_registros = nrow(dataico1))
  
} else {
  
  print("No hay registros nuevos ICO Etapa 1")
  registrar_actualizacion(cona(), 96, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)  
}
}, error = function(e){registrar_actualizacion(cona(), 96, IdProceso, observacion = e$message)})
#**********************************************************************************************
# ICS -----------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
## Etapa 4 ------------------------------------------------------------------------------------
# se obtienen los ids existentes del DW
ics4exist <- odbc::dbGetQuery(cona(), 'select "IdFaseV" from op."FactEmicICS4"')

lastfileics4 <- list.files(pathfiles, "ICS_Etapa4", full.names = T) %>% tail(1)

dataics4 <- vroom::vroom(lastfileics4, col_types = cols()) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdFaseV %in% ics4exist$IdFaseV)

if (dim(dataics4)[1] > 0) {
  
  dataics4 <- dataics4 %>% 
    #janitor::remove_empty(which = c("cols")) %>% 
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Estado" %in% names(.)) mutate(., Estado = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    {if (!"TipologiaProgramada" %in% names(.)) mutate(., TipologiaProgramada = NA_character_) else .} %>%
    {if (!"TipologiaEjecutada" %in% names(.)) mutate(., TipologiaEjecutada = NA_character_) else .} %>%
    {if (!"KmEjecutadoSae" %in% names(.)) mutate(., KmEjecutadoSae = NA_real_) else .} %>%
    {if (!"KmAdicionalesAutorizados" %in% names(.)) mutate(., KmAdicionalesAutorizados = NA_real_) else .} %>%
    {if (!"KmTeoricosNoRealizadosPorAccionesODesv" %in% names(.)) mutate(., KmTeoricosNoRealizadosPorAccionesODesv = NA_real_) else .} %>%
    {if (!"KmAnadidosPorAccionesJustificadasODesv" %in% names(.)) mutate(., KmAnadidosPorAccionesJustificadasODesv = NA_real_) else .} %>%
    {if (!"KmEstado5" %in% names(.)) mutate(., KmEstado5 = NA_real_) else .} %>%
    {if (!"KmEstado7" %in% names(.)) mutate(., KmEstado7 = NA_real_) else .} %>%
    {if (!"KmEstado8" %in% names(.)) mutate(., KmEstado8 = NA_real_) else .} %>%
    {if (!"KmDescontadosInicioDeViaje" %in% names(.)) mutate(., KmDescontadosInicioDeViaje = NA_real_) else .} %>%
    {if (!"KmDescontadosFinDeViaje" %in% names(.)) mutate(., KmDescontadosFinDeViaje = NA_real_) else .} %>%
    {if ("KmEliminado" %in% names(.)) rename(., KmEliminados = KmEliminado) else .} %>%
    rename(Justificado = Atribuible) %>%
    select("IdFaseV", "Etapa", "Estado","FechaViaje", "FInicioDp","FCierreDp", "Fuente", "Servicio", 
           "IdViaje", "ViajeLinea", "Coche", "IdOperadorProgramado", "OperadorProgramado",
           "IdOperador", "Operador", "LineaSae", "RutaSae", "Vehiculo", "KmProgramado",
           "KmEjecutadoSae", "KmEfectivamenteEjecutado", "IdValidador", 
           "KmAdicionalesAutorizados", "KmEliminados", "KmTeoricosNoRealizadosPorAccionesODesv",
           "KmAnadidosPorAccionesJustificadasODesv", "KmEstado5", "KmEstado7", "KmEstado8",
           "KmDescontadosInicioDeViaje", "KmDescontadosFinDeViaje", "Cumplimiento", 
           "DespachoInicial", "Planificado", "Eliminado", "NodoParadaInicial", "HoraRef", 
           "HoraTeorica", "HoraReal", "Imputacion", "Motivo", "Justificado", "IdPuntualidad",
           "EvalPuntualidad", "TipologiaProgramada", "TipologiaEjecutada", "KmDefinitivo", 
           "DistSupAcc", "DistAutorizada", "DistNoRealizada") %>% 
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>% 
    mutate_at(vars("FInicioDp", "FCierreDp", "FechaViaje", "HoraRef", "HoraTeorica"), .funs = as.character) %>% 
    mutate(OperadorProgramado = str_replace_all(OperadorProgramado, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           InsertDate = format(Sys.time(), tz = "")) %>% 
    distinct(IdFaseV, .keep_all = T)
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicICS4"'), dataics4, append = TRUE)

  print("Registros insertados ICS Etapa 4")

  registrar_actualizacion(cona(), 99, IdProceso, max_fecha_tabla = max(dataics4$FechaViaje, na.rm = TRUE), cantidad_registros = nrow(dataics4))
  
} else {
  
  print("No hay registros nuevos ICS Etapa 4")
  registrar_actualizacion(cona(), 99, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 99, IdProceso, observacion = e$message)})

tryCatch({
## Etapa 1 ------------------------------------------------------------------------------------
ics4exist <- odbc::dbGetQuery(cona(), 'select "IdFaseV" from op."FactEmicICS4"')

ics1exist <- odbc::dbGetQuery(cona(), 'select * from op."FactEmicICS1"') %>%
  filter(!IdFaseV %in% ics4exist$IdFaseV) %>% 
  mutate_at(vars("FInicioDp", "FCierreDp", "InsertDate", "FechaViaje", "HoraRef",
                 "HoraTeorica", "HoraReal"), .funs = as.character) %>% 
  # Se Elimian los casos de la etapa 0
  filter(is.na(Etapa))

# Se define los tipos de columnas para los archivos del ICS
tipos_col = vroom::cols("IdFaseV" = col_double(),
                        "Fecha Viaje" = col_date(format = "%Y-%m-%d"),
                        "F. Inicio DP" = col_datetime(format = "%Y-%m-%d %H:%M:%S"),
                        "IdViaje" = col_double(),
                        "Id Operador" = col_double(),
                        "Linea SAE" = col_double(),
                        "Despacho Inicial" = col_double(),
                        "Nodo Parada Inicial" = col_double(),
                        "Hora Ref." = col_datetime(format = "%Y-%m-%d %H:%M:%S"),
                        "Hora Real" = col_datetime(format = "%Y-%m-%d %H:%M:%S"),
                        "Imputación" = col_double(),
                        "Motivo" = col_character(),
                        "Justificado" = col_double(),
                        "Id Puntualidad" = col_double())

# Cargamos los datos de la etapa 0
dataics0 <- list.files(pathfiles, "ICS_Etapa0", full.names = T) %>% tail(1) %>% 
  vroom::vroom(col_types = tipos_col) %>% 
  janitor::clean_names(., case = c("upper_camel"))

if (nrow(dataics0) == 0) {
  
  dataics0
  
} else { 
  
  dataics0 <- list.files(pathfiles, "ICS_Etapa0", full.names = T) %>% tail(1) %>% 
    vroom::vroom(col_types = tipos_col) %>% 
    janitor::clean_names(., case = c("upper_camel")) %>% 
    #janitor::remove_empty(which = c("cols")) %>% 
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = "Etapa0") else .} %>% 
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    {if (!"Estado" %in% names(.)) mutate(., Estado = NA_character_) else .} %>% 
    {if (!"KmEjecutadoSae" %in% names(.)) mutate(., KmEjecutadoSae = NA_real_) else .} %>%
    {if (!"KmAdicionalesAutorizados" %in% names(.)) mutate(., KmAdicionalesAutorizados = NA_real_) else .} %>%
    {if (!"KmTeoricosNoRealizadosPorAccionesODesv" %in% names(.)) mutate(., KmTeoricosNoRealizadosPorAccionesODesv = NA_real_) else .} %>%
    {if (!"KmAnadidosPorAccionesJustificadasODesv" %in% names(.)) mutate(., KmAnadidosPorAccionesJustificadasODesv = NA_real_) else .} %>%
    {if (!"KmEstado5" %in% names(.)) mutate(., KmEstado5 = NA_real_) else .} %>%
    {if (!"KmEstado7" %in% names(.)) mutate(., KmEstado7 = NA_real_) else .} %>%
    {if (!"KmEstado8" %in% names(.)) mutate(., KmEstado8 = NA_real_) else .} %>%
    {if (!"KmDescontadosInicioDeViaje" %in% names(.)) mutate(., KmDescontadosInicioDeViaje = NA_real_) else .} %>%
    {if (!"KmDescontadosFinDeViaje" %in% names(.)) mutate(., KmDescontadosFinDeViaje = NA_real_) else .} %>%
    {if ("KmEliminado" %in% names(.)) rename(., KmEliminados = KmEliminado) else .} %>%
    rename(Justificado = Atribuible) %>%
    mutate(KmDefinitivo = KmEfectivamenteEjecutado) %>%
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) %>% 
    mutate(HoraReal = hms::as_hms(HoraReal))
  
}

lastfileics1 <- list.files(pathfiles, "ICS_Etapa1", full.names = T) %>% tail(1)

dataics1 <- vroom::vroom(lastfileics1, col_types = cols()) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdFaseV %in% ics1exist$IdFaseV)

if (dim(dataics1)[1] > 0 || dim(dataics0)[1] > 0) {
  
  dataics1 <- dataics1 %>% 
    #janitor::remove_empty(which = c("cols")) %>% 
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"Estado" %in% names(.)) mutate(., Estado = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    {if (!"TipologiaProgramada" %in% names(.)) mutate(., TipologiaProgramada = NA_character_) else .} %>%
    {if (!"TipologiaEjecutada" %in% names(.)) mutate(., TipologiaEjecutada = NA_character_) else .} %>%
    {if (!"KmEjecutadoSae" %in% names(.)) mutate(., KmEjecutadoSae = NA_real_) else .} %>%
    {if (!"KmAdicionalesAutorizados" %in% names(.)) mutate(., KmAdicionalesAutorizados = NA_real_) else .} %>%
    {if (!"KmTeoricosNoRealizadosPorAccionesODesv" %in% names(.)) mutate(., KmTeoricosNoRealizadosPorAccionesODesv = NA_real_) else .} %>%
    {if (!"KmAnadidosPorAccionesJustificadasODesv" %in% names(.)) mutate(., KmAnadidosPorAccionesJustificadasODesv = NA_real_) else .} %>%
    {if (!"KmEstado5" %in% names(.)) mutate(., KmEstado5 = NA_real_) else .} %>%
    {if (!"KmEstado7" %in% names(.)) mutate(., KmEstado7 = NA_real_) else .} %>%
    {if (!"KmEstado8" %in% names(.)) mutate(., KmEstado8 = NA_real_) else .} %>%
    {if (!"KmDescontadosInicioDeViaje" %in% names(.)) mutate(., KmDescontadosInicioDeViaje = NA_real_) else .} %>%
    {if (!"KmDescontadosFinDeViaje" %in% names(.)) mutate(., KmDescontadosFinDeViaje = NA_real_) else .} %>%
    {if ("KmEliminado" %in% names(.)) rename(., KmEliminados = KmEliminado) else .} %>%
    rename(Justificado = Atribuible) %>%
    mutate(KmDefinitivo = KmEfectivamenteEjecutado) %>% 
    select("IdFaseV", "Etapa", "Estado","FechaViaje", "FInicioDp","FCierreDp", "Fuente", "Servicio", 
           "IdViaje", "ViajeLinea", "Coche", "IdOperadorProgramado", "OperadorProgramado",
           "IdOperador", "Operador", "LineaSae", "RutaSae", "Vehiculo", "KmProgramado", "KmProgramadoBeta",
           "ConciliaKmProgBeta", "KmEjecutadoSae", "KmEfectivamenteEjecutado", "IdValidador", 
           "KmAdicionalesAutorizados", "KmEliminados", "KmTeoricosNoRealizadosPorAccionesODesv",
           "KmAnadidosPorAccionesJustificadasODesv", "KmEstado5", "KmEstado7", "KmEstado8",
           "KmDescontadosInicioDeViaje", "KmDescontadosFinDeViaje", "Cumplimiento", 
           "DespachoInicial", "Planificado", "Eliminado", "NodoParadaInicial", "HoraRef", 
           "HoraTeorica", "HoraReal", "Imputacion", "Motivo", "Justificado", "IdPuntualidad",
           "EvalPuntualidad", "TipologiaProgramada", "TipologiaEjecutada", "KmDefinitivo",
           "DistSupAcc", "DistAutorizada", "DistNoRealizada", "Sustituyente") %>% 
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) %>% 
    {if (nrow(dataics0) > 0) bind_rows(., dataics0) else .} %>% 
    mutate_if("is_character", .funs = stringi::stri_trans_general, "Latin-ASCII") %>% 
    mutate_at(vars("FInicioDp", "FCierreDp", "FechaViaje", "HoraRef", "HoraTeorica", "HoraReal"), .funs = as.character) %>% 
    mutate(OperadorProgramado = str_replace_all(OperadorProgramado, c(".*III.*" = "ZMOIII", ".*GREEN MOVIL.*" = "ZMOV", ".*V.*" = "ZMOV")),
           InsertDate = format(Sys.time(), tz = "")) %>% 
    distinct(IdFaseV, .keep_all = T) %>% 
    # Se agregan los datos existentes del DW en la etapa 1
    rbind(ics1exist) %>% 
    mutate(IdValidador = as.integer(IdValidador))
  
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicICS1"'), dataics1, overwrite = TRUE,
                     field.types = c(IdFaseV = "integer",
                                     Etapa = "text",
                                     Estado = "text",
                                     FechaViaje = "date",
                                     FInicioDp = "date",
                                     FCierreDp = "date",
                                     Fuente = "text",
                                     Servicio = "text",
                                     IdViaje = "integer",
                                     ViajeLinea = "integer",
                                     Coche = "integer",
                                     IdOperadorProgramado = "integer",
                                     OperadorProgramado = "text",
                                     IdOperador = "integer",
                                     Operador = "text",
                                     LineaSae = "integer",
                                     RutaSae = "integer",
                                     Vehiculo = "integer",
                                     KmProgramado = "double precision",
                                     KmEjecutadoSae = "double precision",
                                     KmEfectivamenteEjecutado = "double precision",
                                     IdValidador = "integer",
                                     KmAdicionalesAutorizados = "double precision",
                                     KmEliminados = "double precision",
                                     KmTeoricosNoRealizadosPorAccionesODesv = "double precision",
                                     KmAnadidosPorAccionesJustificadasODesv = "double precision",
                                     KmEstado5 = "double precision",
                                     KmEstado7 = "double precision",
                                     KmEstado8 = "double precision",
                                     KmDescontadosInicioDeViaje = "double precision",
                                     KmDescontadosFinDeViaje = "double precision",
                                     Cumplimiento = "text",
                                     DespachoInicial = "integer",
                                     Planificado = "integer",
                                     Eliminado = "integer",
                                     NodoParadaInicial = "integer",
                                     HoraRef = "timestamp",
                                     HoraTeorica = "timestamp",
                                     HoraReal = "time",
                                     Imputacion = "double precision",
                                     Motivo = "text",
                                     Justificado = "integer",
                                     IdPuntualidad = "integer",
                                     EvalPuntualidad = "text",
                                     TipologiaProgramada = "text",
                                     TipologiaEjecutada = "text",
                                     KmDefinitivo = "double precision",
                                     InsertDate = "timestamp",
                                     DistSupAcc = "double precision",
                                     DistAutorizada = "double precision",
                                     DistNoRealizada = "double precision",
                                     Sustituyente = "integer",
                                     KmProgramadoBeta = "double precision",
                                     ConciliaKmProgBeta = "text"))
  
  print("Registros insertados ICS Etapa 1")

  registrar_actualizacion(cona(), 98, IdProceso, max_fecha_tabla = max(dataics1$FechaViaje, na.rm = TRUE), cantidad_registros = nrow(dataics1))
  
} else {
  
  print("No hay registros nuevos ICS Etapa 1")
  registrar_actualizacion(cona(), 98, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 98, IdProceso, observacion = e$message)})

tryCatch({
## Hallazgo - Proceso de transformacion de archivos -------------------------------------------
datafinalhallazgo <- readxl::read_excel(str_c(userpc, siapo, "FactHallazgos.xlsx")) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  janitor::remove_empty(which = c("cols")) %>% 
  mutate(Concesionario = str_replace_all(Concesionario, c(".*III.*" = "ZMOIII", ".*V.*" = "ZMOV")),
         IdNovedadSae = ifelse(IdNovedadSae == T, 1, IdNovedadSae),
         InsertDate = Sys.time())



### Cargue datos al DW ------------------------------------------------------------------------
odbc::dbWriteTable(cona(), DBI::SQL('op."FactHallazgos"'), datafinalhallazgo, overwrite = TRUE,
                   field.types = c(Id = "integer",
                                   TipoConcesion = "text",
                                   Concesionario = "text",
                                   Zona = "text",
                                   Area = "text",
                                   TipoNovedad = "text",
                                   IdNovedadSae = "integer",
                                   IdNovedad = "integer",
                                   FechaNovedad = "date",
                                   HoraNovedad = "time",
                                   CodigoBus = "text",
                                   Placa = "text",
                                   DescripcionNovedad = "text",
                                   UltimaEtapa = "text",
                                   EstadoUltimaEtapa = "text",
                                   TiempoRestante = "text",
                                   FechaNotificacion = "date",
                                   ObservacionesUltimaEtapa = "text",
                                   FechaHoraRegistroUltimaEtapa = "timestamp",
                                   InsertDate = "timestamp"))
registrar_actualizacion(cona(), 104, IdProceso, max_fecha_tabla = max(datafinalhallazgo$FechaNovedad, na.rm = TRUE), cantidad_registros = nrow(datafinalhallazgo))

}, error = function(e){registrar_actualizacion(cona(), 104, IdProceso, observacion = e$message)})
#**********************************************************************************************
# ITS -----------------------------------------------------------------------------------------
#**********************************************************************************************
tryCatch({
## Etapa 4 ------------------------------------------------------------------------------------
# se obtienen los ids existentes del DW
its4exist <- odbc::dbGetQuery(cona(), 'select "IdIts" from op."FactEmicITS4"')

lastfileits4 <- list.files(pathfiles, "ITS_Etapa4", full.names = T) %>% tail(1)

dataits4 <- fread(lastfileits4, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIts %in% its4exist$IdIts)

if (dim(dataits4)[1] > 0) {
  
  dataits4 <- dataits4 %>% 
    
    janitor::remove_empty(which = c("cols")) %>%
    # se agrega esta funcion para crear las columnas que no aparecen en las diferentes etapas
    {if (!"Etapa" %in% names(.)) mutate(., Etapa = NA_character_) else .} %>%
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>%
    mutate(FCierreDp = as.Date(FCierreDp),
           FRegistro = as.Date(FRegistro),
           InsertDate = format(Sys.time(), tz = ""))
    
  # Insertar los datos al DW
  odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicITS4"'), dataits4, append = TRUE)
  
  print("Registros insertados DPV Etapa 4")
  registrar_actualizacion(cona(), 103, IdProceso, max_fecha_tabla = max(dataits4$FRegistro, na.rm = TRUE), cantidad_registros = nrow(dataits4))
} else {
  print("No hay registros nuevos ITS Etapa 4")
  registrar_actualizacion(cona(), 103, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 103, IdProceso, observacion = e$message)})

tryCatch({
## Etapa 1 ------------------------------------------------------------------------------------
its4exist <- odbc::dbGetQuery(cona(), 'select "IdIts" from op."FactEmicITS4"')

its1exist <- odbc::dbGetQuery(cona(), 'select * from op."FactEmicITS1"') %>% 
  filter(!IdIts %in% its4exist$IdIts) %>% 
  # Se Elimian los casos de la etapa 0
  filter(is.na(Etapa)) %>% 
  mutate(InsertDate = as.character(InsertDate))

# Cargamos los datos de la etapa 0
dataits0 <- list.files(pathfiles, "ITS_Etapa0", full.names = T) %>% tail(1) %>% 
  fread(encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  {if (nrow(.) > 0) janitor::remove_empty(., which = c("cols")) else .} %>% 
  {if (!"Etapa" %in% names(.)) mutate(., Etapa = "Etapa0") else .}

# Proceso de validacion cuando no se tiene datos en etapa 0
if (nrow(dataits0) > 0) {
  
  dataits0  <-  dataits0 %>% 
    {if (!"FCierreDp" %in% names(.)) mutate(., FCierreDp = FInicioDp + days(5)) else .} %>% 
    mutate_at(vars("FInicioDp", "FCierreDp"), .funs = as_date) 
}

lastfileits1 <- list.files(pathfiles, "ITS_Etapa1", full.names = T) %>% tail(1)

dataits1 <- fread(lastfileits1, encoding = "UTF-8", fill = T) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  filter(!IdIts %in% its1exist$IdIts) %>%
  {if (nrow(.) > 0) janitor::remove_empty(., which = c("cols")) else .} %>% 
  {if (!"Etapa" %in% names(.)) mutate(., Etapa = "Etapa1") else .}

if (nrow(dataits1) > 0 | nrow(dataits0) > 0) {
  dataitsfinal <- bind_rows(if (nrow(dataits1) > 0) dataits1 else tibble(),
                            if (nrow(dataits0) > 0) dataits0 else tibble()) %>%
    mutate(FInicioDp = as.Date(FInicioDp),
           FCierreDp = as.Date(FCierreDp),
           FRegistro = as.Date(FRegistro),
           InsertDate = format(Sys.time(), tz = ""))
 
 # Insertar los datos al DW
 odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicITS1"'), dataitsfinal, overwrite = TRUE,
                    field.types = c(IdIts = "integer",
                                    Etapa = "text",
                                    Estado = "text",
                                    FInicioDp = "date",
                                    FCierreDp = "date",
                                    FRegistro = "date",
                                    Ano = "integer",
                                    Mes = "integer",
                                    Dia = "integer",
                                    IdOperador = "integer",
                                    Operador = "text",
                                    Movil = "text",
                                    Placa = "text",
                                    Trv = "integer",
                                    Trs = "integer",
                                    Tev = "integer",
                                    Tes = "integer",
                                    Falgie = "integer",
                                    Ecp = "integer",
                                    Ep = "integer",
                                    Falgcpas = "integer",
                                    Vr = "integer",
                                    Pe = "integer",
                                    Cc = "integer",
                                    Falgbpan = "integer",
                                    Me = "integer",
                                    Te = "integer",
                                    Ttr = "integer",
                                    Falgim = "integer",
                                    InsertDate = "timestamp"))
 
  print("Registros insertados ITS Etapa 1 y 0")
  registrar_actualizacion(cona(), 102, IdProceso, max_fecha_tabla = max(dataitsfinal$FRegistro, na.rm = TRUE), cantidad_registros = nrow(dataitsfinal))
} else {
  
  print("No hay registros nuevos ITS Etapa 1 y 0")
  registrar_actualizacion(cona(), 102, IdProceso, max_fecha_tabla = Sys.Date(), cantidad_registros = 0)
}
}, error = function(e){registrar_actualizacion(cona(), 102, IdProceso, observacion = e$message)})

actualizar_fecha_proceso(cona(), IdProceso)
# Ejecucion de los proceso de calculo del emic ------------------------------------------------
source("C:/Users/dev/Documents/01 Modelos/20211230-etl-dwgm/ETL-FactCalculoEMIC.R", chdir = T)
